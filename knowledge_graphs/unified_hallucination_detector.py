"""
Unified AI Hallucination Detector

Detects the language of AI-generated scripts and validates them against
the knowledge graph using the appropriate analyzer and validator.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from dotenv import load_dotenv

# Python analyzers
from ai_script_analyzer import analyze_script as analyze_python_script
from knowledge_graph_validator import validate_script as validate_python_script

# TypeScript analyzers
from ts_script_analyzer import analyze_typescript_script
from ts_knowledge_graph_validator import validate_typescript_script

# Reporter
from hallucination_reporter import HallucinationReporter

logger = logging.getLogger(__name__)


class ScriptLanguage(Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    UNKNOWN = "unknown"


class LanguageDetector:
    """Detects the language of a script file"""
    
    @staticmethod
    def detect_script_language(file_path: str) -> ScriptLanguage:
        """Detect script language from file extension and content"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # Check extension
        if ext == '.py':
            return ScriptLanguage.PYTHON
        elif ext in ['.ts', '.tsx']:
            return ScriptLanguage.TYPESCRIPT
        elif ext in ['.js', '.jsx']:
            return ScriptLanguage.JAVASCRIPT
        
        # If no extension, try to detect from content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 chars
                
            # Look for language indicators
            if 'import ' in content or 'from ' in content:
                if 'from typing import' in content or 'import typing' in content:
                    return ScriptLanguage.PYTHON
                elif 'from ' in content and ' import ' in content:
                    return ScriptLanguage.PYTHON
                elif 'import {' in content or 'import *' in content:
                    return ScriptLanguage.JAVASCRIPT
            
            if 'def ' in content or 'class ' in content and ':' in content:
                return ScriptLanguage.PYTHON
            
            if 'function ' in content or 'const ' in content or 'let ' in content:
                if ': ' in content and '=>' in content:  # TypeScript type annotations
                    return ScriptLanguage.TYPESCRIPT
                return ScriptLanguage.JAVASCRIPT
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
        
        return ScriptLanguage.UNKNOWN


