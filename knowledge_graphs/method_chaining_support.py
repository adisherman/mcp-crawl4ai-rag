"""
Method Chaining Support for TypeScript Knowledge Graph Validator

This module provides support for validating method chains, particularly for
validation libraries like Zod, Yup, and Joi.
"""

from typing import Dict, Set, Optional, List, Tuple
import re


class MethodChainResolver:
    """Resolves method chains by tracking return types."""
    
    def __init__(self):
        # Define return types for known namespace methods
        self.method_return_types = {
            'zod': {
                # Type constructors return their respective schema types
                'string': 'ZodString',
                'number': 'ZodNumber', 
                'boolean': 'ZodBoolean',
                'date': 'ZodDate',
                'bigint': 'ZodBigInt',
                'symbol': 'ZodSymbol',
                'undefined': 'ZodUndefined',
                'null': 'ZodNull',
                'void': 'ZodVoid',
                'any': 'ZodAny',
                'unknown': 'ZodUnknown',
                'never': 'ZodNever',
                'array': 'ZodArray',
                'object': 'ZodObject',
                'union': 'ZodUnion',
                'discriminatedUnion': 'ZodDiscriminatedUnion',
                'intersection': 'ZodIntersection',
                'tuple': 'ZodTuple',
                'record': 'ZodRecord',
                'map': 'ZodMap',
                'set': 'ZodSet',
                'function': 'ZodFunction',
                'lazy': 'ZodLazy',
                'literal': 'ZodLiteral',
                'enum': 'ZodEnum',
                'nativeEnum': 'ZodNativeEnum',
                'promise': 'ZodPromise',
                'effect': 'ZodEffects',
                'preprocess': 'ZodEffects',
                'custom': 'ZodType',
                'instanceof': 'ZodType',
                'coerce': 'ZodType'
            },
            'yup': {
                'string': 'StringSchema',
                'number': 'NumberSchema',
                'boolean': 'BooleanSchema',
                'date': 'DateSchema',
                'array': 'ArraySchema',
                'object': 'ObjectSchema',
                'mixed': 'MixedSchema',
                'ref': 'Reference',
                'lazy': 'LazySchema'
            },
            'joi': {
                'string': 'JoiStringSchema',
                'number': 'JoiNumberSchema',
                'boolean': 'JoiBooleanSchema',
                'date': 'JoiDateSchema',
                'array': 'JoiArraySchema',
                'object': 'JoiObjectSchema',
                'any': 'JoiAnySchema',
                'alternatives': 'JoiAlternativesSchema',
                'binary': 'JoiBinarySchema',
                'function': 'JoiFunctionSchema',
                'link': 'JoiLinkSchema',
                'symbol': 'JoiSymbolSchema'
            }
        }
        
        # Define methods available on each schema type
        self.schema_type_methods = {
            # Zod schema types
            'ZodString': {
                # String-specific validations
                'email', 'url', 'emoji', 'uuid', 'cuid', 'cuid2', 'ulid',
                'regex', 'includes', 'startsWith', 'endsWith', 'datetime',
                'ip', 'base64', 'duration', 'nanoid',
                # String transformations
                'trim', 'toLowerCase', 'toUpperCase',
                # String constraints
                'min', 'max', 'length', 'nonempty',
                # Common Zod methods (inherited)
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodNumber': {
                # Number-specific validations
                'gt', 'gte', 'lt', 'lte', 'int', 'positive', 'nonnegative',
                'negative', 'nonpositive', 'multipleOf', 'finite', 'safe',
                'min', 'max',
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodBoolean': {
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodDate': {
                # Date-specific validations
                'min', 'max',
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodArray': {
                # Array-specific validations
                'element', 'min', 'max', 'length', 'nonempty',
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodObject': {
                # Object-specific methods
                'shape', 'extend', 'merge', 'pick', 'omit', 'partial',
                'deepPartial', 'required', 'passthrough', 'strict', 'strip',
                'catchall', 'keyof', 'augment', 'setKey',
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodUnion': {
                'options',
                # Common Zod methods
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            'ZodType': {
                # Base methods available on all Zod types
                'parse', 'parseAsync', 'safeParse', 'safeParseAsync',
                'refine', 'superRefine', 'transform', 'default', 'catch',
                'optional', 'nullable', 'nullish', 'array', 'promise',
                'or', 'and', 'brand', 'readonly', 'describe', 'pipe',
                'isOptional', 'isNullable'
            },
            # Add more Zod types as needed
            'ZodBigInt': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodSymbol': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodUndefined': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodNull': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodVoid': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodAny': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodUnknown': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodNever': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            'ZodEffects': {'parse', 'parseAsync', 'safeParse', 'safeParseAsync', 'refine', 'superRefine', 'transform', 'default', 'catch', 'optional', 'nullable', 'nullish', 'array', 'promise', 'or', 'and', 'brand', 'readonly', 'describe', 'pipe'},
            
            # Yup schema types
            'StringSchema': {
                'required', 'defined', 'notRequired', 'nullable', 'nonNullable',
                'email', 'url', 'uuid', 'ensure', 'trim', 'lowercase', 'uppercase',
                'matches', 'min', 'max', 'length', 'test', 'when', 'transform',
                'default', 'strip', 'concat', 'validate', 'validateSync',
                'isValid', 'isValidSync', 'cast', 'describe', 'resolve',
                'typeError', 'oneOf', 'notOneOf', 'equals'
            },
            'NumberSchema': {
                'required', 'defined', 'notRequired', 'nullable', 'nonNullable',
                'min', 'max', 'lessThan', 'moreThan', 'positive', 'negative',
                'integer', 'truncate', 'round', 'test', 'when', 'transform',
                'default', 'strip', 'concat', 'validate', 'validateSync',
                'isValid', 'isValidSync', 'cast', 'describe', 'resolve',
                'typeError', 'oneOf', 'notOneOf', 'equals'
            },
            'BooleanSchema': {
                'required', 'defined', 'notRequired', 'nullable', 'nonNullable',
                'isTrue', 'isFalse', 'test', 'when', 'transform',
                'default', 'strip', 'concat', 'validate', 'validateSync',
                'isValid', 'isValidSync', 'cast', 'describe', 'resolve',
                'typeError', 'oneOf', 'notOneOf', 'equals'
            },
            'ArraySchema': {
                'required', 'defined', 'notRequired', 'nullable', 'nonNullable',
                'of', 'length', 'min', 'max', 'ensure', 'compact', 'test', 'when',
                'transform', 'default', 'strip', 'concat', 'validate', 'validateSync',
                'isValid', 'isValidSync', 'cast', 'describe', 'resolve',
                'typeError', 'oneOf', 'notOneOf', 'equals'
            },
            'ObjectSchema': {
                'required', 'defined', 'notRequired', 'nullable', 'nonNullable',
                'shape', 'from', 'noUnknown', 'unknown', 'transformKeys',
                'camelCase', 'snakeCase', 'constantCase', 'describe', 'test',
                'when', 'transform', 'default', 'strip', 'concat', 'validate',
                'validateSync', 'isValid', 'isValidSync', 'cast', 'resolve',
                'typeError', 'pick', 'omit'
            },
            
            # Joi schema types
            'JoiStringSchema': {
                'alphanum', 'base64', 'case', 'creditCard', 'dataUri', 'domain',
                'email', 'guid', 'hex', 'hostname', 'insensitive', 'ip', 'isoDate',
                'isoDuration', 'length', 'lowercase', 'max', 'min', 'normalize',
                'pattern', 'regex', 'replace', 'token', 'trim', 'truncate', 'uppercase',
                'uri', 'uuid', 'valid', 'invalid', 'required', 'optional', 'forbidden',
                'strip', 'default', 'concat', 'when', 'empty', 'error', 'label',
                'messages', 'meta', 'note', 'only', 'preferences', 'presence', 'raw',
                'result', 'rule', 'ruleset', 'tag', 'unit', 'warning', 'allow',
                'alter', 'cast', 'describe', 'example', 'external', 'failover',
                'fork', 'id', 'keep', 'prefs', 'shared', 'strict', 'tailor',
                'validate', 'validateAsync'
            },
            'JoiNumberSchema': {
                'greater', 'integer', 'less', 'max', 'min', 'multiple', 'negative',
                'port', 'positive', 'precision', 'sign', 'unsafe', 'valid', 'invalid',
                'required', 'optional', 'forbidden', 'strip', 'default', 'concat',
                'when', 'empty', 'error', 'label', 'messages', 'meta', 'note', 'only',
                'preferences', 'presence', 'raw', 'result', 'rule', 'ruleset', 'tag',
                'unit', 'warning', 'allow', 'alter', 'cast', 'describe', 'example',
                'external', 'failover', 'fork', 'id', 'keep', 'prefs', 'shared',
                'strict', 'tailor', 'validate', 'validateAsync'
            },
            'JoiBooleanSchema': {
                'falsy', 'sensitive', 'truthy', 'valid', 'invalid', 'required',
                'optional', 'forbidden', 'strip', 'default', 'concat', 'when',
                'empty', 'error', 'label', 'messages', 'meta', 'note', 'only',
                'preferences', 'presence', 'raw', 'result', 'rule', 'ruleset',
                'tag', 'unit', 'warning', 'allow', 'alter', 'cast', 'describe',
                'example', 'external', 'failover', 'fork', 'id', 'keep', 'prefs',
                'shared', 'strict', 'tailor', 'validate', 'validateAsync'
            },
            'JoiArraySchema': {
                'has', 'items', 'length', 'max', 'min', 'ordered', 'single',
                'sort', 'sparse', 'unique', 'valid', 'invalid', 'required',
                'optional', 'forbidden', 'strip', 'default', 'concat', 'when',
                'empty', 'error', 'label', 'messages', 'meta', 'note', 'only',
                'preferences', 'presence', 'raw', 'result', 'rule', 'ruleset',
                'tag', 'unit', 'warning', 'allow', 'alter', 'cast', 'describe',
                'example', 'external', 'failover', 'fork', 'id', 'keep', 'prefs',
                'shared', 'strict', 'tailor', 'validate', 'validateAsync'
            },
            'JoiObjectSchema': {
                'and', 'append', 'assert', 'instance', 'keys', 'length', 'max',
                'min', 'nand', 'or', 'oxor', 'pattern', 'ref', 'rename', 'schema',
                'unknown', 'with', 'without', 'xor', 'valid', 'invalid', 'required',
                'optional', 'forbidden', 'strip', 'default', 'concat', 'when',
                'empty', 'error', 'label', 'messages', 'meta', 'note', 'only',
                'preferences', 'presence', 'raw', 'result', 'rule', 'ruleset',
                'tag', 'unit', 'warning', 'allow', 'alter', 'cast', 'describe',
                'example', 'external', 'failover', 'fork', 'id', 'keep', 'prefs',
                'shared', 'strict', 'tailor', 'validate', 'validateAsync'
            }
        }
        
        # Methods that return the same type (for chaining)
        self.same_type_methods = {
            'optional', 'nullable', 'nullish', 'required', 'readonly',
            'brand', 'describe', 'default', 'catch', 'strip',
            'nonNullable', 'defined', 'notRequired'
        }
        
        # Methods that might change the type
        self.type_changing_methods = {
            'array': lambda t: f'{t}Array',
            'promise': lambda t: f'{t}Promise',
            'transform': lambda t: 'ZodEffects',
            'refine': lambda t: 'ZodEffects',
            'superRefine': lambda t: 'ZodEffects',
            'preprocess': lambda t: 'ZodEffects',
            'pipe': lambda t: 'ZodPipeline'
        }

    def parse_method_chain(self, object_text: str) -> List[Tuple[str, str]]:
        """
        Parse a method chain like 'z.string().email()' into components.
        Returns a list of (object, method) tuples.
        """
        # Handle nested function calls in the chain
        parts = []
        current = object_text
        
        # Use regex to split by method calls
        # Match patterns like .method() or .method(args)
        pattern = r'\.([a-zA-Z_]\w*)\s*\([^)]*\)'
        
        matches = list(re.finditer(pattern, current))
        
        if not matches:
            # No method calls found, might be a simple property access
            return []
        
        # Get the base object (everything before the first method call)
        base = current[:matches[0].start()]
        
        # Extract each method call
        for i, match in enumerate(matches):
            method = match.group(1)
            if i == 0:
                parts.append((base, method))
            else:
                # For subsequent calls, the object is the result of the previous call
                parts.append(('__previous__', method))
        
        return parts

    def resolve_chain_type(self, namespace: str, chain: List[Tuple[str, str]]) -> Optional[str]:
        """
        Resolve the type at each step of a method chain.
        Returns the final type or None if unable to resolve.
        """
        if not chain:
            return None
        
        current_type = None
        
        for i, (obj, method) in enumerate(chain):
            if i == 0:
                # First call - check if it's a namespace method
                if namespace in self.method_return_types and method in self.method_return_types[namespace]:
                    current_type = self.method_return_types[namespace][method]
                else:
                    return None
            else:
                # Subsequent calls - check if method exists on current type
                if current_type in self.schema_type_methods:
                    if method in self.schema_type_methods[current_type]:
                        # Check if this method changes the type
                        if method in self.same_type_methods:
                            # Type stays the same
                            pass
                        elif method in self.type_changing_methods:
                            # Type changes according to the transformation
                            current_type = self.type_changing_methods[method](current_type)
                        else:
                            # Method might return the same type (most Zod methods do)
                            # Unless we have specific knowledge otherwise
                            pass
                    else:
                        return None
                else:
                    return None
        
        return current_type

    def validate_method_chain(self, object_text: str, method_name: str, namespace: str) -> Tuple[bool, str, List[str]]:
        """
        Validate a method chain.
        Returns (is_valid, message, suggestions).
        """
        # First, try to parse the chain
        chain = self.parse_method_chain(object_text)
        
        if not chain:
            # Not a method chain, return invalid
            return False, f"Unable to parse method chain: {object_text}", []
        
        # Add the final method to the chain
        chain.append(('__previous__', method_name))
        
        # Resolve the type at each step
        current_type = None
        
        for i, (obj, method) in enumerate(chain):
            if i == 0:
                # First call - check if it's a namespace method
                if namespace in self.method_return_types and method in self.method_return_types[namespace]:
                    current_type = self.method_return_types[namespace][method]
                else:
                    return False, f"Unknown namespace method '{method}' on '{namespace}'", []
            else:
                # Subsequent calls - check if method exists on current type
                if current_type in self.schema_type_methods:
                    available_methods = self.schema_type_methods[current_type]
                    if method in available_methods:
                        # Method is valid
                        # Update type if necessary
                        if method in self.same_type_methods:
                            # Type stays the same
                            pass
                        elif method in self.type_changing_methods:
                            # Type changes according to the transformation
                            current_type = self.type_changing_methods[method](current_type)
                        # Continue to next method
                    else:
                        # Method not found on this type
                        suggestions = self._find_similar_methods(method, available_methods)
                        return False, f"Method '{method}' does not exist on {current_type}", suggestions
                else:
                    # Unknown type
                    return False, f"Unknown type '{current_type}' in method chain", []
        
        # If we made it here, the chain is valid
        chain_str = object_text + '.' + method_name + '()'
        return True, f"Valid method chain: {chain_str}", []

    def _find_similar_methods(self, method: str, available_methods: Set[str]) -> List[str]:
        """Find similar method names for suggestions."""
        from difflib import get_close_matches
        return get_close_matches(method, available_methods, n=3, cutoff=0.6)

    def is_chainable_method_call(self, object_text: str) -> bool:
        """
        Check if the object text represents a method call that returns a chainable type.
        E.g., 'z.string()' returns true, 'myVar' returns false.
        """
        # Check if it ends with method call parentheses
        return bool(re.search(r'\.\w+\s*\([^)]*\)\s*$', object_text))