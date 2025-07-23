# Neo4j Schema Design for TypeScript/JavaScript Code Intelligence

## Executive Summary

This document presents research findings on optimal Neo4j schema design for storing TypeScript and JavaScript code structures, with a focus on performance, query efficiency, and hallucination detection capabilities.

## 1. Optimal Node and Relationship Types

### Core Node Types

Based on industry best practices and GitHub's stack graphs implementation, the following node types are recommended:

#### Language-Agnostic Nodes
- **Repository**: Root node for a codebase
- **File**: Source file node with path and module information
- **Module**: Logical module/package representation

#### TypeScript/JavaScript Specific Nodes
- **Component**: React components (functional/class)
- **Interface**: TypeScript interfaces
- **Type**: Type aliases and complex types
- **Enum**: Enumeration definitions
- **Namespace**: TypeScript namespaces
- **Hook**: React hooks (built-in and custom)
- **JSFunction**: JavaScript/TypeScript functions
- **JSClass**: ES6+ classes
- **Method**: Class methods
- **Property**: Class/interface properties
- **Parameter**: Function/method parameters
- **Generic**: Generic type parameters

### Relationship Types

#### Structural Relationships
- `(:Repository)-[:CONTAINS]->(:File)`
- `(:File)-[:DEFINES]->(:Component|Interface|Type|JSFunction|JSClass)`
- `(:Module)-[:EXPORTS]->(:Component|Interface|Type|JSFunction|JSClass)`
- `(:File)-[:IMPORTS_FROM]->(:File|Module)`

#### Type System Relationships
- `(:Interface)-[:EXTENDS]->(:Interface)`
- `(:JSClass)-[:IMPLEMENTS]->(:Interface)`
- `(:Type)-[:REFERENCES]->(:Type|Interface)`
- `(:Component|JSFunction)-[:HAS_PARAMETER]->(:Parameter)`
- `(:Parameter)-[:HAS_TYPE]->(:Type|Interface)`

#### React-Specific Relationships
- `(:Component)-[:USES_HOOK]->(:Hook)`
- `(:Component)-[:ACCEPTS_PROPS]->(:Props)`
- `(:Component)-[:RENDERS]->(:Component)`
- `(:Hook)-[:DEPENDS_ON]->(:Hook)`

#### Call Graph Relationships
- `(:JSFunction|Method)-[:CALLS]->(:JSFunction|Method)`
- `(:Component)-[:USES_CONTEXT]->(:Context)`
- `(:JSFunction)-[:RETURNS_TYPE]->(:Type|Interface)`

## 2. Handling React Components, Hooks, and JSX

### Component Schema

```cypher
// Functional Component
(:Component {
  name: String,
  full_name: String,  // module.ComponentName
  type: 'functional',
  exported: Boolean,
  memo: Boolean,
  forward_ref: Boolean,
  async: Boolean  // For RSC
})

// Props Type
(:Props {
  component_full_name: String,
  type: 'interface' | 'type' | 'inline',
  properties: [String],  // List of prop names
  required_props: [String],
  optional_props: [String]
})
```

### Hook Storage

```cypher
(:Hook {
  name: String,
  custom: Boolean,
  dependencies: [String],  // For useEffect, useMemo, etc.
  rules: [String]  // Hook rules/constraints
})
```

### JSX Representation

Store JSX as metadata on Component nodes rather than separate nodes:
- `jsx_elements_used`: Array of JSX elements used
- `conditional_renders`: Boolean indicating conditional rendering
- `fragment_usage`: Boolean for React.Fragment usage

## 3. Type Information and Generics

### Type Storage Strategy

```cypher
// Interface with generics
(:Interface {
  name: String,
  full_name: String,
  generics: [String],  // e.g., ['T', 'K extends keyof T']
  generic_constraints: Map,  // { T: 'extends BaseType' }
  properties: [String],
  methods: [String]
})

// Type alias
(:Type {
  name: String,
  full_name: String,
  definition: String,  // Raw type definition
  generics: [String],
  is_union: Boolean,
  is_intersection: Boolean,
  union_types: [String],  // For union types
  referenced_types: [String]
})

// Generic parameter
(:Generic {
  name: String,
  constraint: String,  // e.g., 'extends React.Component'
  default_type: String
})
```

### Relationships for Generics

- `(:Interface|Type|JSFunction)-[:HAS_GENERIC]->(:Generic)`
- `(:Generic)-[:CONSTRAINS_TO]->(:Type|Interface)`
- `(:Type)-[:INSTANTIATES_GENERIC]->(:Generic)`

## 4. Performance Considerations

### Indexing Strategy

