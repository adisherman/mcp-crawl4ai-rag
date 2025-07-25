"""
Connection Pool Manager for Neo4j Database

Manages database connections with proper pooling, health checks, and automatic recovery.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

from error_handler import ErrorHandler, ErrorCategory, with_error_handling

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for connection pool"""
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    connection_resets: int = 0


class Neo4jConnectionPool:
    """
    Manages Neo4j connections with pooling, health checks, and recovery.
    
    Features:
    - Connection pooling with configurable limits
    - Automatic reconnection on failure
    - Health checks with configurable intervals
    - Query retry with backoff
    - Connection statistics and monitoring
    """
    
    def __init__(self, uri: str, user: str, password: str,
                 max_connection_lifetime: int = 3600,
                 max_connection_pool_size: int = 50,
                 connection_acquisition_timeout: int = 60,
                 health_check_interval: int = 30):
        """
        Initialize connection pool
        
        Args:
            uri: Neo4j connection URI
            user: Username
            password: Password
            max_connection_lifetime: Maximum connection lifetime in seconds
            max_connection_pool_size: Maximum number of connections in pool
            connection_acquisition_timeout: Timeout for acquiring connection
            health_check_interval: Interval between health checks in seconds
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.config = {
            'max_connection_lifetime': max_connection_lifetime,
            'max_connection_pool_size': max_connection_pool_size,
            'connection_acquisition_timeout': connection_acquisition_timeout,
            'connection_timeout': 30.0,
            'keep_alive': True
        }
        
        self.driver: Optional[AsyncDriver] = None
        self.stats = ConnectionStats()
        self.health_check_interval = health_check_interval
        self.last_health_check = datetime.now()
        self.is_healthy = False
        self.error_handler = ErrorHandler()
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        self._health_check_task = None
        
    async def connect(self) -> bool:
        """
        Establish connection to Neo4j
        
        Returns:
            True if connection successful
        """
        async with self._lock:
            if self.driver:
                logger.info("Connection pool already initialized")
                return True
                
            try:
                logger.info(f"Creating Neo4j connection pool to {self.uri}")
                self.driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    **self.config
                )
                
                # Verify connection
                await self.driver.verify_connectivity()
                
                self.is_healthy = True
                self.stats.total_connections += 1
                logger.info("Neo4j connection pool created successfully")
                
                # Start health check task
                if not self._health_check_task:
                    self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                self.stats.failed_connections += 1
                self.stats.last_error = str(e)
                self.stats.last_error_time = datetime.now()
                
                # Try to recover
                context = {
                    'operation': self.connect,
                    'reconnect': self._reconnect
                }
                
                result = await self.error_handler.handle_error(e, context)
                return bool(result)
                
    async def _reconnect(self) -> bool:
        """Reconnect to database"""
        logger.info("Attempting to reconnect to Neo4j")
        
        # Close existing connection
        if self.driver:
            try:
                await self.driver.close()
            except:
                pass
            self.driver = None
            
        # Wait before reconnecting
        await asyncio.sleep(5)
        
        # Reset state
        self.is_healthy = False
        self.stats.connection_resets += 1
        
        # Try to connect again
        return await self.connect()
        
    async def close(self):
        """Close connection pool"""
        async with self._lock:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                    
            if self.driver:
                logger.info("Closing Neo4j connection pool")
                await self.driver.close()
                self.driver = None
                self.is_healthy = False
                
    @asynccontextmanager
    async def get_session(self, database: Optional[str] = None):
        """
        Get a database session from the pool
        
        Args:
            database: Database name (None for default)
            
        Yields:
            Neo4j session
        """
        if not self.driver:
            await self.connect()
            
        if not self.is_healthy:
            logger.warning("Connection pool unhealthy, attempting recovery")
            await self._reconnect()
            
        session = None
        try:
            session = self.driver.session(database=database)
            self.stats.active_connections += 1
            yield session
            
        except (ServiceUnavailable, SessionExpired) as e:
            logger.error(f"Session error: {e}")
            self.stats.failed_queries += 1
            
            # Mark as unhealthy and try to recover
            self.is_healthy = False
            await self._reconnect()
            
            # Retry with new session
            if self.driver:
                session = self.driver.session(database=database)
                yield session
            else:
                raise
                
        finally:
            if session:
                await session.close()
                self.stats.active_connections -= 1
                
    @with_error_handling(ErrorCategory.DATABASE)
    async def execute_query(self, query: str, parameters: Optional[Dict] = None,
                          database: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute a query with automatic retry and error handling
        
        Args:
            query: Cypher query
            parameters: Query parameters
            database: Database name
            
        Returns:
            Query results
        """
        self.stats.total_queries += 1
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with self.get_session(database) as session:
                    result = await session.run(query, parameters or {})
                    records = [dict(record) async for record in result]
                    return records
                    
            except TransientError as e:
                logger.warning(f"Transient error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    self.stats.failed_queries += 1
                    raise
                    
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                self.stats.failed_queries += 1
                self.stats.last_error = str(e)
                self.stats.last_error_time = datetime.now()
                raise
                
    async def execute_transaction(self, transaction_func, database: Optional[str] = None,
                                max_retry_time: int = 30):
        """
        Execute a transaction with automatic retry
        
        Args:
            transaction_func: Async function to execute in transaction
            database: Database name
            max_retry_time: Maximum time to retry in seconds
            
        Returns:
            Transaction result
        """
        async with self.get_session(database) as session:
            return await session.execute_write(
                transaction_func,
                max_retry_time=max_retry_time
            )
            
    async def health_check(self) -> bool:
        """
        Perform health check on connection
        
        Returns:
            True if healthy
        """
        if not self.driver:
            return False
            
        try:
            await self.driver.verify_connectivity()
            
            # Run a simple query
            async with self.get_session() as session:
                result = await session.run("RETURN 1 as n")
                record = await result.single()
                
                if record and record["n"] == 1:
                    self.is_healthy = True
                    return True
                    
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            
        return False
        
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not await self.health_check():
                    logger.warning("Health check failed, attempting recovery")
                    await self._reconnect()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'total_connections': self.stats.total_connections,
            'active_connections': self.stats.active_connections,
            'failed_connections': self.stats.failed_connections,
            'total_queries': self.stats.total_queries,
            'failed_queries': self.stats.failed_queries,
            'query_success_rate': self._calculate_success_rate(),
            'connection_resets': self.stats.connection_resets,
            'is_healthy': self.is_healthy,
            'last_error': self.stats.last_error,
            'last_error_time': self.stats.last_error_time.isoformat() if self.stats.last_error_time else None
        }
        
    def _calculate_success_rate(self) -> float:
        """Calculate query success rate"""
        if self.stats.total_queries == 0:
            return 100.0
            
        successful = self.stats.total_queries - self.stats.failed_queries
        return (successful / self.stats.total_queries) * 100
        
    async def optimize_pool(self):
        """Optimize connection pool based on usage patterns"""
        stats = self.get_stats()
        
        # Adjust pool size based on active connections
        avg_active = self.stats.active_connections
        current_max = self.config['max_connection_pool_size']
        
        if avg_active > current_max * 0.8:
            # Increase pool size
            new_max = min(current_max * 1.5, 100)
            logger.info(f"Increasing pool size from {current_max} to {new_max}")
            self.config['max_connection_pool_size'] = int(new_max)
            
            # Recreate driver with new config
            await self._reconnect()
            
        elif avg_active < current_max * 0.2 and current_max > 10:
            # Decrease pool size
            new_max = max(current_max * 0.5, 10)
            logger.info(f"Decreasing pool size from {current_max} to {new_max}")
            self.config['max_connection_pool_size'] = int(new_max)
            
            # Recreate driver with new config
            await self._reconnect()


