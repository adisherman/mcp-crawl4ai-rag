#!/bin/bash
# Start the MCP server with proper environment

cd "$(dirname "$0")"
source .venv/bin/activate
export TRANSPORT=sse
export HOST=0.0.0.0
export PORT=8051

echo "Starting Crawl4AI RAG MCP Server..."
echo "Server will be available at: http://localhost:8051/sse"
echo ""

uv run src/crawl4ai_mcp.py