#!/usr/bin/env python3
"""
Test script to demonstrate improved relative import validation

This script tests the TypeScript validator with various import scenarios
to ensure false positives are reduced for relative imports.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from ts_knowledge_graph_validator import TypeScriptKnowledgeGraphValidator
from validator_config import ValidatorConfig
from dotenv import load_dotenv

load_dotenv()


async def test_relative_imports():
    """Test validation of various import scenarios"""
    
    # Create test TypeScript file with various imports
    test_code = """
import React from 'react';
import { useState, useEffect } from 'react';
import { Button } from './components/Button';
import { useAuth } from '../hooks/useAuth';
import { ApiService } from '@/services/api';
import { formatDate } from '../../utils/date';
import type { User } from './types/user';
import { nonExistentFunction } from 'made-up-library';

export function MyComponent() {
    const [count, setCount] = useState(0);
    const auth = useAuth();
    
    return (
        <div>
            <Button onClick={() => setCount(count + 1)}>
                Count: {count}
            </Button>
        </div>
    );
}
"""
    
    # Write test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
        f.write(test_code)
        test_file = f.name
    
    try:
        # Get Neo4j credentials
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if not neo4j_password:
            print("NEO4J_PASSWORD not set in environment")
            return
        
        # Test with default config (lenient mode)
        print("=== Testing with lenient mode (default) ===")
        config = ValidatorConfig(
            allow_missing_internal_modules=True,
            strict_internal_imports=False
        )
        
        validator = TypeScriptKnowledgeGraphValidator(
            neo4j_uri, neo4j_user, neo4j_password, config
        )
        
        await validator.initialize()
        result = await validator.validate_script(test_file)
        
        print(f"\nScript: {test_file}")
        print(f"Overall Confidence: {result.overall_confidence:.2f}")
        
        print("\nImport Validations:")
        for imp_val in result.import_validations:
            print(f"  - {imp_val.module}: {imp_val.validation.status.value}")
            print(f"    Confidence: {imp_val.validation.confidence:.2f}")
            print(f"    Message: {imp_val.validation.message}")
            if imp_val.validation.details:
                print(f"    Details: {imp_val.validation.details}")
        
        print(f"\nHallucinations Detected: {len(result.hallucinations_detected)}")
        for h in result.hallucinations_detected:
            print(f"  - {h['type']}: {h['element']}")
            print(f"    {h['message']}")
            print(f"    Confidence: {h['confidence']:.2f}")
        
        await validator.close()
        
        # Test with strict mode
        print("\n\n=== Testing with strict mode ===")
        strict_config = ValidatorConfig(
            allow_missing_internal_modules=False,
            strict_internal_imports=True
        )
        
        strict_validator = TypeScriptKnowledgeGraphValidator(
            neo4j_uri, neo4j_user, neo4j_password, strict_config
        )
        
        await strict_validator.initialize()
        strict_result = await strict_validator.validate_script(test_file)
        
        print(f"\nScript: {test_file}")
        print(f"Overall Confidence: {strict_result.overall_confidence:.2f}")
        
        print("\nImport Validations:")
        for imp_val in strict_result.import_validations:
            print(f"  - {imp_val.module}: {imp_val.validation.status.value}")
            print(f"    Confidence: {imp_val.validation.confidence:.2f}")
            print(f"    Message: {imp_val.validation.message}")
        
        print(f"\nHallucinations Detected: {len(strict_result.hallucinations_detected)}")
        for h in strict_result.hallucinations_detected:
            print(f"  - {h['type']}: {h['element']}")
            print(f"    {h['message']}")
            print(f"    Confidence: {h['confidence']:.2f}")
        
        await strict_validator.close()
        
    finally:
        # Clean up test file
        os.unlink(test_file)


if __name__ == "__main__":
    asyncio.run(test_relative_imports())