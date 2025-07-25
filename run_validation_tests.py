#!/usr/bin/env python3
"""
Run hallucination detector on all test validation files
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple


def run_hallucination_detector(file_path: str) -> Tuple[bool, str, Dict]:
    """Run the hallucination detector on a single file"""
    cmd = [
        sys.executable,
        "knowledge_graphs/unified_hallucination_detector.py",
        file_path,
        "json"  # Use JSON output format
    ]
    
    # Set environment variables if needed
    env = os.environ.copy()
    if 'NEO4J_URI' not in env:
        env['NEO4J_URI'] = 'bolt://localhost:7687'  # Default URI
    if 'NEO4J_USER' not in env:
        env['NEO4J_USER'] = 'neo4j'  # Default user
    if 'NEO4J_PASSWORD' not in env:
        env['NEO4J_PASSWORD'] = 'As835169'  # Default password
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        output = result.stdout + result.stderr
        
        # Try to find the report JSON file
        report_path = Path(file_path).with_suffix('.hallucination_report.json')
        if report_path.exists():
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            # Clean up the report file
            os.remove(report_path)
            
            # Check if hallucinations were detected
            hallucinations_found = len(report_data.get("hallucinations_detected", [])) > 0 or \
                                 report_data.get("hallucination_count", 0) > 0 or \
                                 report_data.get("validation_summary", {}).get("hallucination_count", 0) > 0
                                 
            return True, output, {
                "hallucinations_found": hallucinations_found,
                "confidence": report_data.get("overall_confidence", 0),
                "hallucinations": report_data.get("hallucinations_detected", []),
                "summary": report_data.get("validation_summary", {})
            }
        else:
            # Parse output for results
            hallucinations_found = False
            confidence = 0.0
            
            # Look for hallucination count in output
            if "Hallucinations found:" in output:
                match = re.search(r"Hallucinations found:\s*(\d+)", output)
                if match:
                    count = int(match.group(1))
                    hallucinations_found = count > 0
                    
            # Look for confidence score
            if "Overall confidence:" in output:
                match = re.search(r"Overall confidence:\s*([0-9.]+)", output)
                if match:
                    confidence = float(match.group(1))
                    
            # Check for errors in output
            if "Error:" in output or "NEO4J_PASSWORD not set" in output:
                return False, output, {"error": "Neo4j connection error"}
                
            return True, output, {
                "hallucinations_found": hallucinations_found,
                "confidence": confidence
            }
            
    except subprocess.TimeoutExpired:
        return False, "Timeout", {}
    except Exception as e:
        return False, f"Error: {str(e)}", {}


def main():
    """Main function to run tests"""
    test_dir = Path("test_validation")
    
    # Categorize files
    correct_files = list(test_dir.glob("correct_*.tsx")) + \
                   list(test_dir.glob("correct_*.ts")) + \
                   list(test_dir.glob("correct_*.js"))
                   
    hallucinated_files = list(test_dir.glob("hallucinated_*.tsx")) + \
                        list(test_dir.glob("hallucinated_*.ts")) + \
                        list(test_dir.glob("hallucinated_*.js"))
    
    results = {
        "correct_files": {},
        "hallucinated_files": {},
        "summary": {
            "total_correct": len(correct_files),
            "total_hallucinated": len(hallucinated_files),
            "correct_passed": 0,
            "hallucinated_caught": 0,
            "false_positives": 0,
            "false_negatives": 0
        }
    }
    
    print("Running TypeScript/JavaScript Hallucination Detection Tests")
    print("=" * 60)
    
    # Test correct files (should have no hallucinations)
    print("\nTesting CORRECT files (should pass):")
    print("-" * 40)
    
    for file_path in correct_files:
        print(f"\nTesting {file_path.name}...", end=" ", flush=True)
        success, output, report = run_hallucination_detector(str(file_path))
        
        if success:
            has_hallucinations = report.get("hallucinations_found", False)
            if not has_hallucinations:
                print("✓ PASSED (no hallucinations)")
                results["summary"]["correct_passed"] += 1
                results["correct_files"][str(file_path)] = {
                    "passed": True,
                    "hallucinations": []
                }
            else:
                print("✗ FAILED (false positive)")
                results["summary"]["false_positives"] += 1
                results["correct_files"][str(file_path)] = {
                    "passed": False,
                    "hallucinations": report.get("hallucinations", []),
                    "confidence": report.get("confidence_score", 0)
                }
        else:
            print(f"✗ ERROR: {output}")
            results["correct_files"][str(file_path)] = {
                "passed": False,
                "error": output
            }
    
    # Test hallucinated files (should detect hallucinations)
    print("\n\nTesting HALLUCINATED files (should fail):")
    print("-" * 40)
    
    for file_path in hallucinated_files:
        print(f"\nTesting {file_path.name}...", end=" ", flush=True)
        success, output, report = run_hallucination_detector(str(file_path))
        
        if success:
            has_hallucinations = report.get("hallucinations_found", False)
            if has_hallucinations:
                print("✓ CAUGHT (hallucinations detected)")
                results["summary"]["hallucinated_caught"] += 1
                results["hallucinated_files"][str(file_path)] = {
                    "caught": True,
                    "hallucinations": report.get("hallucinations", []),
                    "confidence": report.get("confidence_score", 0)
                }
            else:
                print("✗ MISSED (false negative)")
                results["summary"]["false_negatives"] += 1
                results["hallucinated_files"][str(file_path)] = {
                    "caught": False,
                    "hallucinations": []
                }
        else:
            print(f"✗ ERROR: {output}")
            results["hallucinated_files"][str(file_path)] = {
                "caught": False,
                "error": output
            }
    
    # Print summary
    print("\n\nSUMMARY")
    print("=" * 60)
    print(f"Correct files tested: {results['summary']['total_correct']}")
    print(f"  - Passed (no hallucinations): {results['summary']['correct_passed']}")
    print(f"  - False positives: {results['summary']['false_positives']}")
    print(f"\nHallucinated files tested: {results['summary']['total_hallucinated']}")
    print(f"  - Caught (hallucinations detected): {results['summary']['hallucinated_caught']}")
    print(f"  - False negatives: {results['summary']['false_negatives']}")
    
    # Calculate accuracy
    total_tests = results['summary']['total_correct'] + results['summary']['total_hallucinated']
    correct_results = results['summary']['correct_passed'] + results['summary']['hallucinated_caught']
    accuracy = (correct_results / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nOverall accuracy: {accuracy:.1f}%")
    
    # Save detailed results
    with open("validation_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: validation_test_results.json")
    
    # Print details of any failures
    if results['summary']['false_positives'] > 0:
        print("\n\nFALSE POSITIVES (correct files marked as hallucinated):")
        print("-" * 50)
        for file_path, data in results['correct_files'].items():
            if not data.get('passed', False) and 'error' not in data:
                print(f"\n{Path(file_path).name}:")
                for h in data.get('hallucinations', []):
                    print(f"  - {h}")
    
    if results['summary']['false_negatives'] > 0:
        print("\n\nFALSE NEGATIVES (hallucinated files not caught):")
        print("-" * 50)
        for file_path, data in results['hallucinated_files'].items():
            if not data.get('caught', False) and 'error' not in data:
                print(f"\n{Path(file_path).name}: Not detected")


if __name__ == "__main__":
    main()