class ConnectionPoolManager:
    """Manages multiple connection pools for different databases"""
    
    def __init__(self):
        self.pools: Dict[str, Neo4jConnectionPool] = {}
        self._lock = asyncio.Lock()
        
    async def get_pool(self, name: str, uri: str, user: str, password: str,
                      **kwargs) -> Neo4jConnectionPool:
        """
        Get or create a connection pool
        
        Args:
            name: Pool name
            uri: Database URI
            user: Username
            password: Password
            **kwargs: Additional pool configuration
            
        Returns:
            Connection pool instance
        """
        async with self._lock:
            if name not in self.pools:
                pool = Neo4jConnectionPool(uri, user, password, **kwargs)
                await pool.connect()
                self.pools[name] = pool
                
            return self.pools[name]
            
    async def close_all(self):
        """Close all connection pools"""
        async with self._lock:
            for name, pool in self.pools.items():
                logger.info(f"Closing connection pool: {name}")
                await pool.close()
                
            self.pools.clear()
            
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools"""
        return {
            name: pool.get_stats()
            for name, pool in self.pools.items()
        }


# Global connection pool manager
_pool_manager = ConnectionPoolManager()

async def get_connection_pool(name: str = "default", **kwargs) -> Neo4jConnectionPool:
    """Get a connection pool by name"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    uri = kwargs.get('uri', os.getenv('NEO4J_URI', 'bolt://localhost:7687'))
    user = kwargs.get('user', os.getenv('NEO4J_USER', 'neo4j'))
    password = kwargs.get('password', os.getenv('NEO4J_PASSWORD', 'password'))
    
    return await _pool_manager.get_pool(name, uri, user, password, **kwargs)


# Context manager for automatic connection handling
@asynccontextmanager
async def neo4j_connection(pool_name: str = "default", **kwargs):
    """
    Context manager for Neo4j connections
    
    Usage:
        async with neo4j_connection() as pool:
            results = await pool.execute_query("MATCH (n) RETURN n LIMIT 1")
    """
    pool = await get_connection_pool(pool_name, **kwargs)
    try:
        yield pool
    finally:
        # Pool is managed globally, so we don't close it here
        pass