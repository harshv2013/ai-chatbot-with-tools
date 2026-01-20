"""
MCP File System Server
A simple file system server that provides read access to files in the test_files directory.
"""
import asyncio
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Initialize server
app = Server("mcp-filesystem")

# Define allowed directory - relative to this script's location
SCRIPT_DIR = Path(__file__).parent.parent  # Go up to mcp-file-server/
ALLOWED_DIR = SCRIPT_DIR / "test_files"
print("ALLOWED_DIR : ",ALLOWED_DIR)
# Ensure directory exists
ALLOWED_DIR.mkdir(exist_ok=True)

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List all files in the test_files directory"""
    resources = []
    
    if not ALLOWED_DIR.exists():
        return resources
    
    for file in ALLOWED_DIR.rglob("*"):
        if file.is_file():
            # Determine MIME type based on extension
            mime_type = "text/plain"
            if file.suffix == ".json":
                mime_type = "application/json"
            elif file.suffix == ".md":
                mime_type = "text/markdown"
            elif file.suffix == ".csv":
                mime_type = "text/csv"
            
            resources.append(
                Resource(
                    uri=f"file://{file}",
                    name=str(file.relative_to(ALLOWED_DIR)),
                    mimeType=mime_type,
                    description=f"File: {file.name}"
                )
            )
    
    return resources

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a file's contents"""
    # Extract path from URI
    path = Path(uri.replace("file://", ""))
    
    # Security check: ensure file is within allowed directory
    if not str(path.resolve()).startswith(str(ALLOWED_DIR.resolve())):
        raise ValueError(f"Access denied: file outside allowed directory")
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Read and return content
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # If it's binary, return base64 encoded
        import base64
        return base64.b64encode(path.read_bytes()).decode('utf-8')

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_files",
            description="List all files in the test_files directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files (e.g., '*.txt')"
                    }
                }
            }
        ),
        Tool(
            name="read_file",
            description="Read the contents of a specific file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to read (relative to test_files/)"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="write_file",
            description="Create or overwrite a file with content",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to create"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["filename", "content"]
            }
        ),
        Tool(
            name="search_content",
            description="Search for text within all files",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="file_stats",
            description="Get statistics about a file (size, lines, words)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file"
                    }
                },
                "required": ["filename"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    if name == "list_files":
        pattern = arguments.get("pattern", "*")
        files = [
            str(f.relative_to(ALLOWED_DIR)) 
            for f in ALLOWED_DIR.glob(pattern) 
            if f.is_file()
        ]
        
        if not files:
            return [TextContent(
                type="text",
                text=f"No files found matching pattern: {pattern}"
            )]
        
        return [TextContent(
            type="text",
            text=f"Files found ({len(files)}):\n" + "\n".join(f"  - {f}" for f in sorted(files))
        )]
    
    elif name == "read_file":
        filename = arguments["filename"]
        path = ALLOWED_DIR / filename
        
        # Security check
        if not str(path.resolve()).startswith(str(ALLOWED_DIR.resolve())):
            return [TextContent(
                type="text",
                text=f"Error: Access denied to file outside test_files directory"
            )]
        
        if not path.exists():
            return [TextContent(
                type="text",
                text=f"Error: File '{filename}' not found"
            )]
        
        try:
            content = path.read_text(encoding='utf-8')
            return [TextContent(
                type="text",
                text=f"Contents of {filename}:\n\n{content}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading file: {str(e)}"
            )]
        
    elif name == "write_file":
        filename = arguments["filename"]
        content = arguments["content"]
        path = ALLOWED_DIR / filename
        
        # Security check
        if not str(path.resolve()).startswith(str(ALLOWED_DIR.resolve())):
            return [TextContent(
                type="text",
                text=f"Error: Cannot write outside test_files directory"
            )]
        
        try:
            path.write_text(content, encoding='utf-8')
            return [TextContent(
                type="text",
                text=f"✓ Successfully wrote {len(content)} characters to {filename}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error writing file: {str(e)}"
            )]
    
    elif name == "search_content":
        query = arguments["query"].lower()
        results = []
        
        for file in ALLOWED_DIR.rglob("*"):
            if file.is_file():
                try:
                    content = file.read_text(encoding='utf-8')
                    if query in content.lower():
                        # Find matching lines
                        lines = content.split('\n')
                        matching_lines = [
                            f"  Line {i+1}: {line.strip()}" 
                            for i, line in enumerate(lines) 
                            if query in line.lower()
                        ]
                        results.append(
                            f"{file.relative_to(ALLOWED_DIR)}:\n" + 
                            "\n".join(matching_lines[:3])  # Show first 3 matches
                        )
                except:
                    pass  # Skip files that can't be read as text
        
        if not results:
            return [TextContent(
                type="text",
                text=f"No matches found for: {query}"
            )]
        
        return [TextContent(
            type="text",
            text=f"Found '{query}' in {len(results)} file(s):\n\n" + "\n\n".join(results)
        )]
    
    elif name == "file_stats":
        filename = arguments["filename"]
        path = ALLOWED_DIR / filename
        
        if not path.exists():
            return [TextContent(type="text", text=f"Error: File not found")]
        
        content = path.read_text(encoding='utf-8')
        stats = {
            "size_bytes": path.stat().st_size,
            "lines": len(content.split('\n')),
            "words": len(content.split()),
            "characters": len(content)
        }
        
        return [TextContent(
            type="text",
            text=f"Statistics for {filename}:\n" +
                f"  Size: {stats['size_bytes']} bytes\n" +
                f"  Lines: {stats['lines']}\n" +
                f"  Words: {stats['words']}\n" +
                f"  Characters: {stats['characters']}"
        )]
    
    raise ValueError(f"Unknown tool: {name}")

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