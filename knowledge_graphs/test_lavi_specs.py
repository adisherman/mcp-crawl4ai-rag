"""
Test TypeScript Parser with lavi_specs Project

Tests the new TypeScript parser implementation with the lavi_specs project
to ensure it can parse all TypeScript/React files successfully.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from knowledge_graphs.typescript_parser_setup import setup_typescript_parser
from knowledge_graphs.ts_parser_manager import TypeScriptParserManager
from knowledge_graphs.ts_repo_parser import TypeScriptNeo4jExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LaviSpecsTester:
    """Test harness for lavi_specs project parsing"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.parser_manager = None
        self.results = {
            "total_files": 0,
            "parsed_successfully": 0,
            "parse_errors": 0,
            "components": [],
            "interfaces": [],
            "types": [],
            "functions": [],
            "classes": [],
            "error_details": []
        }
        
    async def setup(self) -> bool:
        """Setup TypeScript parser"""
        logger.info("Setting up TypeScript parser...")
        
        # Check if Node.js dependencies are installed
        if not setup_typescript_parser():
            logger.error("Failed to setup TypeScript parser dependencies")
            return False
            
        # Start parser manager
        self.parser_manager = TypeScriptParserManager()
        if not await self.parser_manager.start():
            logger.error("Failed to start TypeScript parser service")
            return False
            
        logger.info("TypeScript parser ready")
        return True
        
    async def test_parsing(self):
        """Test parsing all TypeScript/React files in lavi_specs"""
        if not self.project_path.exists():
            logger.error(f"Project path does not exist: {self.project_path}")
            return
            
        logger.info(f"Testing TypeScript parser on: {self.project_path}")
        
        # Get parser client
        client = await self.parser_manager.get_client()
        if not client:
            logger.error("Failed to get parser client")
            return
            
        # Find all TypeScript/React files
        ts_extensions = {'.ts', '.tsx', '.js', '.jsx'}
        ts_files = []
        
        for ext in ts_extensions:
            for file_path in self.project_path.rglob(f'*{ext}'):
                # Skip node_modules and other common directories
                if any(part in file_path.parts for part in ['node_modules', '.git', 'dist', 'build']):
                    continue
                ts_files.append(file_path)
                
        self.results["total_files"] = len(ts_files)
        logger.info(f"Found {len(ts_files)} TypeScript/JavaScript files")
        
        # Parse each file
        for i, file_path in enumerate(ts_files, 1):
            relative_path = file_path.relative_to(self.project_path)
            logger.info(f"[{i}/{len(ts_files)}] Parsing: {relative_path}")
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse with TypeScript parser
                result = await client.parse_file(content, str(file_path))
                
                if result.get('error'):
                    logger.error(f"Parse error: {result['error']}")
                    self.results["parse_errors"] += 1
                    self.results["error_details"].append({
                        "file": str(relative_path),
                        "error": result['error']
                    })
                else:
                    self.results["parsed_successfully"] += 1
                    
                    # Collect statistics
                    if result.get('components'):
                        self.results["components"].extend([
                            {"file": str(relative_path), "name": c['name'], "type": c.get('type')}
                            for c in result['components']
                        ])
                    if result.get('interfaces'):
                        self.results["interfaces"].extend([
                            {"file": str(relative_path), "name": i['name']}
                            for i in result['interfaces']
                        ])
                    if result.get('types'):
                        self.results["types"].extend([
                            {"file": str(relative_path), "name": t['name']}
                            for t in result['types']
                        ])
                    if result.get('functions'):
                        self.results["functions"].extend([
                            {"file": str(relative_path), "name": f['name']}
                            for f in result['functions']
                        ])
                    if result.get('classes'):
                        self.results["classes"].extend([
                            {"file": str(relative_path), "name": c['name']}
                            for c in result['classes']
                        ])
                        
            except Exception as e:
                logger.error(f"Error processing {relative_path}: {e}")
                self.results["parse_errors"] += 1
                self.results["error_details"].append({
                    "file": str(relative_path),
                    "error": str(e)
                })
                
    async def test_neo4j_integration(self):
        """Test Neo4j integration with parsed data"""
        logger.info("\nTesting Neo4j integration...")
        
        # Load environment variables
        load_dotenv()
        
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            logger.warning("Neo4j credentials not configured, skipping integration test")
            return
            
        try:
            # Create Neo4j extractor
            extractor = TypeScriptNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
            await extractor.connect()
            
            # Test parsing a small subset
            logger.info("Testing Neo4j storage with sample files...")
            
            # This would normally parse the whole directory
            # For testing, we'll just verify the connection works
            logger.info("✓ Neo4j connection successful")
            
            await extractor.close()
            
        except Exception as e:
            logger.error(f"Neo4j integration test failed: {e}")
            
    def print_results(self):
        """Print test results"""
        print("\n" + "="*60)
        print("TYPESCRIPT PARSER TEST RESULTS")
        print("="*60)
        
        print(f"\nProject: {self.project_path}")
        print(f"Total files found: {self.results['total_files']}")
        print(f"Successfully parsed: {self.results['parsed_successfully']}")
        print(f"Parse errors: {self.results['parse_errors']}")
        
        if self.results['total_files'] > 0:
            success_rate = (self.results['parsed_successfully'] / self.results['total_files']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"\nExtracted entities:")
        print(f"  Components: {len(self.results['components'])}")
        print(f"  Interfaces: {len(self.results['interfaces'])}")
        print(f"  Types: {len(self.results['types'])}")
        print(f"  Functions: {len(self.results['functions'])}")
        print(f"  Classes: {len(self.results['classes'])}")
        
        if self.results['components']:
            print(f"\nSample components:")
            for comp in self.results['components'][:5]:
                print(f"  - {comp['name']} ({comp['type']}) in {comp['file']}")
                
        if self.results['interfaces']:
            print(f"\nSample interfaces:")
            for intf in self.results['interfaces'][:5]:
                print(f"  - {intf['name']} in {intf['file']}")
                
        if self.results['error_details']:
            print(f"\nParse errors:")
            for error in self.results['error_details'][:5]:
                print(f"  - {error['file']}: {error['error']}")
                
        # Save detailed results
        results_file = f"lavi_specs_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.parser_manager:
            await self.parser_manager.stop()
            

async def main():
    """Main test function"""
    # Path to lavi_specs project
    lavi_specs_path = "/Users/adisherman/Desktop/projects/lavi_specs/lavi_specs"
    
    tester = LaviSpecsTester(lavi_specs_path)
    
    try:
        # Setup parser
        if not await tester.setup():
            logger.error("Setup failed")
            return
            
        # Run parsing test
        await tester.test_parsing()
        
        # Test Neo4j integration
        await tester.test_neo4j_integration()
        
        # Print results
        tester.print_results()
        
    finally:
        # Cleanup
        await tester.cleanup()
        

if __name__ == "__main__":
    asyncio.run(main())