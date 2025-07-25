#!/usr/bin/env python3
"""Debug parser output to see what's being extracted"""

import asyncio
import json
import sys
from pathlib import Path

# Add the knowledge_graphs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'knowledge_graphs'))

from ts_script_analyzer import TypeScriptScriptAnalyzer

async def debug_parser_output():
    analyzer = TypeScriptScriptAnalyzer()
    
    # Test file with zod imports
    test_file = "test_validation/correct_form_implementation.tsx"
    result = await analyzer.analyze_script(test_file)
    
    print("Imports:")
    print(json.dumps(result['imports'], indent=2))
    
    print("\nMethod calls:")
    for mc in result['method_calls']:
        if 'z.' in f"{mc.get('object', '')}.{mc.get('method', '')}":
            print(f"  Object: {mc.get('object')}, Method: {mc.get('method')}, Line: {mc.get('line')}")
    
    print("\nFunction calls:")
    for fc in result['function_calls']:
        if 'z.' in fc.get('name', ''):
            print(f"  Name: {fc.get('name')}, Line: {fc.get('line')}")

if __name__ == "__main__":
    asyncio.run(debug_parser_output())