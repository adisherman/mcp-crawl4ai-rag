#!/usr/bin/env python3
"""Test built-in JavaScript object method validation"""

import asyncio
import os
import sys
from pathlib import Path
from ts_knowledge_graph_validator import TypeScriptKnowledgeGraphValidator
from dotenv import load_dotenv

load_dotenv()

# Test TypeScript code with various built-in method calls
TEST_CODE = """
// Test Array methods
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
const filtered = numbers.filter(n => n > 2);
const sum = numbers.reduce((a, b) => a + b, 0);
const sorted = numbers.toSorted(); // ES2023 method
const reversed = numbers.toReversed(); // ES2023 method
const invalid = numbers.filterr(n => n > 2); // Typo - should be caught

// Test String methods
const text = "Hello, World!";
const upper = text.toUpperCase();
const lower = text.toLowerCase();
const trimmed = text.trim();
const parts = text.split(',');
const replaced = text.replaceAll('o', '0'); // ES2021 method
const badMethod = text.lenght(); // Common typo - should be caught

// Test static methods
const arr = Array.from([1, 2, 3]);
const isArr = Array.isArray(arr);
const keys = Object.keys({a: 1, b: 2});
const entries = Object.entries({a: 1, b: 2});
const parsed = JSON.parse('{"key": "value"}');
const stringified = JSON.stringify({key: 'value'});
const random = Math.random();
const floored = Math.floor(3.7);
const invalidStatic = Array.filterr([1, 2, 3]); // Invalid static method

// Test prototype methods
const sliced = Array.prototype.slice.call(arguments, 1);
const stringified2 = Object.prototype.toString.call(arr);
const invalidProto = Array.prototype.filterr.call(arr); // Invalid prototype method

// Test DOM methods (browser environment)
const element = document.getElementById('test');
const elements = document.querySelectorAll('.class');
const created = document.createElement('div');

// Test console methods
console.log('Hello');
console.error('Error message');
console.warn('Warning');
console.invalidMethod('This should fail'); // Invalid console method

// Test with inferred types
const items = [1, 2, 3]; // Should infer Array type
const result = items.map(x => x * 2);
const names = ['Alice', 'Bob']; // Should infer Array type
const uppercased = names.map(name => name.toUpperCase());

// Test method on unknown variable
const myData = getData();
const processed = myData.process(); // Should be uncertain

function getData() {
    return { process: () => {} };
}
"""

async def test_builtin_validation():
    """Test the built-in method validation"""
    # Save test code to a file
    test_file = Path("/tmp/test_builtin_methods.ts")
    test_file.write_text(TEST_CODE)
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("NEO4J_PASSWORD not set in environment")
        return
    
    # Create validator
    validator = TypeScriptKnowledgeGraphValidator(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        await validator.initialize()
        print("Validating TypeScript code with built-in method calls...")
        result = await validator.validate_script(str(test_file))
        
        # Debug: Print analysis results
        print("\n=== Analysis Result ===")
        print(f"Method calls found: {len(result.analysis_result.get('method_calls', []))}")
        print(f"Function calls found: {len(result.analysis_result.get('function_calls', []))}")
        
        if result.analysis_result.get('method_calls'):
            print("\nMethod calls:")
            for mc in result.analysis_result['method_calls'][:5]:
                print(f"  - {mc.get('object', 'unknown')}.{mc.get('method', 'unknown')}")
        
        if result.analysis_result.get('function_calls'):
            print("\nFunction calls:")
            for fc in result.analysis_result['function_calls'][:5]:
                print(f"  - {fc.get('name', 'unknown')}")
        
        print("\n=== Validation Results ===")
        print(f"Overall Confidence: {result.overall_confidence:.2f}")
        
        print("\n=== Function/Method Validations ===")
        for val in result.function_validations:
            status_symbol = "✓" if val.validation.status.value == "VALID" else "✗"
            print(f"{status_symbol} {val.function_name}: {val.validation.message}")
            if val.validation.suggestions:
                print(f"  Suggestions: {val.validation.suggestions}")
        
        print("\n=== Hallucinations Detected ===")
        if result.hallucinations_detected:
            for h in result.hallucinations_detected:
                print(f"- {h['type']}: {h['element']} - {h['message']}")
        else:
            print("No hallucinations detected!")
        
        # Verify expected results
        print("\n=== Test Verification ===")
        
        # Check that valid methods passed
        valid_methods = ['map', 'filter', 'reduce', 'toUpperCase', 'toLowerCase', 'trim', 'split', 
                        'Array.from', 'Array.isArray', 'Object.keys', 'JSON.parse', 'Math.random',
                        'console.log', 'document.getElementById']
        
        # Check that invalid methods were caught
        expected_errors = ['filterr', 'lenght', 'Array.filterr', 'console.invalidMethod', 'Array.prototype.filterr']
        
        passed = 0
        failed = 0
        
        for method in valid_methods:
            found = any(method in val.function_name and val.validation.status.value == "VALID" 
                       for val in result.function_validations)
            if found:
                print(f"✓ {method} correctly validated as VALID")
                passed += 1
            else:
                print(f"✗ {method} was not validated as VALID")
                failed += 1
        
        for method in expected_errors:
            found = any(method in val.function_name and val.validation.status.value in ["INVALID", "NOT_FOUND"]
                       for val in result.function_validations)
            if found:
                print(f"✓ {method} correctly identified as INVALID")
                passed += 1
            else:
                print(f"✗ {method} was not caught as invalid")
                failed += 1
        
        print(f"\nTest Results: {passed} passed, {failed} failed")
        
    finally:
        await validator.close()
        # Clean up test file
        test_file.unlink()

if __name__ == "__main__":
    asyncio.run(test_builtin_validation())