"""
AI Hallucination Detector

This module now redirects to the unified hallucination detector that supports
both Python and TypeScript/JavaScript code analysis.
"""

import asyncio
import sys
from unified_hallucination_detector import main

# Preserve backward compatibility by redirecting to the unified detector
if __name__ == "__main__":
    print("Note: This script now uses the unified hallucination detector that supports multiple languages.")
    print("Redirecting to unified detector...\n")
    asyncio.run(main())