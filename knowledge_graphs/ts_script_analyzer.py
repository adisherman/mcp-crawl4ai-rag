"""
TypeScript/JavaScript Script Analyzer for AI Hallucination Detection

Analyzes AI-generated TypeScript/JavaScript/React code to extract:
- Imports and their usage
- Component instantiations and their props
- Function calls and their parameters
- Hook usage patterns
- Type usage and interface implementations
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import logging

try:
    import esprima
except ImportError:
    logging.warning("esprima not installed. Install with: pip install esprima")
    esprima = None

logger = logging.getLogger(__name__)


class TypeScriptScriptAnalyzer:
    """Analyzes TypeScript/JavaScript scripts for validation against knowledge graph"""
    
    def __init__(self):
        self.imports = {}  # module -> imported items
        self.component_uses = []  # List of component instantiations
        self.function_calls = []  # List of function calls
        self.class_instantiations = []  # List of class instantiations
        self.hook_uses = []  # List of React hook calls
        self.type_uses = []  # List of type/interface uses
        self.jsx_elements = []  # List of JSX elements used
        self.variable_types = {}  # Variable name -> inferred type
        
    def analyze_script(self, script_path: str) -> Dict[str, Any]:
        """Analyze a TypeScript/JavaScript script and extract usage patterns"""
        logger.info(f"Analyzing script: {script_path}")
        
        # Reset state
        self._reset_state()
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract TypeScript-specific patterns before parsing
            self._extract_typescript_patterns(content)
            
            # Clean TypeScript syntax for esprima
            cleaned_content = self._clean_typescript_syntax(content)
            
            # Parse with esprima
            try:
                tree = esprima.parseScript(cleaned_content, {
                    'jsx': True,
                    'tolerant': True,
                    'loc': True,
                    'range': True
                })
                
                # Analyze the AST
                self._analyze_ast(tree)
                
            except Exception as e:
                logger.warning(f"Failed to parse script: {e}")
                # Still return what we could extract from regex patterns
            
            return self._compile_results()
            
        except Exception as e:
            logger.error(f"Error analyzing script: {e}")
            return self._compile_results()
    
    def _reset_state(self):
        """Reset analyzer state"""
        self.imports = {}
        self.component_uses = []
        self.function_calls = []
        self.class_instantiations = []
        self.hook_uses = []
        self.type_uses = []
        self.jsx_elements = []
        self.variable_types = {}
    
    def _clean_typescript_syntax(self, content: str) -> str:
        """Remove TypeScript-specific syntax for esprima parsing"""
        # Remove type annotations
        content = re.sub(r':\s*[A-Za-z<>\[\]{}|&\s,\(\)]+(?=[,\)]|\s*=|\s*{)', '', content)
        
        # Remove interface declarations
        content = re.sub(r'interface\s+\w+\s*(?:<[^>]+>)?\s*{[^}]*}', '', content, flags=re.DOTALL)
        
        # Remove type aliases
        content = re.sub(r'type\s+\w+\s*(?:<[^>]+>)?\s*=\s*[^;]+;', '', content)
        
        # Remove generic type parameters
        content = re.sub(r'<[A-Za-z\s,=]+>', '', content)
        
        # Remove 'as' type assertions
        content = re.sub(r'\s+as\s+[A-Za-z<>\[\]{}|&\s,\(\)]+', '', content)
        
        # Remove type imports
        content = re.sub(r'import\s+type\s*{[^}]*}\s*from\s*[\'"][^\'"]+[\'"];?', '', content)
        
        # Remove decorators
        content = re.sub(r'@\w+(\([^)]*\))?\s*', '', content)
        
        return content
    
    def _extract_typescript_patterns(self, content: str):
        """Extract TypeScript-specific patterns using regex"""
        # Extract type usage in variable declarations
        type_pattern = r'(?:const|let|var)\s+(\w+)\s*:\s*([A-Za-z<>\[\]{}|&\s,\(\)]+)\s*='
        for match in re.finditer(type_pattern, content):
            var_name = match.group(1)
            type_name = match.group(2).strip()
            self.variable_types[var_name] = type_name
            self._extract_type_names(type_name)
        
        # Extract interface implementations
        implements_pattern = r'class\s+\w+\s*(?:extends\s+\w+\s*)?implements\s+([^{]+)'
        for match in re.finditer(implements_pattern, content):
            interfaces = match.group(1)
            for interface in re.split(r',\s*', interfaces):
                self.type_uses.append({
                    'name': interface.strip(),
                    'kind': 'implements'
                })
        
        # Extract function parameter types
        func_param_pattern = r'function\s+\w+\s*\([^)]*\)\s*:\s*([A-Za-z<>\[\]{}|&\s,\(\)]+)\s*{'
        for match in re.finditer(func_param_pattern, content):
            return_type = match.group(1).strip()
            self._extract_type_names(return_type)
        
        # Extract JSX component usage with props
        jsx_pattern = r'<(\w+)(?:\s+[^>]*)?>'
        for match in re.finditer(jsx_pattern, content):
            component_name = match.group(1)
            if component_name[0].isupper():  # React components start with uppercase
                self.jsx_elements.append(component_name)
    
    def _extract_type_names(self, type_string: str):
        """Extract type names from a type annotation"""
        # Remove generic parameters first
        type_string = re.sub(r'<[^>]+>', '', type_string)
        
        # Split by common separators
        type_names = re.split(r'[|&,\s]+', type_string)
        
        for name in type_names:
            name = name.strip()
            if name and name[0].isupper() and name not in ['Array', 'Object', 'String', 'Number', 'Boolean']:
                self.type_uses.append({
                    'name': name,
                    'kind': 'type_annotation'
                })
    
    def _analyze_ast(self, tree):
        """Analyze the ESTree AST"""
        self._walk_ast(tree)
    
    def _walk_ast(self, node):
        """Walk the AST and extract information"""
        if isinstance(node, dict):
            node_type = node.get('type')
            
            if node_type == 'ImportDeclaration':
                self._handle_import(node)
            elif node_type == 'CallExpression':
                self._handle_call_expression(node)
            elif node_type == 'NewExpression':
                self._handle_new_expression(node)
            elif node_type == 'JSXElement':
                self._handle_jsx_element(node)
            elif node_type == 'VariableDeclarator':
                self._handle_variable_declarator(node)
            
            # Recursively walk children
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    self._walk_ast(value)
                    
        elif isinstance(node, list):
            for item in node:
                self._walk_ast(item)
    
    def _handle_import(self, node):
        """Handle import statements"""
        source = node.get('source', {}).get('value', '')
        if not source:
            return
        
        imported_items = []
        
        for spec in node.get('specifiers', []):
            spec_type = spec.get('type')
            if spec_type == 'ImportDefaultSpecifier':
                imported_items.append({
                    'name': spec.get('local', {}).get('name', ''),
                    'kind': 'default'
                })
            elif spec_type == 'ImportSpecifier':
                imported_items.append({
                    'name': spec.get('imported', {}).get('name', ''),
                    'local': spec.get('local', {}).get('name', ''),
                    'kind': 'named'
                })
            elif spec_type == 'ImportNamespaceSpecifier':
                imported_items.append({
                    'name': '*',
                    'local': spec.get('local', {}).get('name', ''),
                    'kind': 'namespace'
                })
        
        self.imports[source] = imported_items
    
    def _handle_call_expression(self, node):
        """Handle function/method calls"""
        callee = node.get('callee', {})
        arguments = node.get('arguments', [])
        
        if callee.get('type') == 'Identifier':
            func_name = callee.get('name', '')
            
            # Check if it's a React hook
            if func_name.startswith('use'):
                self.hook_uses.append({
                    'name': func_name,
                    'args_count': len(arguments)
                })
            else:
                self.function_calls.append({
                    'name': func_name,
                    'args_count': len(arguments),
                    'module': None
                })
                
        elif callee.get('type') == 'MemberExpression':
            obj = callee.get('object', {})
            prop = callee.get('property', {})
            
            if obj.get('type') == 'Identifier' and prop.get('type') == 'Identifier':
                obj_name = obj.get('name', '')
                method_name = prop.get('name', '')
                
                self.function_calls.append({
                    'name': method_name,
                    'object': obj_name,
                    'args_count': len(arguments),
                    'module': self._resolve_module(obj_name)
                })
    
    def _handle_new_expression(self, node):
        """Handle class instantiations"""
        callee = node.get('callee', {})
        arguments = node.get('arguments', [])
        
        if callee.get('type') == 'Identifier':
            class_name = callee.get('name', '')
            self.class_instantiations.append({
                'name': class_name,
                'args_count': len(arguments),
                'module': self._resolve_module(class_name)
            })
        elif callee.get('type') == 'MemberExpression':
            obj = callee.get('object', {})
            prop = callee.get('property', {})
            
            if obj.get('type') == 'Identifier' and prop.get('type') == 'Identifier':
                module_name = obj.get('name', '')
                class_name = prop.get('name', '')
                
                self.class_instantiations.append({
                    'name': class_name,
                    'module': module_name,
                    'args_count': len(arguments)
                })
    
    def _handle_jsx_element(self, node):
        """Handle JSX elements (React components)"""
        opening_element = node.get('openingElement', {})
        element_name = opening_element.get('name', {})
        
        if element_name.get('type') == 'JSXIdentifier':
            name = element_name.get('name', '')
            if name and name[0].isupper():  # React components
                props = []
                for attr in opening_element.get('attributes', []):
                    if attr.get('type') == 'JSXAttribute':
                        prop_name = attr.get('name', {}).get('name', '')
                        if prop_name:
                            props.append(prop_name)
                
                self.component_uses.append({
                    'name': name,
                    'props': props,
                    'module': self._resolve_module(name)
                })
        elif element_name.get('type') == 'JSXMemberExpression':
            # Handle compound components like Modal.Header
            obj = element_name.get('object', {})
            prop = element_name.get('property', {})
            
            if obj.get('type') == 'JSXIdentifier' and prop.get('type') == 'JSXIdentifier':
                parent = obj.get('name', '')
                child = prop.get('name', '')
                
                self.component_uses.append({
                    'name': f"{parent}.{child}",
                    'props': [],
                    'module': self._resolve_module(parent)
                })
    
    def _handle_variable_declarator(self, node):
        """Handle variable declarations to track types"""
        id_node = node.get('id', {})
        init_node = node.get('init', {})
        
        if id_node.get('type') == 'Identifier' and init_node:
            var_name = id_node.get('name', '')
            
            # Try to infer type from initialization
            if init_node.get('type') == 'NewExpression':
                callee = init_node.get('callee', {})
                if callee.get('type') == 'Identifier':
                    self.variable_types[var_name] = callee.get('name', '')
            elif init_node.get('type') == 'CallExpression':
                # Check for hook calls that return typed values
                callee = init_node.get('callee', {})
                if callee.get('type') == 'Identifier':
                    func_name = callee.get('name', '')
                    if func_name == 'useState':
                        # For useState, we track it but can't infer type without TypeScript
                        self.variable_types[var_name] = 'StateVariable'
    
    def _resolve_module(self, name: str) -> Optional[str]:
        """Try to resolve which module a name comes from"""
        # Check if it's directly imported
        for module, items in self.imports.items():
            for item in items:
                if item['kind'] == 'default' and item['name'] == name:
                    return module
                elif item['kind'] == 'named' and item['name'] == name:
                    return module
                elif item['kind'] == 'namespace' and 'local' in item:
                    # This would be used as item['local'].name
                    pass
        
        return None
    
    def _compile_results(self) -> Dict[str, Any]:
        """Compile analysis results"""
        return {
            'imports': self.imports,
            'component_uses': self.component_uses,
            'function_calls': self.function_calls,
            'class_instantiations': self.class_instantiations,
            'hook_uses': self.hook_uses,
            'type_uses': self.type_uses,
            'jsx_elements': list(set(self.jsx_elements)),
            'variable_types': self.variable_types
        }


def analyze_typescript_script(script_path: str) -> Dict[str, Any]:
    """Convenience function to analyze a TypeScript/JavaScript script"""
    analyzer = TypeScriptScriptAnalyzer()
    return analyzer.analyze_script(script_path)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
        results = analyze_typescript_script(script_path)
        
        print("\n=== TypeScript/JavaScript Script Analysis ===")
        print(f"\nImports:")
        for module, items in results['imports'].items():
            print(f"  from {module}:")
            for item in items:
                print(f"    - {item}")
        
        print(f"\nComponent Uses: {len(results['component_uses'])}")
        for comp in results['component_uses']:
            print(f"  - {comp['name']} with props: {comp['props']}")
        
        print(f"\nFunction Calls: {len(results['function_calls'])}")
        for call in results['function_calls']:
            if 'object' in call:
                print(f"  - {call['object']}.{call['name']}({call['args_count']} args)")
            else:
                print(f"  - {call['name']}({call['args_count']} args)")
        
        print(f"\nClass Instantiations: {len(results['class_instantiations'])}")
        for cls in results['class_instantiations']:
            print(f"  - new {cls['name']}({cls['args_count']} args)")
        
        print(f"\nReact Hooks Used: {len(results['hook_uses'])}")
        for hook in results['hook_uses']:
            print(f"  - {hook['name']}")
        
        print(f"\nType Uses: {len(results['type_uses'])}")
        for type_use in results['type_uses']:
            print(f"  - {type_use['name']} ({type_use['kind']})")
        
        print(f"\nJSX Elements: {results['jsx_elements']}")
        
        print(f"\nVariable Types:")
        for var, type_name in results['variable_types'].items():
            print(f"  - {var}: {type_name}")