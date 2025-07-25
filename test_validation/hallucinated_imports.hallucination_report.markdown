{
  "script_path": "test_validation/hallucinated_imports.tsx",
  "analysis_timestamp": "2025-07-25T08:37:42.433331+00:00",
  "overall_confidence": 0.10227272727272727,
  "total_validations": 44,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "authService.useCurrentUser",
      "message": "Method 'useCurrentUser' not found in any class or interface",
      "confidence": 0.8,
      "line": 50
    },
    {
      "type": "method",
      "element": "cacheService.prefetch",
      "message": "Method 'prefetch' not found in any class or interface",
      "confidence": 0.8,
      "line": 54
    },
    {
      "type": "method",
      "element": "aiService.predictFormCompletion",
      "message": "Method 'predictFormCompletion' not found in any class or interface",
      "confidence": 0.8,
      "line": 55
    },
    {
      "type": "method",
      "element": "e.preventDefault",
      "message": "Method 'preventDefault' not found in any class or interface",
      "confidence": 0.8,
      "line": 59
    },
    {
      "type": "method",
      "element": "formValidator.validateAsync",
      "message": "Method 'validateAsync' not found in any class or interface",
      "confidence": 0.8,
      "line": 62
    },
    {
      "type": "method",
      "element": "quantumCalculator.process",
      "message": "Method 'process' not found in any class or interface",
      "confidence": 0.8,
      "line": 64
    },
    {
      "type": "method",
      "element": "authService.submitSecurely",
      "message": "Method 'submitSecurely' not found in any class or interface",
      "confidence": 0.8,
      "line": 68
    },
    {
      "type": "jsx_element",
      "element": "Card",
      "message": "JSX element 'Card' references non-existent component",
      "confidence": 1.0,
      "line": 74
    },
    {
      "type": "import",
      "element": "JSX Element: Card",
      "message": "JSX element 'Card' component not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "sync",
      "message": "Function 'sync' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "authService.useCurrentUser",
      "message": "Method 'useCurrentUser' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "cacheService.prefetch",
      "message": "Method 'prefetch' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "aiService.predictFormCompletion",
      "message": "Method 'predictFormCompletion' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "e.preventDefault",
      "message": "Method 'preventDefault' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "formValidator.validateAsync",
      "message": "Method 'validateAsync' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "quantumCalculator.process",
      "message": "Method 'process' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "authService.submitSecurely",
      "message": "Method 'submitSecurely' not found in any known type",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 16,
    "functions": 17,
    "components": 4,
    "types": 2,
    "hooks": 5,
    "hallucination_count": 17
  },
  "recommendations": [
    "Fix 17 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}