```cypher
// Unique constraints (automatically indexed)
CREATE CONSTRAINT FOR (c:Component) REQUIRE c.full_name IS UNIQUE;
CREATE CONSTRAINT FOR (i:Interface) REQUIRE i.full_name IS UNIQUE;
CREATE CONSTRAINT FOR (t:Type) REQUIRE t.full_name IS UNIQUE;
CREATE CONSTRAINT FOR (f:JSFunction) REQUIRE f.full_name IS UNIQUE;
CREATE CONSTRAINT FOR (m:Module) REQUIRE m.path IS UNIQUE;
CREATE CONSTRAINT FOR (f:File) REQUIRE f.path IS UNIQUE;

// Additional indexes for query performance
CREATE INDEX FOR (c:Component) ON (c.name);
CREATE INDEX FOR (i:Interface) ON (i.name);
CREATE INDEX FOR (h:Hook) ON (h.name);
CREATE INDEX FOR (f:JSFunction) ON (f.name);
CREATE INDEX FOR (c:JSClass) ON (c.name);
CREATE INDEX FOR (f:File) ON (f.module);
CREATE INDEX FOR (c:Component) ON (c.exported);
```

### Query Optimization Patterns

1. **Use indexed properties in WHERE clauses**
   ```cypher
   // Good: Uses indexed full_name
   MATCH (c:Component {full_name: $fullName})
   
   // Avoid: Non-indexed property
   MATCH (c:Component) WHERE c.some_property = $value
   ```

2. **Limit search scope with labels**
   ```cypher
   // Good: Specific label
   MATCH (c:Component)-[:USES_HOOK]->(h:Hook)
   
   // Avoid: Generic node search
   MATCH (n)-[:USES_HOOK]->(h)
   ```

3. **Use relationship directions**
   ```cypher
   // Good: Directed relationship
   MATCH (c:Component)-[:IMPORTS_FROM]->(m:Module)
   
   // Avoid: Undirected
   MATCH (c:Component)-[:IMPORTS_FROM]-(m:Module)
   ```

### Batch Operations

For repository parsing, use batch operations:

```cypher
UNWIND $components AS comp
MATCH (f:File {path: comp.file_path})
MERGE (c:Component {full_name: comp.full_name})
SET c += comp.properties
MERGE (f)-[:DEFINES]->(c)
```

## 5. AST Metadata Storage

### AST Node Properties

Store essential AST information without full AST:

```cypher
(:JSFunction {
  // Identity
  name: String,
  full_name: String,
  
  // AST metadata
  start_line: Integer,
  end_line: Integer,
  start_column: Integer,
  end_column: Integer,
  
  // Function characteristics
  async: Boolean,
  generator: Boolean,
  arrow_function: Boolean,
  expression: Boolean,
  
  // Complexity metrics
  cyclomatic_complexity: Integer,
  parameter_count: Integer,
  line_count: Integer,
  
  // Dependencies
  calls: [String],  // Function names called
  external_deps: [String]  // External modules used
})
```

### Storing Code Snippets

For hallucination detection, store relevant code:

```cypher
(:JSFunction {
  signature: String,  // Just the function signature
  body_hash: String,  // Hash of function body for comparison
  has_jsx: Boolean,
  has_async_await: Boolean,
  has_try_catch: Boolean
})
```

## 6. Best Practices for Hallucination Detection

### Query Patterns for Validation

1. **Component Existence Check**
   ```cypher
   MATCH (c:Component {name: $componentName})
   OPTIONAL MATCH (c)-[:ACCEPTS_PROPS]->(p:Props)
   RETURN c, p.properties AS validProps
   ```

2. **Import Validation**
   ```cypher
   MATCH (m:Module {path: $modulePath})
   OPTIONAL MATCH (m)-[:EXPORTS]->(e)
   RETURN collect(e.name) AS availableExports
   ```

3. **Type Compatibility Check**
   ```cypher
   MATCH (t:Type {name: $typeName})
   OPTIONAL MATCH (t)-[:REFERENCES]->(ref)
   OPTIONAL MATCH (t)-[:HAS_GENERIC]->(g:Generic)
   RETURN t, collect(ref), collect(g)
   ```

### Confidence Scoring

Store validation metadata:

```cypher
(:ValidationCache {
  element_type: String,
  element_name: String,
  last_validated: DateTime,
  confidence_score: Float,
  validation_details: Map
})
```

## 7. Schema Evolution Strategy

### Versioning

```cypher
(:SchemaVersion {
  version: String,
  created_at: DateTime,
  migration_notes: String
})
```

### Migration Patterns

1. **Adding new node types**: No migration needed
2. **Adding properties**: Use `SET` with defaults
3. **Changing relationships**: Create new, migrate, delete old

## 8. Recommended Implementation

### Phase 1: Core Schema
- Repository, File, Module nodes
- Basic Component, Interface, Type nodes
- Import/export relationships

### Phase 2: Type System
- Generic support
- Type references
- Interface inheritance

### Phase 3: React Features
- Hook relationships
- Props validation
- Component composition

### Phase 4: Advanced Features
- Call graphs
- Complexity metrics
- AST metadata

## Conclusion

This schema design balances:
- **Completeness**: Captures all essential TypeScript/JavaScript/React constructs
- **Performance**: Optimized for common queries with proper indexing
- **Flexibility**: Extensible for future language features
- **Practicality**: Focused on hallucination detection use cases

The design follows GitHub's stack graphs approach while adapting to Neo4j's property graph model, ensuring efficient code intelligence operations at scale.