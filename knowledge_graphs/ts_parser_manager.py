"""
TypeScript Parser Service Manager

Manages the TypeScript parser service with health checks, automatic restart,
and graceful error handling for the MCP server integration.
"""

import asyncio
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

from ts_parser_client import TypeScriptParserService

logger = logging.getLogger(__name__)


class TypeScriptParserManager:
    """
    Manages TypeScript parser service lifecycle with health monitoring
    and automatic restart capabilities.
    """
    
    def __init__(self, 
                 port: int = 3456,
                 health_check_interval: int = 30,
                 max_restart_attempts: int = 3):
        """
        Initialize the TypeScript parser manager
        
        Args:
            port: Port for the parser service
            health_check_interval: Seconds between health checks
            max_restart_attempts: Maximum restart attempts before giving up
        """
        self.port = port
        self.health_check_interval = health_check_interval
        self.max_restart_attempts = max_restart_attempts
        
        self.service: Optional[TypeScriptParserService] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.restart_count = 0
        self.last_restart_time = None
        self.is_running = False
        
    async def start(self) -> bool:
        """
        Start the TypeScript parser service with health monitoring
        
        Returns:
            True if service started successfully
        """
        try:
            logger.info("Starting TypeScript parser manager...")
            
            # Create service instance
            self.service = TypeScriptParserService(port=self.port)
            
            # Start the service
            if not await self.service.start():
                logger.error("Failed to start TypeScript parser service")
                return False
                
            self.is_running = True
            self.restart_count = 0
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_monitor())
            
            logger.info("TypeScript parser manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting TypeScript parser manager: {e}")
            return False
            
    async def stop(self):
        """Stop the TypeScript parser service and health monitoring"""
        logger.info("Stopping TypeScript parser manager...")
        
        self.is_running = False
        
        # Cancel health monitoring
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
                
        # Stop the service
        if self.service:
            try:
                await self.service.stop()
                logger.info("TypeScript parser service stopped")
            except Exception as e:
                logger.error(f"Error stopping TypeScript parser service: {e}")
                
    async def _health_monitor(self):
        """Monitor service health and restart if necessary"""
        while self.is_running:
            try:
                # Wait for the health check interval
                await asyncio.sleep(self.health_check_interval)
                
                if not self.is_running:
                    break
                    
                # Check service health
                if self.service and self.service.client:
                    is_healthy = await self.service.client.health_check()
                    
                    if not is_healthy:
                        logger.warning("TypeScript parser service health check failed")
                        await self._handle_unhealthy_service()
                    else:
                        # Reset restart count on successful health check
                        if self.restart_count > 0:
                            logger.info("TypeScript parser service recovered")
                            self.restart_count = 0
                            
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                
    async def _handle_unhealthy_service(self):
        """Handle unhealthy service with restart logic"""
        # Check if we've exceeded max restart attempts
        if self.restart_count >= self.max_restart_attempts:
            logger.error(f"TypeScript parser service failed after {self.max_restart_attempts} restart attempts")
            self.is_running = False
            return
            
        # Check if we're restarting too frequently (within 5 minutes)
        if self.last_restart_time:
            time_since_restart = datetime.now() - self.last_restart_time
            if time_since_restart < timedelta(minutes=5):
                wait_time = 300 - time_since_restart.total_seconds()
                logger.info(f"Waiting {wait_time:.0f}s before restart attempt")
                await asyncio.sleep(wait_time)
                
        # Attempt restart
        logger.info(f"Attempting to restart TypeScript parser service (attempt {self.restart_count + 1}/{self.max_restart_attempts})")
        
        # Stop the current service
        if self.service:
            try:
                await self.service.stop()
            except Exception as e:
                logger.error(f"Error stopping service during restart: {e}")
                
        # Wait a moment before restarting
        await asyncio.sleep(2)
        
        # Start the service again
        self.service = TypeScriptParserService(port=self.port)
        if await self.service.start():
            logger.info("TypeScript parser service restarted successfully")
            self.restart_count += 1
            self.last_restart_time = datetime.now()
        else:
            logger.error("Failed to restart TypeScript parser service")
            self.restart_count = self.max_restart_attempts  # Prevent further attempts
            
    async def get_client(self):
        """
        Get the TypeScript parser client
        
        Returns:
            TypeScriptParserClient instance or None if service not running
        """
        if self.service and self.is_running:
            return self.service.client
        return None
        
    async def ensure_healthy(self) -> bool:
        """
        Ensure the service is healthy, attempting restart if needed
        
        Returns:
            True if service is healthy or successfully restarted
        """
        if not self.service or not self.is_running:
            return False
            
        # Check health
        is_healthy = await self.service.client.health_check()
        
        if not is_healthy:
            logger.warning("Service unhealthy, attempting immediate restart")
            await self._handle_unhealthy_service()
            
            # Check if restart was successful
            if self.service and self.is_running:
                return await self.service.client.health_check()
                
        return is_healthy
        
    def get_status(self) -> dict:
        """
        Get current status of the TypeScript parser service
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.is_running,
            "port": self.port,
            "restart_count": self.restart_count,
            "last_restart": self.last_restart_time.isoformat() if self.last_restart_time else None,
            "health_check_interval": self.health_check_interval,
            "max_restart_attempts": self.max_restart_attempts
        }


# Example usage
if __name__ == "__main__":
    async def test_manager():
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create and start manager
        manager = TypeScriptParserManager(
            health_check_interval=10,  # Check every 10 seconds for testing
            max_restart_attempts=3
        )
        
        if await manager.start():
            logger.info("Manager started successfully")
            
            # Get status
            status = manager.get_status()
            logger.info(f"Status: {status}")
            
            # Test parsing
            client = await manager.get_client()
            if client:
                result = await client.parse_file(
                    "const x: number = 42;",
                    "test.ts"
                )
                logger.info(f"Parse result: {result}")
                
            # Simulate running for a while
            await asyncio.sleep(30)
            
            # Stop manager
            await manager.stop()
        else:
            logger.error("Failed to start manager")
            
    asyncio.run(test_manager())