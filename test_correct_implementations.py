#!/usr/bin/env python3
"""Test hallucination detector on correct implementation files"""

import subprocess
import json
import sys
from pathlib import Path

def test_file(file_path):
    """Test a single file and return results"""
    print(f"\n{'='*60}")
    print(f"Testing: {file_path}")
    print('='*60)
    
    cmd = [sys.executable, "knowledge_graphs/unified_hallucination_detector.py", file_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        # Check for report file
        report_path = Path(file_path).with_suffix('.hallucination_report.json')
        if report_path.exists():
            with open(report_path, 'r') as f:
                report = json.load(f)
                
            return {
                'file': file_path,
                'success': True,
                'hallucinations_found': len(report.get('hallucinations_detected', [])),
                'confidence': report.get('overall_confidence', 0),
                'error': None
            }
        else:
            # Try markdown report
            report_path = Path(file_path).with_suffix('.hallucination_report.markdown')
            if report_path.exists():
                return {
                    'file': file_path,
                    'success': True,
                    'hallucinations_found': 'See markdown report',
                    'confidence': 'See markdown report',
                    'error': None
                }
            else:
                return {
                    'file': file_path,
                    'success': False,
                    'hallucinations_found': None,
                    'confidence': None,
                    'error': 'No report generated'
                }
                
    except Exception as e:
        return {
            'file': file_path,
            'success': False,
            'hallucinations_found': None,
            'confidence': None,
            'error': str(e)
        }

def main():
    """Test all correct implementation files"""
    test_files = [
        "test_validation/correct_form_implementation.tsx",
        "test_validation/correct_dynamic_form.tsx",
        "test_validation/correct_page_component.tsx",
        "test_validation/correct_utility_usage.ts",
        "test_validation/correct_service_integration.js"
    ]
    
    results = []
    
    for file_path in test_files:
        result = test_file(file_path)
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF RESULTS")
    print("="*60)
    
    for result in results:
        print(f"\nFile: {result['file']}")
        if result['success']:
            print(f"  ✓ Success")
            print(f"  Hallucinations: {result['hallucinations_found']}")
            print(f"  Confidence: {result['confidence']}")
        else:
            print(f"  ✗ Failed: {result['error']}")
    
    # Overall summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    false_positives = sum(1 for r in results if r['success'] and isinstance(r['hallucinations_found'], int) and r['hallucinations_found'] > 0)
    
    print(f"\n{'='*60}")
    print(f"Overall: {successful}/{total} files tested successfully")
    if false_positives > 0:
        print(f"WARNING: {false_positives} files had false positive hallucinations detected!")
    else:
        print("SUCCESS: No false positives detected in correct implementations!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()