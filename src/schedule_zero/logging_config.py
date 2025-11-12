"""
Centralized logging configuration for ScheduleZero.

Provides consistent, structured logging across all components with:
- Component/class/method context in every log
- File, line number, and function name in every log
- Configurable log levels per module
- Performance tracing for frequent operations
- No print() statements - 100% logging
"""
import logging
import sys
import inspect
from pathlib import Path
from typing import Optional
from collections import defaultdict
from threading import Lock


class StructuredLogger:
    """
    Logger wrapper that automatically adds component context to all log messages.
    
    Usage:
        logger = StructuredLogger(__name__, component="ZMQServer", obj_id="reg-server-1")
        logger.info("message", method="start")
        # Output: [ZMQServer.reg-server-1.start] message
    """
    
    def __init__(self, name: str, component: str = None, obj_id: str = None):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (usually __name__)
            component: Component name (e.g., "ZMQServer", "JobExecutor")
            obj_id: Object instance identifier (optional)
        """
        self._logger = logging.getLogger(name)
        self.component = component or name.split('.')[-1]
        self.obj_id = obj_id
        self._event_counters = defaultdict(int)
        self._counter_lock = Lock()
    
    def _get_caller_info(self) -> tuple[str, int, str]:
        """Get caller's file, line number, and function name."""
        # Walk up the stack to find the actual caller (skip logger methods)
        frame = inspect.currentframe()
        try:
            # Skip: _get_caller_info -> debug/info/error -> actual caller
            caller_frame = frame.f_back.f_back.f_back
            if caller_frame:
                filename = Path(caller_frame.f_code.co_filename).name
                lineno = caller_frame.f_lineno
                funcname = caller_frame.f_code.co_name
                return filename, lineno, funcname
        finally:
            del frame
        return "unknown", 0, "unknown"
    
    def _format_context(self, method: str = None, **kwargs) -> str:
        """Build context prefix for log messages with file/line/function."""
        # Get caller information
        filename, lineno, funcname = self._get_caller_info()
        
        # Build component context
        parts = [self.component]
        if self.obj_id:
            parts.append(self.obj_id)
        if method:
            parts.append(method)
        
        component_context = '.'.join(parts)
        
        # Format: [component.obj.method] [file.py:123:function_name]
        file_context = f"[{filename}:{lineno}:{funcname}]"
        full_context = f"[{component_context}] {file_context}"
        
        # Add any extra context as key=value pairs
        if kwargs:
            extras = ' '.join(f"{k}={v}" for k, v in kwargs.items())
            return f"{full_context} ({extras})"
        
        return full_context
    
    def debug(self, msg: str, method: str = None, **kwargs):
        """Log debug message with context."""
        self._logger.debug(f"{self._format_context(method, **kwargs)} {msg}")
    
    def info(self, msg: str, method: str = None, **kwargs):
        """Log info message with context."""
        self._logger.info(f"{self._format_context(method, **kwargs)} {msg}")
    
    def warning(self, msg: str, method: str = None, **kwargs):
        """Log warning message with context."""
        self._logger.warning(f"{self._format_context(method, **kwargs)} {msg}")
    
    def error(self, msg: str, method: str = None, exc_info: bool = False, **kwargs):
        """Log error message with context."""
        self._logger.error(f"{self._format_context(method, **kwargs)} {msg}", exc_info=exc_info)
    
    def critical(self, msg: str, method: str = None, exc_info: bool = False, **kwargs):
        """Log critical message with context."""
        self._logger.critical(f"{self._format_context(method, **kwargs)} {msg}", exc_info=exc_info)
    
    def trace_event(self, event_name: str, method: str = None):
        """
        Trace frequent events with counters instead of logging every occurrence.
        
        Args:
            event_name: Name of the event to trace
            method: Method name for context
        """
        with self._counter_lock:
            self._event_counters[event_name] += 1
            count = self._event_counters[event_name]
            
            # Log every 100th occurrence
            if count % 100 == 0:
                self.debug(f"Event '{event_name}' occurred {count} times", method=method)
    
    def get_event_counts(self) -> dict:
        """Get all event counters."""
        with self._counter_lock:
            return dict(self._event_counters)
    
    def reset_counters(self):
        """Reset all event counters."""
        with self._counter_lock:
            self._event_counters.clear()


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_style: str = "standard"
):
    """
    Configure logging for the entire application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        format_style: "standard" or "detailed" (includes timestamp, level, module)
    """
    # Define formats with milliseconds and full context
    if format_style == "detailed":
        log_format = "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
    else:
        log_format = "%(asctime)s.%(msecs)03d [%(levelname)s] - %(message)s"
        date_format = "%H:%M:%S"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        # File logs get full context with milliseconds
        file_formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce noise from noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("tornado.access").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized at {level} level")
    if log_file:
        root_logger.info(f"Logging to file: {log_file}")


def get_logger(name: str, component: str = None, obj_id: str = None) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        component: Component name for context
        obj_id: Optional object identifier
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, component=component, obj_id=obj_id)
