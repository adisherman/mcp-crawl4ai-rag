"""
Centralized Error Handler for TypeScript Hallucination Detection System

Provides comprehensive error handling, logging, recovery mechanisms, and monitoring
for all components of the system.
"""

import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from functools import wraps
import time
from collections import deque, defaultdict
import psutil
import aiofiles

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knowledge_graphs/error_handler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    PARSING = "parsing"
    DATABASE = "database"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    VALIDATION = "validation"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    CIRCUIT_BREAK = "circuit_break"
    FALLBACK = "fallback"
    SKIP = "skip"
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RECONNECT = "reconnect"
    NONE = "none"


class ErrorMetrics:
    """Track error metrics for monitoring"""
    
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.window_size = window_size
        self.errors: deque = deque()
        self.error_counts = defaultdict(lambda: defaultdict(int))
        self.recovery_success = defaultdict(int)
        self.recovery_failure = defaultdict(int)
        
    def record_error(self, category: ErrorCategory, severity: ErrorSeverity, error: Exception):
        """Record an error occurrence"""
        timestamp = datetime.now()
        self.errors.append({
            'timestamp': timestamp,
            'category': category.value,
            'severity': severity.value,
            'error_type': type(error).__name__,
            'message': str(error)
        })
        
        # Update counts
        self.error_counts[category.value][severity.value] += 1
        
        # Clean old entries
        self._clean_old_entries()
        
    def record_recovery(self, strategy: RecoveryStrategy, success: bool):
        """Record recovery attempt result"""
        if success:
            self.recovery_success[strategy.value] += 1
        else:
            self.recovery_failure[strategy.value] += 1
            
    def _clean_old_entries(self):
        """Remove entries older than window size"""
        cutoff = datetime.now() - timedelta(seconds=self.window_size)
        while self.errors and self.errors[0]['timestamp'] < cutoff:
            self.errors.popleft()
            
    def get_error_rate(self, category: Optional[ErrorCategory] = None) -> float:
        """Get error rate per minute"""
        self._clean_old_entries()
        
        if category:
            count = sum(1 for e in self.errors if e['category'] == category.value)
        else:
            count = len(self.errors)
            
        return count / (self.window_size / 60)  # Per minute
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        self._clean_old_entries()
        
        return {
            'total_errors': len(self.errors),
            'error_rate_per_minute': self.get_error_rate(),
            'errors_by_category': dict(self.error_counts),
            'recovery_success': dict(self.recovery_success),
            'recovery_failure': dict(self.recovery_failure),
            'recovery_success_rate': self._calculate_recovery_rate()
        }
        
    def _calculate_recovery_rate(self) -> float:
        """Calculate overall recovery success rate"""
        total_success = sum(self.recovery_success.values())
        total_failure = sum(self.recovery_failure.values())
        total = total_success + total_failure
        
        return (total_success / total) * 100 if total > 0 else 0


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            
    def can_attempt(self) -> bool:
        """Check if operation can be attempted"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                return True
            return False
            
        # half-open state
        return True


class ErrorHandler:
    """Centralized error handler with recovery mechanisms"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.metrics = ErrorMetrics()
        self.circuit_breakers = {}
        self.error_log_path = Path("knowledge_graphs/logs/errors")
        self.error_log_path.mkdir(parents=True, exist_ok=True)
        
        # Resource monitoring
        self.resource_monitor = ResourceMonitor()
        
        # Error recovery strategies
        self.recovery_strategies = {
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorCategory.DATABASE: RecoveryStrategy.RECONNECT,
            ErrorCategory.TIMEOUT: RecoveryStrategy.RETRY,
            ErrorCategory.RESOURCE: RecoveryStrategy.CIRCUIT_BREAK,
            ErrorCategory.PARSING: RecoveryStrategy.SKIP,
            ErrorCategory.FILESYSTEM: RecoveryStrategy.RETRY,
            ErrorCategory.VALIDATION: RecoveryStrategy.FALLBACK,
            ErrorCategory.CONFIGURATION: RecoveryStrategy.NONE,
            ErrorCategory.UNKNOWN: RecoveryStrategy.RETRY
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load error handler configuration"""
        default_config = {
            'max_retries': 3,
            'base_backoff': 1,
            'max_backoff': 60,
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60,
            'log_errors_to_file': True,
            'alert_on_critical': True,
            'resource_limits': {
                'max_memory_percent': 80,
                'max_cpu_percent': 90,
                'max_file_handles': 1000
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            default_config.update(user_config)
            
        return default_config
        
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and message"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Network errors
        if any(keyword in error_msg for keyword in ['connection', 'network', 'socket', 'dns']):
            return ErrorCategory.NETWORK
            
        # Database errors
        if any(keyword in error_msg for keyword in ['database', 'neo4j', 'query', 'cypher']):
            return ErrorCategory.DATABASE
            
        # Timeout errors
        if 'timeout' in error_msg or error_type == 'TimeoutError':
            return ErrorCategory.TIMEOUT
            
        # Resource errors
        if any(keyword in error_msg for keyword in ['memory', 'disk space', 'resource']):
            return ErrorCategory.RESOURCE
            
        # Parsing errors
        if any(keyword in error_msg for keyword in ['parse', 'syntax', 'ast']):
            return ErrorCategory.PARSING
            
        # Filesystem errors
        if any(keyword in error_msg for keyword in ['file', 'directory', 'path', 'permission']):
            return ErrorCategory.FILESYSTEM
            
        # Validation errors
        if any(keyword in error_msg for keyword in ['valid', 'schema', 'type']):
            return ErrorCategory.VALIDATION
            
        # Configuration errors
        if any(keyword in error_msg for keyword in ['config', 'setting', 'environment']):
            return ErrorCategory.CONFIGURATION
            
        return ErrorCategory.UNKNOWN
        
    def assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess the severity of an error"""
        # Critical errors
        if category in [ErrorCategory.DATABASE, ErrorCategory.RESOURCE]:
            if 'connection refused' in str(error).lower():
                return ErrorSeverity.CRITICAL
                
        # High severity
        if category == ErrorCategory.CONFIGURATION:
            return ErrorSeverity.HIGH
            
        # Medium severity
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
            
        # Low severity
        if category in [ErrorCategory.PARSING, ErrorCategory.VALIDATION]:
            return ErrorSeverity.LOW
            
        return ErrorSeverity.MEDIUM
        
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """
        Handle an error with appropriate recovery strategy
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            Recovery result if successful, None otherwise
        """
        category = self.categorize_error(error)
        severity = self.assess_severity(error, category)
        
        # Record metrics
        self.metrics.record_error(category, severity, error)
        
        # Log error
        await self._log_error(error, category, severity, context)
        
        # Check resource limits
        if not self.resource_monitor.check_resources():
            logger.warning("Resource limits exceeded, attempting cleanup")
            await self._cleanup_resources()
            
        # Get recovery strategy
        strategy = self.recovery_strategies.get(category, RecoveryStrategy.NONE)
        
        # Apply recovery strategy
        recovery_result = await self._apply_recovery_strategy(
            strategy, error, category, context
        )
        
        # Alert on critical errors
        if severity == ErrorSeverity.CRITICAL and self.config['alert_on_critical']:
            await self._send_alert(error, category, severity, context)
            
        return recovery_result
        
    async def _log_error(self, error: Exception, category: ErrorCategory, 
                        severity: ErrorSeverity, context: Dict[str, Any]):
        """Log error with full context"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'category': category.value,
            'severity': severity.value,
            'error_type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context
        }
        
        # Log to file if enabled
        if self.config['log_errors_to_file']:
            filename = f"{datetime.now().strftime('%Y%m%d')}_errors.json"
            filepath = self.error_log_path / filename
            
            async with aiofiles.open(filepath, 'a') as f:
                await f.write(json.dumps(error_entry) + '\n')
                
        # Log to standard logger
        logger.error(f"[{severity.value.upper()}] {category.value}: {error}")
        
    async def _apply_recovery_strategy(self, strategy: RecoveryStrategy, 
                                     error: Exception, category: ErrorCategory,
                                     context: Dict[str, Any]) -> Optional[Any]:
        """Apply the appropriate recovery strategy"""
        
        if strategy == RecoveryStrategy.NONE:
            return None
            
        circuit_breaker = self._get_circuit_breaker(category)
        
        if not circuit_breaker.can_attempt():
            logger.warning(f"Circuit breaker open for {category.value}")
            self.metrics.record_recovery(strategy, False)
            return None
            
        try:
            if strategy == RecoveryStrategy.RETRY:
                result = await self._retry_operation(context)
            elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                result = await self._retry_with_backoff(context)
            elif strategy == RecoveryStrategy.CIRCUIT_BREAK:
                result = await self._circuit_break_operation(context, circuit_breaker)
            elif strategy == RecoveryStrategy.FALLBACK:
                result = await self._fallback_operation(context)
            elif strategy == RecoveryStrategy.RECONNECT:
                result = await self._reconnect_service(context)
            elif strategy == RecoveryStrategy.RESTART_SERVICE:
                result = await self._restart_service(context)
            elif strategy == RecoveryStrategy.CLEAR_CACHE:
                result = await self._clear_cache(context)
            elif strategy == RecoveryStrategy.SKIP:
                result = await self._skip_operation(context)
            else:
                result = None
                
            if result is not None:
                circuit_breaker.record_success()
                self.metrics.record_recovery(strategy, True)
            else:
                circuit_breaker.record_failure()
                self.metrics.record_recovery(strategy, False)
                
            return result
            
        except Exception as e:
            logger.error(f"Recovery strategy {strategy.value} failed: {e}")
            circuit_breaker.record_failure()
            self.metrics.record_recovery(strategy, False)
            return None
            
    def _get_circuit_breaker(self, category: ErrorCategory) -> CircuitBreaker:
        """Get or create circuit breaker for category"""
        if category not in self.circuit_breakers:
            self.circuit_breakers[category] = CircuitBreaker(
                self.config['circuit_breaker_threshold'],
                self.config['circuit_breaker_timeout']
            )
        return self.circuit_breakers[category]
        
    async def _retry_operation(self, context: Dict[str, Any]) -> Optional[Any]:
        """Simple retry strategy"""
        operation = context.get('operation')
        if not operation:
            return None
            
        for attempt in range(self.config['max_retries']):
            try:
                logger.info(f"Retry attempt {attempt + 1}/{self.config['max_retries']}")
                return await operation()
            except Exception as e:
                if attempt == self.config['max_retries'] - 1:
                    raise
                await asyncio.sleep(1)
                
        return None
        
    async def _retry_with_backoff(self, context: Dict[str, Any]) -> Optional[Any]:
        """Retry with exponential backoff"""
        operation = context.get('operation')
        if not operation:
            return None
            
        backoff = self.config['base_backoff']
        
        for attempt in range(self.config['max_retries']):
            try:
                logger.info(f"Retry attempt {attempt + 1} with {backoff}s backoff")
                return await operation()
            except Exception as e:
                if attempt == self.config['max_retries'] - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config['max_backoff'])
                
        return None
        
    async def _circuit_break_operation(self, context: Dict[str, Any], 
                                     circuit_breaker: CircuitBreaker) -> Optional[Any]:
        """Circuit breaker pattern"""
        fallback = context.get('fallback')
        if fallback:
            logger.info("Using fallback due to circuit breaker")
            return await fallback()
        return None
        
    async def _fallback_operation(self, context: Dict[str, Any]) -> Optional[Any]:
        """Use fallback operation"""
        fallback = context.get('fallback')
        if fallback:
            logger.info("Using fallback operation")
            return await fallback()
        return None
        
    async def _reconnect_service(self, context: Dict[str, Any]) -> Optional[Any]:
        """Reconnect to a service"""
        reconnect = context.get('reconnect')
        if reconnect:
            logger.info("Attempting to reconnect service")
            return await reconnect()
        return None
        
    async def _restart_service(self, context: Dict[str, Any]) -> Optional[Any]:
        """Restart a service"""
        restart = context.get('restart')
        if restart:
            logger.info("Attempting to restart service")
            return await restart()
        return None
        
    async def _clear_cache(self, context: Dict[str, Any]) -> Optional[Any]:
        """Clear cache"""
        clear_cache = context.get('clear_cache')
        if clear_cache:
            logger.info("Clearing cache")
            return await clear_cache()
        return None
        
    async def _skip_operation(self, context: Dict[str, Any]) -> Optional[Any]:
        """Skip the failed operation"""
        logger.info("Skipping failed operation")
        return context.get('skip_value')
        
    async def _cleanup_resources(self):
        """Cleanup resources when limits are exceeded"""
        logger.info("Performing resource cleanup")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear any caches in context
        cleanup_callbacks = self.config.get('cleanup_callbacks', [])
        for callback in cleanup_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
                
    async def _send_alert(self, error: Exception, category: ErrorCategory,
                         severity: ErrorSeverity, context: Dict[str, Any]):
        """Send alert for critical errors"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity.value,
            'category': category.value,
            'error': str(error),
            'context': context
        }
        
        # Write to alert file
        alert_file = self.error_log_path / "critical_alerts.json"
        async with aiofiles.open(alert_file, 'a') as f:
            await f.write(json.dumps(alert_data) + '\n')
            
        logger.critical(f"CRITICAL ERROR: {category.value} - {error}")
        
    def get_metrics_report(self) -> Dict[str, Any]:
        """Get comprehensive metrics report"""
        return {
            'error_metrics': self.metrics.get_metrics(),
            'resource_metrics': self.resource_monitor.get_metrics(),
            'circuit_breakers': {
                cat.value: {
                    'state': cb.state,
                    'failure_count': cb.failure_count
                }
                for cat, cb in self.circuit_breakers.items()
            }
        }


