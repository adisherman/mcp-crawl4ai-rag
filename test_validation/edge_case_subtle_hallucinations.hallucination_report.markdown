{
  "script_path": "test_validation/edge_case_subtle_hallucinations.ts",
  "analysis_timestamp": "2025-07-25T13:00:39.324658+00:00",
  "overall_confidence": 0.0703125,
  "total_validations": 32,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "data.fiter",
      "message": "Invalid method 'fiter' on inferred Array type",
      "confidence": 0.8,
      "line": 4
    },
    {
      "type": "method",
      "element": "userName.toUppercase",
      "message": "Invalid method 'toUppercase' on inferred String type",
      "confidence": 0.8,
      "line": 5
    },
    {
      "type": "method",
      "element": "str.push",
      "message": "Invalid method 'push' on inferred String type",
      "confidence": 0.8,
      "line": 10
    },
    {
      "type": "method",
      "element": "num.toUpperCase",
      "message": "Invalid method 'toUpperCase' on inferred Number type",
      "confidence": 0.8,
      "line": 12
    },
    {
      "type": "method",
      "element": "date.getTimeZoneOffset",
      "message": "Invalid method 'getTimeZoneOffset' on inferred Date type",
      "confidence": 0.8,
      "line": 17
    },
    {
      "type": "method",
      "element": "date.getLocalTime",
      "message": "Invalid method 'getLocalTime' on inferred Date type",
      "confidence": 0.8,
      "line": 18
    },
    {
      "type": "method",
      "element": "promise.always",
      "message": "Method 'always' not found in any class or interface",
      "confidence": 0.8,
      "line": 23
    },
    {
      "type": "method",
      "element": "window.localStorage.setItem",
      "message": "Method 'setItem' not found in any class or interface",
      "confidence": 0.8,
      "line": 29
    },
    {
      "type": "method",
      "element": "element.setState",
      "message": "Method 'setState' not found in any class or interface",
      "confidence": 0.8,
      "line": 33
    },
    {
      "type": "method",
      "element": "obs.subscribe",
      "message": "Invalid method 'subscribe' on inferred Array type",
      "confidence": 0.8,
      "line": 39
    },
    {
      "type": "method",
      "element": "obs.onSubscribe",
      "message": "Invalid method 'onSubscribe' on inferred Array type",
      "confidence": 0.8,
      "line": 40
    },
    {
      "type": "method",
      "element": "str2.subString",
      "message": "Invalid method 'subString' on inferred String type",
      "confidence": 0.8,
      "line": 46
    },
    {
      "type": "method",
      "element": "Math.randomInt",
      "message": "Invalid method 'randomInt' on built-in object 'Math'",
      "confidence": 0.95,
      "line": 49
    },
    {
      "type": "method",
      "element": "console.chart",
      "message": "Invalid method 'chart' on built-in object 'console'",
      "confidence": 0.95,
      "line": 51
    },
    {
      "type": "function",
      "element": "keys",
      "message": "Function 'keys' not found in knowledge graph",
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
      "element": "promise.always",
      "message": "Method 'always' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Buffer.from",
      "message": "Class or object 'Buffer' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "window.localStorage.setItem",
      "message": "Method 'setItem' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "element.setState",
      "message": "Method 'setState' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "[].isArray",
      "message": "Class or object '[]' not found in knowledge graph",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 1,
    "functions": 31,
    "components": 0,
    "types": 0,
    "hooks": 0,
    "hallucination_count": 21
  },
  "recommendations": [
    "Fix 21 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}