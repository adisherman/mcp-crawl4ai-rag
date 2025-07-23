#!/usr/bin/env python3
"""
Direct entry point for the Crawl4AI RAG MCP server.
This file can be run directly without module imports.
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function
import crawl4ai_mcp
import asyncio

if __name__ == "__main__":
    asyncio.run(crawl4ai_mcp.main())