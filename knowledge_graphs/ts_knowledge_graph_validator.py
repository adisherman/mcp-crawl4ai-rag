"""
TypeScript/React Knowledge Graph Validator

Validates AI-generated TypeScript/JavaScript/React code against Neo4j knowledge graph.
Checks imports, components, hooks, types, and functions.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from neo4j import AsyncGraphDatabase

from ts_script_analyzer import TypeScriptScriptAnalyzer
from validator_config import ValidatorConfig, get_project_config
from module_resolver import ModuleResolver
from method_chaining_support import MethodChainResolver

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID = "INVALID" 
    UNCERTAIN = "UNCERTAIN"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class ValidationResult:
    """Result of validating a single element"""
    status: ValidationStatus
    confidence: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ComponentValidation:
    """Validation result for React component usage"""
    component_name: str
    props_used: List[str]
    validation: ValidationResult
    expected_props: List[str] = field(default_factory=list)
    missing_required_props: List[str] = field(default_factory=list)
    unknown_props: List[str] = field(default_factory=list)


@dataclass
class HookValidation:
    """Validation result for React hook usage"""
    hook_name: str
    validation: ValidationResult
    hook_rules_violated: List[str] = field(default_factory=list)


@dataclass
class TypeValidation:
    """Validation result for TypeScript type usage"""
    type_name: str
    kind: str  # 'interface', 'type', 'implements', etc.
    validation: ValidationResult
    expected_properties: List[str] = field(default_factory=list)


@dataclass
class FunctionValidation:
    """Validation result for function/method calls"""
    function_name: str
    module: Optional[str]
    args_count: int
    validation: ValidationResult
    expected_params: List[str] = field(default_factory=list)


@dataclass
class ImportValidation:
    """Validation result for imports"""
    module: str
    imported_items: List[Dict[str, str]]
    validation: ValidationResult
    available_exports: List[str] = field(default_factory=list)


@dataclass
class TypeScriptValidationResult:
    """Complete validation results for a TypeScript/React script"""
    script_path: str
    analysis_result: Dict[str, Any]
    import_validations: List[ImportValidation] = field(default_factory=list)
    component_validations: List[ComponentValidation] = field(default_factory=list)
    hook_validations: List[HookValidation] = field(default_factory=list)
    type_validations: List[TypeValidation] = field(default_factory=list)
    function_validations: List[FunctionValidation] = field(default_factory=list)
    overall_confidence: float = 0.0
    hallucinations_detected: List[Dict[str, Any]] = field(default_factory=list)


class TypeScriptKnowledgeGraphValidator:
    """Validates TypeScript/React code against Neo4j knowledge graph"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, config: Optional[ValidatorConfig] = None):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.analyzer = TypeScriptScriptAnalyzer()
        
        # Use provided config or get default
        self.config = config or get_project_config()
        
        # Initialize method chain resolver
        self.method_chain_resolver = MethodChainResolver()
        
        # Local context - populated during validation
        self.local_components: Set[str] = set()
        self.local_functions: Set[str] = set()
        self.local_types: Set[str] = set()
        self.local_interfaces: Set[str] = set()
        self.local_classes: Set[str] = set()
        
        # Track external imports for better validation
        self.external_imports: Dict[str, str] = {}  # name -> module mapping
        
        # Track functions/values from hooks
        self.hook_returns: Dict[str, str] = {}  # name -> hook mapping
        
        # Track variable types for method validation
        self.variable_types: Dict[str, Dict[str, Any]] = {}  # name -> {type, initializer, line}
        
        # React hooks that have specific rules
        self.hooks_with_rules = {
            'useState': ['Must be called at top level', 'Returns array with state and setter'],
            'useEffect': ['Must be called at top level', 'Dependencies array recommended'],
            'useContext': ['Must be called at top level', 'Context must be created first'],
            'useReducer': ['Must be called at top level', 'Requires reducer function'],
            'useCallback': ['Must be called at top level', 'Dependencies array required'],
            'useMemo': ['Must be called at top level', 'Dependencies array required'],
            'useRef': ['Must be called at top level', 'Returns mutable ref object'],
            'useImperativeHandle': ['Must be called at top level', 'Used with forwardRef'],
            'useLayoutEffect': ['Must be called at top level', 'Runs synchronously'],
            'useDebugValue': ['Must be called at top level', 'For custom hooks only']
        }
        
        # Built-in JavaScript constructors
        self.builtin_constructors = {
            # Core JavaScript
            'Date', 'Error', 'TypeError', 'ReferenceError', 'SyntaxError', 'RangeError',
            'EvalError', 'URIError', 'AggregateError',
            'Promise', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Array', 'Object', 'Function',
            'RegExp', 'String', 'Number', 'Boolean', 'Symbol', 'BigInt',
            'Proxy', 'Reflect', 'WeakRef', 'FinalizationRegistry',
            # Typed Arrays
            'Int8Array', 'Uint8Array', 'Uint8ClampedArray', 'Int16Array', 'Uint16Array',
            'Int32Array', 'Uint32Array', 'Float32Array', 'Float64Array', 'BigInt64Array',
            'BigUint64Array', 'ArrayBuffer', 'SharedArrayBuffer', 'DataView',
            # Web APIs
            'URL', 'URLSearchParams', 'TextEncoder', 'TextDecoder', 
            'Blob', 'File', 'FileReader', 'FileList',
            'FormData', 'Headers', 'Request', 'Response', 'AbortController', 'AbortSignal',
            # DOM APIs
            'DOMParser', 'XMLSerializer', 'XPathEvaluator', 'XSLTProcessor',
            'CustomEvent', 'Event', 'EventTarget', 'MediaQueryList',
            'MouseEvent', 'KeyboardEvent', 'TouchEvent', 'FocusEvent', 'InputEvent',
            'WheelEvent', 'DragEvent', 'PointerEvent', 'ClipboardEvent', 'AnimationEvent',
            'TransitionEvent', 'CompositionEvent', 'HashChangeEvent', 'PopStateEvent',
            'ProgressEvent', 'StorageEvent', 'BeforeUnloadEvent', 'PageTransitionEvent',
            # Browser APIs
            'WebSocket', 'EventSource', 'XMLHttpRequest',
            'Worker', 'SharedWorker', 'ServiceWorker', 'MessageChannel', 'MessagePort',
            'BroadcastChannel', 'Notification', 'PerformanceObserver',
            'IntersectionObserver', 'MutationObserver', 'ResizeObserver',
            # Storage APIs
            'Storage', 'StorageEvent', 'IDBDatabase', 'IDBTransaction', 'IDBRequest',
            # Media APIs
            'MediaStream', 'MediaRecorder', 'AudioContext', 'AnalyserNode',
            'RTCPeerConnection', 'RTCSessionDescription', 'RTCIceCandidate',
            # Other APIs
            'ImageData', 'Path2D', 'WebAssembly', 'Intl',
            # HTML Element constructors
            'HTMLElement', 'HTMLDivElement', 'HTMLSpanElement', 'HTMLParagraphElement',
            'HTMLHeadingElement', 'HTMLButtonElement', 'HTMLInputElement', 'HTMLTextAreaElement',
            'HTMLSelectElement', 'HTMLOptionElement', 'HTMLFormElement', 'HTMLLabelElement',
            'HTMLFieldSetElement', 'HTMLLegendElement', 'HTMLUListElement', 'HTMLOListElement',
            'HTMLLIElement', 'HTMLAnchorElement', 'HTMLImageElement', 'HTMLVideoElement',
            'HTMLAudioElement', 'HTMLCanvasElement', 'HTMLTableElement', 'HTMLTableRowElement',
            'HTMLTableCellElement', 'HTMLIFrameElement', 'HTMLScriptElement', 'HTMLStyleElement',
            'HTMLLinkElement', 'HTMLMetaElement', 'HTMLBaseElement', 'HTMLTitleElement'
        }
        
        # Built-in global functions
        self.builtin_global_functions = {
            # Core JavaScript
            'parseInt', 'parseFloat', 'isNaN', 'isFinite', 
            'encodeURI', 'decodeURI', 'encodeURIComponent', 'decodeURIComponent',
            'eval', 'escape', 'unescape',
            # Browser/Web APIs
            'atob', 'btoa', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
            'requestAnimationFrame', 'cancelAnimationFrame',
            'requestIdleCallback', 'cancelIdleCallback', 'queueMicrotask',
            'alert', 'confirm', 'prompt', 'fetch', 'getComputedStyle',
            'matchMedia', 'postMessage', 'structuredClone',
            'createImageBitmap', 'crypto.getRandomValues',
            # Node.js specific (when running in Node environment)
            'setImmediate', 'clearImmediate', 'require', '__dirname', '__filename',
            # Console methods (though usually called as console.log)
            'console', 'assert'
        }
        
        # Track namespace imports (e.g., import * as z from 'zod')
        self.namespace_imports: Dict[str, str] = {}  # alias -> module mapping
        
        # Common namespace methods for popular libraries
        self.namespace_methods = {
            'zod': {
                # Core type constructors
                'string', 'number', 'boolean', 'date', 'undefined', 'null', 'void',
                'any', 'unknown', 'never', 'bigint', 'symbol',
                # Complex types
                'object', 'array', 'tuple', 'union', 'discriminatedUnion', 'intersection',
                'record', 'map', 'set', 'function', 'promise', 'lazy',
                # Literals and enums
                'literal', 'enum', 'nativeEnum',
                # Utility methods
                'optional', 'nullable', 'nullish', 'required', 'preprocess', 'custom',
                'instanceof', 'refine', 'superRefine', 'transform', 'default', 'catch',
                'brand', 'pipe', 'coerce',
                # String specific methods (available on z.string())
                'email', 'url', 'uuid', 'cuid', 'cuid2', 'ulid', 'regex', 'includes',
                'startsWith', 'endsWith', 'datetime', 'ip', 'duration', 'emoji',
                'nanoid', 'toLowerCase', 'toUpperCase', 'length', 'min', 'max', 'trim',
                'nonempty',
                # Number specific methods (available on z.number())
                'gt', 'gte', 'lt', 'lte', 'int', 'positive', 'nonnegative', 'negative',
                'nonpositive', 'multipleOf', 'finite', 'safe',
                # Type guards
                'is', 'check', 'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                # Schema methods
                'shape', 'keyof', 'extend', 'merge', 'pick', 'omit', 'partial', 'deepPartial',
                'required', 'passthrough', 'strict', 'strip', 'catchall', 'describe',
                # Error handling
                'ZodError', 'ZodIssue', 'ZodSchema', 'ZodType', 'infer'
            },
            'yup': {
                # Core types
                'string', 'number', 'boolean', 'date', 'array', 'object', 'mixed',
                # Schema methods
                'reach', 'lazy', 'ref', 'ValidationError', 'setLocale',
                # Type methods
                'required', 'nullable', 'optional', 'defined', 'notRequired',
                'oneOf', 'notOneOf', 'when', 'test', 'transform', 'default',
                'strip', 'strict', 'concat', 'validate', 'validateSync',
                'isValid', 'isValidSync', 'cast', 'describe', 'clone',
                'label', 'meta', 'withMutation'
            },
            'joi': {
                # Core types
                'any', 'array', 'boolean', 'date', 'function', 'number', 'object',
                'string', 'symbol', 'alternatives', 'binary', 'link',
                # Utilities
                'compile', 'defaults', 'expression', 'extend', 'isError', 'isExpression',
                'isRef', 'isSchema', 'ref', 'types', 'version', 'ValidationError',
                # Common methods
                'allow', 'default', 'description', 'empty', 'error', 'example',
                'external', 'failover', 'forbidden', 'id', 'invalid', 'label',
                'meta', 'note', 'optional', 'prefs', 'presence', 'raw',
                'required', 'result', 'rule', 'ruleset', 'shared', 'strict',
                'strip', 'tag', 'tailor', 'unit', 'valid', 'validate',
                'validateAsync', 'warn', 'warning', 'when'
            },
            'lodash': {
                # Array methods
                'chunk', 'compact', 'concat', 'difference', 'differenceBy', 'differenceWith',
                'drop', 'dropRight', 'dropRightWhile', 'dropWhile', 'fill', 'findIndex',
                'findLastIndex', 'first', 'flatten', 'flattenDeep', 'flattenDepth',
                'fromPairs', 'head', 'indexOf', 'initial', 'intersection', 'intersectionBy',
                'intersectionWith', 'join', 'last', 'lastIndexOf', 'nth', 'pull', 'pullAll',
                'pullAllBy', 'pullAllWith', 'pullAt', 'remove', 'reverse', 'slice',
                'sortedIndex', 'sortedIndexBy', 'sortedIndexOf', 'sortedLastIndex',
                'sortedLastIndexBy', 'sortedLastIndexOf', 'sortedUniq', 'sortedUniqBy',
                'tail', 'take', 'takeRight', 'takeRightWhile', 'takeWhile', 'union',
                'unionBy', 'unionWith', 'uniq', 'uniqBy', 'uniqWith', 'unzip', 'unzipWith',
                'without', 'xor', 'xorBy', 'xorWith', 'zip', 'zipObject', 'zipObjectDeep', 'zipWith',
                # Collection methods
                'countBy', 'each', 'eachRight', 'every', 'filter', 'find', 'findLast',
                'flatMap', 'flatMapDeep', 'flatMapDepth', 'forEach', 'forEachRight',
                'groupBy', 'includes', 'invokeMap', 'keyBy', 'map', 'orderBy',
                'partition', 'reduce', 'reduceRight', 'reject', 'sample', 'sampleSize',
                'shuffle', 'size', 'some', 'sortBy',
                # Object methods
                'assign', 'assignIn', 'assignInWith', 'assignWith', 'at', 'create',
                'defaults', 'defaultsDeep', 'entries', 'entriesIn', 'extend', 'extendWith',
                'findKey', 'findLastKey', 'forIn', 'forInRight', 'forOwn', 'forOwnRight',
                'functions', 'functionsIn', 'get', 'has', 'hasIn', 'invert', 'invertBy',
                'invoke', 'keys', 'keysIn', 'mapKeys', 'mapValues', 'merge', 'mergeWith',
                'omit', 'omitBy', 'pick', 'pickBy', 'result', 'set', 'setWith', 'toPairs',
                'toPairsIn', 'transform', 'unset', 'update', 'updateWith', 'values', 'valuesIn',
                # String methods
                'camelCase', 'capitalize', 'deburr', 'endsWith', 'escape', 'escapeRegExp',
                'kebabCase', 'lowerCase', 'lowerFirst', 'pad', 'padEnd', 'padStart',
                'parseInt', 'repeat', 'replace', 'snakeCase', 'split', 'startCase',
                'startsWith', 'template', 'toLower', 'toUpper', 'trim', 'trimEnd',
                'trimStart', 'truncate', 'unescape', 'upperCase', 'upperFirst', 'words',
                # Utility methods
                'attempt', 'bindAll', 'cond', 'conforms', 'constant', 'defaultTo',
                'flow', 'flowRight', 'identity', 'iteratee', 'matches', 'matchesProperty',
                'method', 'methodOf', 'mixin', 'noop', 'nthArg', 'over', 'overEvery',
                'overSome', 'property', 'propertyOf', 'range', 'rangeRight', 'stubArray',
                'stubFalse', 'stubObject', 'stubString', 'stubTrue', 'times', 'toPath',
                'uniqueId',
                # Function methods
                'after', 'ary', 'before', 'bind', 'bindKey', 'curry', 'curryRight',
                'debounce', 'defer', 'delay', 'flip', 'memoize', 'negate', 'once',
                'overArgs', 'partial', 'partialRight', 'rearg', 'rest', 'spread',
                'throttle', 'unary', 'wrap',
                # Lang methods
                'castArray', 'clone', 'cloneDeep', 'cloneDeepWith', 'cloneWith',
                'conformsTo', 'eq', 'gt', 'gte', 'isArguments', 'isArray', 'isArrayBuffer',
                'isArrayLike', 'isArrayLikeObject', 'isBoolean', 'isBuffer', 'isDate',
                'isElement', 'isEmpty', 'isEqual', 'isEqualWith', 'isError', 'isFinite',
                'isFunction', 'isInteger', 'isLength', 'isMap', 'isMatch', 'isMatchWith',
                'isNaN', 'isNative', 'isNil', 'isNull', 'isNumber', 'isObject',
                'isObjectLike', 'isPlainObject', 'isRegExp', 'isSafeInteger', 'isSet',
                'isString', 'isSymbol', 'isTypedArray', 'isUndefined', 'isWeakMap',
                'isWeakSet', 'lt', 'lte', 'toArray', 'toFinite', 'toInteger', 'toLength',
                'toNumber', 'toPlainObject', 'toSafeInteger', 'toString',
                # Math methods
                'add', 'ceil', 'divide', 'floor', 'max', 'maxBy', 'mean', 'meanBy',
                'min', 'minBy', 'multiply', 'round', 'subtract', 'sum', 'sumBy',
                # Number methods
                'clamp', 'inRange', 'random'
            },
            'ramda': {
                # Core functions
                'compose', 'pipe', 'curry', 'partial', 'flip', 'identity', 'always',
                'T', 'F', 'not', 'both', 'either', 'complement', 'defaultTo', 'empty',
                'isNil', 'type', 'is', 'equals', 'identical', 'lt', 'lte', 'gt', 'gte',
                # List functions
                'map', 'filter', 'reduce', 'reduceRight', 'find', 'findIndex', 'findLast',
                'findLastIndex', 'all', 'any', 'none', 'head', 'last', 'tail', 'init',
                'take', 'takeLast', 'takeWhile', 'takeLastWhile', 'drop', 'dropLast',
                'dropWhile', 'dropLastWhile', 'slice', 'remove', 'insert', 'insertAll',
                'append', 'prepend', 'concat', 'reverse', 'sort', 'sortBy', 'sortWith',
                'groupBy', 'groupWith', 'indexBy', 'countBy', 'partition', 'pluck',
                'project', 'transpose', 'zip', 'zipWith', 'zipObj', 'uniq', 'uniqBy',
                'uniqWith', 'union', 'unionWith', 'intersection', 'intersectionWith',
                'difference', 'differenceWith', 'symmetricDifference', 'symmetricDifferenceWith',
                # Object functions
                'prop', 'path', 'propOr', 'pathOr', 'props', 'pick', 'pickAll', 'pickBy',
                'omit', 'assoc', 'assocPath', 'dissoc', 'dissocPath', 'has', 'hasIn',
                'hasPath', 'keys', 'keysIn', 'values', 'valuesIn', 'toPairs', 'toPairsIn',
                'fromPairs', 'merge', 'mergeRight', 'mergeDeepRight', 'mergeLeft',
                'mergeDeepLeft', 'mergeWith', 'mergeWithKey', 'mergeDeepWith',
                'mergeDeepWithKey', 'evolve', 'applySpec', 'mapObjIndexed', 'forEachObjIndexed',
                # Function functions
                'apply', 'call', 'unapply', 'binary', 'unary', 'nAry', 'arity', 'invoker',
                'construct', 'constructN', 'converge', 'juxt', 'useWith', 'lift', 'liftN',
                'ap', 'of', 'empty', 'chain', 'pipeK', 'composeK', 'pipeP', 'composeP',
                # Logic functions
                'and', 'or', 'not', 'both', 'either', 'allPass', 'anyPass', 'cond',
                'ifElse', 'unless', 'when', 'pathEq', 'propEq', 'propIs', 'propSatisfies',
                'pathSatisfies', 'where', 'whereEq', 'isEmpty', 'isNil'
            },
            'dayjs': {
                # Constructor and parsing
                'dayjs', 'unix', 'utc', 'parseZone', 'isValid', 'invalidDate',
                # Get and set
                'year', 'month', 'date', 'day', 'hour', 'minute', 'second', 'millisecond',
                'set', 'get', 'clone', 'toDate', 'toArray', 'toJSON', 'toISOString',
                'toString', 'toObject', 'unix', 'valueOf', 'daysInMonth',
                # Manipulate
                'add', 'subtract', 'startOf', 'endOf', 'local', 'utc', 'utcOffset',
                # Display
                'format', 'fromNow', 'from', 'toNow', 'to', 'calendar', 'diff',
                # Query
                'isBefore', 'isSame', 'isAfter', 'isSameOrBefore', 'isSameOrAfter',
                'isBetween', 'isDayjs', 'isLeapYear',
                # Plugin APIs
                'locale', 'localeData', 'weekday', 'isoWeekday', 'weekYear', 'isoWeekYear',
                'quarter', 'isoWeek', 'week', 'isoWeeksInYear', 'weeksInYear',
                'min', 'max', 'extend', 'plugin'
            },
            'axios': {
                # Main methods
                'request', 'get', 'delete', 'head', 'options', 'post', 'put', 'patch',
                'getUri', 'create', 'all', 'spread', 'isCancel', 'CancelToken',
                'isAxiosError', 'toFormData', 'AxiosError', 'Cancel', 'Axios',
                # Interceptors
                'interceptors', 'defaults'
            },
            'react': {
                # Core exports
                'createElement', 'cloneElement', 'createFactory', 'isValidElement',
                'Children', 'Component', 'PureComponent', 'Fragment', 'StrictMode',
                'Suspense', 'Profiler', 'lazy', 'memo', 'forwardRef', 'createRef',
                'createContext', 'useContext', 'useState', 'useReducer', 'useEffect',
                'useLayoutEffect', 'useCallback', 'useMemo', 'useRef', 'useImperativeHandle',
                'useDebugValue', 'useDeferredValue', 'useTransition', 'useId',
                'useSyncExternalStore', 'useInsertionEffect', 'startTransition',
                'version', 'act'
            },
            'next': {
                # Next.js specific
                'Link', 'Image', 'Head', 'Script', 'Router', 'useRouter',
                'withRouter', 'NextPage', 'NextApiRequest', 'NextApiResponse',
                'GetStaticProps', 'GetStaticPaths', 'GetServerSideProps',
                'InferGetStaticPropsType', 'InferGetServerSidePropsType',
                'NextConfig', 'AppProps', 'AppContext', 'AppInitialProps',
                'DocumentContext', 'DocumentInitialProps', 'DocumentProps',
                'Html', 'Main', 'NextScript', 'Document', 'Error', 'ErrorProps',
                'AmpState', 'useAmp', 'isLocalURL', 'isDynamicRoute'
            }
        }
        
        # Built-in JavaScript object methods
        self.builtin_object_methods = {
            'Array': {
                # Mutating methods
                'push', 'pop', 'shift', 'unshift', 'splice', 'sort', 'reverse', 'fill', 'copyWithin',
                # Non-mutating methods
                'concat', 'slice', 'indexOf', 'lastIndexOf', 'includes', 'join', 'toString', 'toLocaleString',
                # Iteration methods
                'forEach', 'map', 'filter', 'reduce', 'reduceRight', 'find', 'findIndex', 'findLast', 'findLastIndex',
                'some', 'every', 'flat', 'flatMap',
                # ES6+ methods
                'from', 'isArray', 'of', 'entries', 'keys', 'values', 'at', 'toSorted', 'toReversed', 'toSpliced', 'with'
            },
            'String': {
                'charAt', 'charCodeAt', 'codePointAt', 'concat', 'includes', 'endsWith', 'indexOf', 'lastIndexOf',
                'localeCompare', 'match', 'matchAll', 'normalize', 'padEnd', 'padStart', 'repeat', 'replace',
                'replaceAll', 'search', 'slice', 'split', 'startsWith', 'substring', 'substr', 'toLowerCase',
                'toLocaleLowerCase', 'toUpperCase', 'toLocaleUpperCase', 'trim', 'trimStart', 'trimLeft',
                'trimEnd', 'trimRight', 'valueOf', 'toString', 'at', 'anchor', 'big', 'blink', 'bold',
                'fixed', 'fontcolor', 'fontsize', 'italics', 'link', 'small', 'strike', 'sub', 'sup'
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
            },
            'Event': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'MouseEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath', 'initMouseEvent', 'getModifierState'
            },
            'KeyboardEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath', 'initKeyboardEvent', 'getModifierState'
            },
            'TouchEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'FocusEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'InputEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath', 'getTargetRanges'
            },
            'DragEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'WheelEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'ClipboardEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'PointerEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath', 'getCoalescedEvents', 'getPredictedEvents'
            },
            'SubmitEvent': {
                'preventDefault', 'stopPropagation', 'stopImmediatePropagation', 'initEvent',
                'composedPath'
            },
            'HTMLElement': {
                'click', 'focus', 'blur', 'scroll', 'scrollTo', 'scrollBy', 'scrollIntoView',
                'contains', 'cloneNode', 'appendChild', 'removeChild', 'insertBefore',
                'replaceChild', 'remove', 'before', 'after', 'replaceWith', 'prepend',
                'append', 'querySelector', 'querySelectorAll', 'closest', 'matches',
                'webkitMatchesSelector', 'getAttribute', 'setAttribute', 'removeAttribute',
                'hasAttribute', 'toggleAttribute', 'getAttributeNames', 'getAttributeNode',
                'setAttributeNode', 'removeAttributeNode', 'getElementsByClassName',
                'getElementsByTagName', 'getElementsByTagNameNS', 'insertAdjacentElement',
                'insertAdjacentHTML', 'insertAdjacentText', 'attachShadow', 'requestFullscreen',
                'requestPointerLock', 'setPointerCapture', 'releasePointerCapture',
                'hasPointerCapture', 'animate', 'getAnimations', 'computedStyleMap',
                'addEventListener', 'removeEventListener', 'dispatchEvent', 'getBoundingClientRect',
                'getClientRects', 'checkVisibility'
            },
            'HTMLInputElement': {
                'click', 'focus', 'blur', 'select', 'setSelectionRange', 'setRangeText',
                'checkValidity', 'reportValidity', 'setCustomValidity', 'stepUp', 'stepDown',
                'showPicker'
            },
            'HTMLFormElement': {
                'submit', 'reset', 'checkValidity', 'reportValidity', 'requestSubmit'
            },
            'HTMLSelectElement': {
                'add', 'remove', 'checkValidity', 'reportValidity', 'setCustomValidity'
            },
            'HTMLTextAreaElement': {
                'select', 'setSelectionRange', 'setRangeText', 'checkValidity', 'reportValidity',
                'setCustomValidity'
            },
            'Element': {
                'animate', 'attachShadow', 'closest', 'computedStyleMap', 'getAttribute',
                'getAttributeNS', 'getAttributeNames', 'getAttributeNode', 'getAttributeNodeNS',
                'getBoundingClientRect', 'getClientRects', 'getElementsByClassName',
                'getElementsByTagName', 'getElementsByTagNameNS', 'hasAttribute', 'hasAttributeNS',
                'hasAttributes', 'hasPointerCapture', 'insertAdjacentElement', 'insertAdjacentHTML',
                'insertAdjacentText', 'matches', 'querySelector', 'querySelectorAll',
                'releasePointerCapture', 'remove', 'removeAttribute', 'removeAttributeNS',
                'removeAttributeNode', 'requestFullscreen', 'requestPointerLock', 'scroll',
                'scrollBy', 'scrollIntoView', 'scrollTo', 'setAttribute', 'setAttributeNS',
                'setAttributeNode', 'setAttributeNodeNS', 'setPointerCapture', 'toggleAttribute',
                'webkitMatchesSelector', 'addEventListener', 'removeEventListener', 'dispatchEvent'
            }
        }
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        logger.info("TypeScript validator initialized with Neo4j")
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    def _extract_local_context(self, analysis_result: Dict[str, Any]):
        """Extract locally defined components, types, functions, etc. from the analysis result"""
        # Clear previous context
        self.local_components.clear()
        self.local_functions.clear()
        self.local_types.clear()
        self.local_interfaces.clear()
        self.local_classes.clear()
        self.external_imports.clear()
        self.hook_returns.clear()
        self.variable_types.clear()
        
        # Track function parameters from components and functions
        self.function_parameters: Set[str] = set()
        
        # Extract local components and their props
        for component in analysis_result.get('components', []):
            self.local_components.add(component['name'])
            # Extract function props from component props type
            props_type = component.get('props')
            if props_type:
                # Parse common prop patterns like onSubmit, onClick, onChange, etc.
                # This is a heuristic approach - could be enhanced with proper type parsing
                import re
                # Match function props like: onSubmit: (data: any) => void
                func_prop_pattern = r'(on[A-Z]\w*|handle[A-Z]\w*|callback|onClick|onSubmit|onChange|onComplete)\s*[?:]'
                matches = re.findall(func_prop_pattern, props_type, re.IGNORECASE)
                for match in matches:
                    self.function_parameters.add(match)
        
        # Extract local functions and their parameters
        for func in analysis_result.get('functions', []):
            self.local_functions.add(func['name'])
            # Track ALL function parameters
            for param in func.get('parameters', []):
                param_name = param.get('name', '')
                param_type = param.get('type', '')
                if param_name:
                    # Always track function parameters
                    # This helps avoid false positives when parameters are called as functions
                    self.function_parameters.add(param_name)
        
        # Extract local types
        for type_def in analysis_result.get('types', []):
            self.local_types.add(type_def['name'])
        
        # Extract local interfaces and their function properties
        for interface in analysis_result.get('interfaces', []):
            self.local_interfaces.add(interface['name'])
            # Check for function properties in interfaces
            for prop in interface.get('properties', []):
                prop_name = prop.get('name', '')
                prop_type = prop.get('type', '')
                # Check if it's a function type
                if prop_type and ('=>' in prop_type or 'Function' in prop_type):
                    self.function_parameters.add(prop_name)
        
        # Extract local classes and their method parameters
        for cls in analysis_result.get('classes', []):
            self.local_classes.add(cls['name'])
            # Track parameters from class methods
            for member in cls.get('members', []):
                if member.get('type') == 'method':
                    # Track method parameters
                    for param in member.get('parameters', []):
                        param_name = param.get('name', '')
                        if param_name:
                            # Track all method parameters
                            self.function_parameters.add(param_name)
        
        # Extract hook returns (functions/values from hooks)
        # This is a simple heuristic - could be enhanced with proper AST analysis
        for hook_use in analysis_result.get('hook_uses', []):
            hook_name = hook_use['name']
            # Track common patterns for hook returns
            if hook_name == 'useTranslation':
                self.hook_returns['t'] = hook_name
                self.hook_returns['i18n'] = hook_name
            elif hook_name == 'useNavigate':
                self.hook_returns['navigate'] = hook_name
            elif hook_name == 'useParams':
                # useParams returns an object, we can't know all properties
                pass
            elif hook_name == 'useState':
                # useState returns [value, setter] - hard to track without AST
                pass
            elif hook_name == 'useForm':
                # useForm returns common form methods
                self.hook_returns['register'] = hook_name
                self.hook_returns['handleSubmit'] = hook_name
                self.hook_returns['watch'] = hook_name
                self.hook_returns['reset'] = hook_name
                self.hook_returns['setValue'] = hook_name
                self.hook_returns['getValues'] = hook_name
                self.hook_returns['trigger'] = hook_name
                self.hook_returns['clearErrors'] = hook_name
                self.hook_returns['setError'] = hook_name
                self.hook_returns['unregister'] = hook_name
            elif hook_name == 'useRouter':
                self.hook_returns['push'] = hook_name
                self.hook_returns['replace'] = hook_name
                self.hook_returns['prefetch'] = hook_name
                self.hook_returns['back'] = hook_name
                self.hook_returns['reload'] = hook_name
            elif hook_name in self.external_imports:
                # Custom hook from external library
                pass
        
        # Extract variables and their types
        for var in analysis_result.get('variables', []):
            var_name = var['name']
            var_type = var.get('type')
            inferred_type = var.get('inferredType')
            initializer = var.get('initializer')
            
            self.variable_types[var_name] = {
                'type': var_type,
                'inferredType': inferred_type,
                'initializer': initializer,
                'line': var.get('line', 0)
            }
        
        logger.info(f"Extracted local context: {len(self.local_components)} components, "
                   f"{len(self.local_functions)} functions, {len(self.local_types)} types, "
                   f"{len(self.local_interfaces)} interfaces, {len(self.local_classes)} classes, "
                   f"{len(self.variable_types)} variables")
    
    async def validate_script(self, script_path: str) -> TypeScriptValidationResult:
        """Validate a TypeScript/React script against knowledge graph"""
        logger.info(f"Validating TypeScript script: {script_path}")
        
        # Store script path for import resolution
        self.script_path = script_path
        
        # Get project-specific config if available
        project_root = self._find_project_root(Path(script_path))
        if project_root:
            project_config = get_project_config(project_root)
            # TODO: Implement config merge
            # self.config.merge(project_config)
            
        # Initialize module resolver
        self.module_resolver = ModuleResolver(
            project_root or Path(script_path).parent,
            config={'require_file_exists': False}
        )
        
        # Analyze the script
        analysis_result = await self.analyzer.analyze_script(script_path)
        
        # Extract local context from the analysis
        self._extract_local_context(analysis_result)
        
        # Store parse result for class method validation
        self.parse_result = analysis_result
        
        # Create result object
        result = TypeScriptValidationResult(
            script_path=script_path,
            analysis_result=analysis_result
        )
        
        # Validate each type of element
        await self._validate_imports(analysis_result['imports'], result)
        await self._validate_components(analysis_result['component_uses'], result)
        await self._validate_hooks(analysis_result['hook_uses'], result)
        await self._validate_types(analysis_result['type_uses'], result)
        await self._validate_functions(analysis_result['function_calls'], result)
        await self._validate_classes(analysis_result['class_instantiations'], result)
        await self._validate_method_calls(analysis_result['method_calls'], result)
        
        # Add new validations
        await self._validate_jsx_elements(analysis_result.get('jsx_elements', []), result)
        await self._validate_component_props(analysis_result.get('component_uses', []), result)
        await self._validate_type_usage(analysis_result.get('type_annotations', []), result)
        
        # Calculate overall confidence
        result.overall_confidence = self._calculate_overall_confidence(result)
        
        # Identify hallucinations
        self._identify_hallucinations(result)
        
        return result
    
    async def _validate_imports(self, imports: Dict[str, List[Dict]], result: TypeScriptValidationResult):
        """Validate import statements"""
        # First pass: track all imports for later validation
        for module, items in imports.items():
            # Handle both string lists and dictionary lists
            if items and isinstance(items[0], str):
                imported_names = items
            else:
                imported_names = [item.get('name', item.get('default', '')) for item in items]
            
            # Track all imports (external and internal) for component/function validation
            for i, name in enumerate(imported_names):
                if name and name.startswith('* as '):
                    # Handle namespace import format "* as alias"
                    alias = name.replace('* as ', '').strip()
                    if alias:
                        if self.config.is_external_library(module) or self.config.is_trusted_external_pattern(module):
                            self.external_imports[alias] = module
                            # Track namespace imports for method validation
                            self.namespace_imports[alias] = module
                        else:
                            # For internal namespace imports, still track them
                            self.external_imports[alias] = f"internal:{module}"
                            self.namespace_imports[alias] = module
                elif name and name != '*':
                    # Check if it's an external library or internal module
                    if self.config.is_external_library(module) or self.config.is_trusted_external_pattern(module):
                        self.external_imports[name] = module
                    else:
                        # For internal imports, we still track them to avoid false positives
                        # when components/functions are used but not in knowledge graph
                        self.external_imports[name] = f"internal:{module}"
                elif name == '*' and items:
                    # Handle namespace imports like "import * as z from 'zod'"
                    # Get the alias name
                    item = items[i] if isinstance(items[i], dict) else {'local': items[i]}
                    alias = item.get('local', item.get('name', ''))
                    if alias:
                        if self.config.is_external_library(module) or self.config.is_trusted_external_pattern(module):
                            self.external_imports[alias] = module
                            # Track namespace imports for method validation
                            self.namespace_imports[alias] = module
                        else:
                            # For internal namespace imports, still track them
                            self.external_imports[alias] = f"internal:{module}"
                            self.namespace_imports[alias] = module
        
        # Second pass: validate imports
        for module, items in imports.items():
            # Check if it's a UI library import pattern first
            if self.config.is_ui_library_import(module):
                # Check if all imported items are common UI components
                # Handle both string lists and dictionary lists
                if items and isinstance(items[0], str):
                    imported_names = items
                else:
                    imported_names = [item.get('name', item.get('default', '')) for item in items]
                all_ui_components = all(
                    self.config.is_common_ui_component(name) 
                    for name in imported_names if name
                )
                
                if all_ui_components:
                    validation = ImportValidation(
                        module=module,
                        imported_items=items,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"UI library import '{module}' with common components - assuming valid"
                        )
                    )
                else:
                    validation = ImportValidation(
                        module=module,
                        imported_items=items,
                        validation=ValidationResult(
                            status=ValidationStatus.UNCERTAIN,
                            confidence=0.7,
                            message=f"UI library import '{module}' - components may be custom"
                        )
                    )
                result.import_validations.append(validation)
                continue
            
            # Skip external libraries
            if self.config.is_external_library(module):
                # Check if it's a known library or unknown
                is_known = self._is_known_library(module)
                
                if is_known or self.config.trust_external_libraries:
                    validation = ImportValidation(
                        module=module,
                        imported_items=items,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=1.0 if is_known else 0.8,
                            message=f"{'Known' if is_known else 'Unknown'} external library '{module}' - skipping validation"
                        )
                    )
                else:
                    validation = ImportValidation(
                        module=module,
                        imported_items=items,
                        validation=ValidationResult(
                            status=ValidationStatus.UNCERTAIN,
                            confidence=0.5,
                            message=f"Unknown external library '{module}' - existence not verified"
                        )
                    )
                result.import_validations.append(validation)
                continue
            
            # Use module resolver to normalize the import path
            resolved = self.module_resolver.resolve(module, Path(self.script_path))
            
            if resolved and resolved.is_external:
                # External module, skip validation
                validation = ImportValidation(
                    module=module,
                    imported_items=items,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=self.config.get_confidence('external_library', True, None),
                        message=f"External module '{module}' - skipping validation"
                    )
                )
                result.import_validations.append(validation)
                continue
            
            # Check if module exists in knowledge graph
            async with self.driver.session() as session:
                normalized_module = resolved.module_path if resolved else module
                
                # Try to find the module/file with improved matching
                module_result = await session.run("""
                    MATCH (f:File)
                    WHERE f.module = $module OR 
                          f.module = $normalized_module OR 
                          f.module STARTS WITH $normalized_module + '.'
                    RETURN f.path as path, f.module as module
                    ORDER BY 
                        CASE WHEN f.module = $normalized_module THEN 0
                             WHEN f.name STARTS WITH 'index.' THEN 1
                             ELSE 2 END
                    LIMIT 1
                """, module=module, normalized_module=normalized_module)
                
                module_record = await module_result.single()
                
                if not module_record:
                    # Check if this is a relative import or internal project import
                    is_relative = module.startswith('.') or module.startswith('../')
                    is_internal_alias = module.startswith('@/') or module.startswith('~/')
                    is_likely_internal = is_relative or is_internal_alias or (resolved and not resolved.is_external)
                    
                    if is_likely_internal and self.config.allow_missing_internal_modules:
                        # For internal imports not in the knowledge graph, be more lenient
                        validation = ImportValidation(
                            module=module,
                            imported_items=items,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.7,
                                message=f"Internal module '{module}' not found in knowledge graph - may not be parsed yet",
                                details={'is_relative': is_relative, 'is_internal_alias': is_internal_alias}
                            )
                        )
                    else:
                        # For truly missing modules, mark as not found
                        validation = ImportValidation(
                            module=module,
                            imported_items=items,
                            validation=ValidationResult(
                                status=ValidationStatus.NOT_FOUND,
                                confidence=0.0,
                                message=f"Module '{module}' not found in knowledge graph"
                            )
                        )
                else:
                    # Get available exports from the module - check both DEFINES and EXPORTS relationships
                    exports_result = await session.run("""
                        MATCH (f:File {module: $module})
                        OPTIONAL MATCH (f)-[:DEFINES]->(defined_item)
                        WHERE defined_item:Component OR defined_item:JSFunction OR defined_item:JSClass OR defined_item:Interface OR defined_item:Type
                        OPTIONAL MATCH (f)-[:EXPORTS]->(exported_item)
                        WHERE exported_item:Component OR exported_item:JSFunction OR exported_item:JSClass OR exported_item:Interface OR exported_item:Type
                        WITH COLLECT(DISTINCT defined_item) + COLLECT(DISTINCT exported_item) AS items
                        UNWIND items AS item
                        WITH item
                        WHERE item IS NOT NULL
                        RETURN DISTINCT item.name as name, labels(item)[0] as type
                    """, module=module_record['module'] or normalized_module)
                    
                    available_exports = []
                    async for record in exports_result:
                        available_exports.append(record['name'])
                    
                    # Validate each imported item
                    all_valid = True
                    invalid_items = []
                    
                    for item in items:
                        # Handle both string and dict formats
                        if isinstance(item, str):
                            item_name = item
                        else:
                            item_name = item.get('name', item.get('local', ''))
                        
                        # Skip namespace imports
                        if item_name.startswith('* as'):
                            continue
                            
                        if item_name != '*' and item_name not in available_exports:
                            all_valid = False
                            invalid_items.append(item_name)
                    
                    if all_valid:
                        validation = ImportValidation(
                            module=module,
                            imported_items=items,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=f"All imports from '{module}' are valid"
                            ),
                            available_exports=available_exports
                        )
                    else:
                        # Check if this is an internal module
                        is_relative = module.startswith('.') or module.startswith('../')
                        is_internal_alias = module.startswith('@/') or module.startswith('~/')
                        is_likely_internal = is_relative or is_internal_alias or (resolved and not resolved.is_external)
                        
                        if is_likely_internal and not self.config.strict_internal_imports:
                            # Internal module - be lenient about missing exports
                            if not available_exports:
                                # No exports detected - might be incomplete parsing
                                validation = ImportValidation(
                                    module=module,
                                    imported_items=items,
                                    validation=ValidationResult(
                                        status=ValidationStatus.UNCERTAIN,
                                        confidence=0.6,
                                        message=f"Imports from internal module '{module}' could not be verified - exports may not be fully parsed",
                                        details={'unverified_items': invalid_items}
                                    ),
                                    available_exports=available_exports
                                )
                            else:
                                # Some exports found but not the ones we're looking for
                                validation = ImportValidation(
                                    module=module,
                                    imported_items=items,
                                    validation=ValidationResult(
                                        status=ValidationStatus.UNCERTAIN,
                                        confidence=0.5,
                                        message=f"Some imports from internal module '{module}' could not be verified: {invalid_items}",
                                        details={'unverified_items': invalid_items},
                                        suggestions=[f"Found exports: {', '.join(available_exports[:5])}{'...' if len(available_exports) > 5 else ''}"]
                                    ),
                                    available_exports=available_exports
                                )
                        else:
                            # Module has exports but requested items not found
                            validation = ImportValidation(
                                module=module,
                                imported_items=items,
                                validation=ValidationResult(
                                    status=ValidationStatus.INVALID,
                                    confidence=0.3,
                                    message=f"Invalid imports from '{module}': {invalid_items}",
                                    suggestions=[f"Available exports: {', '.join(available_exports)}"]
                                ),
                                available_exports=available_exports
                            )
                
                result.import_validations.append(validation)
    
    async def _validate_components(self, component_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate React component usage"""
        for comp_use in component_uses:
            comp_name = comp_use['name']
            props_used = comp_use.get('props', [])
            
            # Skip HTML elements
            if self.config.is_html_element(comp_name):
                validation = ComponentValidation(
                    component_name=comp_name,
                    props_used=props_used,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"HTML element '{comp_name}' - no validation needed"
                    )
                )
                result.component_validations.append(validation)
                continue
            
            # Check if it's a locally defined component
            if comp_name in self.local_components:
                validation = ComponentValidation(
                    component_name=comp_name,
                    props_used=props_used,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Component '{comp_name}' is defined locally in the same file"
                    )
                )
                result.component_validations.append(validation)
                continue
            
            # Check if it's a common UI component
            if self.config.is_common_ui_component(comp_name):
                validation = ComponentValidation(
                    component_name=comp_name,
                    props_used=props_used,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=0.9,
                        message=f"Common UI component '{comp_name}' - assuming valid"
                    )
                )
                result.component_validations.append(validation)
                continue
            
            # Check if it's imported from any module (external or internal)
            if comp_name in self.external_imports:
                source = self.external_imports[comp_name]
                is_internal = source.startswith('internal:')
                
                validation = ComponentValidation(
                    component_name=comp_name,
                    props_used=props_used,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0 if not is_internal else 0.9,
                        message=f"Component '{comp_name}' imported from {'internal module' if is_internal else 'external library'} '{source.replace('internal:', '')}'"
                    )
                )
                result.component_validations.append(validation)
                continue
            
            async with self.driver.session() as session:
                # Find the component in knowledge graph
                comp_result = await session.run("""
                    MATCH (c:Component {name: $name})
                    RETURN c.full_name as full_name, c.type as type, 
                           c.isForwardRef as isForwardRef, c.isMemo as isMemo
                    LIMIT 1
                """, name=comp_name)
                
                comp_record = await comp_result.single()
                
                if not comp_record:
                    # Check if the component name looks like a UI component
                    is_likely_ui_component = (
                        comp_name[0].isupper() and  # Starts with uppercase
                        any(pattern in comp_name.lower() for pattern in [
                            'button', 'input', 'select', 'modal', 'dialog', 'card',
                            'list', 'menu', 'nav', 'header', 'footer', 'panel',
                            'tab', 'form', 'field', 'container', 'layout', 'grid'
                        ])
                    )
                    
                    if is_likely_ui_component:
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.6,
                                message=f"Component '{comp_name}' not found but appears to be a UI component",
                                suggestions=["This might be a custom UI component not yet in the knowledge graph"]
                            )
                        )
                    else:
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.NOT_FOUND,
                                confidence=0.0,
                                message=f"Component '{comp_name}' not found in knowledge graph"
                            )
                        )
                else:
                    # Get component props if available
                    props_result = await session.run("""
                        MATCH (c:Component {full_name: $full_name})-[:HAS_PROPS]->(p)
                        RETURN p.properties as properties
                    """, full_name=comp_record['full_name'])
                    
                    props_record = await props_result.single()
                    expected_props = props_record['properties'] if props_record else []
                    
                    # Handle ref prop for forwardRef components
                    is_forward_ref = comp_record.get('isForwardRef', False)
                    has_ref_prop = 'ref' in props_used
                    
                    # If component accepts ref, add it to expected props
                    if is_forward_ref and 'ref' not in expected_props:
                        expected_props = expected_props + ['ref']
                    
                    # Validate props usage
                    unknown_props = [p for p in props_used if p not in expected_props]
                    
                    # Special validation for ref prop on non-forwardRef components
                    if has_ref_prop and not is_forward_ref:
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.9,
                                message=f"Component '{comp_name}' does not support ref prop (not a forwardRef component)",
                                suggestions=["Use React.forwardRef() to enable ref forwarding"]
                            ),
                            expected_props=expected_props,
                            unknown_props=['ref']
                        )
                    elif not unknown_props or not expected_props:  # No props info or all props valid
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.9 if expected_props else 0.7,
                                message=f"Component '{comp_name}' usage is valid"
                            ),
                            expected_props=expected_props
                        )
                    else:
                        validation = ComponentValidation(
                            component_name=comp_name,
                            props_used=props_used,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.5,
                                message=f"Unknown props used in '{comp_name}': {unknown_props}",
                                suggestions=[f"Expected props: {', '.join(expected_props)}"]
                            ),
                            expected_props=expected_props,
                            unknown_props=unknown_props
                        )
                
                result.component_validations.append(validation)
    
    async def _validate_hooks(self, hook_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate React hook usage"""
        for hook_use in hook_uses:
            hook_name = hook_use['name']
            
            # Check if it's a known React hook
            if hook_name in self.hooks_with_rules:
                validation = HookValidation(
                    hook_name=hook_name,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"React hook '{hook_name}' is valid",
                        details={'rules': self.hooks_with_rules[hook_name]}
                    )
                )
            else:
                # Check if it's a custom hook in the knowledge graph
                async with self.driver.session() as session:
                    hook_result = await session.run("""
                        MATCH (h:Hook {name: $name})
                        RETURN h.custom as custom
                        LIMIT 1
                    """, name=hook_name)
                    
                    hook_record = await hook_result.single()
                    
                    if hook_record:
                        validation = HookValidation(
                            hook_name=hook_name,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.9,
                                message=f"Custom hook '{hook_name}' found in knowledge graph"
                            )
                        )
                    else:
                        validation = HookValidation(
                            hook_name=hook_name,
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.6,
                                message=f"Unknown hook '{hook_name}' - might be a valid custom hook"
                            )
                        )
            
            result.hook_validations.append(validation)
    
    async def _validate_types(self, type_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate TypeScript type usage"""
        for type_use in type_uses:
            type_name = type_use['name']
            kind = type_use['kind']
            
            # Skip React built-in types
            if self.config.is_react_type(type_name):
                validation = TypeValidation(
                    type_name=type_name,
                    kind=kind,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"React built-in type '{type_name}' - no validation needed"
                    )
                )
                result.type_validations.append(validation)
                continue
            
            # Check if it's a locally defined type or interface
            if type_name in self.local_types or type_name in self.local_interfaces:
                validation = TypeValidation(
                    type_name=type_name,
                    kind=kind,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"{kind.capitalize()} '{type_name}' is defined locally in the same file"
                    )
                )
                result.type_validations.append(validation)
                continue
            
            async with self.driver.session() as session:
                # Check for interface or type in knowledge graph
                type_result = await session.run("""
                    MATCH (t)
                    WHERE (t:Interface OR t:Type) AND t.name = $name
                    RETURN t.name as name, labels(t)[0] as type, 
                           t.properties as properties
                    LIMIT 1
                """, name=type_name)
                
                type_record = await type_result.single()
                
                if type_record:
                    validation = TypeValidation(
                        type_name=type_name,
                        kind=kind,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=1.0,
                            message=f"{type_record['type']} '{type_name}' is valid"
                        ),
                        expected_properties=type_record.get('properties', [])
                    )
                else:
                    # Check if it's a built-in type or TypeScript utility type
                    builtin_types = {
                        'string', 'number', 'boolean', 'any', 'void', 'never', 'unknown',
                        'null', 'undefined', 'object', 'symbol', 'bigint',
                        # TypeScript utility types
                        'Partial', 'Required', 'Readonly', 'Record', 'Pick', 'Omit',
                        'Exclude', 'Extract', 'NonNullable', 'Parameters', 'ConstructorParameters',
                        'ReturnType', 'InstanceType', 'ThisType', 'ThisParameterType',
                        'OmitThisParameter', 'Uppercase', 'Lowercase', 'Capitalize', 'Uncapitalize',
                        'Promise', 'Awaited', 'Array', 'ReadonlyArray', 'Tuple',
                        # Other common global types
                        'Error', 'Date', 'RegExp', 'Function', 'Map', 'Set', 'WeakMap', 'WeakSet',
                        'ArrayBuffer', 'DataView', 'Int8Array', 'Uint8Array', 'Int16Array',
                        'Uint16Array', 'Int32Array', 'Uint32Array', 'Float32Array', 'Float64Array',
                        'BigInt64Array', 'BigUint64Array'
                    }
                    
                    if type_name in builtin_types:
                        validation = TypeValidation(
                            type_name=type_name,
                            kind=kind,
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=f"Built-in type '{type_name}' is valid"
                            )
                        )
                    else:
                        validation = TypeValidation(
                            type_name=type_name,
                            kind=kind,
                            validation=ValidationResult(
                                status=ValidationStatus.NOT_FOUND,
                                confidence=0.0,
                                message=f"Type '{type_name}' not found in knowledge graph"
                            )
                        )
                
                result.type_validations.append(validation)
    
    async def _validate_functions(self, function_calls: List[Dict], result: TypeScriptValidationResult):
        """Validate function calls"""
        for func_call in function_calls:
            func_name = func_call['name']
            module = func_call.get('module')
            args_count = func_call.get('args_count', 0)
            
            # Skip if function name is Unknown (parser couldn't determine it)
            if func_name == 'Unknown' or not func_name:
                continue
            
            # Skip if it's from an external library
            if module and self._is_external_library(module):
                continue
            
            # Check if it's a locally defined function
            if func_name in self.local_functions:
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Function '{func_name}' is defined locally in the same file"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's returned from a hook
            if func_name in self.hook_returns:
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Function '{func_name}' returned from hook '{self.hook_returns[func_name]}'"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's imported from an external library
            if func_name in self.external_imports:
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Function '{func_name}' imported from external library '{self.external_imports[func_name]}'"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's a built-in global function
            if func_name in self.builtin_global_functions:
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Built-in global function '{func_name}' is valid"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Skip React hooks
            if self.config.is_react_hook(func_name):
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"React hook '{func_name}' - no validation needed"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's a function parameter (e.g., onSubmit, callback, handleClick)
            if func_name in self.function_parameters:
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=0.95,
                        message=f"Function '{func_name}' is a function parameter (likely passed as prop or callback)"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's a React state setter (starts with 'set' and follows camelCase)
            if func_name.startswith('set') and len(func_name) > 3 and func_name[3].isupper():
                # This is likely a state setter from useState
                validation = FunctionValidation(
                    function_name=func_name,
                    module=module,
                    args_count=args_count,
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=0.9,
                        message=f"React state setter '{func_name}' - likely from useState hook"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            async with self.driver.session() as session:
                # Find the function in knowledge graph
                func_result = await session.run("""
                    MATCH (f:JSFunction {name: $name})
                    RETURN f.full_name as full_name, f.params as params
                    LIMIT 1
                """, name=func_name)
                
                func_record = await func_result.single()
                
                if func_record:
                    expected_params = func_record.get('params', [])
                    validation = FunctionValidation(
                        function_name=func_name,
                        module=module,
                        args_count=args_count,
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"Function '{func_name}' is valid"
                        ),
                        expected_params=expected_params
                    )
                else:
                    validation = FunctionValidation(
                        function_name=func_name,
                        module=module,
                        args_count=args_count,
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Function '{func_name}' not found in knowledge graph"
                        )
                    )
                
                result.function_validations.append(validation)
    
    async def _validate_classes(self, class_uses: List[Dict], result: TypeScriptValidationResult):
        """Validate class instantiations"""
        for class_use in class_uses:
            class_name = class_use['name']
            module = class_use.get('module')
            
            # Skip if class name is Unknown (parser couldn't determine it)
            if class_name == 'Unknown' or not class_name:
                continue
            
            # Skip if it's from an external library
            if module and self.config.is_external_library(module):
                continue
            
            # Check if it's a built-in constructor
            if class_name in self.builtin_constructors:
                validation = FunctionValidation(
                    function_name=class_name,
                    module=module,
                    args_count=class_use.get('args_count', 0),
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Built-in constructor '{class_name}' is valid"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            # Check if it's a locally defined class
            if class_name in self.local_classes:
                validation = FunctionValidation(
                    function_name=class_name,
                    module=module,
                    args_count=class_use.get('args_count', 0),
                    validation=ValidationResult(
                        status=ValidationStatus.VALID,
                        confidence=1.0,
                        message=f"Class '{class_name}' is defined locally in the same file"
                    )
                )
                result.function_validations.append(validation)
                continue
            
            async with self.driver.session() as session:
                # Find the class in knowledge graph
                class_result = await session.run("""
                    MATCH (c:JSClass {name: $name})
                    RETURN c.full_name as full_name
                    LIMIT 1
                """, name=class_name)
                
                class_record = await class_result.single()
                
                if class_record:
                    validation = FunctionValidation(
                        function_name=class_name,
                        module=module,
                        args_count=class_use.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"Class '{class_name}' is valid"
                        )
                    )
                else:
                    validation = FunctionValidation(
                        function_name=class_name,
                        module=module,
                        args_count=class_use.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Class '{class_name}' not found in knowledge graph"
                        )
                    )
                
                result.function_validations.append(validation)
    
    async def _validate_method_calls(self, method_calls: List[Dict], result: TypeScriptValidationResult):
        """Validate method calls on objects - enhanced with type checking"""
        for method_call in method_calls:
            object_name = method_call.get('object', '')
            method_name = method_call.get('method', '')
            line = method_call.get('line', 0)
            object_type = method_call.get('object_type', '')  # Type hint if available
            
            # Check if object is a tracked variable with known type
            if object_name in self.variable_types:
                var_info = self.variable_types[object_name]
                var_type = var_info.get('type')
                inferred_type = var_info.get('inferredType')
                initializer = var_info.get('initializer')
                
                # Handle Zod schema variables
                if inferred_type and 'Zod' in inferred_type:
                    # Zod methods are chainable
                    if 'zod' in self.namespace_methods:
                        known_methods = self.namespace_methods['zod']
                        if method_name in known_methods:
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.VALID,
                                    confidence=1.0,
                                    message=f"Valid Zod method '{method_name}' on variable '{object_name}' (inferred as {inferred_type})"
                                )
                            )
                            result.function_validations.append(validation)
                            continue
                
                # Handle variables initialized with method calls
                if initializer and initializer.get('type') == 'methodCall':
                    init_object = initializer.get('object')
                    init_method = initializer.get('method')
                    
                    # If initialized with z.string(), z.object(), etc., it's a Zod schema
                    if init_object == 'z' and 'zod' in self.namespace_methods:
                        known_methods = self.namespace_methods['zod']
                        if method_name in known_methods:
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.VALID,
                                    confidence=1.0,
                                    message=f"Valid Zod method '{method_name}' on variable '{object_name}' (initialized with {init_object}.{init_method}())"
                                )
                            )
                            result.function_validations.append(validation)
                            continue
                        else:
                            # Invalid method on Zod schema
                            similar_methods = self._find_similar_methods(method_name, known_methods)
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.INVALID,
                                    confidence=0.1,
                                    message=f"Method '{method_name}' does not exist on Zod schema variable '{object_name}'",
                                    suggestions=[f"Did you mean: {', '.join(similar_methods[:3])}?"] if similar_methods else ["Check Zod documentation for available methods"]
                                )
                            )
                            result.function_validations.append(validation)
                            result.hallucinations_detected.append({
                                'type': 'method',
                                'element': f'{object_name}.{method_name}',
                                'message': f"Invalid Zod method '{method_name}' on variable '{object_name}'",
                                'confidence': 0.9,
                                'line': line
                            })
                            continue
                
                # Handle variables initialized with new expressions
                if initializer and initializer.get('type') == 'newExpression':
                    class_name = initializer.get('className')
                    
                    # Check if it's a local class
                    if class_name in self.local_classes:
                        # Check methods in the local class
                        for class_info in self.parse_result.get('classes', []) if self.parse_result else []:
                            if class_info.get('name') == class_name:
                                for member in class_info.get('members', []):
                                    if member.get('type') == 'method' and member.get('name') == method_name:
                                        validation = FunctionValidation(
                                            function_name=f"{object_name}.{method_name}",
                                            module=None,
                                            args_count=method_call.get('args_count', 0),
                                            validation=ValidationResult(
                                                status=ValidationStatus.VALID,
                                                confidence=1.0,
                                                message=f"Method '{method_name}' exists on class '{class_name}' instance"
                                            )
                                        )
                                        result.function_validations.append(validation)
                                        continue
                
                # Handle typed variables (e.g., const schema: ZodString)
                if var_type:
                    # Map common type patterns to their methods
                    if 'Array' in var_type or '[]' in var_type:
                        if method_name in self.builtin_object_methods.get('Array', []):
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.VALID,
                                    confidence=1.0,
                                    message=f"Array method '{method_name}' on typed variable '{object_name}'"
                                )
                            )
                            result.function_validations.append(validation)
                            continue
                    elif 'string' in var_type.lower():
                        if method_name in self.builtin_object_methods.get('String', []):
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.VALID,
                                    confidence=1.0,
                                    message=f"String method '{method_name}' on typed variable '{object_name}'"
                                )
                            )
                            result.function_validations.append(validation)
                            continue
            
            # Handle 'this' method calls - check local class methods
            if object_name == 'this':
                # Check if the method exists in any local class
                method_found = False
                for class_info in self.parse_result.get('classes', []) if self.parse_result else []:
                    for member in class_info.get('members', []):
                        if member.get('type') == 'method' and member.get('name') == method_name:
                            method_found = True
                            break
                    if method_found:
                        break
                
                if method_found:
                    validation = FunctionValidation(
                        function_name=f"this.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=1.0,
                            message=f"Method '{method_name}' exists in local class definition"
                        )
                    )
                    result.function_validations.append(validation)
                    continue
                else:
                    # Method not found in local classes - might be inherited or dynamic
                    validation = FunctionValidation(
                        function_name=f"this.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.UNCERTAIN,
                            confidence=0.5,
                            message=f"Method '{method_name}' not found in local class - might be inherited or dynamic",
                            suggestions=["Check parent class definitions", "Verify method is defined in the class"]
                        )
                    )
                    result.function_validations.append(validation)
                    continue
            
            # Handle prototype method calls (e.g., Array.prototype.slice)
            if object_name.endswith('.prototype'):
                base_object = object_name.replace('.prototype', '')
                if base_object in self.builtin_object_methods:
                    valid_methods = self.builtin_object_methods[base_object]
                    if method_name in valid_methods:
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=f"Prototype method '{method_name}' on '{base_object}' is valid"
                            )
                        )
                    else:
                        similar_methods = self._find_similar_methods(method_name, valid_methods)
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.1,
                                message=f"Method '{method_name}' does not exist on {base_object}.prototype",
                                suggestions=[f"Did you mean: {', '.join(similar_methods)}?"] if similar_methods else [f"Available methods: {', '.join(sorted(valid_methods)[:10])}..."]
                            )
                        )
                        result.hallucinations_detected.append({
                            'type': 'method',
                            'element': f'{object_name}.{method_name}',
                            'message': f"Invalid prototype method '{method_name}' on '{base_object}'",
                            'confidence': 0.95,
                            'line': line
                        })
                    result.function_validations.append(validation)
                    continue
            
            # Check if the object is imported from an external library (for static methods)
            if object_name in self.external_imports:
                # Debug logging
                logger.debug(f"Object '{object_name}' found in external_imports: {self.external_imports.get(object_name)}")
                logger.debug(f"Namespace imports: {self.namespace_imports}")
                
                # Check if it's a namespace import with known methods
                if object_name in self.namespace_imports:
                    module_name = self.namespace_imports[object_name]
                    # Get the base module name for namespace methods lookup
                    # Handle both 'zod' and '@zod/core' style imports
                    base_module = module_name.split('/')[0].replace('@', '').replace('-', '_')
                    
                    # Direct module name check first (e.g., 'zod', 'lodash', etc.)
                    lookup_key = module_name if module_name in self.namespace_methods else base_module
                    
                    # Check if we have known methods for this namespace
                    if lookup_key in self.namespace_methods:
                        known_methods = self.namespace_methods[lookup_key]
                        if method_name in known_methods:
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.VALID,
                                    confidence=1.0,
                                    message=f"Known namespace method '{method_name}' on '{object_name}' from '{module_name}'"
                                )
                            )
                            result.function_validations.append(validation)
                            continue
                        else:
                            # Method not in known methods for this namespace
                            similar_methods = self._find_similar_methods(method_name, known_methods)
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.INVALID,
                                    confidence=0.2,
                                    message=f"Unknown method '{method_name}' on namespace '{object_name}' from '{module_name}'",
                                    suggestions=[f"Did you mean: {', '.join(similar_methods[:3])}?"] if similar_methods else [f"Available methods: {', '.join(sorted(known_methods)[:10])}..."]
                                )
                            )
                            result.function_validations.append(validation)
                            result.hallucinations_detected.append({
                                'type': 'method',
                                'element': f'{object_name}.{method_name}',
                                'message': f"Invalid namespace method '{method_name}' on '{object_name}'",
                                'confidence': 0.8,
                                'line': line
                            })
                            continue
                
                # Check if it's an internal service import
                import_source = self.external_imports[object_name]
                is_internal_service = import_source.startswith('internal:')
                
                if is_internal_service:
                    # It's an internal service, check service method patterns
                    if self.config.is_trusted_service_method(object_name, method_name):
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.95,
                                message=f"Service method '{method_name}' on '{object_name}' matches common service patterns"
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    else:
                        # Method doesn't match service patterns, be more lenient but flag as uncertain
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.UNCERTAIN,
                                confidence=0.7,
                                message=f"Method '{method_name}' on internal service '{object_name}' could not be verified",
                                suggestions=["Method may be valid but doesn't match common service patterns"]
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                else:
                    # Object is from external library, assume method is valid
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.95,
                            message=f"Method '{method_name}' on external object '{object_name}' from '{self.external_imports[object_name]}'"
                        )
                    )
                    result.function_validations.append(validation)
                    continue
            
            # Check if it's a built-in object with known methods
            if object_name in self.builtin_object_methods:
                valid_methods = self.builtin_object_methods[object_name]
                if method_name in valid_methods:
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=1.0,
                            message=f"Built-in method '{method_name}' on '{object_name}' is valid"
                        )
                    )
                else:
                    similar_methods = self._find_similar_methods(method_name, valid_methods)
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.INVALID,
                            confidence=0.1,
                            message=f"Method '{method_name}' does not exist on built-in object '{object_name}'",
                            suggestions=[f"Did you mean: {', '.join(similar_methods)}?"] if similar_methods else [f"Available methods: {', '.join(sorted(valid_methods)[:10])}..."]
                        )
                    )
                    result.hallucinations_detected.append({
                        'type': 'method',
                        'element': f'{object_name}.{method_name}',
                        'message': f"Invalid method '{method_name}' on built-in object '{object_name}'",
                        'confidence': 0.95,
                        'line': line
                    })
                result.function_validations.append(validation)
                continue
            
            # Check if it's a method chain (e.g., z.string().email())
            if self.method_chain_resolver.is_chainable_method_call(object_name):
                # Try to find the namespace for the chain
                namespace = None
                
                # Extract the base object from the chain (e.g., 'z' from 'z.string()')
                chain_parts = self.method_chain_resolver.parse_method_chain(object_name)
                if chain_parts and chain_parts[0][0] in self.namespace_imports:
                    base_obj = chain_parts[0][0]
                    module_name = self.namespace_imports[base_obj]
                    # Get the base module name for namespace methods lookup
                    base_module = module_name.split('/')[0].replace('@', '').replace('-', '_')
                    namespace = module_name if module_name in self.namespace_methods else base_module
                
                if namespace and namespace in self.namespace_methods:
                    # Validate the method chain
                    is_valid, message, suggestions = self.method_chain_resolver.validate_method_chain(
                        object_name, method_name, namespace
                    )
                    
                    if is_valid:
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=1.0,
                                message=message
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    else:
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.1,
                                message=message,
                                suggestions=suggestions
                            )
                        )
                        result.function_validations.append(validation)
                        result.hallucinations_detected.append({
                            'type': 'method',
                            'element': f'{object_name}.{method_name}',
                            'message': message,
                            'confidence': 0.95,
                            'line': line
                        })
                        continue
            
            # For array instance methods (e.g., myArray.filter())
            if object_type == 'Array' or (object_type and 'Array' in object_type) or (object_type and '[]' in object_type):
                if method_name in self.builtin_object_methods['Array']:
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.95,
                            message=f"Array method '{method_name}' is valid"
                        )
                    )
                    result.function_validations.append(validation)
                    continue
                else:
                    similar_methods = self._find_similar_methods(method_name, self.builtin_object_methods['Array'])
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.INVALID,
                            confidence=0.1,
                            message=f"Method '{method_name}' does not exist on Array type",
                            suggestions=[f"Did you mean: {', '.join(similar_methods)}?"] if similar_methods else ["Check Array methods documentation"]
                        )
                    )
                    result.function_validations.append(validation)
                    result.hallucinations_detected.append({
                        'type': 'method',
                        'element': f'{object_name}.{method_name}',
                        'message': f"Invalid Array method '{method_name}'",
                        'confidence': 0.95,
                        'line': line
                    })
                    continue
            
            # For string instance methods
            if object_type == 'string' or object_type == 'String':
                if method_name in self.builtin_object_methods['String']:
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.95,
                            message=f"String method '{method_name}' is valid"
                        )
                    )
                    result.function_validations.append(validation)
                    continue
                else:
                    similar_methods = self._find_similar_methods(method_name, self.builtin_object_methods['String'])
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.INVALID,
                            confidence=0.1,
                            message=f"Method '{method_name}' does not exist on String type",
                            suggestions=[f"Did you mean: {', '.join(similar_methods)}?"] if similar_methods else ["Check String methods documentation"]
                        )
                    )
                    result.function_validations.append(validation)
                    result.hallucinations_detected.append({
                        'type': 'method',
                        'element': f'{object_name}.{method_name}',
                        'message': f"Invalid String method '{method_name}'",
                        'confidence': 0.95,
                        'line': line
                    })
                    continue
                
            async with self.driver.session() as session:
                # First check if we have type information for the object
                if object_type and object_type not in ['any', 'unknown']:
                    # Check if the method exists on the type/interface
                    typed_method_result = await session.run("""
                        MATCH (t {name: $type_name})
                        WHERE t:Interface OR t:Type OR t:JSClass
                        OPTIONAL MATCH (t)-[:HAS_METHOD]->(m:Method {name: $method_name})
                        OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:Property {name: $method_name})
                        WHERE p.type CONTAINS 'function' OR p.type CONTAINS '=>'
                        RETURN m.name as method_name, p.name as property_name,
                               t.name as type_name, labels(t)[0] as type_kind
                    """, type_name=object_type, method_name=method_name)
                    
                    typed_record = await typed_method_result.single()
                    
                    if typed_record and (typed_record['method_name'] or typed_record['property_name']):
                        # Method exists on the type - valid
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.95,
                                message=f"Method '{method_name}' exists on type '{object_type}'"
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    elif typed_record:
                        # Type exists but method doesn't
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.1,
                                message=f"Method '{method_name}' does not exist on type '{object_type}'",
                                details={'object_type': object_type, 'type_kind': typed_record['type_kind']}
                            )
                        )
                        result.function_validations.append(validation)
                        
                        result.hallucinations_detected.append({
                            'type': 'method',
                            'element': f'{object_name}.{method_name}',
                            'message': f"Method '{method_name}' does not exist on type '{object_type}'",
                            'confidence': 0.95,
                            'line': line,
                            'object_type': object_type
                        })
                        continue
                
                # Check if the object is a local class first
                if object_name in self.local_classes:
                    # For local classes, we can't validate methods from the knowledge graph
                    # but we can assume the method call is valid since the class is defined locally
                    validation = FunctionValidation(
                        function_name=f"{object_name}.{method_name}",
                        module=None,
                        args_count=method_call.get('args_count', 0),
                        validation=ValidationResult(
                            status=ValidationStatus.VALID,
                            confidence=0.9,
                            message=f"Method '{method_name}' on local class '{object_name}' - assuming valid"
                        )
                    )
                    result.function_validations.append(validation)
                    continue
                
                # Check if the object is a known class in Neo4j
                class_result = await session.run("""
                    MATCH (c:JSClass {name: $object_name})
                    RETURN c.name as name
                    LIMIT 1
                """, object_name=object_name)
                
                class_record = await class_result.single()
                
                if class_record:
                    # Check if the method exists on the class (instance or static)
                    method_result = await session.run("""
                        MATCH (c:JSClass {name: $object_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
                        RETURN m.name as name, m.isStatic as isStatic
                        LIMIT 1
                    """, object_name=object_name, method_name=method_name)
                    
                    method_record = await method_result.single()
                    
                    if method_record:
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.9,
                                message=f"{'Static' if method_record['isStatic'] else 'Instance'} method '{method_name}' exists on class '{object_name}'"
                            )
                        )
                        result.function_validations.append(validation)
                    else:
                        # Method doesn't exist on class
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.1,
                                message=f"Method '{method_name}' does not exist on class '{object_name}'"
                            )
                        )
                        result.function_validations.append(validation)
                        
                        result.hallucinations_detected.append({
                            'type': 'method',
                            'element': f'{object_name}.{method_name}',
                            'message': f"Method '{method_name}' does not exist on class '{object_name}'",
                            'confidence': 1.0,
                            'line': line
                        })
                else:
                    # Check if the object is imported from an external library
                    if object_name in self.external_imports:
                        # Object is from external library, assume method is valid
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.95,
                                message=f"Method '{method_name}' on external object '{object_name}' from '{self.external_imports[object_name]}'"
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    
                    # Check if the object is from a hook return
                    if object_name in self.hook_returns:
                        # Object is from hook, assume method is valid (e.g., i18n.changeLanguage)
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.95,
                                message=f"Method '{method_name}' on object '{object_name}' from hook '{self.hook_returns[object_name]}'"
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    
                    # Check if it's an event object (common parameter names)
                    if object_name in ['e', 'event', 'ev', 'evt'] and method_name in ['preventDefault', 'stopPropagation', 'stopImmediatePropagation']:
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.VALID,
                                confidence=0.95,
                                message=f"Event method '{method_name}' on event object '{object_name}' is valid"
                            )
                        )
                        result.function_validations.append(validation)
                        continue
                    
                    # Object might be an instance - check if method exists on any interface/type
                    if object_name[0].islower():  # Likely an instance variable
                        # Try to infer the type from the variable name
                        inferred_type = self._infer_builtin_type_from_name(object_name)
                        
                        if inferred_type and inferred_type in self.builtin_object_methods:
                            # Check if the method exists on the inferred type
                            if method_name in self.builtin_object_methods[inferred_type]:
                                validation = FunctionValidation(
                                    function_name=f"{object_name}.{method_name}",
                                    module=None,
                                    args_count=method_call.get('args_count', 0),
                                    validation=ValidationResult(
                                        status=ValidationStatus.VALID,
                                        confidence=0.8,
                                        message=f"Method '{method_name}' likely valid on inferred {inferred_type} type (based on variable name)"
                                    )
                                )
                                result.function_validations.append(validation)
                                continue
                            else:
                                validation = FunctionValidation(
                                    function_name=f"{object_name}.{method_name}",
                                    module=None,
                                    args_count=method_call.get('args_count', 0),
                                    validation=ValidationResult(
                                        status=ValidationStatus.INVALID,
                                        confidence=0.2,
                                        message=f"Method '{method_name}' does not exist on inferred {inferred_type} type",
                                        suggestions=[f"Did you mean: {', '.join(self._find_similar_methods(method_name, self.builtin_object_methods[inferred_type]))}?"]
                                    )
                                )
                                result.function_validations.append(validation)
                                result.hallucinations_detected.append({
                                    'type': 'method',
                                    'element': f'{object_name}.{method_name}',
                                    'message': f"Invalid method '{method_name}' on inferred {inferred_type} type",
                                    'confidence': 0.8,
                                    'line': line
                                })
                                continue
                        
                        # Try to find any type/interface/class that has this method
                        any_type_result = await session.run("""
                            MATCH (t)-[:HAS_METHOD]->(m:Method {name: $method_name})
                            WHERE t:JSClass OR t:Interface
                            RETURN t.name as typeName, labels(t)[0] as typeKind
                            UNION
                            MATCH (t:Interface)-[:HAS_PROPERTY]->(p:Property {name: $method_name})
                            WHERE p.type CONTAINS 'function' OR p.type CONTAINS '=>'
                            RETURN t.name as typeName, 'Interface' as typeKind
                            LIMIT 5
                        """, method_name=method_name)
                        
                        possible_types = []
                        async for record in any_type_result:
                            possible_types.append(f"{record['typeName']} ({record['typeKind']})")
                        
                        # Also check if the method exists on any built-in types
                        builtin_matches = []
                        for builtin_type, methods in self.builtin_object_methods.items():
                            if method_name in methods:
                                builtin_matches.append(builtin_type)
                        
                        if possible_types or builtin_matches:
                            # Method exists somewhere - uncertain validation
                            all_types = possible_types[:3] + [f"{t} (built-in)" for t in builtin_matches[:2]]
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.UNCERTAIN,
                                    confidence=0.6,
                                    message=f"Method '{method_name}' found in: {', '.join(all_types)}",
                                    suggestions=[f"Verify that '{object_name}' is an instance of one of these types"]
                                )
                            )
                            result.function_validations.append(validation)
                        else:
                            # Method doesn't exist anywhere
                            validation = FunctionValidation(
                                function_name=f"{object_name}.{method_name}",
                                module=None,
                                args_count=method_call.get('args_count', 0),
                                validation=ValidationResult(
                                    status=ValidationStatus.NOT_FOUND,
                                    confidence=0.0,
                                    message=f"Method '{method_name}' not found in any known type"
                                )
                            )
                            result.function_validations.append(validation)
                            
                            result.hallucinations_detected.append({
                                'type': 'method',
                                'element': f'{object_name}.{method_name}',
                                'message': f"Method '{method_name}' not found in any class or interface",
                                'confidence': 0.8,
                                'line': line
                            })
                    else:
                        # Object name starts with uppercase - might be a static call on unknown class
                        validation = FunctionValidation(
                            function_name=f"{object_name}.{method_name}",
                            module=None,
                            args_count=method_call.get('args_count', 0),
                            validation=ValidationResult(
                                status=ValidationStatus.NOT_FOUND,
                                confidence=0.0,
                                message=f"Class or object '{object_name}' not found in knowledge graph"
                            )
                        )
                        result.function_validations.append(validation)
    
    async def _validate_jsx_elements(self, jsx_elements: List[Dict], result: TypeScriptValidationResult):
        """Validate JSX elements - check if components exist in Neo4j"""
        for element in jsx_elements:
            element_name = element.get('name', '')
            
            # Skip HTML elements
            if self.config.is_html_element(element_name):
                continue
            
            # Skip empty or invalid element names
            if not element_name or element_name[0].islower():
                continue
            
            # Check if it's a locally defined component
            if element_name in self.local_components:
                # Component is defined locally - skip Neo4j validation
                continue
            
            # Check if it's an imported component (external or internal)
            if element_name in self.external_imports:
                source = self.external_imports[element_name]
                # Component is imported - trust it exists
                continue
            
            async with self.driver.session() as session:
                # Check if component exists in Neo4j
                comp_result = await session.run("""
                    MATCH (c:Component {name: $name})
                    RETURN c.name as name
                    LIMIT 1
                """, name=element_name)
                
                comp_record = await comp_result.single()
                
                if not comp_record:
                    # Component not found - add to import validations as a JSX element validation
                    validation = ImportValidation(
                        module=f"JSX Element: {element_name}",
                        imported_items=[{'name': element_name, 'type': 'jsx_element'}],
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"JSX element '{element_name}' component not found in knowledge graph"
                        )
                    )
                    result.import_validations.append(validation)
                    
                    # Also add to hallucinations
                    result.hallucinations_detected.append({
                        'type': 'jsx_element',
                        'element': element_name,
                        'message': f"JSX element '{element_name}' references non-existent component",
                        'confidence': 1.0,
                        'line': element.get('line', 0)
                    })
    
    async def _validate_component_props(self, component_uses: List[Dict], result: TypeScriptValidationResult):
        """Enhanced validation of component props against their interfaces/types"""
        # This extends the existing component validation with more detailed prop checking
        for comp_use in component_uses:
            comp_name = comp_use['name']
            props_used = comp_use.get('props', [])
            
            # Skip HTML elements and components without props
            if self.config.is_html_element(comp_name) or not props_used:
                continue
            
            async with self.driver.session() as session:
                # Get component and its props interface/type
                props_result = await session.run("""
                    MATCH (c:Component {name: $name})
                    OPTIONAL MATCH (c)-[:HAS_PROPS]->(p)
                    OPTIONAL MATCH (c)-[:HAS_PROPS_TYPE]->(t:Interface)
                    OPTIONAL MATCH (c)-[:HAS_PROPS_TYPE]->(type:Type)
                    RETURN c.name as component_name,
                           p.properties as props_properties,
                           t.properties as interface_properties,
                           type.definition as type_definition,
                           c.isForwardRef as isForwardRef
                """, name=comp_name)
                
                props_record = await props_result.single()
                
                if props_record:
                    # Collect all expected props from various sources
                    expected_props = set()
                    
                    if props_record['props_properties']:
                        expected_props.update(props_record['props_properties'])
                    
                    if props_record['interface_properties']:
                        expected_props.update(props_record['interface_properties'])
                    
                    # Check if any prop is marked as required
                    required_props_result = await session.run("""
                        MATCH (c:Component {name: $name})-[:HAS_PROPS_TYPE]->(i:Interface)
                        OPTIONAL MATCH (i)-[:HAS_PROPERTY]->(prop:Property {required: true})
                        RETURN collect(prop.name) as required_props
                    """, name=comp_name)
                    
                    required_record = await required_props_result.single()
                    required_props = set(required_record['required_props'] if required_record and required_record['required_props'] else [])
                    
                    # Find missing required props
                    missing_required = required_props - set(props_used)
                    
                    if missing_required:
                        # Add validation error for missing required props
                        validation = ImportValidation(
                            module=f"Component Props: {comp_name}",
                            imported_items=[{'name': p, 'type': 'required_prop'} for p in missing_required],
                            validation=ValidationResult(
                                status=ValidationStatus.INVALID,
                                confidence=0.1,
                                message=f"Missing required props for '{comp_name}': {list(missing_required)}",
                                suggestions=[f"Add required props: {', '.join(missing_required)}"]
                            )
                        )
                        result.import_validations.append(validation)
    
    async def _validate_type_usage(self, type_annotations: List[Dict], result: TypeScriptValidationResult):
        """Validate type annotations in function parameters and return types"""
        for annotation in type_annotations:
            type_name = annotation.get('type', '')
            usage_context = annotation.get('context', '')  # 'parameter', 'return', 'variable'
            
            # Skip built-in types
            if type_name in ['string', 'number', 'boolean', 'any', 'void', 'never', 'unknown', 'null', 'undefined']:
                continue
            
            # Skip array and generic types for base validation
            base_type = type_name.split('[')[0].split('<')[0].strip()
            
            # Skip React types
            if self.config.is_react_type(base_type):
                continue
            
            # Check if it's a locally defined type or interface
            if base_type in self.local_types or base_type in self.local_interfaces:
                # Type is defined locally - skip Neo4j validation
                continue
            
            async with self.driver.session() as session:
                # Check if type exists
                type_result = await session.run("""
                    MATCH (t)
                    WHERE (t:Interface OR t:Type OR t:Enum) AND t.name = $name
                    RETURN t.name as name, labels(t)[0] as kind
                    LIMIT 1
                """, name=base_type)
                
                type_record = await type_result.single()
                
                if not type_record:
                    # Type not found
                    validation = ImportValidation(
                        module=f"Type Usage: {usage_context}",
                        imported_items=[{'name': type_name, 'type': 'type_annotation'}],
                        validation=ValidationResult(
                            status=ValidationStatus.NOT_FOUND,
                            confidence=0.0,
                            message=f"Type '{type_name}' used in {usage_context} not found in knowledge graph"
                        )
                    )
                    result.import_validations.append(validation)
                    
                    # Add to hallucinations
                    result.hallucinations_detected.append({
                        'type': 'type_usage',
                        'element': type_name,
                        'message': f"Type '{type_name}' used in {usage_context} does not exist",
                        'confidence': 0.9,
                        'line': annotation.get('line', 0),
                        'context': usage_context
                    })
                else:
                    # For function parameters, check if the type has the expected properties being accessed
                    if usage_context == 'parameter' and 'accessed_properties' in annotation:
                        accessed = set(annotation['accessed_properties'])
                        
                        # Get type properties
                        props_result = await session.run("""
                            MATCH (t {name: $name})
                            WHERE t:Interface OR t:Type
                            RETURN t.properties as properties
                        """, name=base_type)
                        
                        props_record = await props_result.single()
                        
                        if props_record and props_record['properties']:
                            available = set(props_record['properties'])
                            invalid_access = accessed - available
                            
                            if invalid_access:
                                validation = ImportValidation(
                                    module=f"Type Property Access: {base_type}",
                                    imported_items=[{'name': prop, 'type': 'property_access'} for prop in invalid_access],
                                    validation=ValidationResult(
                                        status=ValidationStatus.INVALID,
                                        confidence=0.2,
                                        message=f"Invalid property access on type '{base_type}': {list(invalid_access)}",
                                        suggestions=[f"Available properties: {', '.join(available)}"]
                                    )
                                )
                                result.import_validations.append(validation)
    
    def _is_external_library(self, module_name: str) -> str:
        """Check if a module is an external library"""
        # This is a simplified check - could be enhanced
        return not module_name.startswith('.') and not module_name.startswith('/')
    
    def _is_known_library(self, module_name: str) -> bool:
        """Check if a module is in the list of known external libraries"""
        # Just delegate to the config method which has the comprehensive list
        return self.config.is_external_library(module_name) or self.config.is_trusted_external_pattern(module_name)
    
    def _find_similar_methods(self, method_name: str, valid_methods: Set[str], max_suggestions: int = 5) -> List[str]:
        """Find similar method names for suggestions"""
        suggestions = []
        
        # Check for exact prefix matches
        prefix_matches = [m for m in valid_methods if m.startswith(method_name[:3])]
        suggestions.extend(prefix_matches[:max_suggestions])
        
        # Check for common typos
        if method_name == 'lenght':  # Common typo
            if 'length' in valid_methods:
                suggestions.insert(0, 'length')
        elif method_name == 'indexof':  # Case error
            if 'indexOf' in valid_methods:
                suggestions.insert(0, 'indexOf')
        elif method_name == 'tolowercase':  # Case error
            if 'toLowerCase' in valid_methods:
                suggestions.insert(0, 'toLowerCase')
        elif method_name == 'touppercase':  # Case error
            if 'toUpperCase' in valid_methods:
                suggestions.insert(0, 'toUpperCase')
        
        # Check for Levenshtein distance for close matches
        from difflib import get_close_matches
        close_matches = get_close_matches(method_name, valid_methods, n=max_suggestions, cutoff=0.6)
        for match in close_matches:
            if match not in suggestions:
                suggestions.append(match)
        
        return suggestions[:max_suggestions]
    
    def _infer_builtin_type_from_name(self, var_name: str) -> Optional[str]:
        """Infer built-in type from variable naming conventions"""
        var_lower = var_name.lower()
        
        # Common naming patterns for arrays
        if (var_lower.endswith('s') or var_lower.endswith('list') or 
            var_lower.endswith('array') or var_lower.startswith('arr') or
            var_lower in ['items', 'elements', 'data', 'values', 'results']):
            return 'Array'
        
        # Common naming patterns for strings
        if (var_lower.startswith('str') or var_lower.endswith('name') or 
            var_lower.endswith('text') or var_lower.endswith('message') or
            var_lower.endswith('label') or var_lower.endswith('title') or
            var_lower.endswith('path') or var_lower.endswith('url') or
            var_lower in ['text', 'name', 'message', 'label', 'title', 'path', 'url']):
            return 'String'
        
        # Common naming patterns for numbers
        if (var_lower.startswith('num') or var_lower.endswith('count') or
            var_lower.endswith('index') or var_lower.endswith('size') or
            var_lower.endswith('length') or var_lower.endswith('total') or
            var_lower.endswith('amount') or var_lower.endswith('price') or
            var_lower in ['count', 'index', 'size', 'length', 'total', 'amount', 'price']):
            return 'Number'
        
        # Common naming patterns for dates
        if (var_lower.startswith('date') or var_lower.endswith('date') or
            var_lower.endswith('time') or var_lower.startswith('time') or
            var_lower in ['date', 'time', 'timestamp', 'datetime']):
            return 'Date'
        
        # Common naming patterns for maps/objects
        if (var_lower.startswith('map') or var_lower.endswith('map') or
            var_lower.endswith('dict') or var_lower.endswith('object')):
            return 'Map'
        
        # Common naming patterns for sets
        if (var_lower.startswith('set') or var_lower.endswith('set') or
            var_lower.endswith('unique')):
            return 'Set'
        
        return None
    
    def _find_project_root(self, script_path: Path) -> Optional[Path]:
        """Find the project root directory by looking for common markers"""
        current = script_path.parent
        
        # Look for common project root indicators
        markers = ['package.json', 'tsconfig.json', '.git', 'node_modules']
        
        while current != current.parent:
            for marker in markers:
                if (current / marker).exists():
                    return current
            current = current.parent
        
        return None
    
    def _calculate_overall_confidence(self, result: TypeScriptValidationResult) -> float:
        """Calculate overall confidence score"""
        all_validations = []
        
        # Collect all validation results
        all_validations.extend([v.validation for v in result.import_validations])
        all_validations.extend([v.validation for v in result.component_validations])
        all_validations.extend([v.validation for v in result.hook_validations])
        all_validations.extend([v.validation for v in result.type_validations])
        all_validations.extend([v.validation for v in result.function_validations])
        
        if not all_validations:
            return 1.0
        
        # Filter out external library validations for confidence calculation
        internal_validations = [
            v for v in all_validations 
            if not (hasattr(v, 'message') and 'External' in v.message)
        ]
        
        if not internal_validations:
            return 1.0
        
        # If there are any hallucinations, heavily penalize the confidence
        hallucination_count = len(result.hallucinations_detected)
        if hallucination_count > 0:
            # Base confidence on ratio of hallucinations to total validations
            base_confidence = max(0.0, 1.0 - (hallucination_count / len(internal_validations)))
            # Further reduce confidence based on number of hallucinations
            return base_confidence * (0.5 ** min(hallucination_count, 3))
        
        # Otherwise calculate weighted average
        total_confidence = sum(v.confidence for v in internal_validations)
        return total_confidence / len(internal_validations)
    
    def _identify_hallucinations(self, result: TypeScriptValidationResult):
        """Identify hallucinations in the validation results"""
        
        # Check imports
        for imp_val in result.import_validations:
            if imp_val.validation.status == ValidationStatus.NOT_FOUND:
                # Only flag as hallucination if we're confident it's missing
                result.hallucinations_detected.append({
                    'type': 'import',
                    'element': imp_val.module,
                    'message': imp_val.validation.message,
                    'confidence': 1.0 - imp_val.validation.confidence
                })
            elif imp_val.validation.status == ValidationStatus.INVALID:
                # For invalid imports, check if it's an internal module issue
                if imp_val.validation.confidence < 0.5:  # Low confidence invalids might be false positives
                    result.hallucinations_detected.append({
                        'type': 'import',
                        'element': imp_val.module,
                        'message': imp_val.validation.message,
                        'confidence': 1.0 - imp_val.validation.confidence
                    })
            # UNCERTAIN status is not considered a hallucination
        
        # Check components
        for comp_val in result.component_validations:
            if comp_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'component',
                    'element': comp_val.component_name,
                    'message': comp_val.validation.message,
                    'confidence': 1.0 - comp_val.validation.confidence
                })
        
        # Check types
        for type_val in result.type_validations:
            if type_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'type',
                    'element': type_val.type_name,
                    'message': type_val.validation.message,
                    'confidence': 1.0 - type_val.validation.confidence
                })
        
        # Check functions
        for func_val in result.function_validations:
            if func_val.validation.status == ValidationStatus.NOT_FOUND:
                result.hallucinations_detected.append({
                    'type': 'function',
                    'element': func_val.function_name,
                    'message': func_val.validation.message,
                    'confidence': 1.0 - func_val.validation.confidence
                })


async def validate_typescript_script(script_path: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str, config: Optional[ValidatorConfig] = None) -> TypeScriptValidationResult:
    """Convenience function to validate a TypeScript script"""
    validator = TypeScriptKnowledgeGraphValidator(neo4j_uri, neo4j_user, neo4j_password, config)
    try:
        await validator.initialize()
        return await validator.validate_script(script_path)
    finally:
        await validator.close()


if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python ts_knowledge_graph_validator.py <script_path>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("NEO4J_PASSWORD not set in environment")
        sys.exit(1)
    
    # Run validation
    async def main():
        result = await validate_typescript_script(script_path, neo4j_uri, neo4j_user, neo4j_password)
        
        print(f"\n=== TypeScript Validation Results ===")
        print(f"Script: {result.script_path}")
        print(f"Overall Confidence: {result.overall_confidence:.2f}")
        
        if result.hallucinations_detected:
            print(f"\nHallucinations Detected: {len(result.hallucinations_detected)}")
            for h in result.hallucinations_detected:
                print(f"  - {h['type']}: {h['element']} - {h['message']}")
        else:
            print("\nNo hallucinations detected!")
    
    asyncio.run(main())