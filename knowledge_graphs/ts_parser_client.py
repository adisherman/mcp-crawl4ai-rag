"""
TypeScript Parser Client

Python client for communicating with the TypeScript parser service.
Provides a clean interface for parsing TypeScript/JavaScript files.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import aiohttp
from pathlib import Path
import hashlib
import time
import os

# Import setup utility
from typescript_parser_setup import setup_typescript_parser, TypeScriptParserSetup

logger = logging.getLogger(__name__)


class TypeScriptParserClient:
    """Client for TypeScript parser service"""
    
    def __init__(self, base_url: str = "http://localhost:3456", timeout: int = 30):
        """
        Initialize the parser client
        
        Args:
            base_url: Base URL of the parser service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._health_check_cache = {"time": 0, "healthy": False}
        self._parse_cache: Dict[str, Dict[str, Any]] = {}  # Cache parsed results
        
    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
            
    async def ensure_session(self):
        """Ensure we have an active session"""
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
            
    async def health_check(self) -> bool:
        """
        Check if the parser service is healthy
        
        Returns:
            True if service is healthy, False otherwise
        """
        # Cache health check for 5 seconds
        if time.time() - self._health_check_cache["time"] < 5:
            return self._health_check_cache["healthy"]
            
        try:
            await self.ensure_session()
            async with self._session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    healthy = data.get("status") == "healthy"
                    self._health_check_cache = {"time": time.time(), "healthy": healthy}
                    return healthy
                return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    async def get_info(self) -> Dict[str, Any]:
        """
        Get parser service information
        
        Returns:
            Service capabilities and version info
        """
        try:
            await self.ensure_session()
            async with self._session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.error(f"Failed to get service info: {e}")
            return {}
            
    async def parse_file(self, content: str, filename: str, 
                        use_cache: bool = True) -> Dict[str, Any]:
        """
        Parse a single TypeScript/JavaScript file
        
        Args:
            content: File content
            filename: Filename (used to determine parser mode)
            use_cache: Whether to use cached results
            
        Returns:
            Parsed AST information
        """
        # Generate cache key
        cache_key = hashlib.md5(f"{filename}:{content}".encode()).hexdigest()
        
        # Check cache
        if use_cache and cache_key in self._parse_cache:
            logger.debug(f"Using cached parse result for {filename}")
            return self._parse_cache[cache_key]
            
        try:
            await self.ensure_session()
            
            # Check service health first
            if not await self.health_check():
                raise RuntimeError("Parser service is not healthy")
                
            payload = {
                "content": content,
                "filename": filename
            }
            
            async with self._session.post(
                f"{self.base_url}/parse-file",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Cache successful result
                    if use_cache and not result.get("error"):
                        self._parse_cache[cache_key] = result
                        
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Parse error for {filename}: {error_text}")
                    return {
                        "error": f"HTTP {response.status}: {error_text}",
                        "filename": filename
                    }
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout parsing {filename}")
            return {
                "error": "Parse timeout",
                "filename": filename
            }
        except Exception as e:
            logger.error(f"Failed to parse {filename}: {e}")
            return {
                "error": str(e),
                "filename": filename
            }
            
    async def parse_batch(self, files: List[Tuple[str, str]], 
                         max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """
        Parse multiple files in batch
        
        Args:
            files: List of (content, filename) tuples
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of parsed results
        """
        # For small batches, use individual requests with concurrency control
        if len(files) <= max_concurrent:
            tasks = [
                self.parse_file(content, filename)
                for content, filename in files
            ]
            return await asyncio.gather(*tasks)
            
        # For larger batches, use the batch endpoint
        try:
            await self.ensure_session()
            
            # Check service health first
            if not await self.health_check():
                raise RuntimeError("Parser service is not healthy")
                
            payload = {
                "files": [
                    {"content": content, "filename": filename}
                    for content, filename in files
                ]
            }
            
            # Increase timeout for batch operations
            batch_timeout = aiohttp.ClientTimeout(total=self.timeout.total * 2)
            
            async with self._session.post(
                f"{self.base_url}/parse-batch",
                json=payload,
                timeout=batch_timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                else:
                    error_text = await response.text()
                    logger.error(f"Batch parse error: {error_text}")
                    # Return individual errors
                    return [
                        {
                            "error": f"Batch parse failed: {error_text}",
                            "filename": filename
                        }
                        for _, filename in files
                    ]
                    
        except Exception as e:
            logger.error(f"Batch parse failed: {e}")
            # Return individual errors
            return [
                {
                    "error": f"Batch parse failed: {str(e)}",
                    "filename": filename
                }
                for _, filename in files
            ]
            
    def clear_cache(self):
        """Clear the parse cache"""
        self._parse_cache.clear()
        logger.info("Parse cache cleared")
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_files": len(self._parse_cache),
            "cache_size_bytes": sum(
                len(json.dumps(v)) for v in self._parse_cache.values()
            )
        }


class TypeScriptParserService:
    """Manager for the TypeScript parser service lifecycle"""
    
    def __init__(self, port: int = 3456):
        """
        Initialize the parser service manager
        
        Args:
            port: Port to run the service on
        """
        self.port = port
        self.process: Optional[asyncio.subprocess.Process] = None
        self.client = TypeScriptParserClient(f"http://localhost:{port}")
        
    async def start(self) -> bool:
        """
        Start the parser service
        
        Returns:
            True if service started successfully
        """
        if self.process and self.process.returncode is None:
            logger.info("Parser service already running")
            return True
            
        # Ensure dependencies are installed
        setup = TypeScriptParserSetup()
        if not setup.check_node_installed():
            logger.error("Node.js is not installed. Please install Node.js 14+ first.")
            logger.info(setup.get_install_instructions())
            return False
            
        if not setup.check_dependencies_installed():
            logger.info("Installing TypeScript parser dependencies...")
            if not setup.setup():
                logger.error("Failed to setup TypeScript parser dependencies")
                return False
                
        try:
            # Start the Node.js service
            service_path = Path(__file__).parent / "typescript_parser_service.js"
            
            self.process = await asyncio.create_subprocess_exec(
                "node",
                str(service_path),
                env={
                    **os.environ,
                    "PARSER_PORT": str(self.port),
                    "NODE_ENV": "production"
                },
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for service to be ready
            for _ in range(30):  # 30 second timeout
                if await self.client.health_check():
                    logger.info(f"Parser service started on port {self.port}")
                    return True
                await asyncio.sleep(1)
                
            logger.error("Parser service failed to start within timeout")
            await self.stop()
            return False
            
        except Exception as e:
            logger.error(f"Failed to start parser service: {e}")
            return False
            
    async def stop(self):
        """Stop the parser service"""
        if self.process and self.process.returncode is None:
            logger.info("Stopping parser service...")
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                logger.warning("Parser service didn't stop gracefully, killing...")
                self.process.kill()
                await self.process.wait()
            logger.info("Parser service stopped")
            
    async def restart(self) -> bool:
        """
        Restart the parser service
        
        Returns:
            True if service restarted successfully
        """
        await self.stop()
        return await self.start()
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        await self.client.__aenter__()
        return self.client
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        await self.stop()


# Convenience function for one-off parsing
async def parse_typescript_file(content: str, filename: str) -> Dict[str, Any]:
    """
    Parse a single TypeScript/JavaScript file
    
    Args:
        content: File content
        filename: Filename
        
    Returns:
        Parsed AST information
    """
    async with TypeScriptParserClient() as client:
        return await client.parse_file(content, filename)


# Example usage
if __name__ == "__main__":
    import os
    
    async def test_parser():
        # Test with service manager
        async with TypeScriptParserService() as client:
            # Test React component
            react_code = '''
            import React, { useState, useEffect } from 'react';
            
            interface Props {
                title: string;
                count?: number;
            }
            
            const MyComponent: React.FC<Props> = ({ title, count = 0 }) => {
                const [value, setValue] = useState(count);
                
                useEffect(() => {
                    console.log('Component mounted');
                }, []);
                
                return (
                    <div>
                        <h1>{title}</h1>
                        <p>Count: {value}</p>
                    </div>
                );
            };
            
            export default MyComponent;
            '''
            
            result = await client.parse_file(react_code, "MyComponent.tsx")
            print(json.dumps(result, indent=2))
            
    # Run the test
    asyncio.run(test_parser())