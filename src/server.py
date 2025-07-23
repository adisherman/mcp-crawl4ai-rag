"""MCP server entry point for Crawl4AI RAG"""

from .crawl4ai_mcp import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())