class UnifiedHallucinationDetector:
    """Unified detector that handles multiple languages"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.language_detector = LanguageDetector()
        self.reporter = HallucinationReporter()
    
    async def detect_hallucinations(self, script_path: str, output_format: str = 'markdown') -> Dict[str, Any]:
        """
        Detect hallucinations in an AI-generated script
        
        Args:
            script_path: Path to the script file
            output_format: Output format ('markdown' or 'json')
            
        Returns:
            Dictionary with detection results
        """
        # Detect language
        language = self.language_detector.detect_script_language(script_path)
        logger.info(f"Detected language: {language.value}")
        
        if language == ScriptLanguage.UNKNOWN:
            return {
                'error': 'Could not detect script language',
                'script_path': script_path,
                'language': 'unknown'
            }
        
        # Analyze and validate based on language
        if language == ScriptLanguage.PYTHON:
            return await self._detect_python_hallucinations(script_path, output_format)
        elif language in [ScriptLanguage.TYPESCRIPT, ScriptLanguage.JAVASCRIPT]:
            return await self._detect_typescript_hallucinations(script_path, output_format)
        
        return {
            'error': f'Language {language.value} not yet supported',
            'script_path': script_path,
            'language': language.value
        }
    
    async def _detect_python_hallucinations(self, script_path: str, output_format: str) -> Dict[str, Any]:
        """Detect hallucinations in Python scripts"""
        try:
            # Analyze script
            logger.info("Analyzing Python script...")
            analysis_result = analyze_python_script(script_path)
            
            # Validate against knowledge graph
            logger.info("Validating against knowledge graph...")
            validation_result = await validate_python_script(
                script_path, 
                self.neo4j_uri, 
                self.neo4j_user, 
                self.neo4j_password
            )
            
            # Generate report
            logger.info("Generating report...")
            if output_format == 'json':
                report = self.reporter.generate_json_report(validation_result)
            else:
                report = self.reporter.generate_markdown_report(validation_result)
            
            # Create output file
            output_path = Path(script_path).with_suffix(f'.hallucination_report.{output_format}')
            with open(output_path, 'w') as f:
                f.write(report)
            
            logger.info(f"Report saved to: {output_path}")
            
            return {
                'script_path': script_path,
                'language': 'python',
                'hallucinations_found': len(validation_result.hallucinations_detected),
                'overall_confidence': validation_result.overall_confidence,
                'report_path': str(output_path),
                'summary': self._generate_summary(validation_result)
            }
            
        except Exception as e:
            logger.error(f"Error detecting Python hallucinations: {e}")
            return {
                'error': str(e),
                'script_path': script_path,
                'language': 'python'
            }
    
    async def _detect_typescript_hallucinations(self, script_path: str, output_format: str) -> Dict[str, Any]:
        """Detect hallucinations in TypeScript/JavaScript scripts"""
        try:
            # Analyze script
            logger.info("Analyzing TypeScript/JavaScript script...")
            analysis_result = analyze_typescript_script(script_path)
            
            # Validate against knowledge graph
            logger.info("Validating against knowledge graph...")
            validation_result = await validate_typescript_script(
                script_path, 
                self.neo4j_uri, 
                self.neo4j_user, 
                self.neo4j_password
            )
            
            # Generate report using TypeScript adapter
            logger.info("Generating report...")
            adapted_result = self._adapt_typescript_result_for_reporter(validation_result)
            
            if output_format == 'json':
                report = self.reporter.generate_json_report(adapted_result)
            else:
                report = self.reporter.generate_markdown_report(adapted_result)
            
            # Create output file
            output_path = Path(script_path).with_suffix(f'.hallucination_report.{output_format}')
            with open(output_path, 'w') as f:
                f.write(report)
            
            logger.info(f"Report saved to: {output_path}")
            
            return {
                'script_path': script_path,
                'language': 'typescript/javascript',
                'hallucinations_found': len(validation_result.hallucinations_detected),
                'overall_confidence': validation_result.overall_confidence,
                'report_path': str(output_path),
                'summary': self._generate_typescript_summary(validation_result)
            }
            
        except Exception as e:
            logger.error(f"Error detecting TypeScript hallucinations: {e}")
            return {
                'error': str(e),
                'script_path': script_path,
                'language': 'typescript/javascript'
            }
    
    def _adapt_typescript_result_for_reporter(self, ts_result):
        """Adapt TypeScript validation result to work with the existing reporter"""
        # Create a mock Python-style result that the reporter can understand
        class AdaptedResult:
            def __init__(self, ts_result):
                self.script_path = ts_result.script_path
                self.overall_confidence = ts_result.overall_confidence
                self.hallucinations_detected = ts_result.hallucinations_detected
                
                # Adapt validation results
                self.import_validations = ts_result.import_validations
                self.method_validations = []  # TypeScript doesn't have method validations in same format
                self.function_validations = ts_result.function_validations
                self.class_validations = []  # Adapt component validations
                self.attribute_validations = []  # Not applicable for TypeScript
                
                # Add component validations as a special type
                self.component_validations = ts_result.component_validations
                self.hook_validations = ts_result.hook_validations
                self.type_validations = ts_result.type_validations
        
        return AdaptedResult(ts_result)
    
    def _generate_summary(self, validation_result) -> str:
        """Generate a summary of Python validation results"""
        hallucination_count = len(validation_result.hallucinations_detected)
        
        if hallucination_count == 0:
            return "No hallucinations detected. The code appears to be valid."
        elif hallucination_count < 3:
            return f"Found {hallucination_count} potential hallucinations. Minor issues that may need attention."
        else:
            return f"Found {hallucination_count} hallucinations. Significant issues detected in the generated code."
    
    def _generate_typescript_summary(self, validation_result) -> str:
        """Generate a summary of TypeScript validation results"""
        hallucination_count = len(validation_result.hallucinations_detected)
        
        if hallucination_count == 0:
            return "No hallucinations detected. The TypeScript/React code appears to be valid."
        elif hallucination_count < 3:
            return f"Found {hallucination_count} potential hallucinations. Minor issues with imports or type usage."
        else:
            return f"Found {hallucination_count} hallucinations. Significant issues with components, types, or imports."


async def main():
    """Main entry point"""
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python unified_hallucination_detector.py <script_path> [output_format]")
        print("  output_format: 'markdown' (default) or 'json'")
        sys.exit(1)
    
    script_path = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'markdown'
    
    if output_format not in ['markdown', 'json']:
        print("Error: output_format must be 'markdown' or 'json'")
        sys.exit(1)
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("Error: NEO4J_PASSWORD not set in environment")
        sys.exit(1)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create detector and run
    detector = UnifiedHallucinationDetector(neo4j_uri, neo4j_user, neo4j_password)
    
    print(f"\nAnalyzing script: {script_path}")
    print("="*50)
    
    result = await detector.detect_hallucinations(script_path, output_format)
    
    if 'error' in result:
        print(f"\nError: {result['error']}")
    else:
        print(f"\nLanguage detected: {result['language']}")
        print(f"Hallucinations found: {result['hallucinations_found']}")
        print(f"Overall confidence: {result['overall_confidence']:.2f}")
        print(f"\nSummary: {result['summary']}")
        print(f"\nDetailed report saved to: {result['report_path']}")


if __name__ == "__main__":
    asyncio.run(main())