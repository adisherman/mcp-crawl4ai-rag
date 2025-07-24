#!/usr/bin/env python
"""
Test script to validate TypeScript hallucination detection on lavi_specs test files
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure knowledge graph is enabled
os.environ['USE_KNOWLEDGE_GRAPH'] = 'true'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import the MCP function directly
from crawl4ai_mcp import check_ai_script_hallucinations

# Create mock context
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

async def test_file(ctx, file_path, expected_hallucinations):
    """Test a single file and report results"""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(file_path).name}")
    print(f"{'='*80}")
    
    try:
        # Run hallucination detection
        result_json = await check_ai_script_hallucinations(ctx, file_path)
        result = json.loads(result_json)
        
        if result.get('success'):
            print(f"✅ Analysis completed successfully")
            print(f"📊 Overall confidence: {result.get('overall_confidence', 0.0):.2%}")
            print(f"🔍 Hallucinations found: {result.get('hallucinations_found', 0)}")
            
            hallucinations = result.get('hallucinations_detected', [])
            
            if hallucinations:
                print(f"\n🚨 Detected Hallucinations:")
                for i, h in enumerate(hallucinations, 1):
                    print(f"\n  {i}. {h.get('type', 'Unknown').upper()}: {h.get('element', 'Unknown')}")
                    print(f"     📍 Line {h.get('line', 'N/A')}")
                    print(f"     💬 {h.get('message', 'No message')}")
                    print(f"     🎯 Confidence: {h.get('confidence', 0.0):.2%}")
            else:
                print("\n✅ No hallucinations detected!")
            
            # Verify expectations
            if expected_hallucinations == 0:
                if hallucinations:
                    print(f"\n❌ UNEXPECTED: Found {len(hallucinations)} hallucinations in valid code!")
                else:
                    print(f"\n✅ PASS: No hallucinations found as expected")
            else:
                if len(hallucinations) >= expected_hallucinations * 0.8:  # Allow 80% detection rate
                    print(f"\n✅ PASS: Detected {len(hallucinations)}/{expected_hallucinations} expected hallucinations")
                else:
                    print(f"\n❌ FAIL: Only detected {len(hallucinations)}/{expected_hallucinations} expected hallucinations")
                    
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error testing file: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run tests on all three test files"""
    print("🚀 Starting TypeScript Hallucination Detection Tests")
    print(f"📁 Testing files in lavi_specs project")
    
    # Create context
    ctx = MockContext()
    
    # Define test files and expected results
    test_dir = "/Users/adisherman/Desktop/projects/lavi_specs/lavi_specs/src/test_hallucinations"
    tests = [
        {
            "file": os.path.join(test_dir, "test_valid_code.tsx"),
            "expected_hallucinations": 0,
            "description": "Valid TypeScript code - should have NO hallucinations"
        },
        {
            "file": os.path.join(test_dir, "test_hallucinated_code.tsx"),
            "expected_hallucinations": 25,  # Approximate count of hallucinations
            "description": "Hallucinated code - should detect MANY hallucinations"
        },
        {
            "file": os.path.join(test_dir, "test_mixed_code.tsx"),
            "expected_hallucinations": 15,  # Approximate count of hallucinations
            "description": "Mixed code - should detect SOME hallucinations"
        }
    ]
    
    # Run tests
    for test in tests:
        print(f"\n\n{'*'*80}")
        print(f"📋 {test['description']}")
        await test_file(ctx, test['file'], test['expected_hallucinations'])
    
    print(f"\n\n{'='*80}")
    print("✅ All tests completed!")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())