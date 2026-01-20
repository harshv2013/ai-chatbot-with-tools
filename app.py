"""
Gradio MCP Chatbot with Azure OpenAI
A powerful chatbot interface with MCP tool integration
"""
import gradio as gr
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from src.azure_openai_client import AzureOpenAIClient
from src.mcp_client import MCPClient, MCPToolRegistry

# Load environment
load_dotenv()

# Initialize clients
ai_client = AzureOpenAIClient()
mcp_client = MCPClient()
tool_registry = MCPToolRegistry(
    file_base_path=os.getenv("FILE_SERVER_PATH", "./test_files")
)

# Custom CSS
custom_css = """
.gradio-container {
    font-family: 'Inter', sans-serif;
}
.chat-message {
    padding: 10px;
    border-radius: 8px;
    margin: 5px 0;
}
"""

async def process_message(message: str, history: list, use_tools: bool, temperature: float):
    if not message.strip():
        return history, ""

    history = history or []

    # Append user message
    history.append({
        "role": "user",
        "content": message
    })

    try:
        response = await ai_client.chat(
            message=message,
            tool_registry=tool_registry if use_tools else None,
            use_tools=use_tools,
            temperature=temperature
        )

        history.append({
            "role": "assistant",
            "content": response
        })

    except Exception as e:
        history.append({
            "role": "assistant",
            "content": f"❌ Error:\n{str(e)}"
        })

    return history, ""


def clear_conversation():
    """Clear conversation history"""
    count = ai_client.clear_history()
    return [], f"Cleared {count} messages from history"


def get_stats():
    """Get chatbot statistics"""
    history_length = ai_client.get_history_length()
    servers = mcp_client.get_available_servers()
    tools = len(tool_registry.get_all_tools())
    
    return f"""### 📊 Statistics
- **Messages in history:** {history_length}
- **Available tools:** {tools}
- **MCP Servers:** {len(servers)} initialized
- **Status:** ✓ Running
"""


def get_available_tools():
    """Get list of available tools"""
    return f"""### 🛠️ Available Tools

{tool_registry.get_tools_description()}

**Usage Examples:**
- "List all files in the directory"
- "Read the contents of test1.txt"
- "Calculate 25 + 75 + 100"
- "What's the factorial of 8?"
- "Convert 100 Fahrenheit to Celsius"
- "Convert 5 miles to kilometers"
"""


# Create Gradio Interface
app = gr.Blocks(title="MCP Chatbot")

with app:
    # Apply custom CSS
    gr.HTML(f"<style>{custom_css}</style>")
    
    gr.Markdown("""
    # 🤖 MCP Chatbot with Azure OpenAI
    
    A powerful chatbot with integrated tools for file operations, calculations, and unit conversions.
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            # Chat interface
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                show_label=True
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message here...",
                    show_label=False,
                    scale=4,
                    container=False
                )
                submit_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
                use_tools_cb = gr.Checkbox(
                    label="Enable Tools",
                    value=True,
                    info="Allow AI to use MCP tools"
                )
                temperature_slider = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=0.7,
                    step=0.1,
                    label="Temperature",
                    info="Higher = more creative"
                )
        
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ Control Panel")
            
            stats_display = gr.Markdown(get_stats())
            refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")
            
            gr.Markdown("---")
            
            with gr.Accordion("📖 Available Tools", open=False):
                tools_display = gr.Markdown(get_available_tools())
            
            with gr.Accordion("💡 Quick Examples", open=False):
                gr.Markdown("""
                **File Operations:**
                - List all files
                - Read test1.txt
                - Search for "sample" in files
                
                **Calculations:**
                - Add 10, 20, and 30
                - Calculate factorial of 5
                - What's 144 divided by 12?
                
                **Conversions:**
                - Convert 32°F to Celsius
                - Convert 1 mile to meters
                
                **General:**
                - Explain quantum computing
                - Write Python code to sort a list
                """)
            
            gr.Markdown("---")
            
            status_text = gr.Textbox(
                label="Status",
                value="✓ Ready",
                interactive=False
            )
    
    # Event handlers
    # def submit_message(message, history, use_tools, temperature):
    #     return asyncio.run(process_message(message, history, use_tools, temperature))
    def submit_message(message, history, use_tools, temperature):
        return asyncio.run(
            process_message(message, history, use_tools, temperature)
        )

    submit_btn.click(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb, temperature_slider],
        outputs=[chatbot, msg]
    )
    
    msg.submit(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb, temperature_slider],
        outputs=[chatbot, msg]
    )
    
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot, status_text]
    )
    
    refresh_stats_btn.click(
        fn=get_stats,
        outputs=stats_display
    )
    
    gr.Markdown("""
    ---
    ### 🔐 Privacy & Security
    - All conversations are processed through Azure OpenAI
    - File access is restricted to the designated directory
    - No data is stored permanently
    
    ### 📚 Documentation
    Built with Gradio, Azure OpenAI, and Model Context Protocol (MCP)
    """)


if __name__ == "__main__":
    # Initialize MCP servers (optional, for display)
    asyncio.run(mcp_client.start_server(
        "file-system",
        "src/mcp_servers/fs_server.py"
    ))
    asyncio.run(mcp_client.start_server(
        "calculator",
        "src/mcp_servers/calculator_server.py"
    ))
    
    # Launch Gradio
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("APP_PORT", "7860")),
        share=False,
        show_error=True,
        css=custom_css
    )