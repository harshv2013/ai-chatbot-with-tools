"""
Azure OpenAI MCP Server
Provides access to Azure OpenAI capabilities through MCP protocol.
"""
import asyncio
import os
import json
from typing import Any, Optional
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Load environment variables
load_dotenv()

# Initialize server
app = Server("azure-openai")

# Azure OpenAI client
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Configuration
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
MAX_TOKENS = int(os.getenv("MAX_TOKENS_PER_REQUEST", "4000"))

# Conversation history storage (in-memory)
conversation_history = {}

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Define all available Azure OpenAI tools"""
    return [
        Tool(
            name="chat_completion",
            description="Send a message to Azure OpenAI and get a response",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to Azure OpenAI"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt to guide the AI's behavior"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for response randomness (0.0-2.0)",
                        "minimum": 0.0,
                        "maximum": 2.0,
                        "default": 0.7
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "minimum": 1,
                        "maximum": 4000,
                        "default": 1000
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="chat_with_context",
            description="Have a multi-turn conversation with Azure OpenAI (maintains context)",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Your message"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to maintain context"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature (0.0-2.0)",
                        "default": 0.7
                    }
                },
                "required": ["message", "conversation_id"]
            }
        ),
        Tool(
            name="summarize_text",
            description="Summarize a long text using Azure OpenAI",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to summarize"
                    },
                    "length": {
                        "type": "string",
                        "enum": ["brief", "moderate", "detailed"],
                        "description": "Summary length",
                        "default": "moderate"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="analyze_sentiment",
            description="Analyze sentiment of text (positive, negative, neutral)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="generate_code",
            description="Generate code based on requirements",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "Description of what code should do"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (e.g., python, javascript, java)"
                    },
                    "include_comments": {
                        "type": "boolean",
                        "description": "Include code comments",
                        "default": True
                    }
                },
                "required": ["requirements", "language"]
            }
        ),
        Tool(
            name="extract_keywords",
            description="Extract key topics and keywords from text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    },
                    "max_keywords": {
                        "type": "integer",
                        "description": "Maximum number of keywords to extract",
                        "default": 10
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="translate_text",
            description="Translate text to another language",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to translate"
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Target language (e.g., Spanish, French, Japanese)"
                    },
                    "source_language": {
                        "type": "string",
                        "description": "Source language (optional, auto-detect if not provided)"
                    }
                },
                "required": ["text", "target_language"]
            }
        ),
        Tool(
            name="explain_concept",
            description="Get a detailed explanation of a concept",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Concept to explain"
                    },
                    "audience": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "expert"],
                        "description": "Target audience level",
                        "default": "intermediate"
                    }
                },
                "required": ["concept"]
            }
        ),
        Tool(
            name="clear_conversation",
            description="Clear conversation history for a specific conversation ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to clear"
                    }
                },
                "required": ["conversation_id"]
            }
        )
    ]

async def call_azure_openai(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """Helper function to call Azure OpenAI"""
    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Azure OpenAI API error: {str(e)}")

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        # Chat Completion
        if name == "chat_completion":
            message = arguments["message"]
            system_prompt = arguments.get("system_prompt", "You are a helpful AI assistant.")
            temperature = arguments.get("temperature", 0.7)
            max_tokens = arguments.get("max_tokens", 1000)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            response = await call_azure_openai(messages, temperature, max_tokens)
            
            return [TextContent(
                type="text",
                text=f"**Azure OpenAI Response:**\n\n{response}"
            )]
        
        # Chat with Context
        elif name == "chat_with_context":
            message = arguments["message"]
            conversation_id = arguments["conversation_id"]
            temperature = arguments.get("temperature", 0.7)
            
            # Initialize conversation if needed
            if conversation_id not in conversation_history:
                conversation_history[conversation_id] = [
                    {"role": "system", "content": "You are a helpful AI assistant."}
                ]
            
            # Add user message
            conversation_history[conversation_id].append(
                {"role": "user", "content": message}
            )
            
            # Get response
            response = await call_azure_openai(
                conversation_history[conversation_id],
                temperature
            )
            
            # Add assistant response to history
            conversation_history[conversation_id].append(
                {"role": "assistant", "content": response}
            )
            
            return [TextContent(
                type="text",
                text=f"**Response (Conversation: {conversation_id}):**\n\n{response}\n\n*Messages in this conversation: {len(conversation_history[conversation_id]) - 1}*"
            )]
        
        # Summarize Text
        elif name == "summarize_text":
            text = arguments["text"]
            length = arguments.get("length", "moderate")
            
            length_instructions = {
                "brief": "in 2-3 sentences",
                "moderate": "in a short paragraph",
                "detailed": "in detail with key points"
            }
            
            messages = [
                {"role": "system", "content": "You are an expert at summarizing text."},
                {"role": "user", "content": f"Summarize the following text {length_instructions[length]}:\n\n{text}"}
            ]
            
            response = await call_azure_openai(messages)
            
            return [TextContent(
                type="text",
                text=f"**Summary ({length}):**\n\n{response}"
            )]
        
        # Analyze Sentiment
        elif name == "analyze_sentiment":
            text = arguments["text"]
            
            messages = [
                {"role": "system", "content": "You are an expert at sentiment analysis. Respond with the sentiment (positive, negative, or neutral) followed by a brief explanation."},
                {"role": "user", "content": f"Analyze the sentiment of this text:\n\n{text}"}
            ]
            
            response = await call_azure_openai(messages)
            
            return [TextContent(
                type="text",
                text=f"**Sentiment Analysis:**\n\n{response}"
            )]
        
        # Generate Code
        elif name == "generate_code":
            requirements = arguments["requirements"]
            language = arguments["language"]
            include_comments = arguments.get("include_comments", True)
            
            comment_instruction = "with detailed comments" if include_comments else "without comments"
            
            messages = [
                {"role": "system", "content": f"You are an expert {language} programmer. Generate clean, efficient code."},
                {"role": "user", "content": f"Write {language} code {comment_instruction} that does the following:\n\n{requirements}"}
            ]
            
            response = await call_azure_openai(messages, max_tokens=2000)
            
            return [TextContent(
                type="text",
                text=f"**Generated {language.title()} Code:**\n\n{response}"
            )]
        
        # Extract Keywords
        elif name == "extract_keywords":
            text = arguments["text"]
            max_keywords = arguments.get("max_keywords", 10)
            
            messages = [
                {"role": "system", "content": "You are an expert at extracting key topics and keywords from text."},
                {"role": "user", "content": f"Extract up to {max_keywords} key topics/keywords from this text. List them as bullet points:\n\n{text}"}
            ]
            
            response = await call_azure_openai(messages)
            
            return [TextContent(
                type="text",
                text=f"**Extracted Keywords:**\n\n{response}"
            )]
        
        # Translate Text
        elif name == "translate_text":
            text = arguments["text"]
            target_language = arguments["target_language"]
            source_language = arguments.get("source_language", "auto-detect")
            
            source_info = f"from {source_language}" if source_language != "auto-detect" else ""
            
            messages = [
                {"role": "system", "content": "You are an expert translator."},
                {"role": "user", "content": f"Translate the following text {source_info} to {target_language}:\n\n{text}"}
            ]
            
            response = await call_azure_openai(messages)
            
            return [TextContent(
                type="text",
                text=f"**Translation ({target_language}):**\n\n{response}"
            )]
        
        # Explain Concept
        elif name == "explain_concept":
            concept = arguments["concept"]
            audience = arguments.get("audience", "intermediate")
            
            audience_instructions = {
                "beginner": "Explain in simple terms for someone new to this topic.",
                "intermediate": "Provide a comprehensive explanation with examples.",
                "expert": "Provide an in-depth technical explanation."
            }
            
            messages = [
                {"role": "system", "content": f"You are an expert educator. {audience_instructions[audience]}"},
                {"role": "user", "content": f"Explain: {concept}"}
            ]
            
            response = await call_azure_openai(messages, max_tokens=2000)
            
            return [TextContent(
                type="text",
                text=f"**Explanation ({audience} level):**\n\n{response}"
            )]
        
        # Clear Conversation
        elif name == "clear_conversation":
            conversation_id = arguments["conversation_id"]
            
            if conversation_id in conversation_history:
                message_count = len(conversation_history[conversation_id]) - 1
                del conversation_history[conversation_id]
                return [TextContent(
                    type="text",
                    text=f"✓ Cleared conversation '{conversation_id}' ({message_count} messages)"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"No conversation found with ID '{conversation_id}'"
                )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())