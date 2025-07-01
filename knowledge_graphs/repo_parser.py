"""
Universal Repository Parser

Detects repository language and routes to appropriate parser (Python or TypeScript).
Provides a unified interface for parsing repositories of different languages.
"""

import asyncio
import logging
import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

from parse_repo_into_neo4j import Neo4jCodeExtractor
from ts_repo_parser import TypeScriptNeo4jExtractor

logger = logging.getLogger(__name__)


class RepositoryLanguage(Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class LanguageDetector:
    """Detects the primary language of a repository"""
    
    def __init__(self):
        self.language_extensions = {
            RepositoryLanguage.PYTHON: {'.py'},
            RepositoryLanguage.TYPESCRIPT: {'.ts', '.tsx'},
            RepositoryLanguage.JAVASCRIPT: {'.js', '.jsx'}
        }
    
    def detect_language(self, repo_path: str) -> Tuple[RepositoryLanguage, Dict[str, int]]:
        """
        Detect the primary language of a repository
        Returns: (primary_language, file_counts_by_language)
        """
        repo_root = Path(repo_path)
        file_counts = {
            RepositoryLanguage.PYTHON: 0,
            RepositoryLanguage.TYPESCRIPT: 0,
            RepositoryLanguage.JAVASCRIPT: 0
        }
        
        # Count files by extension
        for file_path in repo_root.rglob('*'):
            if file_path.is_file() and 'node_modules' not in str(file_path) and '.git' not in str(file_path):
                ext = file_path.suffix.lower()
                
                for lang, extensions in self.language_extensions.items():
                    if ext in extensions:
                        file_counts[lang] += 1
        
        # Check for language-specific config files
        if (repo_root / 'setup.py').exists() or (repo_root / 'pyproject.toml').exists():
            file_counts[RepositoryLanguage.PYTHON] += 10  # Boost Python score
        
        if (repo_root / 'package.json').exists():
            # Check if it's a TypeScript project
            try:
                with open(repo_root / 'package.json', 'r') as f:
                    package_data = json.load(f)
                    if 'typescript' in package_data.get('devDependencies', {}) or \
                       'typescript' in package_data.get('dependencies', {}):
                        file_counts[RepositoryLanguage.TYPESCRIPT] += 10
                    else:
                        file_counts[RepositoryLanguage.JAVASCRIPT] += 10
            except:
                file_counts[RepositoryLanguage.JAVASCRIPT] += 5
        
        if (repo_root / 'tsconfig.json').exists():
            file_counts[RepositoryLanguage.TYPESCRIPT] += 10
        
        # Determine primary language
        total_files = sum(file_counts.values())
        if total_files == 0:
            return RepositoryLanguage.UNKNOWN, {}
        
        # Get the language with most files
        primary_lang = max(file_counts.items(), key=lambda x: x[1])[0]
        
        # Check if it's a mixed repository
        significant_threshold = 0.2  # 20% of files
        significant_langs = [lang for lang, count in file_counts.items() 
                           if count > 0 and count / total_files >= significant_threshold]
        
        if len(significant_langs) > 1:
            return RepositoryLanguage.MIXED, {k.value: v for k, v in file_counts.items() if v > 0}
        
        # Convert enum keys to string for return
        return primary_lang, {k.value: v for k, v in file_counts.items() if v > 0}


class UniversalRepositoryParser:
    """Universal parser that handles multiple languages"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.language_detector = LanguageDetector()
        self.python_extractor = None
        self.typescript_extractor = None
    
    async def initialize(self):
        """Initialize extractors"""
        # Initialize both extractors
        self.python_extractor = Neo4jCodeExtractor(
            self.neo4j_uri, self.neo4j_user, self.neo4j_password
        )
        self.typescript_extractor = TypeScriptNeo4jExtractor(
            self.neo4j_uri, self.neo4j_user, self.neo4j_password
        )
        
        await self.python_extractor.initialize()
        await self.typescript_extractor.initialize()
        
        logger.info("Universal repository parser initialized")
    
    async def close(self):
        """Close all extractors"""
        if self.python_extractor:
            await self.python_extractor.close()
        if self.typescript_extractor:
            await self.typescript_extractor.close()
    
    def clone_repository(self, repo_url: str, target_dir: str) -> str:
        """Clone a repository"""
        logger.info(f"Cloning repository: {repo_url}")
        
        if os.path.exists(target_dir):
            logger.info(f"Removing existing directory: {target_dir}")
            shutil.rmtree(target_dir, ignore_errors=True)
        
        # Clone with shallow clone for efficiency
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, target_dir],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Successfully cloned to: {target_dir}")
            return target_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise
    
    async def parse_repository(self, repo_url: str, repo_name: Optional[str] = None) -> Dict[str, any]:
        """
        Parse a repository and store in Neo4j
        
        Args:
            repo_url: Git repository URL
            repo_name: Optional repository name (extracted from URL if not provided)
            
        Returns:
            Dictionary with parsing results
        """
        # Extract repo name if not provided
        if not repo_name:
            repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        
        # Clone repository
        target_dir = f"/tmp/{repo_name}"
        repo_path = self.clone_repository(repo_url, target_dir)
        
        try:
            # Detect language
            primary_language, file_counts = self.language_detector.detect_language(repo_path)
            
            logger.info(f"Detected primary language: {primary_language.value}")
            logger.info(f"File counts: {file_counts}")
            
            # Clear existing data for this repository
            if primary_language == RepositoryLanguage.PYTHON:
                await self.python_extractor.clear_repository_data(repo_name)
            elif primary_language in [RepositoryLanguage.TYPESCRIPT, RepositoryLanguage.JAVASCRIPT]:
                # TypeScript extractor handles both TS and JS
                await self.typescript_extractor.clear_repository_data(repo_name)
            elif primary_language == RepositoryLanguage.MIXED:
                # For mixed repos, we need to handle both
                await self._parse_mixed_repository(repo_path, repo_name, file_counts)
                return {
                    'repository': repo_name,
                    'language': 'mixed',
                    'file_counts': file_counts,
                    'status': 'success'
                }
            else:
                return {
                    'repository': repo_name,
                    'language': 'unknown',
                    'error': 'Could not detect repository language',
                    'status': 'failed'
                }
            
            # Parse based on language
            if primary_language == RepositoryLanguage.PYTHON:
                await self.python_extractor.process_repository(repo_path, repo_name)
            elif primary_language in [RepositoryLanguage.TYPESCRIPT, RepositoryLanguage.JAVASCRIPT]:
                await self.typescript_extractor.process_repository(repo_path, repo_name)
            
            return {
                'repository': repo_name,
                'language': primary_language.value,
                'file_counts': file_counts,
                'status': 'success'
            }
            
        finally:
            # Clean up cloned repository
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
    
    async def _parse_mixed_repository(self, repo_path: str, repo_name: str, file_counts: Dict[str, int]):
        """Handle mixed language repositories"""
        logger.info(f"Parsing mixed repository: {repo_name}")
        
        # Process Python files
        if file_counts.get('python', 0) > 0:
            logger.info("Processing Python files...")
            await self.python_extractor.clear_repository_data(f"{repo_name}_python")
            await self.python_extractor.process_repository(repo_path, f"{repo_name}_python")
        
        # Process TypeScript/JavaScript files
        if file_counts.get('typescript', 0) > 0 or file_counts.get('javascript', 0) > 0:
            logger.info("Processing TypeScript/JavaScript files...")
            await self.typescript_extractor.clear_repository_data(f"{repo_name}_typescript")
            await self.typescript_extractor.process_repository(repo_path, f"{repo_name}_typescript")
    
    async def get_repository_info(self, repo_name: str) -> Dict[str, any]:
        """Get information about a parsed repository from Neo4j"""
        from neo4j import AsyncGraphDatabase
        
        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                # Get repository info
                result = await session.run("""
                    MATCH (r:Repository {name: $name})
                    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                    RETURN r.language as language,
                           r.analyzed_at as analyzed_at,
                           count(f) as file_count
                """, name=repo_name)
                
                record = await result.single()
                
                if not record:
                    return {'error': f'Repository {repo_name} not found'}
                
                # Get language-specific counts
                counts_result = await session.run("""
                    MATCH (r:Repository {name: $name})-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[:DEFINES]->(item)
                    RETURN f.language as language,
                           labels(item) as item_type,
                           count(item) as count
                """, name=repo_name)
                
                language_stats = {}
                async for record in counts_result:
                    lang = record['language'] or 'unknown'
                    item_type = record['item_type'][0] if record['item_type'] else 'none'
                    
                    if lang not in language_stats:
                        language_stats[lang] = {}
                    
                    language_stats[lang][item_type] = record['count']
                
                return {
                    'repository': repo_name,
                    'primary_language': record['language'],
                    'analyzed_at': str(record['analyzed_at']),
                    'file_count': record['file_count'],
                    'language_stats': language_stats
                }
                
        finally:
            await driver.close()


async def main():
    """Example usage"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    if not neo4j_password:
        logger.error("NEO4J_PASSWORD not set in environment")
        return
    
    # Example repositories
    test_repos = [
        ("https://github.com/pallets/flask.git", "flask"),  # Python
        ("https://github.com/facebook/react.git", "react"),  # JavaScript/TypeScript
        ("https://github.com/microsoft/vscode.git", "vscode"),  # TypeScript
    ]
    
    parser = UniversalRepositoryParser(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        await parser.initialize()
        
        for repo_url, repo_name in test_repos:
            logger.info(f"\n{'='*50}")
            logger.info(f"Parsing: {repo_name}")
            logger.info(f"{'='*50}")
            
            result = await parser.parse_repository(repo_url, repo_name)
            print(f"\nResult: {result}")
            
            # Get repository info
            info = await parser.get_repository_info(repo_name)
            print(f"Repository Info: {info}")
            
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(main())