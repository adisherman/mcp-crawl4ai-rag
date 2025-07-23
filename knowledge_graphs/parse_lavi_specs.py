"""
Parse lavi_specs repository into Neo4j knowledge graph
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from knowledge_graphs.repo_parser import UniversalRepositoryParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Parse lavi_specs repository"""
    load_dotenv()
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    if not neo4j_password:
        logger.error("NEO4J_PASSWORD not set in environment")
        return
    
    # lavi_specs is a local directory, not a git URL
    lavi_specs_path = "/Users/adisherman/Desktop/projects/lavi_specs/lavi_specs"
    repo_name = "lavi_specs"
    
    logger.info(f"Parsing {repo_name} from {lavi_specs_path}")
    
    # Create parser
    parser = UniversalRepositoryParser(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        await parser.initialize()
        
        # Since it's a local directory, we need to handle it differently
        # Detect language
        primary_language, file_counts = parser.language_detector.detect_language(lavi_specs_path)
        
        logger.info(f"Detected primary language: {primary_language.value}")
        logger.info(f"File counts: {file_counts}")
        
        # Parse based on language
        if primary_language.value in ['typescript', 'javascript']:
            # Start the TypeScript parser service
            async with parser.typescript_extractor as extractor:
                # Use the TypeScript parser
                stats = await extractor.parse_directory(lavi_specs_path, repo_name)
                logger.info(f"Parsing complete! Stats: {stats}")
                logger.info(f"\nSuccessfully parsed {repo_name} into Neo4j!")
                logger.info(f"  - Components: {stats.get('components', 0)}")
                logger.info(f"  - Interfaces: {stats.get('interfaces', 0)}")
                logger.info(f"  - Types: {stats.get('types', 0)}")
                logger.info(f"  - Functions: {stats.get('functions', 0)}")
                logger.info(f"  - Classes: {stats.get('classes', 0)}")
        else:
            logger.error(f"Unexpected language: {primary_language.value}")
        
    finally:
        await parser.close()
        

if __name__ == "__main__":
    asyncio.run(main())