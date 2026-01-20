"""
MCP Client for integrating MCP servers with the chatbot
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import os


class MCPClient:
    """Client to interact with MCP servers"""
    
    def __init__(self):
        self.servers = {}
        self.processes = {}
        
    async def start_server(self, name: str, script_path: str, python_path: str = None):
        """Start an MCP server process"""
        if python_path is None:
            python_path = "python3"
        
        try:
            # For now, we'll import and use the MCP servers directly
            # This is simpler than managing subprocess communication
            print(f"Initializing MCP server: {name}")
            self.servers[name] = {
                'name': name,
                'script': script_path,
                'status': 'running'
            }
            return True
        except Exception as e:
            print(f"Error starting server {name}: {e}")
            return False
    
    async def stop_server(self, name: str):
        """Stop an MCP server"""
        if name in self.processes:
            self.processes[name].terminate()
            del self.processes[name]
            del self.servers[name]
    
    def get_available_servers(self) -> List[str]:
        """Get list of running servers"""
        return list(self.servers.keys())
    
    def is_server_running(self, name: str) -> bool:
        """Check if server is running"""
        return name in self.servers


# Tool implementations (direct Python versions of MCP tools)
class FileSystemTools:
    """File system operations"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def list_files(self, pattern: str = "*") -> str:
        """List files in directory"""
        try:
            files = [f.name for f in self.base_path.glob(pattern) if f.is_file()]
            if not files:
                return f"No files found matching pattern: {pattern}"
            return f"Files found ({len(files)}):\n" + "\n".join(f"  - {f}" for f in sorted(files))
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    def read_file(self, filename: str) -> str:
        """Read file contents"""
        try:
            path = self.base_path / filename
            
            # Security check
            if not str(path.resolve()).startswith(str(self.base_path.resolve())):
                return "Error: Access denied to file outside allowed directory"
            
            if not path.exists():
                return f"Error: File '{filename}' not found"
            
            content = path.read_text(encoding='utf-8')
            return f"Contents of {filename}:\n\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def search_content(self, query: str) -> str:
        """Search for text in files"""
        try:
            query_lower = query.lower()
            results = []
            
            for file in self.base_path.rglob("*"):
                if file.is_file():
                    try:
                        content = file.read_text(encoding='utf-8')
                        if query_lower in content.lower():
                            lines = content.split('\n')
                            matching_lines = [
                                f"  Line {i+1}: {line.strip()}" 
                                for i, line in enumerate(lines) 
                                if query_lower in line.lower()
                            ]
                            results.append(
                                f"{file.relative_to(self.base_path)}:\n" + 
                                "\n".join(matching_lines[:3])
                            )
                    except:
                        pass
            
            if not results:
                return f"No matches found for: {query}"
            
            return f"Found '{query}' in {len(results)} file(s):\n\n" + "\n\n".join(results)
        except Exception as e:
            return f"Error searching: {str(e)}"


