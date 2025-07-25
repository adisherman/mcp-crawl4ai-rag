{
  "script_path": "test_validation/hallucinated_patterns.tsx",
  "analysis_timestamp": "2025-07-25T08:38:25.511398+00:00",
  "overall_confidence": 0.11046511627906977,
  "total_validations": 43,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "setConfig.quantum",
      "message": "Invalid method 'quantum' on inferred Set type",
      "confidence": 0.8,
      "line": 71
    },
    {
      "type": "method",
      "element": "setConfig.neural",
      "message": "Invalid method 'neural' on inferred Set type",
      "confidence": 0.8,
      "line": 72
    },
    {
      "type": "method",
      "element": "el.quantumFocus",
      "message": "Method 'quantumFocus' not found in any class or interface",
      "confidence": 0.8,
      "line": 86
    },
    {
      "type": "method",
      "element": "el.neuralValidate",
      "message": "Method 'neuralValidate' not found in any class or interface",
      "confidence": 0.8,
      "line": 87
    },
    {
      "type": "jsx_element",
      "element": "Component",
      "message": "JSX element 'Component' references non-existent component",
      "confidence": 1.0,
      "line": 134
    },
    {
      "type": "import",
      "element": "JSX Element: Component",
      "message": "JSX element 'Component' component not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "component",
      "element": "Component",
      "message": "Component 'Component' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "DashboardProps",
      "message": "Type 'DashboardProps' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "DashboardProps",
      "message": "Type 'DashboardProps' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "DashboardProps",
      "message": "Type 'DashboardProps' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "DashboardProps",
      "message": "Type 'DashboardProps' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "HTMLDivElement",
      "message": "Type 'HTMLDivElement' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "React.ComponentType",
      "message": "Type 'React.ComponentType' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "withQuantumEnhancement",
      "message": "Function 'withQuantumEnhancement' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "el.quantumFocus",
      "message": "Method 'quantumFocus' not found in any known type",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "el.neuralValidate",
      "message": "Method 'neuralValidate' not found in any known type",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 4,
    "functions": 19,
    "components": 5,
    "types": 7,
    "hooks": 8,
    "hallucination_count": 16
  },
  "recommendations": [
    "Fix 16 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}