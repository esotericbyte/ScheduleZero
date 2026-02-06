"""Local handler registry for Python functions/methods.

Allows registering handlers as local Python callables without ZMQ.
Useful for:
- Single-process deployments
- Testing without network overhead  
- Simple job handlers that don't need distribution
"""
from __future__ import annotations

import asyncio
import inspect
import threading
from datetime import datetime, UTC
from functools import partial
from typing import Any, Callable
from functools import wraps

from .logging_config import get_logger

logger = get_logger(__name__, component="LocalHandlerRegistry")


class LocalHandlerRegistry:
    """Registry for local Python function/method handlers."""
    
    def __init__(self):
        """Initialize the local handler registry."""
        self._handlers: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def register(
        self,
        handler_id: str,
        func: Callable,
        methods: list[str] | None = None
    ) -> bool:
        """Register a local Python function/method as a handler.
        
        Args:
            handler_id: Unique identifier for this handler
            func: The Python callable to register
            methods: List of method names (defaults to [func.__name__])
            
        Returns:
            True if registration successful
            
        Example:
            def my_handler(arg1, arg2):
                return arg1 + arg2
            
            registry = LocalHandlerRegistry()
            registry.register("math_handler", my_handler, ["add"])
        """
        if not callable(func):
            logger.error("Handler must be callable", handler_id=handler_id)
            return False
        
        if methods is None:
            methods = [func.__name__]
        
        with self._lock:
            now = datetime.now(UTC).isoformat()
            self._handlers[handler_id] = {
                'function': func,
                'methods': methods,
                'is_async': inspect.iscoroutinefunction(func),
                'registered_at': now,
                'last_updated': now,
                'status': 'Active',
                'type': 'local'
            }
        
        logger.info(
            "Registered local handler",
            handler_id=handler_id,
            methods=methods,
            is_async=inspect.iscoroutinefunction(func)
        )
        return True
    
    def unregister(self, handler_id: str) -> bool:
        """Unregister a local handler.
        
        Args:
            handler_id: The handler to remove
            
        Returns:
            True if handler was found and removed
        """
        with self._lock:
            if handler_id in self._handlers:
                del self._handlers[handler_id]
                logger.info("Unregistered local handler", handler_id=handler_id)
                return True
            else:
                logger.warning("Handler not found", handler_id=handler_id)
                return False
    
    async def execute(
        self,
        handler_id: str,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute a local handler method.
        
        Args:
            handler_id: The handler to call
            method: The method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from the handler function
            
        Raises:
            KeyError: If handler not found
            ValueError: If method not supported
            Exception: Any exception raised by the handler
        """
        with self._lock:
            if handler_id not in self._handlers:
                raise KeyError(f"Handler '{handler_id}' not found")
            
            handler_info = self._handlers[handler_id]
        
        if method not in handler_info['methods']:
            raise ValueError(
                f"Method '{method}' not in handler methods: {handler_info['methods']}"
            )
        
        func = handler_info['function']
        is_async = handler_info['is_async']
        
        logger.debug(
            "Executing local handler",
            handler_id=handler_id,
            method=method,
            is_async=is_async
        )
        
        try:
            if is_async:
                result = await func(*args, **kwargs)
            else:
                # Run sync function in executor to avoid blocking
                # Use partial to handle kwargs since run_in_executor doesn't support them
                loop = asyncio.get_running_loop()
                func_with_args = partial(func, *args, **kwargs)
                result = await loop.run_in_executor(None, func_with_args)
            
            logger.debug(
                "Local handler execution complete",
                handler_id=handler_id,
                method=method
            )
            return result
        
        except Exception as e:
            logger.error(
                f"Local handler execution failed: {e}",
                handler_id=handler_id,
                method=method,
                exc_info=True
            )
            raise
    
    def get_handler(self, handler_id: str) -> dict[str, Any] | None:
        """Get handler information.
        
        Args:
            handler_id: The handler to look up
            
        Returns:
            Handler info dict or None if not found
        """
        with self._lock:
            if handler_id in self._handlers:
                # Return copy without the function object
                info = self._handlers[handler_id].copy()
                info.pop('function', None)
                return info
            return None
    
    def get_all_handlers(self) -> list[dict[str, Any]]:
        """Get list of all local handlers.
        
        Returns:
            List of handler info dicts
        """
        handlers_list = []
        with self._lock:
            for handler_id, info in self._handlers.items():
                handler_dict = {
                    'id': handler_id,
                    'methods': info['methods'],
                    'is_async': info['is_async'],
                    'status': info.get('status', 'Active'),
                    'registered_at': info.get('registered_at'),
                    'last_updated': info.get('last_updated'),
                    'type': 'local'
                }
                handlers_list.append(handler_dict)
        return handlers_list


# Decorator for registering handlers
def local_handler(
    registry: LocalHandlerRegistry,
    handler_id: str | None = None,
    methods: list[str] | None = None
):
    """Decorator to register a function as a local handler.
    
    Args:
        registry: The LocalHandlerRegistry to register with
        handler_id: Unique ID (defaults to function name)
        methods: Method names (defaults to [function name])
        
    Example:
        registry = LocalHandlerRegistry()
        
        @local_handler(registry, handler_id="math_ops")
        def calculate_sum(a, b):
            return a + b
        
        # Now callable via:
        # await registry.execute("math_ops", "calculate_sum", 5, 10)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal handler_id, methods
        
        if handler_id is None:
            handler_id = func.__name__
        
        if methods is None:
            methods = [func.__name__]
        
        registry.register(handler_id, func, methods)
        
        # Return original function unchanged
        return func
    
    return decorator


# Global instance for convenient import
default_local_registry = LocalHandlerRegistry()


def register_local(
    handler_id: str | None = None,
    methods: list[str] | None = None
):
    """Decorator using default global registry.
    
    Example:
        from schedule_zero.local_handler_registry import register_local
        
        @register_local(handler_id="greeter")
        def say_hello(name: str) -> str:
            return f"Hello, {name}!"
    """
    return local_handler(default_local_registry, handler_id, methods)