class CalculatorTools:
    """Calculator operations"""
    
    @staticmethod
    def add(*numbers: float) -> str:
        """Add numbers"""
        result = sum(numbers)
        return f"Result: {result}\nCalculation: {' + '.join(map(str, numbers))} = {result}"
    
    @staticmethod
    def subtract(a: float, b: float) -> str:
        """Subtract numbers"""
        result = a - b
        return f"Result: {result}\nCalculation: {a} - {b} = {result}"
    
    @staticmethod
    def multiply(*numbers: float) -> str:
        """Multiply numbers"""
        result = 1
        for num in numbers:
            result *= num
        return f"Result: {result}\nCalculation: {' × '.join(map(str, numbers))} = {result}"
    
    @staticmethod
    def divide(a: float, b: float, precision: int = 2) -> str:
        """Divide numbers"""
        if b == 0:
            return "Error: Division by zero"
        result = round(a / b, precision)
        return f"Result: {result}\nCalculation: {a} ÷ {b} = {result}"
    
    @staticmethod
    def factorial(n: int) -> str:
        """Calculate factorial"""
        import math
        if n < 0:
            return "Error: Factorial undefined for negative numbers"
        if n > 20:
            return "Error: Factorial limited to n ≤ 20"
        
        result = math.factorial(n)
        if n <= 5:
            steps = " × ".join(str(i) for i in range(1, n + 1)) if n > 0 else "1"
            calc = f"{n}! = {steps} = {result}"
        else:
            calc = f"{n}! = {result}"
        
        return f"Result: {result}\nCalculation: {calc}"
    
    @staticmethod
    def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
        """Convert temperature"""
        if from_unit == to_unit:
            return f"Result: {value} {to_unit}\n(No conversion needed)"
        
        # Convert to Celsius first
        if from_unit == "F":
            celsius = (value - 32) * 5/9
        elif from_unit == "K":
            celsius = value - 273.15
        else:
            celsius = value
        
        # Convert to target
        if to_unit == "F":
            result = celsius * 9/5 + 32
        elif to_unit == "K":
            result = celsius + 273.15
        else:
            result = celsius
        
        return f"Result: {result:.2f} {to_unit}\nConversion: {value} {from_unit} = {result:.2f} {to_unit}"
    
    @staticmethod
    def convert_distance(value: float, from_unit: str, to_unit: str) -> str:
        """Convert distance"""
        if from_unit == to_unit:
            return f"Result: {value} {to_unit}\n(No conversion needed)"
        
        # Conversion to meters
        to_meters = {"m": 1.0, "ft": 0.3048, "mi": 1609.34, "km": 1000.0}
        from_meters = {"m": 1.0, "ft": 3.28084, "mi": 0.000621371, "km": 0.001}
        
        meters = value * to_meters[from_unit]
        result = meters * from_meters[to_unit]
        
        unit_names = {"m": "meters", "ft": "feet", "mi": "miles", "km": "kilometers"}
        
        return f"""Result: {result:.4f} {to_unit}

Conversion: {value} {unit_names[from_unit]} = {result:.4f} {unit_names[to_unit]}"""


class MCPToolRegistry:
    """Registry for all available MCP tools"""
    
    def __init__(self, file_base_path: str = "./test_files"):
        self.fs_tools = FileSystemTools(file_base_path)
        self.calc_tools = CalculatorTools()
        self.available_tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Any]:
        """Register all available tools"""
        return {
            # File System Tools
            "list_files": {
                "function": self.fs_tools.list_files,
                "description": "List files in the test directory",
                "parameters": ["pattern (optional)"]
            },
            "read_file": {
                "function": self.fs_tools.read_file,
                "description": "Read contents of a file",
                "parameters": ["filename"]
            },
            "search_files": {
                "function": self.fs_tools.search_content,
                "description": "Search for text in files",
                "parameters": ["query"]
            },
            
            # Calculator Tools
            "add": {
                "function": self.calc_tools.add,
                "description": "Add numbers",
                "parameters": ["*numbers"]
            },
            "subtract": {
                "function": self.calc_tools.subtract,
                "description": "Subtract two numbers",
                "parameters": ["a", "b"]
            },
            "multiply": {
                "function": self.calc_tools.multiply,
                "description": "Multiply numbers",
                "parameters": ["*numbers"]
            },
            "divide": {
                "function": self.calc_tools.divide,
                "description": "Divide two numbers",
                "parameters": ["a", "b", "precision (optional)"]
            },
            "factorial": {
                "function": self.calc_tools.factorial,
                "description": "Calculate factorial",
                "parameters": ["n"]
            },
            "convert_temperature": {
                "function": self.calc_tools.convert_temperature,
                "description": "Convert temperature (C, F, K)",
                "parameters": ["value", "from_unit", "to_unit"]
            },
            "convert_distance": {
                "function": self.calc_tools.convert_distance,
                "description": "Convert distance (m, ft, mi, km)",
                "parameters": ["value", "from_unit", "to_unit"]
            }
        }
    
    def get_tool(self, tool_name: str):
        """Get a specific tool"""
        return self.available_tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Get all available tools"""
        return self.available_tools
    
    def get_tools_description(self) -> str:
        """Get formatted description of all tools"""
        descriptions = []
        for name, info in self.available_tools.items():
            params = ", ".join(info["parameters"])
            descriptions.append(f"- {name}({params}): {info['description']}")
        return "\n".join(descriptions)