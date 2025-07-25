{
  "script_path": "test_validation/edge_case_uncommon_libraries.tsx",
  "analysis_timestamp": "2025-07-25T13:00:38.706203+00:00",
  "overall_confidence": 0.09294871794871795,
  "total_validations": 39,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "new Observable(observer => {\n  observer.next(1);\n}).pipe",
      "message": "Method 'pipe' not found in any class or interface",
      "confidence": 0.8,
      "line": 13
    },
    {
      "type": "method",
      "element": "observer.next",
      "message": "Method 'next' not found in any class or interface",
      "confidence": 0.8,
      "line": 14
    },
    {
      "type": "method",
      "element": "R.add",
      "message": "Invalid namespace method 'add' on 'R'",
      "confidence": 0.8,
      "line": 22
    },
    {
      "type": "method",
      "element": "R.multiply",
      "message": "Invalid namespace method 'multiply' on 'R'",
      "confidence": 0.8,
      "line": 23
    },
    {
      "type": "method",
      "element": "tf.layers.dense",
      "message": "Invalid method 'dense' on inferred Array type",
      "confidence": 0.8,
      "line": 83
    },
    {
      "type": "method",
      "element": "model.predict",
      "message": "Method 'predict' not found in any class or interface",
      "confidence": 0.8,
      "line": 87
    },
    {
      "type": "method",
      "element": "entry.target.classList.add",
      "message": "Invalid method 'add' on inferred Array type",
      "confidence": 0.8,
      "line": 100
    },
    {
      "type": "method",
      "element": "canvas.getContext",
      "message": "Invalid method 'getContext' on inferred Array type",
      "confidence": 0.8,
      "line": 107
    },
    {
      "type": "method",
      "element": "gl.clearColor",
      "message": "Method 'clearColor' not found in any class or interface",
      "confidence": 0.8,
      "line": 108
    },
    {
      "type": "method",
      "element": "gl.enable",
      "message": "Method 'enable' not found in any class or interface",
      "confidence": 0.8,
      "line": 109
    },
    {
      "type": "function",
      "element": "calculate",
      "message": "Function 'calculate' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "customFilter",
      "message": "Function 'customFilter' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "import",
      "message": "Function 'import' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Observable",
      "message": "Class 'Observable' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "new Observable(observer => {\n  observer.next(1);\n}).pipe",
      "message": "Method 'pipe' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "observer.next",
      "message": "Method 'next' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "model.predict",
      "message": "Method 'predict' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "React.lazy",
      "message": "Class or object 'React' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "gl.clearColor",
      "message": "Method 'clearColor' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "gl.enable",
      "message": "Method 'enable' not found in any known type",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 8,
    "functions": 30,
    "components": 0,
    "types": 0,
    "hooks": 1,
    "hallucination_count": 20
  },
  "recommendations": [
    "Fix 20 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}