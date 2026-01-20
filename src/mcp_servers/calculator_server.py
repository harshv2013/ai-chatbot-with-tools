"""
MCP Calculator Server
Provides mathematical operations and conversions as tools.
"""
import asyncio
import math
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize server
app = Server("calculator")

# Store calculation history (in-memory for this session)
calculation_history = []

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Define all available calculator tools"""
    return [
        # Basic arithmetic
        Tool(
            name="add",
            description="Add two or more numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numbers to add",
                        "minItems": 2
                    }
                },
                "required": ["numbers"]
            }
        ),
        Tool(
            name="subtract",
            description="Subtract second number from first number",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number (minuend)"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number (subtrahend)"
                    }
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="multiply",
            description="Multiply two or more numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numbers to multiply",
                        "minItems": 2
                    }
                },
                "required": ["numbers"]
            }
        ),
        Tool(
            name="divide",
            description="Divide first number by second number",
            inputSchema={
                "type": "object",
                "properties": {
                    "dividend": {
                        "type": "number",
                        "description": "Number to be divided"
                    },
                    "divisor": {
                        "type": "number",
                        "description": "Number to divide by"
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Number of decimal places (default: 2)",
                        "default": 2
                    }
                },
                "required": ["dividend", "divisor"]
            }
        ),
        
        # Advanced operations
        Tool(
            name="power",
            description="Raise a number to a power (a^b)",
            inputSchema={
                "type": "object",
                "properties": {
                    "base": {
                        "type": "number",
                        "description": "Base number"
                    },
                    "exponent": {
                        "type": "number",
                        "description": "Exponent"
                    }
                },
                "required": ["base", "exponent"]
            }
        ),
        Tool(
            name="square_root",
            description="Calculate square root of a number",
            inputSchema={
                "type": "object",
                "properties": {
                    "number": {
                        "type": "number",
                        "description": "Number to find square root of",
                        "minimum": 0
                    }
                },
                "required": ["number"]
            }
        ),
        Tool(
            name="percentage",
            description="Calculate percentage (what is X% of Y?)",
            inputSchema={
                "type": "object",
                "properties": {
                    "percent": {
                        "type": "number",
                        "description": "Percentage value"
                    },
                    "of": {
                        "type": "number",
                        "description": "Base number"
                    }
                },
                "required": ["percent", "of"]
            }
        ),
        Tool(
            name="factorial",
            description="Calculate factorial of a number (n!). Factorial is the product of all positive integers less than or equal to n.",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Non-negative integer to calculate factorial of (0-20)",
                        "minimum": 0,
                        "maximum": 20
                    }
                },
                "required": ["n"]
            }
        ),
                
        # Statistical operations
        Tool(
            name="average",
            description="Calculate the average (mean) of numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numbers",
                        "minItems": 1
                    }
                },
                "required": ["numbers"]
            }
        ),
        Tool(
            name="statistics",
            description="Calculate comprehensive statistics (mean, median, min, max, sum)",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numbers",
                        "minItems": 1
                    }
                },
                "required": ["numbers"]
            }
        ),
        
        # Trigonometry
        Tool(
            name="trigonometry",
            description="Calculate sin, cos, or tan of an angle",
            inputSchema={
                "type": "object",
                "properties": {
                    "function": {
                        "type": "string",
                        "enum": ["sin", "cos", "tan"],
                        "description": "Trigonometric function to use"
                    },
                    "angle": {
                        "type": "number",
                        "description": "Angle value"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["degrees", "radians"],
                        "description": "Unit of angle (default: degrees)",
                        "default": "degrees"
                    }
                },
                "required": ["function", "angle"]
            }
        ),
        
        # Unit conversions
        Tool(
            name="convert_temperature",
            description="Convert temperature between Celsius, Fahrenheit, and Kelvin",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "Temperature value"
                    },
                    "from_unit": {
                        "type": "string",
                        "enum": ["C", "F", "K"],
                        "description": "Source unit (C=Celsius, F=Fahrenheit, K=Kelvin)"
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["C", "F", "K"],
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        ),
        
        # History
        Tool(
            name="history",
            description="View calculation history for this session",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent calculations to show (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="clear_history",
            description="Clear the calculation history",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # ADD CURRENCY CONVERTER HERE ↓
        Tool(
            name="convert_currency",
            description="Convert between USD, EUR, and GBP using current exchange rates",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount to convert",
                        "minimum": 0
                    },
                    "from_currency": {
                        "type": "string",
                        "enum": ["USD", "EUR", "GBP"],
                        "description": "Source currency (USD=US Dollar, EUR=Euro, GBP=British Pound)"
                    },
                    "to_currency": {
                        "type": "string",
                        "enum": ["USD", "EUR", "GBP"],
                        "description": "Target currency"
                    }
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        ),
        # DISTANCE CONVERTER
        Tool(
            name="convert_distance",
            description="Convert between meters, feet, miles, and kilometers",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "Distance value to convert",
                        "minimum": 0
                    },
                    "from_unit": {
                        "type": "string",
                        "enum": ["m", "ft", "mi", "km"],
                        "description": "Source unit (m=meters, ft=feet, mi=miles, km=kilometers)"
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["m", "ft", "mi", "km"],
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        )
    ]

def add_to_history(operation: str, result: Any):
    """Add a calculation to history"""
    calculation_history.append({
        "operation": operation,
        "result": result
    })
    # Keep only last 100 calculations
    if len(calculation_history) > 100:
        calculation_history.pop(0)

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        # Basic arithmetic
        if name == "add":
            numbers = arguments["numbers"]
            result = sum(numbers)
            add_to_history(f"add({', '.join(map(str, numbers))})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {' + '.join(map(str, numbers))} = {result}"
            )]
        
        elif name == "subtract":
            a = arguments["a"]
            b = arguments["b"]
            result = a - b
            add_to_history(f"subtract({a}, {b})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {a} - {b} = {result}"
            )]
        
        elif name == "multiply":
            numbers = arguments["numbers"]
            result = 1
            for num in numbers:
                result *= num
            add_to_history(f"multiply({', '.join(map(str, numbers))})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {' × '.join(map(str, numbers))} = {result}"
            )]
        
        elif name == "divide":
            dividend = arguments["dividend"]
            divisor = arguments["divisor"]
            precision = arguments.get("precision", 2)
            
            if divisor == 0:
                return [TextContent(
                    type="text",
                    text="Error: Division by zero is undefined"
                )]
            
            result = dividend / divisor
            formatted_result = round(result, precision)
            add_to_history(f"divide({dividend}, {divisor})", result)
            
            return [TextContent(
                type="text",
                text=f"Result: {formatted_result}\n\nCalculation: {dividend} ÷ {divisor} = {formatted_result}"
            )]
        
        # Advanced operations
        elif name == "power":
            base = arguments["base"]
            exponent = arguments["exponent"]
            result = base ** exponent
            add_to_history(f"power({base}, {exponent})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {base}^{exponent} = {result}"
            )]
        
        elif name == "square_root":
            number = arguments["number"]
            if number < 0:
                return [TextContent(
                    type="text",
                    text="Error: Cannot calculate square root of negative number"
                )]
            result = math.sqrt(number)
            add_to_history(f"sqrt({number})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: √{number} = {result}"
            )]
        
        elif name == "percentage":
            percent = arguments["percent"]
            of = arguments["of"]
            result = (percent / 100) * of
            add_to_history(f"percentage({percent}, {of})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {percent}% of {of} = {result}"
            )]
        
        elif name == "factorial":
            n = arguments["n"]
            
            # Validate input
            if n < 0:
                return [TextContent(
                    type="text",
                    text="Error: Factorial is not defined for negative numbers"
                )]
            
            if n > 20:
                return [TextContent(
                    type="text",
                    text="Error: Factorial limited to n ≤ 20 to prevent overflow"
                )]
            
            # Calculate factorial
            result = math.factorial(n)
            
            # Create step-by-step calculation for small numbers
            if n <= 5:
                steps = " × ".join(str(i) for i in range(1, n + 1)) if n > 0 else "1"
                calculation_text = f"{n}! = {steps} = {result}"
            else:
                calculation_text = f"{n}! = {result}"
            
            add_to_history(f"factorial({n})", result)
            
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nCalculation: {calculation_text}"
            )]
        
        # Statistical operations
        elif name == "average":
            numbers = arguments["numbers"]
            result = sum(numbers) / len(numbers)
            add_to_history(f"average({', '.join(map(str, numbers))})", result)
            return [TextContent(
                type="text",
                text=f"Result: {result}\n\nAverage of {len(numbers)} numbers: {result}"
            )]
        
        elif name == "statistics":
            numbers = sorted(arguments["numbers"])
            n = len(numbers)
            
            stats = {
                "count": n,
                "sum": sum(numbers),
                "mean": sum(numbers) / n,
                "median": numbers[n//2] if n % 2 == 1 else (numbers[n//2-1] + numbers[n//2]) / 2,
                "min": min(numbers),
                "max": max(numbers),
                "range": max(numbers) - min(numbers)
            }
            
            add_to_history(f"statistics({len(numbers)} numbers)", stats)
            
            return [TextContent(
                type="text",
                text=f"""Statistics for {n} numbers:
                    Count:  {stats['count']}
                    Sum:    {stats['sum']}
                    Mean:   {stats['mean']:.4f}
                    Median: {stats['median']}
                    Min:    {stats['min']}
                    Max:    {stats['max']}
                    Range:  {stats['range']}"""
                    )]
        
        # Trigonometry
        elif name == "trigonometry":
            function = arguments["function"]
            angle = arguments["angle"]
            unit = arguments.get("unit", "degrees")
            
            # Convert to radians if needed
            if unit == "degrees":
                angle_rad = math.radians(angle)
            else:
                angle_rad = angle
            
            # Calculate
            if function == "sin":
                result = math.sin(angle_rad)
            elif function == "cos":
                result = math.cos(angle_rad)
            else:  # tan
                result = math.tan(angle_rad)
            
            add_to_history(f"{function}({angle} {unit})", result)
            
            return [TextContent(
                type="text",
                text=f"Result: {result:.6f}\n\nCalculation: {function}({angle}°) = {result:.6f}"
            )]
        
        # Temperature conversion
        elif name == "convert_temperature":
            value = arguments["value"]
            from_unit = arguments["from_unit"]
            to_unit = arguments["to_unit"]
            
            if from_unit == to_unit:
                return [TextContent(
                    type="text",
                    text=f"Result: {value} {to_unit}\n\n(No conversion needed)"
                )]
            
            # Convert to Celsius first
            if from_unit == "F":
                celsius = (value - 32) * 5/9
            elif from_unit == "K":
                celsius = value - 273.15
            else:
                celsius = value
            
            # Convert from Celsius to target
            if to_unit == "F":
                result = celsius * 9/5 + 32
            elif to_unit == "K":
                result = celsius + 273.15
            else:
                result = celsius
            
            add_to_history(f"convert({value}{from_unit} to {to_unit})", result)
            
            return [TextContent(
                type="text",
                text=f"Result: {result:.2f} {to_unit}\n\nConversion: {value} {from_unit} = {result:.2f} {to_unit}"
            )]
        
        # History management
        elif name == "history":
            limit = arguments.get("limit", 10)
            
            if not calculation_history:
                return [TextContent(
                    type="text",
                    text="No calculation history available."
                )]
            
            recent = calculation_history[-limit:]
            history_text = "Calculation History:\n\n"
            for i, calc in enumerate(recent, 1):
                history_text += f"{i}. {calc['operation']} = {calc['result']}\n"
            
            return [TextContent(type="text", text=history_text)]
        
        elif name == "clear_history":
            count = len(calculation_history)
            calculation_history.clear()
            return [TextContent(
                type="text",
                text=f"Cleared {count} calculations from history."
            )]

        # ADD CURRENCY CONVERTER HANDLER HERE ↓
        elif name == "convert_currency":
            amount = arguments["amount"]
            from_currency = arguments["from_currency"]
            to_currency = arguments["to_currency"]
            
            # Exchange rates (hardcoded for learning - as of Jan 2025 approximations)
            # Base: 1 USD =
            exchange_rates = {
                "USD": {"USD": 1.0, "EUR": 0.92, "GBP": 0.79},
                "EUR": {"USD": 1.09, "EUR": 1.0, "GBP": 0.86},
                "GBP": {"USD": 1.27, "EUR": 1.16, "GBP": 1.0}
            }
            
            if from_currency == to_currency:
                return [TextContent(
                    type="text",
                    text=f"Result: {amount:.2f} {to_currency}\n\n(No conversion needed)"
                )]
            
            # Get the exchange rate
            rate = exchange_rates[from_currency][to_currency]
            result = amount * rate
            
            add_to_history(f"convert({amount} {from_currency} to {to_currency})", result)
            
            # Create formatted output
            symbol_map = {"USD": "$", "EUR": "€", "GBP": "£"}
            from_symbol = symbol_map[from_currency]
            to_symbol = symbol_map[to_currency]
            
            return [TextContent(
                type="text",
                text=f"""Result: {to_symbol}{result:.2f} {to_currency}

        Conversion: {from_symbol}{amount:.2f} {from_currency} = {to_symbol}{result:.2f} {to_currency}
        Exchange Rate: 1 {from_currency} = {rate:.4f} {to_currency}

        Note: Using approximate exchange rates for demonstration."""
            )]
        
        # DISTANCE CONVERTER 
        elif name == "convert_distance":
            value = arguments["value"]
            from_unit = arguments["from_unit"]
            to_unit = arguments["to_unit"]
            
            if from_unit == to_unit:
                return [TextContent(
                    type="text",
                    text=f"Result: {value} {to_unit}\n\n(No conversion needed)"
                )]
            
            # Conversion factors to meters (base unit)
            to_meters = {
                "m": 1.0,           # meters to meters
                "ft": 0.3048,       # feet to meters
                "mi": 1609.34,      # miles to meters
                "km": 1000.0        # kilometers to meters
            }
            
            # Conversion factors from meters
            from_meters = {
                "m": 1.0,           # meters to meters
                "ft": 3.28084,      # meters to feet
                "mi": 0.000621371,  # meters to miles
                "km": 0.001         # meters to kilometers
            }
            
            # Convert to meters first, then to target unit
            meters = value * to_meters[from_unit]
            result = meters * from_meters[to_unit]
            
            add_to_history(f"convert({value} {from_unit} to {to_unit})", result)
            
            # Unit full names for better display
            unit_names = {
                "m": "meters",
                "ft": "feet",
                "mi": "miles",
                "km": "kilometers"
            }
            
            return [TextContent(
                type="text",
                text=f"""Result: {result:.4f} {to_unit}

        Conversion: {value} {unit_names[from_unit]} = {result:.4f} {unit_names[to_unit]}

        Common conversions from {value} {unit_names[from_unit]}:
        • Meters: {meters:.2f} m
        • Feet: {meters * from_meters['ft']:.2f} ft
        • Miles: {meters * from_meters['mi']:.4f} mi
        • Kilometers: {meters * from_meters['km']:.4f} km"""
            )]
                        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

async def main():
    """Run the MCP calculator server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())