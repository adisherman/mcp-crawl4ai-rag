#!/usr/bin/env python3
"""
Parse a local repository without Git cloning
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the knowledge_graphs directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knowledge_graphs'))

from repo_parser import UniversalRepoParser
import shutil


async def parse_local_repository(local_path: str, repo_name: str = None):
    """
    Parse a local repository by copying it to temp directory
    
    Args:
        local_path: Path to local repository
        repo_name: Optional name for the repository
    """
    # Validate path exists
    if not os.path.exists(local_path):
        print(f"❌ Error: Path does not exist: {local_path}")
        return
    
    # Generate repo name from path if not provided
    if not repo_name:
        repo_name = os.path.basename(os.path.abspath(local_path))
    
    # Create temp directory
    temp_dir = f"/tmp/{repo_name}_parse"
    
    try:
        # Copy local repository to temp directory
        print(f"📁 Copying local repository: {local_path}")
        print(f"   Target: {temp_dir}")
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        shutil.copytree(local_path, temp_dir, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', 'node_modules'))
        
        # Create parser
        parser = UniversalRepoParser()
        
        # Parse directly (bypass git clone)
        # Detect language
        language, file_counts = parser.language_detector.detect_language(temp_dir)
        
        print(f"\n🔍 Detected language: {language.value}")
        print(f"   File counts: {file_counts}")
        
        # Parse based on language
        if language in [parser.language_detector.RepositoryLanguage.PYTHON]:
            print("\n🐍 Parsing as Python repository...")
            result = await parser.python_parser.parse_directory(temp_dir, repo_name)
        elif language in [parser.language_detector.RepositoryLanguage.TYPESCRIPT, 
                         parser.language_detector.RepositoryLanguage.JAVASCRIPT]:
            print("\n📘 Parsing as TypeScript/JavaScript repository...")
            result = await parser.typescript_parser.parse_directory(temp_dir, repo_name)
        elif language == parser.language_detector.RepositoryLanguage.MIXED:
            print("\n🔀 Mixed repository detected, parsing both Python and TypeScript...")
            results = {}
            if file_counts.get('python', 0) > 0:
                results['python'] = await parser.python_parser.parse_directory(temp_dir, f"{repo_name}_python")
            if file_counts.get('typescript', 0) > 0 or file_counts.get('javascript', 0) > 0:
                results['typescript'] = await parser.typescript_parser.parse_directory(temp_dir, f"{repo_name}_ts")
            result = results
        else:
            print("❌ Unable to detect repository language")
            return None
        
        print("\n✅ Repository parsed successfully!")
        return result
        
    except Exception as e:
        print(f"❌ Error parsing repository: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_local_repo.py <local_repository_path> [repo_name]")
        sys.exit(1)
    
    local_path = sys.argv[1]
    repo_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run parser
    asyncio.run(parse_local_repository(local_path, repo_name))


if __name__ == "__main__":
    main()