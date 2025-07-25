# Built-in JavaScript Object Method Validation Fix

## Summary

I've enhanced the TypeScript knowledge graph validator to properly validate built-in JavaScript object methods. This fix addresses the issue where method calls on built-in objects like Array, String, Math, etc. were not being validated.

## Changes Made

### 1. Added Comprehensive Built-in Method Dictionary

In `ts_knowledge_graph_validator.py`, I added a comprehensive dictionary of built-in JavaScript object methods:

```python
self.builtin_object_methods = {
    'Array': {
        'push', 'pop', 'shift', 'unshift', 'splice', 'sort', 'reverse', 'fill', 'copyWithin',
        'concat', 'slice', 'indexOf', 'lastIndexOf', 'includes', 'join', 'toString', 'toLocaleString',
        'forEach', 'map', 'filter', 'reduce', 'reduceRight', 'find', 'findIndex', 'findLast', 'findLastIndex',
        'some', 'every', 'flat', 'flatMap', 'from', 'isArray', 'of', 'entries', 'keys', 'values', 
        'at', 'toSorted', 'toReversed', 'toSpliced', 'with'
    },
    'String': {
        'charAt', 'charCodeAt', 'codePointAt', 'concat', 'includes', 'endsWith', 'indexOf', 'lastIndexOf',
        'localeCompare', 'match', 'matchAll', 'normalize', 'padEnd', 'padStart', 'repeat', 'replace',
        'replaceAll', 'search', 'slice', 'split', 'startsWith', 'substring', 'substr', 'toLowerCase',
        'toLocaleLowerCase', 'toUpperCase', 'toLocaleUpperCase', 'trim', 'trimStart', 'trimLeft',
        'trimEnd', 'trimRight', 'valueOf', 'toString', 'at'
    },
    'Number': {
        'isFinite', 'isInteger', 'isNaN', 'isSafeInteger', 'parseFloat', 'parseInt',
        'toExponential', 'toFixed', 'toLocaleString', 'toPrecision', 'toString', 'valueOf'
    },
    'Object': {
        'assign', 'create', 'defineProperties', 'defineProperty', 'entries', 'freeze',
        'fromEntries', 'getOwnPropertyDescriptor', 'getOwnPropertyDescriptors',
        'getOwnPropertyNames', 'getOwnPropertySymbols', 'getPrototypeOf', 'hasOwn',
        'is', 'isExtensible', 'isFrozen', 'isSealed', 'keys', 'preventExtensions',
        'seal', 'setPrototypeOf', 'values', 'hasOwnProperty', 'isPrototypeOf',
        'propertyIsEnumerable', 'toLocaleString', 'toString', 'valueOf'
    },
    'Math': {
        'abs', 'acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh', 'cbrt', 'ceil',
        'clz32', 'cos', 'cosh', 'exp', 'expm1', 'floor', 'fround', 'hypot', 'imul', 'log',
        'log10', 'log1p', 'log2', 'max', 'min', 'pow', 'random', 'round', 'sign', 'sin',
        'sinh', 'sqrt', 'tan', 'tanh', 'trunc'
    },
    'Date': {
        'now', 'parse', 'UTC', 'getDate', 'getDay', 'getFullYear', 'getHours', 'getMilliseconds',
        'getMinutes', 'getMonth', 'getSeconds', 'getTime', 'getTimezoneOffset', 'getUTCDate',
        'getUTCDay', 'getUTCFullYear', 'getUTCHours', 'getUTCMilliseconds', 'getUTCMinutes',
        'getUTCMonth', 'getUTCSeconds', 'getYear', 'setDate', 'setFullYear', 'setHours',
        'setMilliseconds', 'setMinutes', 'setMonth', 'setSeconds', 'setTime', 'setUTCDate',
        'setUTCFullYear', 'setUTCHours', 'setUTCMilliseconds', 'setUTCMinutes', 'setUTCMonth',
        'setUTCSeconds', 'setYear', 'toDateString', 'toISOString', 'toJSON', 'toLocaleDateString',
        'toLocaleString', 'toLocaleTimeString', 'toString', 'toTimeString', 'toUTCString', 'valueOf'
    },
    'JSON': {
        'parse', 'stringify'
    },
    'Promise': {
        'all', 'allSettled', 'any', 'race', 'reject', 'resolve', 'then', 'catch', 'finally'
    },
    'Map': {
        'clear', 'delete', 'entries', 'forEach', 'get', 'has', 'keys', 'set', 'values'
    },
    'Set': {
        'add', 'clear', 'delete', 'entries', 'forEach', 'has', 'keys', 'values'
    },
    'RegExp': {
        'exec', 'test', 'toString', 'compile'
    },
    'Function': {
        'apply', 'bind', 'call', 'toString'
    },
    'console': {
        'assert', 'clear', 'count', 'countReset', 'debug', 'dir', 'dirxml', 'error',
        'group', 'groupCollapsed', 'groupEnd', 'info', 'log', 'table', 'time', 'timeEnd',
        'timeLog', 'timeStamp', 'trace', 'warn'
    },
    'window': {
        'alert', 'blur', 'clearInterval', 'clearTimeout', 'close', 'confirm', 'focus',
        'getComputedStyle', 'getSelection', 'matchMedia', 'moveBy', 'moveTo', 'open',
        'postMessage', 'print', 'prompt', 'requestAnimationFrame', 'requestIdleCallback',
        'resizeBy', 'resizeTo', 'scroll', 'scrollBy', 'scrollTo', 'setInterval', 'setTimeout',
        'stop', 'cancelAnimationFrame', 'cancelIdleCallback'
    },
    'document': {
        'getElementById', 'getElementsByClassName', 'getElementsByName', 'getElementsByTagName',
        'getElementsByTagNameNS', 'querySelector', 'querySelectorAll', 'createElement',
        'createElementNS', 'createTextNode', 'createComment', 'createDocumentFragment',
        'createEvent', 'createRange', 'createTreeWalker', 'adoptNode', 'importNode',
        'open', 'close', 'write', 'writeln', 'hasFocus', 'execCommand', 'queryCommandEnabled',
        'queryCommandIndeterm', 'queryCommandState', 'queryCommandSupported', 'queryCommandValue',
        'elementFromPoint', 'elementsFromPoint', 'caretPositionFromPoint', 'getSelection'
    },
    'process': {
        'abort', 'chdir', 'cpuUsage', 'cwd', 'disconnect', 'dlopen', 'emitWarning', 'exit',
        'getActiveResourcesInfo', 'getegid', 'geteuid', 'getgid', 'getgroups', 'getuid',
        'hasUncaughtExceptionCaptureCallback', 'hrtime', 'initgroups', 'kill', 'memoryUsage',
        'nextTick', 'resourceUsage', 'send', 'setegid', 'seteuid', 'setgid', 'setgroups',
        'setuid', 'setUncaughtExceptionCaptureCallback', 'umask', 'uptime'
    },
    'global': {
        'clearImmediate', 'clearInterval', 'clearTimeout', 'setImmediate', 'setInterval', 'setTimeout'
    }
}
```

