# Relative Import Validation Fix

## Problem
The TypeScript knowledge graph validator was producing false positives when validating relative imports that weren't present in the knowledge graph. This commonly occurred when:
- Analyzing AI-generated scripts that import from local project files
- The knowledge graph didn't contain all project files
- Using internal aliases like `@/components` or `~/utils`

## Solution
The validation logic has been enhanced to better distinguish between:
1. **External libraries** - Should exist in npm/node_modules
2. **Internal project files** - May not be in the knowledge graph yet
3. **Actual hallucinations** - References to non-existent APIs/methods

## Changes Made

### 1. Enhanced Import Classification
- Added logic to identify relative imports (`./`, `../`)
- Added detection for internal aliases (`@/`, `~/`, etc.)
- Module resolver integration to determine if imports are external

### 2. Validation Status Updates
- Internal modules not found in knowledge graph now return `UNCERTAIN` status instead of `NOT_FOUND`
- Confidence scores adjusted based on import type
- Missing exports from internal modules are treated more leniently

### 3. Configuration Options
Added new configuration options in `ValidatorConfig`:
- `strict_internal_imports`: Controls strictness for internal imports (default: False)
- `allow_missing_internal_modules`: Allows missing internal modules (default: True)

### 4. Improved Hallucination Detection
- `UNCERTAIN` status is no longer flagged as a hallucination
- Only high-confidence missing imports are considered hallucinations
- Better handling of partial knowledge graph coverage

## Usage

### Lenient Mode (Default)
```python
config = ValidatorConfig(
    allow_missing_internal_modules=True,
    strict_internal_imports=False
)
validator = TypeScriptKnowledgeGraphValidator(uri, user, password, config)
```

### Strict Mode
```python
config = ValidatorConfig(
    allow_missing_internal_modules=False,
    strict_internal_imports=True
)
validator = TypeScriptKnowledgeGraphValidator(uri, user, password, config)
```

## Example Results

### Before Fix
```
Import './components/Button' - NOT_FOUND (Confidence: 0.0) ❌ HALLUCINATION
Import '../hooks/useAuth' - NOT_FOUND (Confidence: 0.0) ❌ HALLUCINATION
Import '@/services/api' - NOT_FOUND (Confidence: 0.0) ❌ HALLUCINATION
```

### After Fix (Lenient Mode)
```
Import './components/Button' - UNCERTAIN (Confidence: 0.7) ⚠️ May not be parsed yet
Import '../hooks/useAuth' - UNCERTAIN (Confidence: 0.7) ⚠️ May not be parsed yet
Import '@/services/api' - UNCERTAIN (Confidence: 0.7) ⚠️ May not be parsed yet
```

## Testing
Run the test script to see the difference:
```bash
python knowledge_graphs/test_relative_imports.py
```

This will demonstrate:
1. How relative imports are handled in lenient mode
2. The difference when using strict mode
3. That true hallucinations (like 'made-up-library') are still caught

## Results Summary

The fix successfully reduces false positives by:

1. **Import Classification**: 
   - Properly identifies relative imports (`./`, `../`)
   - Recognizes internal aliases (`@/`, `~/`)
   - Distinguishes between known and unknown external libraries

2. **Confidence Scoring**:
   - Known external libraries: 1.00 confidence
   - Unknown external libraries: 0.80 confidence (configurable)
   - Missing internal modules: 0.70 confidence (UNCERTAIN status)
   - True hallucinations: 0.00 confidence (NOT_FOUND status)

3. **Configurable Behavior**:
   - `allow_missing_internal_modules`: Controls leniency for internal imports
   - `strict_internal_imports`: Enforces strict validation
   - `trust_external_libraries`: Assumes external libraries exist

This approach provides flexibility while maintaining accuracy in detecting actual code hallucinations.