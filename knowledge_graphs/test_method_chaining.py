#!/usr/bin/env python3
"""
Test script for method chaining support in TypeScript Knowledge Graph Validator
"""

import asyncio
import os
from pathlib import Path
from method_chaining_support import MethodChainResolver


def test_method_chain_parsing():
    """Test parsing of method chains"""
    resolver = MethodChainResolver()
    
    test_cases = [
        ("z.string()", [("z", "string")]),
        ("z.string().email()", [("z", "string"), ("__previous__", "email")]),
        ("z.string().email().min(5)", [("z", "string"), ("__previous__", "email"), ("__previous__", "min")]),
        ("z.object({}).strict()", [("z", "object"), ("__previous__", "strict")]),
        ("z.array(z.string())", [("z", "array")]),
        ("z.string().refine(val => val.length > 0)", [("z", "string"), ("__previous__", "refine")]),
    ]
    
    print("Testing method chain parsing:")
    for input_str, expected in test_cases:
        result = resolver.parse_method_chain(input_str)
        print(f"  Input: {input_str}")
        print(f"  Expected: {expected}")
        print(f"  Result: {result}")
        print(f"  Status: {'✓' if result == expected else '✗'}")
        print()


def test_method_chain_validation():
    """Test validation of method chains"""
    resolver = MethodChainResolver()
    
    test_cases = [
        # Valid chains
        ("z.string()", "email", "zod", True),
        ("z.string()", "min", "zod", True),
        ("z.string().email()", "min", "zod", True),
        ("z.number()", "positive", "zod", True),
        ("z.boolean()", "refine", "zod", True),
        ("z.array(z.string())", "min", "zod", True),
        ("z.object({})", "strict", "zod", True),
        ("z.string().optional()", "nullable", "zod", True),
        
        # Invalid chains
        ("z.string()", "positive", "zod", False),  # positive is for numbers
        ("z.number()", "email", "zod", False),  # email is for strings
        ("z.boolean()", "min", "zod", False),  # min is not for booleans
        ("z.string()", "notAMethod", "zod", False),  # method doesn't exist
    ]
    
    print("\nTesting method chain validation:")
    for object_text, method_name, namespace, expected_valid in test_cases:
        is_valid, message, suggestions = resolver.validate_method_chain(object_text, method_name, namespace)
        print(f"  Chain: {object_text}.{method_name}()")
        print(f"  Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"  Result: {'Valid' if is_valid else 'Invalid'}")
        print(f"  Message: {message}")
        if suggestions:
            print(f"  Suggestions: {suggestions}")
        print(f"  Status: {'✓' if is_valid == expected_valid else '✗'}")
        print()


def test_chainable_detection():
    """Test detection of chainable method calls"""
    resolver = MethodChainResolver()
    
    test_cases = [
        ("z.string()", True),
        ("z.string().email()", True),
        ("myVariable", False),
        ("this.props", False),
        ("console.log('test')", True),
        ("arr.filter(x => x > 0)", True),
        ("obj.property", False),
    ]
    
    print("\nTesting chainable method call detection:")
    for text, expected in test_cases:
        result = resolver.is_chainable_method_call(text)
        print(f"  Text: {text}")
        print(f"  Expected: {expected}")
        print(f"  Result: {result}")
        print(f"  Status: {'✓' if result == expected else '✗'}")
        print()


async def test_integration_with_validator():
    """Test integration with the full validator"""
    from ts_knowledge_graph_validator import TypeScriptKnowledgeGraphValidator
    
    # Create test TypeScript code with method chains
    test_code = '''
import { z } from 'zod';

// Valid Zod chains
const emailSchema = z.string().email().min(5);
const ageSchema = z.number().positive().int();
const userSchema = z.object({
    name: z.string(),
    email: z.string().email(),
    age: z.number().min(18).max(100),
    isActive: z.boolean().optional()
}).strict();

// Invalid Zod chains (these should be flagged)
const badSchema1 = z.string().positive();  // positive is for numbers
const badSchema2 = z.number().email();     // email is for strings
const badSchema3 = z.boolean().min(5);     // min is not for booleans

// More complex valid chains
const complexSchema = z.string()
    .email()
    .refine(val => val.includes('@company.com'))
    .transform(val => val.toLowerCase());

const arraySchema = z.array(z.string()).min(1).max(10);
'''
    
    # Save test code to a temporary file
    test_file = Path("test_zod_chains.ts")
    test_file.write_text(test_code)
    
    try:
        # Initialize validator (using dummy Neo4j credentials for this test)
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        validator = TypeScriptKnowledgeGraphValidator(neo4j_uri, neo4j_user, neo4j_password)
        
        print("\nTesting integration with validator:")
        print("Note: This test requires a running Neo4j instance with the knowledge graph.")
        print("If Neo4j is not available, the test will show connection errors.\n")
        
        try:
            await validator.initialize()
            result = await validator.validate_script(str(test_file))
            
            print("Validation Results:")
            print(f"  Total function validations: {len(result.function_validations)}")
            print(f"  Valid: {sum(1 for v in result.function_validations if v.validation.status.value == 'VALID')}")
            print(f"  Invalid: {sum(1 for v in result.function_validations if v.validation.status.value == 'INVALID')}")
            print(f"  Hallucinations detected: {len(result.hallucinations_detected)}")
            
            print("\nMethod chain validations:")
            for validation in result.function_validations:
                if '.string().' in validation.function_name or '.number().' in validation.function_name or '.boolean().' in validation.function_name:
                    print(f"  {validation.function_name}: {validation.validation.status.value}")
                    print(f"    Message: {validation.validation.message}")
                    if validation.validation.suggestions:
                        print(f"    Suggestions: {validation.validation.suggestions}")
            
            await validator.close()
        except Exception as e:
            print(f"Could not connect to Neo4j: {e}")
            print("Skipping integration test.")
    
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()


def main():
    """Run all tests"""
    print("=" * 80)
    print("Method Chaining Support Tests")
    print("=" * 80)
    
    test_method_chain_parsing()
    test_method_chain_validation()
    test_chainable_detection()
    
    # Run async test
    asyncio.run(test_integration_with_validator())
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()