### 2. Enhanced Method Call Validation

Updated the `_validate_method_calls` method to:

1. **Validate static method calls** on built-in objects (e.g., `Array.from()`, `Object.keys()`)
2. **Validate instance method calls** based on type information (e.g., `myArray.filter()`)
3. **Infer types from variable names** when type information is not available
4. **Handle prototype method calls** (e.g., `Array.prototype.slice.call()`)
5. **Provide helpful suggestions** for misspelled or invalid methods

### 3. Added Smart Method Suggestion System

Created `_find_similar_methods` function that:
- Finds methods with similar prefixes
- Detects common typos (e.g., "lenght" → "length")
- Uses fuzzy matching to suggest closest valid methods
- Provides helpful error messages with suggestions

### 4. Added Type Inference from Variable Names

Created `_infer_builtin_type_from_name` function that infers types based on common naming patterns:
- Arrays: variables ending with 's', 'list', 'array', or named 'items', 'elements', etc.
- Strings: variables ending with 'name', 'text', 'message', 'url', etc.
- Numbers: variables ending with 'count', 'index', 'size', 'total', etc.
- Dates: variables containing 'date' or 'time'
- Maps/Sets: variables containing 'map' or 'set'

## How It Works

When validating method calls, the validator now:

1. **Checks if the object is a known built-in object** (e.g., `Math`, `JSON`, `console`)
   - Validates the method against the known methods for that object
   - Reports hallucinations for invalid methods with suggestions

2. **Checks if the object has type information** (e.g., typed as `Array`, `string`)
   - Validates methods against the appropriate built-in type
   - Reports hallucinations for invalid methods

3. **Infers type from variable name** when no type information is available
   - Uses naming conventions to guess the type
   - Validates methods with reduced confidence

4. **Handles prototype method calls** (e.g., `Array.prototype.slice`)
   - Validates against the base object's methods

5. **Provides helpful suggestions** for invalid methods
   - Suggests similar method names
   - Corrects common typos
   - Lists available methods

## Benefits

1. **Catches common hallucinations**: AI often invents plausible-sounding but non-existent methods
2. **Helps with typos**: Suggests corrections for misspelled method names
3. **Educates about available methods**: Shows what methods are actually available
4. **Supports modern JavaScript**: Includes ES2021+ methods like `replaceAll`, `at`, etc.
5. **Works with type inference**: Can validate even without explicit type annotations

## Note on Current Limitation

The current TypeScript parser service only extracts **definitions** (classes, functions, types) from code, not **usage** (method calls, function calls). This means the validator can't detect method calls in AI-generated code unless the parser is enhanced to extract usage information.

To fully utilize this validation, the TypeScript parser needs to be updated to extract:
- Method calls (`object.method()`)
- Function calls (`function()`)
- Property accesses (`object.property`)

Once the parser extracts this information, the built-in method validation will automatically work.