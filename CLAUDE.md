# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crawl4AI RAG MCP Server - A Model Context Protocol server combining web crawling (Crawl4AI) with RAG functionality using Supabase vector database and Neo4j knowledge graphs. Provides semantic search over crawled documentation and AI hallucination detection for Python, TypeScript, React, and Node.js code.

## Prerequisites

- Python 3.12+ (if running without Docker)
- Docker/Docker Desktop (for container deployment)
- Supabase account and project
- OpenAI API key
- Neo4j (optional, for knowledge graph functionality)
- Node.js 14+ (for TypeScript/JavaScript parsing)

## Development Commands

### Running the Server
```bash
# Direct execution with uv
uv run src/crawl4ai_mcp.py

# Docker build
docker build -t mcp/crawl4ai-rag --build-arg PORT=8051 .

# Docker run
docker run --env-file .env -p 8051:8051 mcp/crawl4ai-rag

# Initialize Crawl4AI (first time setup)
crawl4ai-setup
```

### Knowledge Graph Operations
```bash
# Parse a repository into knowledge graph (auto-detects language)
python knowledge_graphs/repo_parser.py [repo-name] [--branch branch-name]

# Check AI-generated script for hallucinations (supports Python/TypeScript)
python knowledge_graphs/unified_hallucination_detector.py [script_path]

# Query the knowledge graph interactively
python knowledge_graphs/query_neo4j.py
```

**Note**: Knowledge graph isn't fully compatible with Docker yet. Run directly through uv if using hallucination detection. When adding repositories, ensure URL ends with .git.

## Architecture

### Core Components

1. **MCP Server (src/crawl4ai_mcp.py)**: FastMCP server providing crawling, search, and knowledge graph tools. Supports SSE and stdio transport.

2. **Utilities (src/utils.py)**: Handles Supabase operations, chunking, embeddings, and search (vector/hybrid).

3. **Knowledge Graph System (knowledge_graphs/)**: 
   - **repo_parser.py**: Universal parser with language detection
   - **parse_repo_into_neo4j.py**: Python repository parser
   - **ts_repo_parser.py**: TypeScript/JavaScript repository parser
   - **ai_script_analyzer.py**: Python script analyzer
   - **ts_script_analyzer.py**: TypeScript/React script analyzer
   - **knowledge_graph_validator.py**: Python code validator
   - **ts_knowledge_graph_validator.py**: TypeScript code validator
   - **unified_hallucination_detector.py**: Language-agnostic detector
   - **hallucination_reporter.py**: Multi-language reporting

### Database Schema

PostgreSQL with pgvector:
- `sources`: Domain/source metadata
- `crawled_pages`: Documentation chunks with embeddings
- `code_examples`: Extracted code with summaries

Neo4j schema extends across languages:
- **Python**: Repository, File, Class, Function, Method, Parameter
- **TypeScript**: Interface, Type, Enum, Namespace, Component, Hook, Props, Module, JSFunction, JSClass

**Setup**: Run `crawled_pages.sql` in Supabase SQL Editor before first use.

### Language Detection

The system auto-detects language based on:
- File extensions (.py, .ts, .tsx, .js, .jsx)
- Repository structure (package.json vs setup.py)
- Script content analysis

### RAG Strategies

Configure via environment variables:
- `USE_CONTEXTUAL_EMBEDDINGS`: Enriches chunks with context (requires MODEL_CHOICE)
- `USE_HYBRID_SEARCH`: Combines vector and keyword search
- `USE_AGENTIC_RAG`: Extracts and indexes code blocks ≥300 characters
- `USE_RERANKING`: Uses cross-encoder model
- `USE_KNOWLEDGE_GRAPH`: Enables hallucination detection

## Key Configuration

All in `.env`:
- API keys: `OPENAI_API_KEY`
- Database: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- Neo4j: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Server: `HOST`, `PORT`, `TRANSPORT`

## MCP Client Integration

### Claude Code
```bash
# Start server first
uv run src/crawl4ai_mcp.py

# In another terminal, add to Claude
claude mcp add-json crawl4ai-rag '{"type":"http","url":"http://localhost:8051/sse"}' --scope user
```

### Docker Networking
For MCP clients in containers, use `host.docker.internal` instead of `localhost`.

### Windsurf Configuration
Use `serverUrl` instead of `url` in the MCP configuration.

## TypeScript/React/Node.js Support

### Parsing Capabilities
- React components (functional and class-based)
- Hooks (custom and built-in)
- TypeScript interfaces, types, enums
- ES6+ modules and imports
- JSX syntax
- Async/await patterns

### Validation Rules
- Component existence and prop types
- Hook usage patterns
- Type/interface definitions
- Import validity
- Function signatures

### Example Usage
```bash
# Parse a TypeScript/React repository
python knowledge_graphs/repo_parser.py https://github.com/example/react-app.git

# Validate AI-generated React component
python knowledge_graphs/unified_hallucination_detector.py generated_component.tsx
```

## Performance Considerations

- **Contextual embeddings**: Slower indexing (LLM calls per chunk)
- **Agentic RAG**: Slower crawling (code extraction/summarization)
- **TypeScript parsing**: Uses esprima, may be slower for large codebases
- **Knowledge graph queries**: Complex validations may take 1-2 seconds
- **Reranking**: Adds ~100-200ms to searches

## Implementation Notes

1. **Crawling logic**: Main functions are `crawl_single_page()` and `smart_crawl_url()` in src/crawl4ai_mcp.py

2. **Search modularity**: Each RAG strategy toggles independently. Core logic in `perform_rag_query()` in src/utils.py

3. **Language routing**: `repo_parser.py` detects language and routes to appropriate parser. Unified detector follows same pattern.

4. **TypeScript AST**: Uses esprima for parsing. See `parse_with_esprima()` in ts_repo_parser.py for implementation details.

5. **Import handling**: Module imports use try/except for compatibility with both module and direct execution modes.

6. **MCP tools**: Use `@server.tool()` decorator pattern. Tools auto-detect language when applicable.

7. **Neo4j optimization**: Batch operations used for repository parsing. See `create_batch()` methods in parsers.

8. **Error handling**: TypeScript parser gracefully handles JSX and modern JS features that might fail in strict mode.

9. **Testing hallucination detection**: Use test scripts in knowledge_graphs/test_scripts/