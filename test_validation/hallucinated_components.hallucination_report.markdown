{
  "script_path": "test_validation/hallucinated_components.tsx",
  "analysis_timestamp": "2025-07-25T08:36:15.179064+00:00",
  "overall_confidence": 0.10984848484848485,
  "total_validations": 33,
  "hallucinations_detected": [
    {
      "type": "method",
      "element": "e.preventDefault",
      "message": "Method 'preventDefault' not found in any class or interface",
      "confidence": 0.8,
      "line": 47
    },
    {
      "type": "jsx_element",
      "element": "FormSlider",
      "message": "JSX element 'FormSlider' references non-existent component",
      "confidence": 1.0,
      "line": 68
    },
    {
      "type": "jsx_element",
      "element": "FormColorPicker",
      "message": "JSX element 'FormColorPicker' references non-existent component",
      "confidence": 1.0,
      "line": 79
    },
    {
      "type": "jsx_element",
      "element": "AdvancedDatePicker",
      "message": "JSX element 'AdvancedDatePicker' references non-existent component",
      "confidence": 1.0,
      "line": 89
    },
    {
      "type": "import",
      "element": "JSX Element: FormSlider",
      "message": "JSX element 'FormSlider' component not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "import",
      "element": "JSX Element: FormColorPicker",
      "message": "JSX element 'FormColorPicker' component not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "import",
      "element": "JSX Element: AdvancedDatePicker",
      "message": "JSX element 'AdvancedDatePicker' component not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "component",
      "element": "AdvancedDatePicker",
      "message": "Component 'AdvancedDatePicker' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "Date",
      "message": "Type 'Date' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "type",
      "element": "ProfileFormProps",
      "message": "Type 'ProfileFormProps' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "validate",
      "message": "Function 'validate' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "onSubmit",
      "message": "Function 'onSubmit' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "animateField",
      "message": "Function 'animateField' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Date",
      "message": "Class 'Date' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Date",
      "message": "Class 'Date' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "Date",
      "message": "Class 'Date' not found in knowledge graph",
      "confidence": 1.0
    },
    {
      "type": "function",
      "element": "e.preventDefault",
      "message": "Method 'preventDefault' not found in any known type",
      "confidence": 1.0
    }
  ],
  "validation_summary": {
    "imports": 6,
    "functions": 15,
    "components": 5,
    "types": 4,
    "hooks": 3,
    "hallucination_count": 17
  },
  "recommendations": [
    "Fix 17 detected hallucinations",
    "Review imported modules and their available exports",
    "Verify method calls exist on their respective objects",
    "Check type definitions and interfaces are properly imported"
  ]
}