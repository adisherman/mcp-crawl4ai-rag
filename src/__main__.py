#!/usr/bin/env python3
"""Entry point for Crawl4AI RAG MCP Server when run as a module."""

from . import crawl4ai_mcp

if __name__ == "__main__":
    import asyncio
    asyncio.run(crawl4ai_mcp.main())