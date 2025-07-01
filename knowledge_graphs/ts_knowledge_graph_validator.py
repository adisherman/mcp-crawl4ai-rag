"""
TypeScript/React Knowledge Graph Validator

Validates AI-generated TypeScript/JavaScript/React code against Neo4j knowledge graph.
Checks imports, components, hooks, types, and functions.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from neo4j import AsyncGraphDatabase

from ts_script_analyzer import TypeScriptScriptAnalyzer

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID = "INVALID" 
    UNCERTAIN = "UNCERTAIN"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class ValidationResult:
    """Result of validating a single element"""
    status: ValidationStatus
    confidence: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ComponentValidation:
    """Validation result for React component usage"""
    component_name: str
    props_used: List[str]
    validation: ValidationResult
    expected_props: List[str] = field(default_factory=list)
    missing_required_props: List[str] = field(default_factory=list)
    unknown_props: List[str] = field(default_factory=list)


@dataclass
class HookValidation:
    """Validation result for React hook usage"""
    hook_name: str
    validation: ValidationResult
    hook_rules_violated: List[str] = field(default_factory=list)


@dataclass
class TypeValidation:
    """Validation result for TypeScript type usage"""
    type_name: str
    kind: str  # 'interface', 'type', 'implements', etc.
    validation: ValidationResult
    expected_properties: List[str] = field(default_factory=list)


@dataclass
class FunctionValidation:
    """Validation result for function/method calls"""
    function_name: str
    module: Optional[str]
    args_count: int
    validation: ValidationResult
    expected_params: List[str] = field(default_factory=list)


@dataclass
class ImportValidation:
    """Validation result for imports"""
    module: str
    imported_items: List[Dict[str, str]]
    validation: ValidationResult
    available_exports: List[str] = field(default_factory=list)


@dataclass
class TypeScriptValidationResult:
    """Complete validation results for a TypeScript/React script"""
    script_path: str
    analysis_result: Dict[str, Any]
    import_validations: List[ImportValidation] = field(default_factory=list)
    component_validations: List[ComponentValidation] = field(default_factory=list)
    hook_validations: List[HookValidation] = field(default_factory=list)
    type_validations: List[TypeValidation] = field(default_factory=list)
    function_validations: List[FunctionValidation] = field(default_factory=list)
    overall_confidence: float = 0.0
    hallucinations_detected: List[Dict[str, Any]] = field(default_factory=list)


class TypeScriptKnowledgeGraphValidator:
    """Validates TypeScript/React code against Neo4j knowledge graph"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.analyzer = TypeScriptScriptAnalyzer()
        
        # React hooks that have specific rules
        self.hooks_with_rules = {
            'useState': ['Must be called at top level', 'Returns array with state and setter'],
            'useEffect': ['Must be called at top level', 'Dependencies array recommended'],
            'useContext': ['Must be called at top level', 'Context must be created first'],
            'useReducer': ['Must be called at top level', 'Requires reducer function'],
            'useCallback': ['Must be called at top level', 'Dependencies array required'],
            'useMemo': ['Must be called at top level', 'Dependencies array required'],
            'useRef': ['Must be called at top level', 'Returns mutable ref object'],
            'useImperativeHandle': ['Must be called at top level', 'Used with forwardRef'],
            'useLayoutEffect': ['Must be called at top level', 'Runs synchronously'],
            'useDebugValue': ['Must be called at top level', 'For custom hooks only']
        }
        
        # Common external libraries to skip validation
        self.external_libraries = {
            'react', 'react-dom', 'react-router', 'react-router-dom',
            'axios', 'lodash', 'moment', 'express', 'next', 'vue', 'angular',
            '@mui/material', 'antd', 'styled-components', '@emotion/react'
        }
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        logger.info("TypeScript validator initialized with Neo4j")
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    async def validate_script(self, script_path: str) -> TypeScriptValidationResult:
        """Validate a TypeScript/React script against knowledge graph"""
        logger.info(f"Validating TypeScript script: {script_path}")
        
        # Analyze the script
        analysis_result = self.analyzer.analyze_script(script_path)
        
        # Create result object
        result = TypeScriptValidationResult(
            script_path=script_path,
            analysis_result=analysis_result
        )
        
        # Validate each type of element
        await self._validate_imports(analysis_result['imports'], result)
        await self._validate_components(analysis_result['component_uses'], result)
        await self._validate_hooks(analysis_result['hook_uses'], result)
        await self._validate_types(analysis_result['type_uses'], result)
        await self._validate_functions(analysis_result['function_calls'], result)
        await self._validate_classes(analysis_result['class_instantiations'], result)
        
        # Calculate overall confidence
        result.overall_confidence = self._calculate_overall_confidence(result)
        
        # Identify hallucinations
        self._identify_hallucinations(result)
        
        return result
    
    async def _validate_imports(self, imports: Dict[str, List[Dict]], result: TypeScriptValidationResult):
        """Validate import statements"""
        for module, items in imports.items():
            # Skip external libraries
            if self._is_external_library(module):
                validation = ImportValidation(
                    module=module,
                    imported_items=items,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"External library '{module}' - skipping validation"
                    )
                )
                result.import_validations.append(validation)
                continue
            
            # Check if module exists in knowledge graph
            async with self.driver.session() as session:
                # Try to find the module/file
                module_result = await session.run("""
                    MATCH (f:File)
                    WHERE f.module = $module OR f.path CONTAINS $module
                    RETURN f.path as path, f.module as module
                    LIMIT 1
                """, module=module)
                
                module_record = await module_result.single()
                
                if not module_record:
                    validation = ImportValidation(
                        module=module,
                        imported_items=items,
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Module '{module}' not found in knowledge graph"
                        )
                    )
                else:
                    # Get available exports from the module
                    exports_result = await session.run("""
                        MATCH (f:File {module: $module})-[:DEFINES]->(item)
                        WHERE item:Component OR item:JSFunction OR item:JSClass OR item:Interface OR item:Type
                        AND (item.exported = true OR item.exported IS NULL)
                        RETURN item.name as name, labels(item)[0] as type
                    """, module=module_record['module'])
                    
                    available_exports = []
                    async for record in exports_result:
                        available_exports.append(record['name'])
                    
                    # Validate each imported item
                    all_valid = True
                    invalid_items = []
                    
                    for item in items:
                        item_name = item.get('name', item.get('local', ''))
                        if item_name != '*' and item_name not in available_exports:
                            all_valid = False
                            invalid_items.append(item_name)
                    
                    if all_valid:
                        validation = ImportValidation(
                            module=module,
                            imported_items=items,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=f"All imports from '{module}' are valid"
                            ),
                            available_exports=available_exports
                        )
                    else:
                        validation = ImportValidation(
                            module=module,
                            imported_items=items,
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.3,
                                message=f"Invalid imports from '{module}': {invalid_items}",
                                suggestions=[f"Available exports: {', '.join(available_exports)}"]
                            ),
                            available_exports=available_exports
                        )
                
                result.import_validations.append(validation)
    
    async def _validate_components(self, component_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate React component usage"""
        for comp_use in component_uses:
            comp_name = comp_use['name']
            props_used = comp_use.get('props', [])
            
            async with self.driver.session() as session:
                # Find the component in knowledge graph
                comp_result = await session.run("""
                    MATCH (c:Component {name: $name})
                    RETURN c.full_name as full_name, c.type as type
                    LIMIT 1
                """, name=comp_name)
                
                comp_record = await comp_result.single()
                
                if not comp_record:
                    validation = ComponentValidation(
                        component_name=comp_name,
                        props_used=props_used,
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Component '{comp_name}' not found in knowledge graph"
                        )
                    )
                else:
                    # Get component props if available
                    props_result = await session.run("""
                        MATCH (c:Component {full_name: $full_name})-[:HAS_PROPS]->(p)
                        RETURN p.properties as properties
                    """, full_name=comp_record['full_name'])
                    
                    props_record = await props_result.single()
                    expected_props = props_record['properties'] if props_record else []
                    
                    # Validate props usage
                    unknown_props = [p for p in props_used if p not in expected_props]
                    
                    if not unknown_props or not expected_props:  # No props info or all props valid
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.9 if expected_props else 0.7,
                                message=f"Component '{comp_name}' usage is valid"
                            ),
                            expected_props=expected_props
                        )
                    else:
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.5,
                                message=f"Unknown props used in '{comp_name}': {unknown_props}",
                                suggestions=[f"Expected props: {', '.join(expected_props)}"]
                            ),
                            expected_props=expected_props,
                            unknown_props=unknown_props
                        )
                
                result.component_validations.append(validation)
    
    async def _validate_hooks(self, hook_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate React hook usage"""
        for hook_use in hook_uses:
            hook_name = hook_use['name']
            
            # Check if it's a known React hook
            if hook_name in self.hooks_with_rules:
                validation = HookValidation(
                    hook_name=hook_name,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"React hook '{hook_name}' is valid",
                        details={'rules': self.hooks_with_rules[hook_name]}
                    )
                )
            else:
                # Check if it's a custom hook in the knowledge graph
                async with self.driver.session() as session:
                    hook_result = await session.run("""
                        MATCH (h:Hook {name: $name})
                        RETURN h.custom as custom
                        LIMIT 1
                    """, name=hook_name)
                    
                    hook_record = await hook_result.single()
                    
                    if hook_record:
                        validation = HookValidation(
                            hook_name=hook_name,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.9,
                                message=f"Custom hook '{hook_name}' found in knowledge graph"
                            )
                        )
                    else:
                        validation = HookValidation(
                            hook_name=hook_name,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.6,
                                message=f"Unknown hook '{hook_name}' - might be a valid custom hook"
                            )
                        )
            
            result.hook_validations.append(validation)
    
    async def _validate_types(self, type_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate TypeScript type usage"""
        for type_use in type_uses:
            type_name = type_use['name']
            kind = type_use['kind']
            
            async with self.driver.session() as session:
                # Check for interface or type in knowledge graph
                type_result = await session.run("""
                    MATCH (t)
                    WHERE (t:Interface OR t:Type) AND t.name = $name
                    RETURN t.name as name, labels(t)[0] as type, 
                           t.properties as properties
                    LIMIT 1
                """, name=type_name)
                
                type_record = await type_result.single()
                
                if type_record:
                    validation = TypeValidation(
                        type_name=type_name,
                        kind=kind,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=1.0,
                            message=f"{type_record['type']} '{type_name}' is valid"
                        ),
                        expected_properties=type_record.get('properties', [])
                    )
                else:
                    # Check if it's a built-in type
                    if type_name in ['string', 'number', 'boolean', 'any', 'void', 'never', 'unknown']:
                        validation = TypeValidation(
                            type_name=type_name,
                            kind=kind,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=f"Built-in type '{type_name}' is valid"
                            )
                        )
                    else:
                        validation = TypeValidation(
                            type_name=type_name,
                            kind=kind,
                            validation=ValidationResult(
                                status=ValidationStatus.NOT_FOUND,
                                confidence=0.0,
                                message=f"Type '{type_name}' not found in knowledge graph"
                            )
                        )
                
                result.type_validations.append(validation)
    
    async def _validate_functions(self, function_calls: List[Dict], result: TypeScriptValidationResult):
        """Validate function calls"""
        for func_call in function_calls:
            func_name = func_call['name']
            module = func_call.get('module')
            args_count = func_call.get('args_count', 0)
            
            # Skip if it's from an external library
            if module and self._is_external_library(module):
                continue
            
            async with self.driver.session() as session:
                # Find the function in knowledge graph
                func_result = await session.run("""
                    MATCH (f:JSFunction {name: $name})
                    RETURN f.full_name as full_name, f.params as params
                    LIMIT 1
                """, name=func_name)
                
                func_record = await func_result.single()
                
                if func_record:
                    expected_params = func_record.get('params', [])
                    validation = FunctionValidation(
                        function_name=func_name,
                        module=module,
                        args_count=args_count,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"Function '{func_name}' is valid"
                        ),
                        expected_params=expected_params
                    )
                else:
                    validation = FunctionValidation(
                        function_name=func_name,
                        module=module,
                        args_count=args_count,
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Function '{func_name}' not found in knowledge graph"
                        )
                    )
                
                result.function_validations.append(validation)
    
    async def _validate_classes(self, class_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate class instantiations"""
        for class_use in class_uses:
            class_name = class_use['name']
            module = class_use.get('module')
            
            # Skip if it's from an external library
            if module and self._is_external_library(module):
                continue
            
            async with self.driver.session() as session:
                # Find the class in knowledge graph
                class_result = await session.run("""
                    MATCH (c:JSClass {name: $name})
                    RETURN c.full_name as full_name
                    LIMIT 1
                """, name=class_name)
                
                class_record = await class_result.single()
                
                if class_record:
                    validation = FunctionValidation(
                        function_name=class_name,
                        module=module,
                        args_count=class_use.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"Class '{class_name}' is valid"
                        )
                    )
                else:
                    validation = FunctionValidation(
                        function_name=class_name,
                        module=module,
                        args_count=class_use.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Class '{class_name}' not found in knowledge graph"
                        )
                    )
                
                result.function_validations.append(validation)
    
    def _is_external_library(self, module: str) -> bool:
        """Check if a module is an external library"""
        # Direct match
        if module in self.external_libraries:
            return True
        
        # Check scoped packages
        if module.startswith('@'):
            base_module = '/'.join(module.split('/')[:2])
            if base_module in self.external_libraries:
                return True
        else:
            base_module = module.split('/')[0]
            if base_module in self.external_libraries:
                return True
        
        return False
    
    def _calculate_overall_confidence(self, result: TypeScriptValidationResult) -> float:
        """Calculate overall confidence score"""
        all_validations = []
        
        # Collect all validation results
        all_validations.extend([v.validation for v in result.import_validations])
        all_validations.extend([v.validation for v in result.component_validations])
        all_validations.extend([v.validation for v in result.hook_validations])
        all_validations.extend([v.validation for v in result.type_validations])
        all_validations.extend([v.validation for v in result.function_validations])
        
        if not all_validations:
            return 1.0
        
        # Calculate weighted average
        total_confidence = sum(v.confidence for v in all_validations)
        return total_confidence / len(all_validations)
    
    def _identify_hallucinations(self, result: TypeScriptValidationResult):
        """Identify hallucinations in the validation results"""
        
        # Check imports
        for imp_val in result.import_validations:
            if imp_val.validation.status in [ValidationStatus.NOT_FOUND, ValidationStatus.INVALID]:
                result.hallucinations_detected.append({
                    'type': 'import',
                    'element': imp_val.module,
                    'message': imp_val.validation.message,
                    'confidence': 1.0 - imp_val.validation.confidence
                })
        
        # Check components
        for comp_val in result.component_validations:
            if comp_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'component',
                    'element': comp_val.component_name,
                    'message': comp_val.validation.message,
                    'confidence': 1.0 - comp_val.validation.confidence
                })
        
        # Check types
        for type_val in result.type_validations:
            if type_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'type',
                    'element': type_val.type_name,
                    'message': type_val.validation.message,
                    'confidence': 1.0 - type_val.validation.confidence
                })
        
        # Check functions
        for func_val in result.function_validations:
            if func_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'function',
                    'element': func_val.function_name,
                    'message': func_val.validation.message,
                    'confidence': 1.0 - func_val.validation.confidence
                })


async def validate_typescript_script(script_path: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> TypeScriptValidationResult:
    """Convenience function to validate a TypeScript script"""
    validator = TypeScriptKnowledgeGraphValidator(neo4j_uri, neo4j_user, neo4j_password)
    try:
        await validator.initialize()
        return await validator.validate_script(script_path)
    finally:
        await validator.close()


if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python ts_knowledge_graph_validator.py <script_path>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("NEO4J_PASSWORD not set in environment")
        sys.exit(1)
    
    # Run validation
    async def main():
        result = await validate_typescript_script(script_path, neo4j_uri, neo4j_user, neo4j_password)
        
        print(f"\n=== TypeScript Validation Results ===")
        print(f"Script: {result.script_path}")
        print(f"Overall Confidence: {result.overall_confidence:.2f}")
        
        if result.hallucinations_detected:
            print(f"\nHallucinations Detected: {len(result.hallucinations_detected)}")
            for h in result.hallucinations_detected:
                print(f"  - {h['type']}: {h['element']} - {h['message']}")
        else:
            print("\nNo hallucinations detected!")
    
    asyncio.run(main())