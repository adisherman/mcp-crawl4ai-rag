#!/usr/bin/env python
"""Direct test of TypeScript hallucination detection"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add knowledge_graphs to path
sys.path.append(str(Path(__file__).parent / 'knowledge_graphs'))

from ts_knowledge_graph_validator import TypeScriptKnowledgeGraphValidator

async def test_hallucination_detection():
    load_dotenv()
    
    # Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    # Initialize validator
    validator = TypeScriptKnowledgeGraphValidator(neo4j_uri, neo4j_user, neo4j_password)
    await validator.initialize()
    
    # Test file
    script_path = "test_typescript_hallucinations.ts"
    
    print(f"Testing hallucination detection on: {script_path}\n")
    
    # Validate script
    result = await validator.validate_script(script_path)
    
    # Close validator
    await validator.close()
    
    print(f"Overall confidence: {result.overall_confidence}")
    print(f"Hallucinations found: {len(result.hallucinations_detected)}")
    
    if result.hallucinations_detected:
        print("\n🚨 HALLUCINATIONS DETECTED:")
        for h in result.hallucinations_detected:
            print(f"\n- Type: {h.get('type', 'Unknown')}")
            print(f"  Element: {h.get('element', 'Unknown')}")
            print(f"  Message: {h.get('message', 'Unknown issue')}")
            print(f"  Confidence: {h.get('confidence', 0.0):.2f}")
    else:
        print("\n✅ No hallucinations detected")
    
    # Print summary
    print(f"\nValidation Summary:")
    print(f"- Imports checked: {len(result.import_validations)}")
    print(f"- Components checked: {len(result.component_validations)}")
    print(f"- Functions checked: {len(result.function_validations)}")
    print(f"- Types checked: {len(result.type_validations)}")
    print(f"- Hooks checked: {len(result.hook_validations)}")

if __name__ == "__main__":
    asyncio.run(test_hallucination_detection())