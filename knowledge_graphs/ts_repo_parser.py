"""
TypeScript/JavaScript/React Repository Parser for Neo4j

Creates nodes and relationships for TypeScript/JavaScript/React code:
- File nodes
- Component nodes
- Interface nodes
- Type nodes
- Function nodes
- Module relationships

Uses esprima for JavaScript parsing with TypeScript handled as best as possible.
"""

import asyncio
import logging
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
import json
import re

try:
    import esprima
except ImportError:
    logger.warning("esprima not installed. Install with: pip install esprima")
    esprima = None

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class TypeScriptCodeAnalyzer:
    """Analyzes TypeScript/JavaScript code for Neo4j insertion"""
    
    def __init__(self):
        # External modules to ignore
        self.external_modules = {
            # Node.js built-ins
            'fs', 'path', 'http', 'https', 'crypto', 'os', 'util', 'stream', 'events',
            'child_process', 'cluster', 'net', 'dns', 'domain', 'tls', 'dgram', 'url',
            'querystring', 'string_decoder', 'timers', 'vm', 'zlib', 'assert', 'buffer',
            'console', 'constants', 'process', 'punycode', 'readline', 'repl', 'tty',
            
            # Common npm packages
            'react', 'react-dom', 'react-router', 'react-router-dom', 'redux', 'react-redux',
            'axios', 'fetch', 'lodash', 'underscore', 'moment', 'date-fns', 'dayjs',
            'express', 'koa', 'fastify', 'next', 'gatsby', 'nuxt', 'vue', 'angular',
            '@angular/core', '@angular/common', '@angular/router', '@angular/forms',
            'typescript', 'webpack', 'babel', 'eslint', 'prettier', 'jest', 'mocha',
            'chai', 'enzyme', '@testing-library/react', 'cypress', 'puppeteer',
            'material-ui', '@mui/material', 'antd', 'bootstrap', 'tailwindcss',
            'styled-components', 'emotion', '@emotion/react', '@emotion/styled',
            'graphql', 'apollo-client', '@apollo/client', 'prisma', '@prisma/client',
            'mongoose', 'sequelize', 'typeorm', 'knex', 'pg', 'mysql', 'sqlite3',
            'jsonwebtoken', 'bcrypt', 'passport', 'cors', 'helmet', 'compression',
            'body-parser', 'cookie-parser', 'multer', 'dotenv', 'config', 'yup',
            'joi', 'zod', 'class-validator', 'class-transformer', 'reflect-metadata'
        }
        
        # React hooks
        self.react_hooks = {
            'useState', 'useEffect', 'useContext', 'useReducer', 'useCallback',
            'useMemo', 'useRef', 'useImperativeHandle', 'useLayoutEffect',
            'useDebugValue', 'useDeferredValue', 'useTransition', 'useId'
        }
    
    def analyze_javascript_file(self, file_path: Path, repo_root: Path, project_modules: Set[str]) -> Dict[str, Any]:
        """Extract structure from JavaScript/TypeScript file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove TypeScript-specific syntax for esprima parsing
            cleaned_content = self._clean_typescript_syntax(content)
            
            # Extract TypeScript interfaces and types using regex before parsing
            interfaces = self._extract_interfaces(content)
            types = self._extract_type_aliases(content)
            
            # Parse with esprima
            try:
                tree = esprima.parseScript(cleaned_content, {
                    'jsx': True,
                    'tolerant': True,
                    'loc': True,
                    'range': True
                })
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
                # Return basic structure even if parsing fails
                return {
                    'path': str(file_path.relative_to(repo_root)),
                    'module_name': self._get_module_name(file_path, repo_root),
                    'components': [],
                    'functions': [],
                    'classes': [],
                    'interfaces': interfaces,
                    'types': types,
                    'imports': [],
                    'exports': []
                }
            
            relative_path = str(file_path.relative_to(repo_root))
            module_name = self._get_module_name(file_path, repo_root)
            
            # Extract structure
            components = []
            functions = []
            classes = []
            imports = []
            exports = []
            hooks_used = set()
            
            # Walk the AST
            for node in self._walk_ast(tree):
                node_type = node.get('type')
                
                if node_type == 'ImportDeclaration':
                    import_info = self._extract_import(node)
                    if import_info:
                        imports.append(import_info)
                
                elif node_type == 'ExportNamedDeclaration' or node_type == 'ExportDefaultDeclaration':
                    export_info = self._extract_export(node)
                    if export_info:
                        exports.append(export_info)
                
                elif node_type == 'FunctionDeclaration' or node_type == 'FunctionExpression':
                    func_info = self._extract_function(node, content)
                    if func_info:
                        # Check if it's a React component
                        if self._is_react_component(func_info['name'], node, content):
                            components.append({
                                'name': func_info['name'],
                                'type': 'functional',
                                'props': self._extract_component_props(node),
                                'hooks': list(self._extract_hooks_from_function(node))
                            })
                        else:
                            functions.append(func_info)
                
                elif node_type == 'ClassDeclaration':
                    class_info = self._extract_class(node)
                    if class_info:
                        # Check if it's a React component
                        if self._is_react_class_component(node):
                            components.append({
                                'name': class_info['name'],
                                'type': 'class',
                                'props': self._extract_class_component_props(node),
                                'hooks': []  # Class components don't use hooks
                            })
                        else:
                            classes.append(class_info)
                
                elif node_type == 'VariableDeclaration':
                    # Check for const MyComponent = () => { ... }
                    for decl in node.get('declarations', []):
                        if decl.get('init', {}).get('type') in ['ArrowFunctionExpression', 'FunctionExpression']:
                            name = decl.get('id', {}).get('name', '')
                            if name and self._is_react_component(name, decl['init'], content):
                                components.append({
                                    'name': name,
                                    'type': 'functional',
                                    'props': self._extract_component_props(decl['init']),
                                    'hooks': list(self._extract_hooks_from_function(decl['init']))
                                })
            
            return {
                'path': relative_path,
                'module_name': module_name,
                'components': components,
                'functions': functions,
                'classes': classes,
                'interfaces': interfaces,
                'types': types,
                'imports': imports,
                'exports': exports
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {
                'path': str(file_path.relative_to(repo_root)),
                'module_name': self._get_module_name(file_path, repo_root),
                'components': [],
                'functions': [],
                'classes': [],
                'interfaces': [],
                'types': [],
                'imports': [],
                'exports': []
            }
    
    def _clean_typescript_syntax(self, content: str) -> str:
        """Remove TypeScript-specific syntax for esprima parsing"""
        # Remove type annotations from variables and parameters
        content = re.sub(r':\s*[A-Za-z<>\[\]{}|&\s,\(\)]+(?=[,\)]|\s*=|\s*{)', '', content)
        
        # Remove interface declarations (we extract them separately)
        content = re.sub(r'interface\s+\w+\s*(?:<[^>]+>)?\s*{[^}]*}', '', content, flags=re.DOTALL)
        
        # Remove type aliases
        content = re.sub(r'type\s+\w+\s*(?:<[^>]+>)?\s*=\s*[^;]+;', '', content)
        
        # Remove generic type parameters
        content = re.sub(r'<[A-Za-z\s,=]+>', '', content)
        
        # Remove 'as' type assertions
        content = re.sub(r'\s+as\s+[A-Za-z<>\[\]{}|&\s,\(\)]+', '', content)
        
        # Remove type imports
        content = re.sub(r'import\s+type\s*{[^}]*}\s*from\s*[\'"][^\'"]+[\'"];?', '', content)
        
        # Remove readonly, public, private, protected modifiers
        content = re.sub(r'\b(readonly|public|private|protected)\s+', '', content)
        
        # Remove decorators
        content = re.sub(r'@\w+(\([^)]*\))?\s*', '', content)
        
        return content
    
    def _extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """Extract TypeScript interfaces using regex"""
        interfaces = []
        # Match interface declarations
        pattern = r'interface\s+(\w+)\s*(?:<([^>]+)>)?\s*(?:extends\s+([^{]+))?\s*{([^}]*)}'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            name = match.group(1)
            generics = match.group(2)
            extends = match.group(3)
            body = match.group(4)
            
            properties = []
            # Extract properties from interface body
            prop_pattern = r'(\w+)(\?)?\s*:\s*([^;,\n]+)'
            for prop_match in re.finditer(prop_pattern, body):
                properties.append({
                    'name': prop_match.group(1),
                    'optional': bool(prop_match.group(2)),
                    'type': prop_match.group(3).strip()
                })
            
            interfaces.append({
                'name': name,
                'generics': generics.split(',') if generics else [],
                'extends': [e.strip() for e in extends.split(',')] if extends else [],
                'properties': properties
            })
        
        return interfaces
    
    def _extract_type_aliases(self, content: str) -> List[Dict[str, Any]]:
        """Extract TypeScript type aliases using regex"""
        types = []
        # Match type declarations
        pattern = r'type\s+(\w+)\s*(?:<([^>]+)>)?\s*=\s*([^;]+);'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            generics = match.group(2)
            definition = match.group(3).strip()
            
            types.append({
                'name': name,
                'generics': generics.split(',') if generics else [],
                'definition': definition
            })
        
        return types
    
    def _walk_ast(self, node):
        """Walk the ESTree AST"""
        if isinstance(node, dict):
            yield node
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    yield from self._walk_ast(value)
        elif isinstance(node, list):
            for item in node:
                yield from self._walk_ast(item)
    
    def _extract_import(self, node: Dict) -> Optional[Dict[str, Any]]:
        """Extract import information"""
        source = node.get('source', {}).get('value', '')
        if not source:
            return None
        
        imported_items = []
        default_import = None
        
        for spec in node.get('specifiers', []):
            spec_type = spec.get('type')
            if spec_type == 'ImportDefaultSpecifier':
                default_import = spec.get('local', {}).get('name', '')
            elif spec_type == 'ImportSpecifier':
                imported = spec.get('imported', {}).get('name', '')
                local = spec.get('local', {}).get('name', '')
                imported_items.append({
                    'imported': imported,
                    'local': local
                })
            elif spec_type == 'ImportNamespaceSpecifier':
                imported_items.append({
                    'imported': '*',
                    'local': spec.get('local', {}).get('name', '')
                })
        
        return {
            'source': source,
            'default': default_import,
            'items': imported_items,
            'is_internal': self._is_internal_import(source)
        }
    
    def _extract_export(self, node: Dict) -> Optional[Dict[str, Any]]:
        """Extract export information"""
        export_type = node.get('type')
        
        if export_type == 'ExportDefaultDeclaration':
            declaration = node.get('declaration', {})
            if declaration.get('type') == 'Identifier':
                return {
                    'type': 'default',
                    'name': declaration.get('name', '')
                }
            elif declaration.get('type') in ['FunctionDeclaration', 'ClassDeclaration']:
                return {
                    'type': 'default',
                    'name': declaration.get('id', {}).get('name', 'anonymous')
                }
        
        elif export_type == 'ExportNamedDeclaration':
            if node.get('declaration'):
                # export const/let/var/function/class
                declaration = node['declaration']
                if declaration.get('type') == 'VariableDeclaration':
                    names = []
                    for decl in declaration.get('declarations', []):
                        if decl.get('id', {}).get('name'):
                            names.append(decl['id']['name'])
                    return {
                        'type': 'named',
                        'names': names
                    }
                elif declaration.get('type') in ['FunctionDeclaration', 'ClassDeclaration']:
                    return {
                        'type': 'named',
                        'names': [declaration.get('id', {}).get('name', '')]
                    }
            else:
                # export { ... }
                names = []
                for spec in node.get('specifiers', []):
                    names.append(spec.get('exported', {}).get('name', ''))
                return {
                    'type': 'named',
                    'names': names
                }
        
        return None
    
    def _extract_function(self, node: Dict, content: str) -> Optional[Dict[str, Any]]:
        """Extract function information"""
        name = node.get('id', {}).get('name', 'anonymous')
        params = []
        
        for param in node.get('params', []):
            if param.get('type') == 'Identifier':
                params.append({
                    'name': param.get('name', ''),
                    'type': 'any'  # Can't get type from JavaScript
                })
            elif param.get('type') == 'ObjectPattern':
                # Destructured parameters
                params.append({
                    'name': '{...}',
                    'type': 'object'
                })
            elif param.get('type') == 'ArrayPattern':
                params.append({
                    'name': '[...]',
                    'type': 'array'
                })
        
        return {
            'name': name,
            'async': node.get('async', False),
            'generator': node.get('generator', False),
            'params': params
        }
    
    def _extract_class(self, node: Dict) -> Optional[Dict[str, Any]]:
        """Extract class information"""
        name = node.get('id', {}).get('name', '')
        if not name:
            return None
        
        extends = None
        if node.get('superClass'):
            extends = node['superClass'].get('name', '')
        
        methods = []
        properties = []
        
        for item in node.get('body', {}).get('body', []):
            if item.get('type') == 'MethodDefinition':
                method_name = item.get('key', {}).get('name', '')
                if method_name and not method_name.startswith('_'):
                    methods.append({
                        'name': method_name,
                        'static': item.get('static', False),
                        'async': item.get('value', {}).get('async', False)
                    })
            elif item.get('type') == 'PropertyDefinition':
                prop_name = item.get('key', {}).get('name', '')
                if prop_name:
                    properties.append({
                        'name': prop_name,
                        'static': item.get('static', False)
                    })
        
        return {
            'name': name,
            'extends': extends,
            'methods': methods,
            'properties': properties
        }
    
    def _is_react_component(self, name: str, node: Dict, content: str) -> bool:
        """Check if a function is a React component"""
        # React components start with uppercase
        if not name or not name[0].isupper():
            return False
        
        # Check if it returns JSX
        body = node.get('body')
        if body:
            # Look for return statements with JSX
            return self._contains_jsx_return(body)
        
        return False
    
    def _is_react_class_component(self, node: Dict) -> bool:
        """Check if a class is a React component"""
        superClass = node.get('superClass')
        if not superClass:
            return False
        
        # Check for React.Component or Component
        if superClass.get('type') == 'Identifier':
            return superClass.get('name') in ['Component', 'PureComponent']
        elif superClass.get('type') == 'MemberExpression':
            obj = superClass.get('object', {}).get('name', '')
            prop = superClass.get('property', {}).get('name', '')
            return obj == 'React' and prop in ['Component', 'PureComponent']
        
        return False
    
    def _contains_jsx_return(self, node: Dict) -> bool:
        """Check if a function body contains JSX return"""
        for item in self._walk_ast(node):
            if item.get('type') == 'ReturnStatement':
                argument = item.get('argument')
                if argument and argument.get('type') == 'JSXElement':
                    return True
        return False
    
    def _extract_component_props(self, node: Dict) -> Dict[str, Any]:
        """Extract props from functional component"""
        params = node.get('params', [])
        if not params:
            return {}
        
        first_param = params[0]
        if first_param.get('type') == 'Identifier':
            return {'type': 'props', 'name': first_param.get('name', 'props')}
        elif first_param.get('type') == 'ObjectPattern':
            # Destructured props
            props = []
            for prop in first_param.get('properties', []):
                if prop.get('type') == 'Property':
                    props.append(prop.get('key', {}).get('name', ''))
            return {'type': 'destructured', 'properties': props}
        
        return {}
    
    def _extract_class_component_props(self, node: Dict) -> Dict[str, Any]:
        """Extract props type from class component"""
        # In JavaScript, we can't easily determine prop types
        # Would need TypeScript parsing for this
        return {'type': 'unknown'}
    
    def _extract_hooks_from_function(self, node: Dict) -> Set[str]:
        """Extract React hooks used in a function"""
        hooks = set()
        
        for item in self._walk_ast(node):
            if item.get('type') == 'CallExpression':
                callee = item.get('callee', {})
                if callee.get('type') == 'Identifier':
                    name = callee.get('name', '')
                    if name.startswith('use') and (name in self.react_hooks or len(name) > 3):
                        hooks.add(name)
        
        return hooks
    
    def _is_internal_import(self, source: str) -> bool:
        """Check if an import is internal to the project"""
        # Relative imports are internal
        if source.startswith('.'):
            return True
        
        # Check against known external modules
        base_module = source.split('/')[0].replace('@', '')
        if base_module in self.external_modules:
            return False
        
        # Check for scoped packages
        if source.startswith('@'):
            scope_and_package = source.split('/')[0:2]
            if len(scope_and_package) == 2:
                package_name = '/'.join(scope_and_package)
                if package_name in self.external_modules:
                    return False
        
        # If not obviously external, consider it internal
        return True
    
    def _get_module_name(self, file_path: Path, repo_root: Path) -> str:
        """Get the module name for a JavaScript/TypeScript file"""
        relative_path = file_path.relative_to(repo_root)
        
        # Remove file extension
        module_path = str(relative_path).replace('.tsx', '').replace('.ts', '').replace('.jsx', '').replace('.js', '')
        
        # Handle index files
        if module_path.endswith('/index'):
            module_path = module_path[:-6]  # Remove '/index'
        
        # Convert to module path
        return module_path.replace('/', '.').replace('\\', '.')


class TypeScriptNeo4jExtractor:
    """Extracts TypeScript/JavaScript code into Neo4j"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.analyzer = TypeScriptCodeAnalyzer()
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        logger.info("Initializing Neo4j connection for TypeScript parser...")
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        # Create TypeScript-specific constraints and indexes
        logger.info("Creating TypeScript constraints and indexes...")
        async with self.driver.session() as session:
            # Create constraints for new node types
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interface) REQUIRE i.full_name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Type) REQUIRE t.full_name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.full_name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hook) REQUIRE h.name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE m.path IS UNIQUE")
            
            # Create indexes
            await session.run("CREATE INDEX IF NOT EXISTS FOR (i:Interface) ON (i.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Type) ON (t.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (h:Hook) ON (h.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (f:JSFunction) ON (f.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:JSClass) ON (c.name)")
        
        logger.info("TypeScript Neo4j initialized successfully")
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    async def process_repository(self, repo_path: str, repo_name: str):
        """Process a TypeScript/JavaScript repository"""
        logger.info(f"Processing TypeScript repository: {repo_name}")
        repo_root = Path(repo_path)
        
        # Create repository node
        async with self.driver.session() as session:
            await session.run("""
                MERGE (r:Repository {name: $name})
                SET r.analyzed_at = datetime(),
                    r.language = 'TypeScript'
            """, name=repo_name)
        
        # Collect all TypeScript/JavaScript files
        ts_files = []
        js_files = []
        for ext in ['*.ts', '*.tsx', '*.js', '*.jsx']:
            ts_files.extend(repo_root.rglob(ext))
        
        # Filter out node_modules and other irrelevant directories
        ts_files = [f for f in ts_files if 'node_modules' not in str(f) and '.git' not in str(f)]
        
        logger.info(f"Found {len(ts_files)} TypeScript/JavaScript files")
        
        # Extract project modules for import resolution
        project_modules = self._extract_project_modules(repo_root, ts_files)
        
        # Process files
        for file_path in ts_files:
            await self._process_file(file_path, repo_root, repo_name, project_modules)
        
        logger.info(f"Completed processing repository: {repo_name}")
    
    def _extract_project_modules(self, repo_root: Path, files: List[Path]) -> Set[str]:
        """Extract project module names for import resolution"""
        modules = set()
        
        # Check package.json for module name
        package_json = repo_root / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    if 'name' in data:
                        modules.add(data['name'])
            except:
                pass
        
        # Extract top-level directories as potential modules
        for file_path in files:
            relative_path = file_path.relative_to(repo_root)
            if len(relative_path.parts) > 1:
                modules.add(relative_path.parts[0])
        
        return modules
    
    async def _process_file(self, file_path: Path, repo_root: Path, repo_name: str, project_modules: Set[str]):
        """Process a single TypeScript/JavaScript file"""
        logger.debug(f"Processing file: {file_path}")
        
        # Analyze file
        analysis = self.analyzer.analyze_javascript_file(file_path, repo_root, project_modules)
        
        # Create file node
        async with self.driver.session() as session:
            await session.run("""
                MATCH (r:Repository {name: $repo_name})
                MERGE (f:File {path: $path})
                SET f.name = $name,
                    f.module = $module,
                    f.language = $language
                MERGE (r)-[:CONTAINS]->(f)
            """, 
                repo_name=repo_name,
                path=analysis['path'],
                name=file_path.name,
                module=analysis['module_name'],
                language=self._detect_language(file_path)
            )
            
            # Create components
            for component in analysis['components']:
                await session.run("""
                    MATCH (f:File {path: $file_path})
                    MERGE (c:Component {full_name: $full_name})
                    SET c.name = $name,
                        c.type = $type,
                        c.exported = $exported
                    MERGE (f)-[:DEFINES]->(c)
                """,
                    file_path=analysis['path'],
                    full_name=f"{analysis['module_name']}.{component['name']}",
                    name=component['name'],
                    type=component['type'],
                    exported=any(component['name'] in exp.get('names', []) or 
                                exp.get('name') == component['name'] 
                                for exp in analysis['exports'])
                )
                
                # Create hook relationships
                for hook in component['hooks']:
                    await session.run("""
                        MATCH (c:Component {full_name: $component_name})
                        MERGE (h:Hook {name: $hook_name})
                        SET h.custom = $custom
                        MERGE (c)-[:USES_HOOK]->(h)
                    """,
                        component_name=f"{analysis['module_name']}.{component['name']}",
                        hook_name=hook,
                        custom=hook not in self.analyzer.react_hooks
                    )
            
            # Create interfaces
            for interface in analysis['interfaces']:
                await session.run("""
                    MATCH (f:File {path: $file_path})
                    MERGE (i:Interface {full_name: $full_name})
                    SET i.name = $name,
                        i.generics = $generics,
                        i.extends = $extends,
                        i.properties = $properties
                    MERGE (f)-[:DEFINES]->(i)
                """,
                    file_path=analysis['path'],
                    full_name=f"{analysis['module_name']}.{interface['name']}",
                    name=interface['name'],
                    generics=interface['generics'],
                    extends=interface['extends'],
                    properties=[p['name'] for p in interface['properties']]
                )
            
            # Create type aliases
            for type_alias in analysis['types']:
                await session.run("""
                    MATCH (f:File {path: $file_path})
                    MERGE (t:Type {full_name: $full_name})
                    SET t.name = $name,
                        t.generics = $generics,
                        t.definition = $definition
                    MERGE (f)-[:DEFINES]->(t)
                """,
                    file_path=analysis['path'],
                    full_name=f"{analysis['module_name']}.{type_alias['name']}",
                    name=type_alias['name'],
                    generics=type_alias['generics'],
                    definition=type_alias['definition']
                )
            
            # Create functions
            for function in analysis['functions']:
                await session.run("""
                    MATCH (f:File {path: $file_path})
                    MERGE (func:JSFunction {full_name: $full_name})
                    SET func.name = $name,
                        func.async = $async,
                        func.generator = $generator,
                        func.params = $params,
                        func.exported = $exported
                    MERGE (f)-[:DEFINES]->(func)
                """,
                    file_path=analysis['path'],
                    full_name=f"{analysis['module_name']}.{function['name']}",
                    name=function['name'],
                    async=function['async'],
                    generator=function['generator'],
                    params=[p['name'] for p in function['params']],
                    exported=any(function['name'] in exp.get('names', []) or 
                               exp.get('name') == function['name'] 
                               for exp in analysis['exports'])
                )
            
            # Create classes
            for cls in analysis['classes']:
                await session.run("""
                    MATCH (f:File {path: $file_path})
                    MERGE (c:JSClass {full_name: $full_name})
                    SET c.name = $name,
                        c.extends = $extends,
                        c.methods = $methods,
                        c.properties = $properties,
                        c.exported = $exported
                    MERGE (f)-[:DEFINES]->(c)
                """,
                    file_path=analysis['path'],
                    full_name=f"{analysis['module_name']}.{cls['name']}",
                    name=cls['name'],
                    extends=cls['extends'],
                    methods=[m['name'] for m in cls['methods']],
                    properties=[p['name'] for p in cls['properties']],
                    exported=any(cls['name'] in exp.get('names', []) or 
                               exp.get('name') == cls['name'] 
                               for exp in analysis['exports'])
                )
            
            # Create import relationships
            for imp in analysis['imports']:
                if imp['is_internal']:
                    # Try to resolve the import to a file
                    target_module = imp['source'].replace('./', '').replace('../', '')
                    await session.run("""
                        MATCH (f1:File {path: $from_path})
                        MATCH (f2:File {module: $to_module})
                        MERGE (f1)-[:IMPORTS_FROM {items: $items}]->(f2)
                    """,
                        from_path=analysis['path'],
                        to_module=target_module,
                        items=[item['imported'] for item in imp['items']]
                    )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect the language from file extension"""
        ext = file_path.suffix.lower()
        if ext in ['.ts', '.tsx']:
            return 'TypeScript'
        elif ext in ['.js', '.jsx']:
            return 'JavaScript'
        return 'Unknown'


async def main():
    """Example usage"""
    load_dotenv()
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    if not neo4j_password:
        logger.error("NEO4J_PASSWORD not set in environment")
        return
    
    # Example: Parse a TypeScript repository
    extractor = TypeScriptNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        await extractor.initialize()
        
        # Clone and process a repository
        repo_url = "https://github.com/example/typescript-project.git"
        repo_name = "typescript-project"
        
        # Process the repository
        # await extractor.process_repository("/path/to/repo", repo_name)
        
    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())