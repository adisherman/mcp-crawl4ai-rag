# JavaScript Built-in False Positives Fix

## Problem
The TypeScript knowledge graph validator was incorrectly flagging JavaScript built-in constructors and global functions as hallucinations, including:
- Constructors: `Date`, `Error`, `Promise`, `Map`, `Set`, `URL`, `URLSearchParams`, etc.
- Global functions: `parseInt`, `parseFloat`, `isNaN`, `isFinite`, `encodeURI`, `decodeURI`, etc.

## Solution Implemented

### 1. Added Built-in Constructor Recognition
Created a comprehensive set of built-in JavaScript constructors in `ts_knowledge_graph_validator.py`:

```python
self.builtin_constructors = {
    # Core JavaScript
    'Date', 'Error', 'TypeError', 'ReferenceError', 'SyntaxError', 'RangeError',
    'EvalError', 'URIError', 'AggregateError',
    'Promise', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Array', 'Object', 'Function',
    'RegExp', 'String', 'Number', 'Boolean', 'Symbol', 'BigInt',
    # ... and many more (93 total)
}
```

### 2. Added Global Function Recognition
Created a comprehensive set of built-in global functions:

```python
self.builtin_global_functions = {
    # Core JavaScript
    'parseInt', 'parseFloat', 'isNaN', 'isFinite', 
    'encodeURI', 'decodeURI', 'encodeURIComponent', 'decodeURIComponent',
    # Browser/Web APIs
    'atob', 'btoa', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
    'fetch', 'alert', 'confirm', 'prompt',
    # ... and more (39 total)
}
```

### 3. Updated Validation Logic

#### For Class Instantiations (`_validate_classes` method):
- Added check for built-in constructors BEFORE querying Neo4j
- If a class name is in `builtin_constructors`, it's immediately marked as VALID with confidence 1.0

#### For Function Calls (`_validate_functions` method):
- Added check for built-in global functions BEFORE querying Neo4j  
- If a function name is in `builtin_global_functions`, it's immediately marked as VALID with confidence 1.0

### 4. Categories of Built-ins Added

1. **Core JavaScript**: Basic types, errors, collections
2. **Typed Arrays**: All typed array constructors
3. **Web APIs**: URL, Blob, File, FormData, Headers, Request/Response
4. **DOM APIs**: DOMParser, Events, Observers
5. **Browser APIs**: WebSocket, Workers, Storage
6. **Media APIs**: MediaStream, WebRTC, Audio
7. **Global Functions**: Parsing, encoding, timers, browser dialogs

## Testing

Created test files to verify the fix:
- `test_builtin_constructors.ts` - TypeScript file using various built-ins
- `test_builtin_logic.py` - Python test to verify recognition logic

Test results show all built-ins are now correctly recognized and won't be flagged as hallucinations.

## Impact

This fix ensures that:
1. Common JavaScript built-in constructors like `new Date()`, `new Error()` are recognized as valid
2. Global functions like `parseInt()`, `parseFloat()` are recognized as valid
3. False positive hallucination detections are significantly reduced
4. Validation confidence scores are more accurate

The validator now properly distinguishes between:
- Valid built-in JavaScript/TypeScript features (high confidence)
- Custom classes/functions that exist in the knowledge graph (high confidence)
- Unknown custom code that might be hallucinated (low confidence)