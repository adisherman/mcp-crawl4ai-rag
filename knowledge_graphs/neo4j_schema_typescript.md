# Neo4j Schema Extension for TypeScript/React/Node Support

## Overview
This document defines the extended Neo4j schema to support TypeScript, React, and Node.js code analysis alongside the existing Python support.

## Node Types

### Existing Nodes (Python)
- `Repository`: GitHub repositories
- `File`: Source files
- `Class`: Python classes
- `Method`: Class methods
- `Function`: Standalone functions
- `Attribute`: Class attributes

### New Node Types (TypeScript/React/Node)

#### Core TypeScript Nodes
1. **Interface**
   - Properties: `name`, `generic_params`, `extends`, `exported`
   - Represents TypeScript interfaces

2. **Type**
   - Properties: `name`, `definition`, `generic_params`, `exported`
   - Represents type aliases and type definitions

3. **Enum**
   - Properties: `name`, `values`, `const`, `exported`
   - Represents TypeScript enums

4. **Namespace**
   - Properties: `name`, `exported`
   - Represents TypeScript namespaces/modules

#### React-Specific Nodes
5. **Component**
   - Properties: `name`, `type` (functional/class), `props_interface`, `exported`
   - Represents React components

6. **Hook**
   - Properties: `name`, `custom` (true for custom hooks), `dependencies`
   - Represents React hooks

7. **Props**
   - Properties: `interface_name`, `properties`
   - Represents component prop types

#### JavaScript/Node Nodes
8. **Module**
   - Properties: `path`, `type` (ES6/CommonJS), `default_export`, `named_exports`
   - Represents JavaScript modules

9. **JSFunction**
   - Properties: `name`, `async`, `generator`, `params`, `exported`
   - JavaScript functions (distinct from Python functions)

10. **JSClass**
    - Properties: `name`, `extends`, `exported`
    - JavaScript/TypeScript classes

## Relationships

### Existing Relationships
- `CONTAINS`: Repository/File contains other elements
- `DEFINES`: File defines classes/functions
- `HAS_METHOD`: Class has methods
- `HAS_ATTRIBUTE`: Class has attributes
- `IMPORTS`: File imports from another file

### New Relationships

#### TypeScript Relationships
1. **IMPLEMENTS**
   - From: Class, Component
   - To: Interface
   - Properties: `partial` (for Partial<T>)

2. **EXTENDS_TYPE**
   - From: Interface, Class, Type
   - To: Interface, Class, Type
   - Properties: `generic_args`

3. **HAS_PROPERTY**
   - From: Interface, Type, Props
   - To: Property (inline node)
   - Properties: `optional`, `readonly`, `type`

4. **USES_TYPE**
   - From: Function, Method, Property
   - To: Type, Interface, Enum
   - Properties: `as_param`, `as_return`, `as_property`

#### React Relationships
5. **USES_HOOK**
   - From: Component, Hook
   - To: Hook
   - Properties: `dependency_array`

6. **HAS_PROPS**
   - From: Component
   - To: Props, Interface
   - Properties: `spread`, `destructured`

7. **RENDERS**
   - From: Component
   - To: Component
   - Properties: `conditional`, `in_map`

8. **USES_CONTEXT**
   - From: Component
   - To: Context (node)
   - Properties: None

#### Module Relationships
9. **EXPORTS**
   - From: Module, File
   - To: Function, Class, Component, Type, Interface
   - Properties: `default`, `named`, `alias`

10. **IMPORTS_FROM**
    - From: File
    - To: Module, File
    - Properties: `import_type` (ES6/CommonJS), `items`

## Schema Queries Examples

### Find all React components that use a specific hook
```cypher
MATCH (c:Component)-[:USES_HOOK]->(h:Hook {name: 'useState'})
RETURN c.name, c.type
```

### Find TypeScript interfaces and their implementations
```cypher
MATCH (i:Interface)<-[:IMPLEMENTS]-(implementor)
RETURN i.name, collect(implementor.name) as implementations
```

### Find all modules that export React components
```cypher
MATCH (m:Module)-[:EXPORTS]->(c:Component)
RETURN m.path, collect(c.name) as exported_components
```

### Validate if a component's props match its interface
```cypher
MATCH (c:Component)-[:HAS_PROPS]->(p:Props)
MATCH (c)-[:IMPLEMENTS]->(i:Interface)
RETURN c.name, p.interface_name, i.name, p.interface_name = i.name as matches
```

## Migration Strategy

1. **Language Detection**
   - Add `language` property to File nodes
   - Support mixed repositories with both Python and TypeScript

2. **Backward Compatibility**
   - Keep existing Python nodes and relationships
   - Use namespacing for language-specific nodes when needed

3. **Cross-Language Support**
   - Track cross-language imports (e.g., Python calling Node.js scripts)
   - Support polyglot repositories

## Implementation Notes

1. **Generic Types**: Store as JSON strings in `generic_params` properties
2. **JSX Elements**: Parse as function calls to components
3. **Decorators**: Store as properties on relevant nodes
4. **Async/Promise Types**: Track in type definitions
5. **Union/Intersection Types**: Store as Type nodes with special properties