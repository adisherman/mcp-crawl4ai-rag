# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Crawl4AI RAG MCP Server - a Model Context Protocol server that combines web crawling (via Crawl4AI) with RAG functionality using Supabase vector database and Neo4j knowledge graphs. It's designed to give AI coding assistants semantic search over crawled documentation and AI hallucination detection capabilities.

## Prerequisites

- Python 3.12+ (if running without Docker)
- Docker/Docker Desktop (for container deployment)
- Supabase account and project
- OpenAI API key
- Neo4j (optional, for knowledge graph functionality)

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
# Parse a GitHub repository into knowledge graph
python knowledge_graphs/repo_parser.py [repo-name] [--branch branch-name]

# Check AI-generated script for hallucinations
python knowledge_graphs/ai_hallucination_detector.py [script_path]

# Query the knowledge graph interactively
python knowledge_graphs/query_neo4j.py
```

**Note**: Knowledge graph implementation isn't fully compatible with Docker yet. Recommend running directly through uv if using hallucination detection within the MCP server. When adding GitHub repositories, ensure the URL ends with .git (e.g., https://github.com/pydantic/pydantic-ai.git).

## Architecture

### Core Components

1. **MCP Server (src/crawl4ai_mcp.py)**: FastMCP-based server providing tools for crawling, searching, and knowledge graph operations. Supports both SSE and stdio transport modes.

2. **Utilities (src/utils.py)**: Handles Supabase operations, document chunking, embedding generation, and search functionality (vector and hybrid).

3. **Knowledge Graph System (knowledge_graphs/)**: 
   - Repository parser for analyzing GitHub repos
   - Script analyzer using AST for Python code structure
   - Validator for checking AI-generated code
   - Reporter for hallucination detection with confidence scores

### Database Schema

The project uses PostgreSQL with pgvector extension:
- `sources`: Domain/source metadata
- `crawled_pages`: Documentation chunks with embeddings
- `code_examples`: Extracted code examples with summaries

**Setup**: Before first use, run the contents of `crawled_pages.sql` in Supabase SQL Editor to create necessary tables and functions.

### RAG Strategies

Configure via environment variables:
- `USE_CONTEXTUAL_EMBEDDINGS`: Enriches chunks with document context using LLM calls (configured via MODEL_CHOICE)
- `USE_HYBRID_SEARCH`: Combines vector and keyword search (no additional API costs)
- `USE_AGENTIC_RAG`: Extracts code blocks ≥300 characters, generates summaries, enables `search_code_examples` tool
- `USE_RERANKING`: Uses local cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`), adds ~100-200ms to queries
- `USE_KNOWLEDGE_GRAPH`: Enables AI hallucination detection (requires repositories to be pre-indexed)

## Key Configuration

All configuration is managed through environment variables in `.env`:
- API keys: `OPENAI_API_KEY`
- Database: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- Neo4j: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Server: `HOST`, `PORT`, `TRANSPORT`

## MCP Client Integration

### Claude Code
```bash
claude mcp add-json crawl4ai-rag '{"type":"http","url":"http://localhost:8051/sse"}' --scope user
```

### Docker Networking
When the MCP client runs in a different container (e.g., n8n), use `host.docker.internal` instead of `localhost`.

### Windsurf Configuration
Use `serverUrl` instead of `url` in the MCP configuration.

## Performance Considerations

- **Contextual embeddings**: Slows indexing due to LLM calls per chunk
- **Agentic RAG**: Significantly slows crawling due to code extraction/summarization
- **Knowledge graph parsing**: Can be slow for large codebases
- **Reranking**: Adds ~100-200ms to search queries

## Important Implementation Notes

1. When modifying crawling behavior, the main logic is in `crawl_single_page()` and `smart_crawl_url()` functions in src/crawl4ai_mcp.py

2. Search functionality is modular - each RAG strategy can be toggled independently. The main search logic is in `perform_rag_query()` in src/utils.py

3. Knowledge graph operations require Neo4j to be running. The graph schema uses nodes for Repositories, Files, Classes, Functions, and Methods with relationships like CONTAINS, DEFINES, IMPORTS, etc.

4. The project uses OpenAI embeddings (text-embedding-3-small) by default. Embedding generation happens in `generate_embeddings()` in src/utils.py

5. When adding new MCP tools, follow the pattern in src/crawl4ai_mcp.py using the `@server.tool()` decorator

6. For testing hallucination detection, use the provided test scripts in knowledge_graphs/test_scripts/