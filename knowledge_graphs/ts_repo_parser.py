"""
TypeScript/JavaScript/React Repository Parser for Neo4j

Creates nodes and relationships for TypeScript/JavaScript/React code:
- File nodes
- Component nodes  
- Interface nodes
- Type nodes
- Function nodes
- Class nodes
- Module relationships

Uses the TypeScript Compiler API via REST service for accurate parsing.
"""

import asyncio
import logging
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
import json

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Import our TypeScript parser client
from ts_parser_client import TypeScriptParserService, TypeScriptParserClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class TypeScriptNeo4jExtractor:
    """Extract TypeScript/JavaScript code structure into Neo4j"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.parser_service = TypeScriptParserService()
        self.parser_client = None
        
        # Track processed items to avoid duplicates
        self.processed_files = set()
        self.processed_components = set()
        self.processed_interfaces = set()
        self.processed_types = set()
        self.processed_functions = set()
        self.processed_classes = set()
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        # Start the parser service
        self.parser_client = await self.parser_service.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.parser_service.__aexit__(exc_type, exc_val, exc_tb)
        await self.close()
        
    async def connect(self):
        """Connect to Neo4j"""
        logger.info("Initializing Neo4j connection for TypeScript parser...")
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        # Create constraints and indexes
        async with self.driver.session() as session:
            logger.info("Creating TypeScript constraints and indexes...")
            
            # Unique constraints
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.full_name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interface) REQUIRE i.full_name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Type) REQUIRE t.full_name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:JSClass) REQUIRE c.full_name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:JSFunction) REQUIRE f.full_name IS UNIQUE",
            ]
            
            for constraint in constraints:
                await session.run(constraint)
            
            # Indexes for better query performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (i:Interface) ON (i.name)",
                "CREATE INDEX IF NOT EXISTS FOR (h:Hook) ON (h.name)",
                "CREATE INDEX IF NOT EXISTS FOR (f:JSFunction) ON (f.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:JSClass) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (m:Module) ON (m.name)",
            ]
            
            for index in indexes:
                await session.run(index)
                
        logger.info("TypeScript Neo4j initialized successfully")
        
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            
    async def parse_directory(self, repo_path: str, repo_name: str) -> Dict[str, Any]:
        """
        Parse a directory and store in Neo4j
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            
        Returns:
            Dictionary with parsing statistics
        """
        repo_root = Path(repo_path)
        
        # Create Repository node
        repo_id = await self._create_repository_node(repo_name)
        
        # Find all TypeScript/JavaScript files
        ts_files = []
        js_files = []
        
        for ext in ['*.ts', '*.tsx', '*.js', '*.jsx', '*.mjs', '*.cjs']:
            for file_path in repo_root.rglob(ext):
                # Skip node_modules and other common directories
                if any(part in file_path.parts for part in ['node_modules', '.git', 'dist', 'build', 'coverage']):
                    continue
                    
                if file_path.suffix in ['.ts', '.tsx']:
                    ts_files.append(file_path)
                else:
                    js_files.append(file_path)
                    
        total_files = len(ts_files) + len(js_files)
        logger.info(f"Found {len(ts_files)} TypeScript files and {len(js_files)} JavaScript files")
        
        # Parse files in batches
        batch_size = 10
        all_files = ts_files + js_files
        
        for i in range(0, len(all_files), batch_size):
            batch = all_files[i:i + batch_size]
            
            # Read file contents
            file_contents = []
            for file_path in batch:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_contents.append((content, str(file_path)))
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    
            # Parse batch
            if file_contents:
                parse_results = await self.parser_client.parse_batch(file_contents)
                
                # Process results
                for result, file_path in zip(parse_results, batch):
                    if isinstance(result, dict) and result.get('filename'):
                        await self._process_parsed_file(
                            result, 
                            file_path, 
                            repo_root, 
                            repo_id
                        )
                        
            # Log progress
            processed = min(i + batch_size, total_files)
            logger.info(f"Processed {processed}/{total_files} files")
            
        # Create module relationships
        await self._create_module_relationships(repo_id)
        
        return {
            'repository': repo_name,
            'total_files': total_files,
            'typescript_files': len(ts_files),
            'javascript_files': len(js_files),
            'components': len(self.processed_components),
            'interfaces': len(self.processed_interfaces),
            'types': len(self.processed_types),
            'functions': len(self.processed_functions),
            'classes': len(self.processed_classes)
        }
        
    async def _process_parsed_file(self, parsed_data: Dict[str, Any], 
                                 file_path: Path, repo_root: Path, 
                                 repo_id: str):
        """Process parsed file data and store in Neo4j"""
        if parsed_data.get('error'):
            logger.error(f"Parse error for {file_path}: {parsed_data['error']}")
            return
            
        relative_path = str(file_path.relative_to(repo_root))
        module_name = self._get_module_name(file_path, repo_root)
        
        # Create File node
        file_id = await self._create_file_node(
            path=relative_path,
            name=file_path.name,
            module_name=module_name,
            language=parsed_data.get('language', 'javascript'),
            line_count=parsed_data.get('lineCount', 0),
            repo_id=repo_id
        )
        
        # Process components
        for component in parsed_data.get('components', []):
            await self._create_component_node(component, file_id, module_name)
            
        # Process interfaces
        for interface in parsed_data.get('interfaces', []):
            await self._create_interface_node(interface, file_id, module_name)
            
        # Process types
        for type_alias in parsed_data.get('types', []):
            await self._create_type_node(type_alias, file_id, module_name)
            
        # Process functions
        for function in parsed_data.get('functions', []):
            await self._create_function_node(function, file_id, module_name)
            
        # Process classes
        for class_info in parsed_data.get('classes', []):
            await self._create_class_node(class_info, file_id, module_name)
            
        # Process imports and exports
        await self._process_imports(parsed_data.get('imports', []), file_id)
        await self._process_exports(parsed_data.get('exports', []), file_id)
        
        # Process JSX elements (track component usage)
        await self._process_jsx_elements(parsed_data.get('jsxElements', []), file_id)
        
    def _get_module_name(self, file_path: Path, repo_root: Path) -> str:
        """Get module name from file path"""
        relative_path = file_path.relative_to(repo_root)
        # Get the directory path (not including the filename)
        dir_path = relative_path.parent
        # Convert to module path
        if dir_path == Path('.'):
            # Root level file
            return ''
        return str(dir_path).replace('/', '.')
        
    async def _create_repository_node(self, repo_name: str) -> str:
        """Create or update Repository node"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (r:Repository {name: $name})
                SET r.updated_at = datetime(),
                    r.language = 'TypeScript/JavaScript'
                RETURN id(r) as repo_id
                """,
                name=repo_name
            )
            record = await result.single()
            return record['repo_id']
            
    async def _create_file_node(self, path: str, name: str, module_name: str,
                              language: str, line_count: int, repo_id: str) -> str:
        """Create File node"""
        if path in self.processed_files:
            return path
            
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository) WHERE id(r) = $repo_id
                MERGE (f:File {path: $path})
                SET f.name = $name,
                    f.module = $module_name,
                    f.language = $language,
                    f.line_count = $line_count,
                    f.updated_at = datetime()
                MERGE (r)-[:CONTAINS]->(f)
                RETURN id(f) as file_id
                """,
                repo_id=repo_id,
                path=path,
                name=name,
                module_name=module_name,
                language=language,
                line_count=line_count
            )
            
        self.processed_files.add(path)
        return path
        
    async def _create_component_node(self, component: Dict[str, Any], 
                                   file_id: str, module_name: str):
        """Create Component node"""
        # For default exports, use the filename as the component name in the full_name
        if component.get('isDefault') and component['name'] == 'default':
            # Extract filename without extension from file_id
            filename = Path(file_id).stem
            if module_name:
                full_name = f"{module_name}.{filename}"
            else:
                full_name = filename
        else:
            # For named exports, use the actual component name
            if module_name:
                full_name = f"{module_name}.{component['name']}"
            else:
                full_name = component['name']
        
        if full_name in self.processed_components:
            return
            
        async with self.driver.session() as session:
            # Create Component node
            await session.run(
                """
                MATCH (f:File {path: $file_id})
                MERGE (c:Component {full_name: $full_name})
                SET c.name = $name,
                    c.type = $type,
                    c.line = $line,
                    c.isExported = $isExported,
                    c.isDefault = $isDefault,
                    c.props = $props,
                    c.isForwardRef = $isForwardRef,
                    c.isMemo = $isMemo,
                    c.displayName = $displayName,
                    c.updated_at = datetime()
                MERGE (f)-[:DEFINES]->(c)
                """,
                file_id=file_id,
                full_name=full_name,
                name=component['name'],
                type=component.get('type', 'functional'),
                line=component.get('line', 0),
                isExported=component.get('isExported', False),
                isDefault=component.get('isDefault', False),
                props=component.get('props'),
                isForwardRef=component.get('isForwardRef', False),
                isMemo=component.get('isMemo', False),
                displayName=component.get('displayName')
            )
            
            # Create Hook relationships
            for hook in component.get('hooks', []):
                await session.run(
                    """
                    MATCH (c:Component {full_name: $full_name})
                    MERGE (h:Hook {name: $hook_name})
                    SET h.isCustom = $isCustom
                    MERGE (c)-[:USES_HOOK]->(h)
                    """,
                    full_name=full_name,
                    hook_name=hook['name'],
                    isCustom=not hook['name'].startswith('use')
                )
                
        self.processed_components.add(full_name)
        
    async def _create_interface_node(self, interface: Dict[str, Any], 
                                   file_id: str, module_name: str):
        """Create Interface node"""
        if module_name:
            full_name = f"{module_name}.{interface['name']}"
        else:
            full_name = interface['name']
        
        if full_name in self.processed_interfaces:
            return
            
        async with self.driver.session() as session:
            # Create Interface node
            await session.run(
                """
                MATCH (f:File {path: $file_id})
                MERGE (i:Interface {full_name: $full_name})
                SET i.name = $name,
                    i.line = $line,
                    i.isExported = $isExported,
                    i.properties = $properties,
                    i.methods = $methods,
                    i.updated_at = datetime()
                MERGE (f)-[:DEFINES]->(i)
                """,
                file_id=file_id,
                full_name=full_name,
                name=interface['name'],
                line=interface.get('line', 0),
                isExported=interface.get('isExported', False),
                properties=json.dumps(interface.get('properties', [])),
                methods=json.dumps(interface.get('methods', []))
            )
            
            # Create extends relationships
            for extended in interface.get('extends', []):
                await session.run(
                    """
                    MATCH (i:Interface {full_name: $full_name})
                    MERGE (e:Interface {name: $extended_name})
                    MERGE (i)-[:EXTENDS]->(e)
                    """,
                    full_name=full_name,
                    extended_name=extended
                )
                
        self.processed_interfaces.add(full_name)
        
    async def _create_type_node(self, type_alias: Dict[str, Any], 
                              file_id: str, module_name: str):
        """Create Type node"""
        if module_name:
            full_name = f"{module_name}.{type_alias['name']}"
        else:
            full_name = type_alias['name']
        
        if full_name in self.processed_types:
            return
            
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (f:File {path: $file_id})
                MERGE (t:Type {full_name: $full_name})
                SET t.name = $name,
                    t.line = $line,
                    t.isExported = $isExported,
                    t.definition = $definition,
                    t.updated_at = datetime()
                MERGE (f)-[:DEFINES]->(t)
                """,
                file_id=file_id,
                full_name=full_name,
                name=type_alias['name'],
                line=type_alias.get('line', 0),
                isExported=type_alias.get('isExported', False),
                definition=type_alias.get('type', '')
            )
            
        self.processed_types.add(full_name)
        
    async def _create_function_node(self, function: Dict[str, Any], 
                                  file_id: str, module_name: str):
        """Create JSFunction node"""
        if module_name:
            full_name = f"{module_name}.{function['name']}"
        else:
            full_name = function['name']
        
        if full_name in self.processed_functions:
            return
            
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (f:File {path: $file_id})
                MERGE (fn:JSFunction {full_name: $full_name})
                SET fn.name = $name,
                    fn.line = $line,
                    fn.isExported = $isExported,
                    fn.isDefault = $isDefault,
                    fn.isAsync = $isAsync,
                    fn.parameters = $params,
                    fn.returnType = $returnType,
                    fn.updated_at = datetime()
                MERGE (f)-[:DEFINES]->(fn)
                """,
                file_id=file_id,
                full_name=full_name,
                name=function['name'],
                line=function.get('line', 0),
                isExported=function.get('isExported', False),
                isDefault=function.get('isDefault', False),
                isAsync=function.get('isAsync', False),
                params=json.dumps(function.get('parameters', [])),
                returnType=function.get('returnType')
            )
            
        self.processed_functions.add(full_name)
        
    async def _create_class_node(self, class_info: Dict[str, Any], 
                               file_id: str, module_name: str):
        """Create JSClass node"""
        if module_name:
            full_name = f"{module_name}.{class_info['name']}"
        else:
            full_name = class_info['name']
        
        if full_name in self.processed_classes:
            return
            
        async with self.driver.session() as session:
            # Create JSClass node
            await session.run(
                """
                MATCH (f:File {path: $file_id})
                MERGE (c:JSClass {full_name: $full_name})
                SET c.name = $name,
                    c.line = $line,
                    c.isExported = $isExported,
                    c.isDefault = $isDefault,
                    c.isAbstract = $isAbstract,
                    c.extends = $extends,
                    c.updated_at = datetime()
                MERGE (f)-[:DEFINES]->(c)
                """,
                file_id=file_id,
                full_name=full_name,
                name=class_info['name'],
                line=class_info.get('line', 0),
                isExported=class_info.get('isExported', False),
                isDefault=class_info.get('isDefault', False),
                isAbstract=class_info.get('isAbstract', False),
                extends=class_info.get('extends')
            )
            
            # Create Method nodes
            for member in class_info.get('members', []):
                if not member:  # Skip empty members
                    continue
                    
                # Debug logging
                logger.debug(f"Processing member in class {full_name}: {member}")
                    
                # For methods: member has keys like name, visibility, isStatic, isAsync, parameters, returnType
                # and a 'type' field set to 'method'
                # For properties: member has keys like name, visibility, isStatic, isReadonly, type (the TS type)
                # and a 'type' field set to 'property'
                
                member_kind = member.get('type')  # This will be 'method' or 'property'
                
                if member_kind == 'method':
                    try:
                        member_name = member.get('name', 'unknown')
                        await session.run(
                            """
                            MATCH (c:JSClass {full_name: $class_name})
                            MERGE (m:Method {full_name: $method_name})
                            SET m.name = $name,
                                m.visibility = $visibility,
                                m.isStatic = $isStatic,
                                m.isAsync = $isAsync,
                                m.parameters = $params,
                                m.returnType = $returnType
                            MERGE (c)-[:HAS_METHOD]->(m)
                            """,
                            class_name=full_name,
                            method_name=f"{full_name}.{member_name}",
                            name=member_name,
                            visibility=member.get('visibility', 'public'),
                            isStatic=member.get('isStatic', False),
                            isAsync=member.get('isAsync', False),
                            params=json.dumps(member.get('parameters', [])),
                            returnType=member.get('returnType')
                        )
                    except Exception as e:
                        logger.error(f"Error creating method node for {full_name}.{member.get('name', 'unknown')}: {e}")
                        logger.error(f"Member data: {member}")
                        raise
                elif member_kind == 'property':
                    try:
                        member_name = member.get('name', 'unknown')
                        # The parser now uses 'propertyType' for the TypeScript type
                        await session.run(
                            """
                            MATCH (c:JSClass {full_name: $class_name})
                            MERGE (p:Property {full_name: $property_name})
                            SET p.name = $name,
                                p.visibility = $visibility,
                                p.isStatic = $isStatic,
                                p.isReadonly = $isReadonly,
                                p.type = $propType
                            MERGE (c)-[:HAS_PROPERTY]->(p)
                            """,
                            class_name=full_name,
                            property_name=f"{full_name}.{member_name}",
                            name=member_name,
                            visibility=member.get('visibility', 'public'),
                            isStatic=member.get('isStatic', False),
                            isReadonly=member.get('isReadonly', False),
                            propType=member.get('propertyType')  # Use propertyType field
                        )
                    except Exception as e:
                        logger.error(f"Error creating property node for {full_name}.{member.get('name', 'unknown')}: {e}")
                        logger.error(f"Member data: {member}")
                        raise
                else:
                    # Log unexpected member types
                    logger.warning(f"Unexpected member type in class {full_name}: {member_kind}")
                    
            # Create implements relationships
            for implemented in class_info.get('implements', []):
                await session.run(
                    """
                    MATCH (c:JSClass {full_name: $full_name})
                    MERGE (i:Interface {name: $interface_name})
                    MERGE (c)-[:IMPLEMENTS]->(i)
                    """,
                    full_name=full_name,
                    interface_name=implemented
                )
                
        self.processed_classes.add(full_name)
        
    async def _process_imports(self, imports: List[Dict[str, Any]], file_id: str):
        """Process import statements"""
        async with self.driver.session() as session:
            for import_info in imports:
                module = import_info.get('module', '')
                
                # Skip external modules
                if module.startswith('.'):
                    # Create Module node for relative imports
                    await session.run(
                        """
                        MATCH (f:File {path: $file_id})
                        MERGE (m:Module {name: $module})
                        MERGE (f)-[:IMPORTS]->(m)
                        """,
                        file_id=file_id,
                        module=module
                    )
                    
    async def _process_exports(self, exports: List[Dict[str, Any]], file_id: str):
        """Process export statements including barrel exports"""
        logger.info(f"=== START _process_exports for file_id: {file_id} ===")
        
        if not exports:
            logger.info(f"No exports to process for file_id: {file_id}")
            return
            
        logger.info(f"Processing {len(exports)} exports for file_id: {file_id}")
        logger.info(f"Export data: {json.dumps(exports, indent=2)}")
            
        async with self.driver.session() as session:
            # First get file info for debugging
            file_info_result = await session.run("""
                MATCH (f:File {path: $file_id})
                RETURN f.path as path, f.module as module, f.name as name
            """, file_id=file_id)
            file_info = await file_info_result.single()
            if file_info:
                logger.info(f"Processing exports for file: {file_info['path']} (module: {file_info['module']})")
            
            for i, export_info in enumerate(exports):
                logger.info(f"\nProcessing export {i+1}/{len(exports)}: {export_info}")
                
                # Check if it's a re-export (barrel export)
                if export_info.get('from'):
                    logger.info(f"Found barrel export: {export_info}")
                    # This is a re-export like: export { X } from './Y'
                    source_module = export_info['from']
                    
                    # The parser gives us the export info directly, not in a 'named' array
                    if export_info.get('all'):
                        # This is export * from './X'
                        await self._process_export_all(session, file_id, source_module)
                    else:
                        # This is a named export - process it directly
                        await self._process_single_barrel_export(
                            session, file_id, export_info, source_module
                        )
                    continue
                    
                # Handle non-barrel exports (direct exports)
                if export_info.get('default'):
                    # This is a default export like: export default FormInput
                    logger.info(f"Processing default export: {export_info}")
                    expression = export_info.get('expression', '')
                    
                    # Mark the component as the default export
                    await session.run("""
                        MATCH (f:File {path: $file_id})
                        MATCH (f)-[:DEFINES]->(item)
                        WHERE item.name = $expression
                        SET item.isDefault = true
                        RETURN item.name as itemName, labels(item) as itemLabels
                    """, file_id=file_id, expression=expression)
                    
                elif export_info.get('name'):
                    # This is a named export (not from another module)
                    logger.info(f"Processing named export: {export_info}")
                    # Mark the item as exported
                    await session.run("""
                        MATCH (f:File {path: $file_id})
                        MATCH (f)-[:DEFINES]->(item)
                        WHERE item.name = $name
                        SET item.isExported = true
                    """, file_id=file_id, name=export_info['name'])
                        
        logger.info(f"=== END _process_exports for file_id: {file_id} ===")
        
    async def _process_single_barrel_export(self, session, file_id: str, 
                                          named_export: Dict[str, Any], 
                                          source_module: str):
        """Process a single named barrel export"""
        logger.info(f"Processing barrel export: {named_export} from {source_module}")
        
        # Handle: export { X as Y } from 'Z' or export { X } from 'Y'
        # Parser gives us: { name: 'X', as: 'Y' } for export { X as Y } from 'Z'
        if named_export.get('as'):
            # export { X as Y } from './Z'
            source_name = named_export['name']  # The original name in the source module
            exported_name = named_export['as']  # The name it's exported as
            logger.info(f"Export with rename: {source_name} as {exported_name}")
        else:
            # export { X } from './Y'
            exported_name = named_export['name']
            source_name = named_export['name']
            logger.info(f"Direct export: {exported_name}")
            
        # Resolve the target module
        target_module = await self._resolve_module_path(session, file_id, source_module)
        if not target_module:
            logger.warning(f"Could not resolve module path: {source_module}")
            return
            
        logger.info(f"Creating EXPORTS relationship: {exported_name} from {target_module} (source: {source_name})")
        
        # Try to find the actual item
        # First, try to find files that match the target module or contain it
        # This handles both exact module matches and file-specific modules
        if source_name == 'default':
            result = await session.run("""
                MATCH (source_file:File)-[:DEFINES]->(item)
                WHERE (source_file.module = $target_module OR 
                       source_file.module STARTS WITH $target_module + '.' OR
                       source_file.module = substring($target_module, 0, size($target_module) - size(split($target_module, '.')[-1]) - 1))
                      AND item.isDefault = true
                WITH source_file, item
                ORDER BY 
                    CASE WHEN source_file.module = $target_module THEN 0
                         WHEN source_file.name STARTS WITH 'index.' THEN 1
                         ELSE 2 END,
                    source_file.module
                LIMIT 1
                MATCH (current_file:File {path: $file_id})
                MERGE (current_file)-[exp:EXPORTS {name: $exported_name}]->(item)
                SET exp.sourceModule = $target_module,
                    exp.sourceName = $source_name,
                    exp.isBarrelExport = true
                RETURN item.name as itemName, labels(item) as itemLabels, source_file.module as sourceModule
            """, 
            file_id=file_id, 
            target_module=target_module,
            source_name=source_name,
            exported_name=exported_name)
        else:
            # For named exports, match by name
            # Try exact module match first, then check parent modules for barrel exports
            result = await session.run("""
                MATCH (source_file:File)-[:DEFINES]->(item)
                WHERE (source_file.module = $target_module OR 
                       source_file.module STARTS WITH $target_module + '.' OR
                       source_file.module = substring($target_module, 0, size($target_module) - size(split($target_module, '.')[-1]) - 1))
                      AND item.name = $source_name
                WITH source_file, item
                ORDER BY 
                    CASE WHEN source_file.module = $target_module THEN 0
                         WHEN source_file.name STARTS WITH 'index.' THEN 1
                         ELSE 2 END,
                    source_file.module
                LIMIT 1
                MATCH (current_file:File {path: $file_id})
                MERGE (current_file)-[exp:EXPORTS {name: $exported_name}]->(item)
                SET exp.sourceModule = $target_module,
                    exp.sourceName = $source_name,
                    exp.isBarrelExport = true
                RETURN item.name as itemName, labels(item) as itemLabels, source_file.module as sourceModule
            """, 
            file_id=file_id, 
            target_module=target_module,
            source_name=source_name,
            exported_name=exported_name)
        
        record = await result.single()
        if record:
            logger.info(f"Successfully created EXPORTS relationship to {record['itemName']} ({record['itemLabels']}) from module {record.get('sourceModule', 'unknown')}")
        else:
            logger.warning(f"Item not found: {source_name} in module {target_module}")
            # Create placeholder
            await session.run("""
                MATCH (current:File {path: $file_id})
                MERGE (placeholder:ExportPlaceholder {
                    name: $exported_name,
                    sourceModule: $target_module,
                    sourceName: $source_name
                })
                MERGE (current)-[:EXPORTS {
                    name: $exported_name,
                    isBarrelExport: true,
                    isPlaceholder: true
                }]->(placeholder)
            """, 
            file_id=file_id,
            exported_name=exported_name,
            target_module=target_module,
            source_name=source_name)
            logger.info(f"Created placeholder for missing export: {exported_name}")
            
    async def _process_export_all(self, session, file_id: str, source_module: str):
        """Process export * from './X'"""
        target_module = await self._resolve_module_path(session, file_id, source_module)
        if not target_module:
            logger.warning(f"Could not resolve module path: {source_module}")
            return
            
        logger.info(f"Processing namespace export: export * from '{source_module}'")
        # Find the source file that corresponds to the target module
        # First try exact match
        result = await session.run("""
            MATCH (current:File {path: $file_id})
            OPTIONAL MATCH (source:File {module: $target_module})
            OPTIONAL MATCH (index:File) 
            WHERE index.module = $target_module AND index.name = 'index.ts'
            WITH current, COALESCE(source, index) as target_file
            WHERE target_file IS NOT NULL
            MERGE (current)-[:EXPORTS_ALL_FROM]->(target_file)
            RETURN target_file.path as path
        """, file_id=file_id, target_module=target_module)
        
        record = await result.single()
        if record:
            logger.info(f"Created EXPORTS_ALL_FROM relationship to file: {record['path']}")
        else:
            logger.warning(f"Could not find file for module: {target_module}")
        
    async def _process_jsx_elements(self, jsx_elements: List[Dict[str, Any]], file_id: str):
        """Process JSX elements to track component usage"""
        if not jsx_elements:
            return
            
        logger.info(f"Processing {len(jsx_elements)} JSX elements for file {file_id}")
        
        async with self.driver.session() as session:
            for jsx_element in jsx_elements:
                tag_name = jsx_element.get('tagName', '')
                is_custom = jsx_element.get('isCustomComponent', False)
                
                # Only process custom components (not HTML elements)
                if is_custom and tag_name:
                    # Create a USES_COMPONENT relationship
                    result = await session.run("""
                        MATCH (f:File {path: $file_id})
                        MATCH (c:Component {name: $component_name})
                        MERGE (f)-[u:USES_COMPONENT {line: $line}]->(c)
                        RETURN c.name as name
                    """, 
                    file_id=file_id,
                    component_name=tag_name,
                    line=jsx_element.get('line', 0))
                    
                    record = await result.single()
                    if record:
                        logger.debug(f"Created USES_COMPONENT relationship for {tag_name}")
                    else:
                        # Component not found, but that's ok - it might be imported from external library
                        logger.debug(f"Component {tag_name} not found in knowledge graph")
        
    async def _resolve_module_path(self, session, file_id: str, source_module: str) -> Optional[str]:
        """Resolve a module path to its full module name"""
        logger.info(f"Resolving module path: {source_module} from file_id: {file_id}")
        
        if not source_module.startswith('.'):
            # Absolute import
            resolved = source_module.replace('/', '.')
            logger.info(f"Absolute import resolved to: {resolved}")
            return resolved
            
        # Get the current file's module
        file_result = await session.run("""
            MATCH (f:File {path: $file_id})
            RETURN f.module as module, f.path as path
        """, file_id=file_id)
        file_record = await file_result.single()
        
        if not file_record:
            logger.error(f"Could not find file with path: {file_id}")
            return None
            
        current_module = file_record['module']
        logger.info(f"Current module: {current_module}, path: {file_record['path']}")
        
        # Resolve relative import
        if source_module.startswith('./'):
            # Same directory as current file
            base_module = current_module
            relative_part = source_module[2:]
        elif source_module.startswith('../'):
            # Parent directory(ies)
            levels_up = source_module.count('../')
            parts = current_module.split('.')
            # Go up 'levels_up' directories from current module
            if len(parts) > levels_up:
                base_module = '.'.join(parts[:-levels_up])
            else:
                base_module = ''
            relative_part = source_module.replace('../', '')
        else:
            # Just '.' - same as current module
            base_module = current_module
            relative_part = ''
        
        # Clean up the relative part
        if relative_part.endswith('.ts') or relative_part.endswith('.tsx'):
            relative_part = relative_part[:-3] if relative_part.endswith('.ts') else relative_part[:-4]
        elif relative_part.endswith('.js') or relative_part.endswith('.jsx'):
            relative_part = relative_part[:-3] if relative_part.endswith('.js') else relative_part[:-4]
        
        # Build the target module
        if base_module and relative_part:
            resolved = f"{base_module}.{relative_part.replace('/', '.')}"
        elif relative_part:
            resolved = relative_part.replace('/', '.')
        else:
            resolved = base_module
            
        logger.info(f"Resolved module path: {source_module} -> {resolved}")
        
        # Check if the resolved module is a directory (barrel export)
        # If so, try to find an index file or the actual file
        result = await session.run("""
            MATCH (f:File)
            WHERE f.module = $module OR 
                  f.module = $module + '.index' OR
                  f.module STARTS WITH $module + '.'
            RETURN f.module as module, f.path as path, f.name as name
            ORDER BY f.path
        """, module=resolved)
        
        files = []
        async for record in result:
            files.append(record)
            
        logger.info(f"Found {len(files)} files matching module {resolved}")
        for f in files:
            logger.info(f"  - {f['path']} (module: {f['module']})")
            
        # If we found an exact match, use it
        exact_match = None
        index_match = None
        for f in files:
            if f['module'] == resolved:
                # Check if it's an index file
                if f['name'].startswith('index.'):
                    index_match = f['module']
                else:
                    exact_match = f['module']
                    
        # For barrel exports from index files, we want the directory module
        if index_match and not exact_match:
            logger.info(f"Found index file for module {resolved}, keeping directory module")
            return resolved
        elif exact_match:
            logger.info(f"Found exact match for module {resolved}")
            return exact_match
            
        # If no exact match, it might be a file in that module
        # For example, './FormInput' from 'src.components.form' should resolve to 'src.components.form.FormInput'
        file_module = f"{resolved}.{relative_part.split('/')[-1]}" if relative_part else resolved
        
        # Check if this file exists
        file_check = await session.run("""
            MATCH (f:File)
            WHERE f.module = $module
            RETURN f.module as module
            LIMIT 1
        """, module=file_module)
        
        file_record = await file_check.single()
        if file_record:
            logger.info(f"Found file module: {file_module}")
            return file_module
            
        return resolved
        
    async def _create_module_relationships(self, repo_id: str):
        """Create relationships between modules based on imports"""
        async with self.driver.session() as session:
            # Link relative imports to actual files
            await session.run(
                """
                MATCH (r:Repository)-[:CONTAINS]->(f1:File)-[:IMPORTS]->(m:Module)
                MATCH (r)-[:CONTAINS]->(f2:File)
                WHERE m.name = f2.module OR 
                      m.name = '.' + f2.module OR
                      m.name = './' + f2.module
                MERGE (f1)-[:IMPORTS_FILE]->(f2)
                """
            )
            
    def clone_repository(self, repo_url: str, target_dir: str, branch: Optional[str] = None) -> str:
        """Clone a repository"""
        logger.info(f"Cloning repository: {repo_url}")
        
        if os.path.exists(target_dir):
            logger.info(f"Removing existing directory: {target_dir}")
            shutil.rmtree(target_dir, ignore_errors=True)
            
        # Clone with shallow clone for efficiency
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["-b", branch])
        clone_cmd.extend([repo_url, target_dir])
        
        try:
            subprocess.run(clone_cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully cloned to: {target_dir}")
            return target_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise


# Example usage
if __name__ == "__main__":
    async def main():
        load_dotenv()
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        async with TypeScriptNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password) as extractor:
            # Example: Parse a local directory
            result = await extractor.parse_directory(
                "/path/to/typescript/project",
                "my-typescript-project"
            )
            
            print(json.dumps(result, indent=2))
            
    asyncio.run(main())