"""
Azure OpenAI Client with function calling support
"""
import os
import json
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()


class AzureOpenAIClient:
    """Client for Azure OpenAI with function calling"""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.conversation_history = []
        self.max_history = int(os.getenv("MAX_HISTORY", "50"))
    
    def get_function_definitions(self, tool_registry) -> List[Dict]:
        """Convert MCP tools to OpenAI function definitions"""
        functions = []
        
        for tool_name, tool_info in tool_registry.get_all_tools().items():
            # Create function definition
            function = {
                "name": tool_name,
                "description": tool_info["description"],
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Add parameters (simplified - you can enhance this)
            for param in tool_info["parameters"]:
                param_name = param.replace(" (optional)", "").replace("*", "")
                is_required = "(optional)" not in param
                
                function["parameters"]["properties"][param_name] = {
                    "type": "number" if param_name in ["a", "b", "value", "n", "precision"] else "string",
                    "description": f"Parameter: {param}"
                }
                
                if is_required and not param.startswith("*"):
                    function["parameters"]["required"].append(param_name)
            
            functions.append(function)
        
        return functions
    
    async def chat(
        self,
        message: str,
        tool_registry=None,
        use_tools: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Send message and get response with optional tool usage"""
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Prepare messages
        messages = self._prepare_messages()
        
        # Prepare function calling if tools available
        tools = None
        if use_tools and tool_registry:
            function_defs = self.get_function_definitions(tool_registry)
            tools = [{"type": "function", "function": func} for func in function_defs]
        
        try:
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
            
            assistant_message = response.choices[0].message
            
            # Check if tool was called
            if assistant_message.tool_calls:
                return await self._handle_tool_calls(
                    assistant_message,
                    tool_registry,
                    temperature,
                    max_tokens
                )
            else:
                # Regular response
                response_text = assistant_message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                return response_text
                
        except Exception as e:
            error_msg = f"Error calling Azure OpenAI: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def _handle_tool_calls(
        self,
        assistant_message,
        tool_registry,
        temperature,
        max_tokens
    ) -> str:
        """Handle function/tool calls"""
        
        # Add assistant message with tool calls
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in assistant_message.tool_calls
            ]
        })
        
        # Execute each tool call
        tool_results = []
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 Calling tool: {function_name} with args: {function_args}")
            
            # Get and execute the tool
            tool = tool_registry.get_tool(function_name)
            if tool:
                try:
                    # Call the function
                    if function_name in ["add", "multiply"]:
                        # Variable arguments
                        result = tool["function"](*function_args.get("numbers", []))
                    else:
                        # Regular arguments
                        result = tool["function"](**function_args)
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": result
                    })
                except Exception as e:
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error executing tool: {str(e)}"
                    })
            else:
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"Tool '{function_name}' not found"
                })
        
        # Add tool results to conversation
        self.conversation_history.extend(tool_results)
        
        # Get final response from model
        messages = self._prepare_messages()
        
        final_response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        final_text = final_response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": final_text
        })
        
        return final_text
    
    def _prepare_messages(self) -> List[Dict]:
        """Prepare messages for API call"""
        # System message
        system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant with access to various tools.

            Available tools:
            - File operations (list_files, read_file, search_files)
            - Calculator operations (add, subtract, multiply, divide, factorial)
            - Unit conversions (convert_temperature, convert_distance)

            When a user asks you to perform operations that these tools can handle, use the appropriate tool.
            Always provide clear, helpful responses and explain what you're doing."""
                    }
        
        messages = [system_message]
        
        # Add conversation history (limit to max_history)
        if len(self.conversation_history) > self.max_history:
            messages.extend(self.conversation_history[-self.max_history:])
        else:
            messages.extend(self.conversation_history)
        
        return messages
    
    def clear_history(self):
        """Clear conversation history"""
        count = len(self.conversation_history)
        self.conversation_history = []
        return count
    
    def get_history_length(self) -> int:
        """Get number of messages in history"""
        return len(self.conversation_history)