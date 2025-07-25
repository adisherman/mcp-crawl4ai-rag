{
  "script_path": "test_validation/edge_case_new_apis.js",
  "analysis_timestamp": "2025-07-25T13:00:39.908534+00:00",
  "overall_confidence": 0.8095238095238095,
  "total_validations": 21,
  "hallucinations_detected": [
    {
      "type": "function",
      "element": "BigInt",
      "message": "Function 'BigInt' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "BigInt.asUintN",
      "message": "Class or object 'BigInt' not found in knowledge graph",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 0,
    "functions": 21,
    "components": 0,
    "types": 0,
    "hooks": 0,
    "hallucination_count": 2
  },
  "recommendations": [
    "Fix 2 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}