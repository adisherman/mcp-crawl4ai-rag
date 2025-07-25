{
  "script_path": "demo_hallucination_test.ts",
  "analysis_timestamp": "2025-07-25T12:32:36.204688+00:00",
  "overall_confidence": 0.075,
  "total_validations": 15,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "z.string().email",
      "message": "Method 'email' not found in any class or interface",
      "confidence": 0.8,
      "line": 12
    },
    {
      "type": "method",
      "element": "z.number().positive",
      "message": "Method 'positive' not found in any class or interface",
      "confidence": 0.8,
      "line": 13
    },
    {
      "type": "method",
      "element": "Array.quantumFilter",
      "message": "Invalid method 'quantumFilter' on built-in object 'Array'",
      "confidence": 0.95,
      "line": 16
    },
    {
      "type": "method",
      "element": "console.neural",
      "message": "Invalid method 'neural' on built-in object 'console'",
      "confidence": 0.95,
      "line": 17
    },
    {
      "type": "method",
      "element": "Math.quantumRandom",
      "message": "Invalid method 'quantumRandom' on built-in object 'Math'",
      "confidence": 0.95,
      "line": 18
    },
    {
      "type": "method",
      "element": "dataService.getFromCache",
      "message": "Method 'getFromCache' not found in any class or interface",
      "confidence": 0.8,
      "line": 21
    },
    {
      "type": "function",
      "element": "z.string().email",
      "message": "Method 'email' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "z.number().positive",
      "message": "Method 'positive' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "dataService.getFromCache",
      "message": "Method 'getFromCache' not found in any known type",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 2,
    "functions": 13,
    "components": 0,
    "types": 0,
    "hooks": 0,
    "hallucination_count": 9
  },
  "recommendations": [
    "Fix 9 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}