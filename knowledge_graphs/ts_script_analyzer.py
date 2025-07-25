"""
TypeScript/JavaScript Script Analyzer for AI Hallucination Detection

Analyzes AI-generated TypeScript/JavaScript/React code to extract:
- Imports and their usage
- Component instantiations and their props
- Function calls and their parameters
- Hook usage patterns
- Type usage and interface implementations

Uses the TypeScript Compiler API via our parser service for accurate parsing.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

# Import our TypeScript parser client
from ts_parser_client import TypeScriptParserService

logger = logging.getLogger(__name__)


class TypeScriptScriptAnalyzer:
    """Analyzes TypeScript/JavaScript scripts for validation against knowledge graph"""
    
    def __init__(self):
        self.imports = {}  # module -> imported items
        self.component_uses = []  # List of component instantiations
        self.function_calls = []  # List of function calls
        self.class_instantiations = []  # List of class instantiations
        self.hook_uses = []  # List of React hook calls
        self.parse_result = None  # Store the parse result for later use
        self.type_uses = []  # List of type/interface uses
        self.jsx_elements = []  # List of JSX elements used
        self.method_calls = []  # List of method calls
        self.property_accesses = []  # List of property accesses
        self.parser_service = None
        
    async def analyze_script(self, script_path: str) -> Dict[str, Any]:
        """Analyze a TypeScript/JavaScript script and extract usage patterns"""
        logger.info(f"Analyzing script: {script_path}")
        
        # Reset state
        self._reset_state()
        
        try:
            # Read the file
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize parser service if needed
            if not self.parser_service:
                self.parser_service = TypeScriptParserService()
                
            async with self.parser_service as parser:
                # Parse the file using TypeScript Compiler API
                try:
                    self.parse_result = await parser.parse_file(content, script_path)
                    
                    if self.parse_result.get('error'):
                        logger.error(f"Parse error: {self.parse_result['error']}")
                        return self._create_error_result(script_path, self.parse_result['error'])
                    
                    # Extract information from the parsed result
                    await self._extract_from_ast(self.parse_result)
                    
                except Exception as e:
                    logger.error(f"Failed to parse script: {e}")
                    return self._create_error_result(script_path, str(e))
            
            # Return the analysis result with local definitions
            return {
                'script_path': script_path,
                'imports': self.imports,
                'component_uses': self.component_uses,
                'function_calls': self.function_calls,
                'class_instantiations': self.class_instantiations,
                'method_calls': self.method_calls,
                'property_accesses': self.property_accesses,
                'hook_uses': self.hook_uses,
                'type_uses': self.type_uses,
                'jsx_elements': self.jsx_elements,
                'parse_errors': [],
                # Include local definitions for the validator
                'components': self.parse_result.get('components', []) if self.parse_result else [],
                'functions': self.parse_result.get('functions', []) if self.parse_result else [],
                'types': self.parse_result.get('types', []) if self.parse_result else [],
                'interfaces': self.parse_result.get('interfaces', []) if self.parse_result else [],
                'classes': self.parse_result.get('classes', []) if self.parse_result else [],
                'variables': self.parse_result.get('variables', []) if self.parse_result else []
            }
            
        except Exception as e:
            logger.error(f"Error analyzing script: {e}")
            return self._create_error_result(script_path, str(e))
    
    def analyze_script_sync(self, script_path: str) -> Dict[str, Any]:
        """Synchronous wrapper for analyze_script"""
        return asyncio.run(self.analyze_script(script_path))
    
    async def _extract_from_ast(self, parse_result: Dict[str, Any]):
        """Extract usage patterns from the parsed AST"""
        # Extract imports
        for imp in parse_result.get('imports', []):
            module = imp.get('module', '')
            if module:
                self.imports[module] = self.imports.get(module, [])
                
                # Handle different import types
                if imp.get('default'):
                    self.imports[module].append(imp['default'])
                
                if imp.get('namespace'):
                    self.imports[module].append(f"* as {imp['namespace']}")
                
                for named in imp.get('named', []):
                    name = named.get('name', '')
                    alias = named.get('alias')
                    if alias:
                        self.imports[module].append(f"{name} as {alias}")
                    else:
                        self.imports[module].append(name)
        
        # Extract USAGE PATTERNS from enhanced parser
        
        # Extract function calls (actual calls, not declarations)
        for call in parse_result.get('functionCalls', []):
            self.function_calls.append({
                'name': call.get('function', call.get('name', 'Unknown')),  # Check both 'function' and 'name' fields
                'arguments': call.get('arguments', []),
                'line': call.get('line', 0),
                'isComplex': call.get('isComplex', False)
            })
        
        # Extract method calls
        for call in parse_result.get('methodCalls', []):
            self.method_calls.append({
                'object': call.get('object', 'Unknown'),
                'method': call.get('method', 'Unknown'),
                'arguments': call.get('arguments', []),
                'line': call.get('line', 0)
            })
        
        # Extract property accesses
        for access in parse_result.get('propertyAccesses', []):
            self.property_accesses.append({
                'object': access.get('object', 'Unknown'),
                'property': access.get('property', 'Unknown'),
                'line': access.get('line', 0)
            })
        
        # Extract constructor calls (class instantiations)
        for ctor in parse_result.get('constructorCalls', []):
            self.class_instantiations.append({
                'name': ctor.get('className', ctor.get('class', 'Unknown')),  # Check both 'className' and 'class' fields
                'arguments': ctor.get('arguments', []),
                'line': ctor.get('line', 0)
            })
        
        # Extract JSX elements usage
        for jsx in parse_result.get('jsxElements', []):
            self.jsx_elements.append({
                'name': jsx.get('tagName', 'Unknown'),  # Changed from 'name' to 'tagName'
                'props': jsx.get('props', []),  # Props is already a list
                'line': jsx.get('line', 0),
                'selfClosing': jsx.get('selfClosing', False),
                'isCustomComponent': jsx.get('isCustomComponent', False)
            })
            
            # Also track as component use if it's a custom component
            if jsx.get('isCustomComponent', False):
                self.component_uses.append({
                    'name': jsx.get('tagName', 'Unknown'),
                    'type': 'jsx',
                    'props': jsx.get('props', []),
                    'line': jsx.get('line', 0)
                })
        
        # Extract hook uses (already captured in functionCalls with 'use' prefix)
        for hook in parse_result.get('hooks', []):
            self.hook_uses.append({
                'name': hook.get('name', 'Unknown'),
                'line': hook.get('line', 0)
            })
        
        # Extract type references (usage of types/interfaces)
        for typeRef in parse_result.get('typeReferences', []):
            self.type_uses.append({
                'name': typeRef.get('name', 'Unknown'),
                'kind': 'reference',
                'line': typeRef.get('line', 0)
            })
        
        # Also extract declarations for context
        
        # Components declared
        for component in parse_result.get('components', []):
            # Track hooks used in this component
            for hook in component.get('hooks', []):
                if not any(h['name'] == hook['name'] and h['line'] == hook['line'] for h in self.hook_uses):
                    self.hook_uses.append({
                        'name': hook.get('name', 'Unknown'),
                        'component': component.get('name', 'Unknown'),
                        'line': hook.get('line', 0)
                    })
        
        # Class declarations (for extends validation)
        for cls in parse_result.get('classes', []):
            if cls.get('extends'):
                # Track this as a type use
                self.type_uses.append({
                    'name': cls.get('extends', 'Unknown'),
                    'kind': 'extends',
                    'line': cls.get('line', 0)
                })
            
            for impl in cls.get('implements', []):
                self.type_uses.append({
                    'name': impl,
                    'kind': 'implements',
                    'line': cls.get('line', 0)
                })
        
        # Interface declarations (for extends validation)
        for interface in parse_result.get('interfaces', []):
            for ext in interface.get('extends', []):
                self.type_uses.append({
                    'name': ext,
                    'kind': 'extends',
                    'line': interface.get('line', 0)
                })
    
    def _reset_state(self):
        """Reset analyzer state"""
        self.imports = {}
        self.component_uses = []
        self.function_calls = []
        self.class_instantiations = []
        self.hook_uses = []
        self.type_uses = []
        self.jsx_elements = []
        self.method_calls = []
        self.property_accesses = []
        self.parse_result = None
    
    def _create_error_result(self, script_path: str, error: str) -> Dict[str, Any]:
        """Create an error result"""
        return {
            'script_path': script_path,
            'imports': {},
            'component_uses': [],
            'function_calls': [],
            'class_instantiations': [],
            'method_calls': [],
            'property_accesses': [],
            'hook_uses': [],
            'type_uses': [],
            'jsx_elements': [],
            'parse_errors': [error]
        }


# For backward compatibility with existing code
def analyze_typescript_script(script_path: str) -> Dict[str, Any]:
    """Analyze a TypeScript/JavaScript script (synchronous wrapper)"""
    analyzer = TypeScriptScriptAnalyzer()
    return analyzer.analyze_script_sync(script_path)


if __name__ == "__main__":
    # Test the analyzer
    import sys
    if len(sys.argv) > 1:
        result = analyze_typescript_script(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python ts_script_analyzer.py <script_path>")