#!/usr/bin/env python
"""Test MCP integration for TypeScript hallucination detection"""

import os
import sys
import json
from pathlib import Path

# Set environment variable
os.environ['USE_KNOWLEDGE_GRAPH'] = 'true'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import the function directly
from crawl4ai_mcp import check_ai_script_hallucinations

# Create a mock context
class MockContext:
    def __init__(self):
        self.request_context = MockRequestContext()

class MockRequestContext:
    def __init__(self):
        self.lifespan_context = MockLifespanContext()

class MockLifespanContext:
    def __init__(self):
        # Import the unified detector
        sys.path.append(str(Path(__file__).parent / 'knowledge_graphs'))
        from unified_hallucination_detector import UnifiedHallucinationDetector
        
        # Initialize the detector
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        
        self.unified_detector = UnifiedHallucinationDetector(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
        )

async def test():
    """Test the MCP tool"""
    ctx = MockContext()
    
    # Test with the TypeScript file
    script_path = str(Path(__file__).parent / "test_typescript_hallucinations.ts")
    
    print("Testing MCP tool with TypeScript file...")
    result = await check_ai_script_hallucinations(ctx, script_path)
    
    # Parse and display result
    result_data = json.loads(result)
    
    print(f"\nSuccess: {result_data.get('success', False)}")
    if 'error' in result_data:
        print(f"Error: {result_data['error']}")
    print(f"Language detected: {result_data.get('detected_language', 'Unknown')}")
    print(f"Overall confidence: {result_data.get('overall_confidence', 0.0):.2f}")
    print(f"Hallucinations found: {result_data.get('hallucinations_found', 0)}")
    
    if result_data.get('hallucinations_detected'):
        print("\nHallucinations detected:")
        for h in result_data['hallucinations_detected']:
            print(f"  - {h.get('type', 'Unknown')}: {h.get('element', 'Unknown')}")
            print(f"    {h.get('message', 'No message')}")
    
    # Clean up - unified detector doesn't need explicit close

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())