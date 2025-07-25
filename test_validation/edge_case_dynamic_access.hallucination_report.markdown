{
  "script_path": "test_validation/edge_case_dynamic_access.js",
  "analysis_timestamp": "2025-07-25T13:00:38.114303+00:00",
  "overall_confidence": 0.2236842105263158,
  "total_validations": 19,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "api.fetchUsers",
      "message": "Method 'fetchUsers' not found in any class or interface",
      "confidence": 0.8,
      "line": 28
    },
    {
      "type": "method",
      "element": "obj.dynamicMethod",
      "message": "Method 'dynamicMethod' not found in any class or interface",
      "confidence": 0.8,
      "line": 33
    },
    {
      "type": "function",
      "element": "dataService[methodName]",
      "message": "Function 'dataService[methodName]' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "method",
      "message": "Function 'method' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Promise.resolve()\n  .then(() => fetch('/api'))\n  ['finally']",
      "message": "Function 'Promise.resolve()\n  .then(() => fetch('/api'))\n  ['finally']' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "[1, 2, 3].customMethod",
      "message": "Class or object '[1, 2, 3]' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "api.fetchUsers",
      "message": "Method 'fetchUsers' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "obj.dynamicMethod",
      "message": "Method 'dynamicMethod' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Reflect.apply",
      "message": "Class or object 'Reflect' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Array.prototype.slice.call",
      "message": "Class or object 'Array.prototype.slice' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Promise.resolve().then",
      "message": "Class or object 'Promise.resolve()' not found in knowledge graph",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 0,
    "functions": 19,
    "components": 0,
    "types": 0,
    "hooks": 0,
    "hallucination_count": 11
  },
  "recommendations": [
    "Fix 11 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}