class ResourceMonitor:
    """Monitor system resources"""
    
    def __init__(self):
        self.process = psutil.Process()
        
    def check_resources(self) -> bool:
        """Check if resources are within limits"""
        memory_percent = self.process.memory_percent()
        cpu_percent = self.process.cpu_percent(interval=0.1)
        open_files = len(self.process.open_files())
        
        if memory_percent > 80:
            logger.warning(f"High memory usage: {memory_percent}%")
            return False
            
        if cpu_percent > 90:
            logger.warning(f"High CPU usage: {cpu_percent}%")
            return False
            
        if open_files > 1000:
            logger.warning(f"Too many open files: {open_files}")
            return False
            
        return True
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics"""
        return {
            'memory_percent': self.process.memory_percent(),
            'cpu_percent': self.process.cpu_percent(interval=0.1),
            'open_files': len(self.process.open_files()),
            'threads': self.process.num_threads()
        }


# Decorator for automatic error handling
T = TypeVar('T')

def with_error_handling(category: Optional[ErrorCategory] = None):
    """Decorator for automatic error handling"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = ErrorHandler()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'operation': lambda: func(*args, **kwargs)
                }
                
                result = await handler.handle_error(e, context)
                if result is not None:
                    return result
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                }
                
                # For sync functions, we can't use async recovery
                cat = category or handler.categorize_error(e)
                severity = handler.assess_severity(e, cat)
                handler.metrics.record_error(cat, severity, e)
                
                logger.error(f"Error in {func.__name__}: {e}")
                raise
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# Global error handler instance
_global_handler = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler