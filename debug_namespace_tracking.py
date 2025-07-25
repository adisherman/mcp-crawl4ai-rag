#!/usr/bin/env python3
"""Debug namespace tracking in the validator"""

import asyncio
import os
import sys
from pathlib import Path

# Add the knowledge_graphs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'knowledge_graphs'))

from ts_knowledge_graph_validator import TypeScriptKnowledgeGraphValidator
from validator_config import get_project_config

async def debug_namespace_tracking():
    # Initialize validator
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j") 
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    validator = TypeScriptKnowledgeGraphValidator(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    
    await validator.initialize()
    
    try:
        # Test file with zod imports
        test_file = "test_validation/correct_form_implementation.tsx"
        result = await validator.validate_script(test_file)
        
        print(f"External imports: {validator.external_imports}")
        print(f"Namespace imports: {validator.namespace_imports}")
        
        # Check method validations
        print("\nMethod validations:")
        for validation in result.function_validations:
            if 'z.' in validation.function_name:
                print(f"  {validation.function_name}: {validation.validation.status} - {validation.validation.message}")
        
    finally:
        await validator.close()

if __name__ == "__main__":
    asyncio.run(debug_namespace_tracking())