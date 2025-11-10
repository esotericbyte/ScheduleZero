"""
Governor Abstract Base Class

Defines the standard interface for all governor implementations.
Governors are responsible for managing handler and server processes/threads.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from pathlib import Path
from .logging_config import get_logger

logger = get_logger(__name__, component="GovernorBase")


class HandlerConfig:
    """Configuration for a handler instance."""
    
    def __init__(
        self,
        handler_id: str,
        module_path: str,
        class_name: str,
        port: int,
        auto_restart: bool = True,
        max_restarts: int = 3,
        restart_delay: float = 5.0,
        **kwargs
    ):
        """
        Initialize handler configuration.
        
        Args:
            handler_id: Unique identifier for this handler instance
            module_path: Python module path (e.g., "tests.ding_dong_handler")
            class_name: Handler class name (e.g., "DingDongHandler")
            port: Port number for ZMQ REP socket
            auto_restart: Whether to auto-restart on failure
            max_restarts: Maximum restart attempts before giving up
            restart_delay: Seconds to wait before restart attempt
            **kwargs: Additional handler-specific configuration
        """
        self.handler_id = handler_id
        self.module_path = module_path
        self.class_name = class_name
        self.port = port
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self.extra_config = kwargs
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'handler_id': self.handler_id,
            'module_path': self.module_path,
            'class_name': self.class_name,
            'port': self.port,
            'auto_restart': self.auto_restart,
            'max_restarts': self.max_restarts,
            'restart_delay': self.restart_delay,
            **self.extra_config
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HandlerConfig':
        """Create from dictionary."""
        return cls(**data)


class ProcessInfo:
    """Information about a running process/thread."""
    
    def __init__(
        self,
        name: str,
        pid: Optional[int] = None,
        status: str = "unknown",
        restart_count: int = 0,
        last_error: Optional[str] = None
    ):
        """
        Initialize process info.
        
        Args:
            name: Process/thread name
            pid: Process ID (for process-based) or None (for thread-based)
            status: Current status (running, stopped, crashed, restarting)
            restart_count: Number of times restarted
            last_error: Last error message if any
        """
        self.name = name
        self.pid = pid
        self.status = status
        self.restart_count = restart_count
        self.last_error = last_error
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'pid': self.pid,
            'status': self.status,
            'restart_count': self.restart_count,
            'last_error': self.last_error
        }


class GovernorBase(ABC):
    """
    Abstract base class for all governor implementations.
    
    A Governor manages the lifecycle of server and handler processes/threads.
    Different implementations can use processes, threads, containers, etc.
    """
    
    def __init__(self, deployment: str, config_path: Optional[Path] = None):
        """
        Initialize governor.
        
        Args:
            deployment: Deployment name (e.g., "default", "production")
            config_path: Optional path to configuration file
        """
        self.deployment = deployment
        self.config_path = config_path
        self.logger = get_logger(__name__, component=self.__class__.__name__, obj_id=deployment)
        self._running = False
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the governor and all managed services.
        
        Returns:
            bool: True if started successfully
        """
        pass
    
    @abstractmethod
    def stop(self, timeout: float = 30.0) -> bool:
        """
        Stop all managed services gracefully.
        
        Args:
            timeout: Maximum seconds to wait for graceful shutdown
            
        Returns:
            bool: True if stopped successfully
        """
        pass
    
    @abstractmethod
    def restart(self, timeout: float = 30.0) -> bool:
        """
        Restart all managed services.
        
        Args:
            timeout: Maximum seconds to wait for stop before starting
            
        Returns:
            bool: True if restarted successfully
        """
        pass
    
    @abstractmethod
    def status(self) -> Dict[str, ProcessInfo]:
        """
        Get status of all managed services.
        
        Returns:
            Dict mapping service name to ProcessInfo
        """
        pass
    
    @abstractmethod
    def add_handler(self, config: HandlerConfig) -> bool:
        """
        Dynamically add a new handler.
        
        Args:
            config: Handler configuration
            
        Returns:
            bool: True if added successfully
        """
        pass
    
    @abstractmethod
    def remove_handler(self, handler_id: str, timeout: float = 10.0) -> bool:
        """
        Remove a handler and stop it gracefully.
        
        Args:
            handler_id: Unique identifier of handler to remove
            timeout: Maximum seconds to wait for shutdown
            
        Returns:
            bool: True if removed successfully
        """
        pass
    
    @abstractmethod
    def restart_handler(self, handler_id: str) -> bool:
        """
        Restart a specific handler.
        
        Args:
            handler_id: Unique identifier of handler to restart
            
        Returns:
            bool: True if restarted successfully
        """
        pass
    
    @abstractmethod
    def get_handler_status(self, handler_id: str) -> Optional[ProcessInfo]:
        """
        Get status of a specific handler.
        
        Args:
            handler_id: Unique identifier of handler
            
        Returns:
            ProcessInfo or None if not found
        """
        pass
    
    @abstractmethod
    def list_handlers(self) -> List[str]:
        """
        Get list of all handler IDs.
        
        Returns:
            List of handler IDs
        """
        pass
    
    @property
    def is_running(self) -> bool:
        """Check if governor is running."""
        return self._running
    
    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all services.
        
        Returns:
            Dict mapping service name to health status (True = healthy)
        """
        status = self.status()
        return {
            name: info.status == "running"
            for name, info in status.items()
        }
    
    def get_metrics(self) -> Dict[str, any]:
        """
        Get operational metrics.
        
        Returns:
            Dict with metrics like uptime, restart counts, etc.
        """
        status = self.status()
        total_restarts = sum(info.restart_count for info in status.values())
        healthy = sum(1 for info in status.values() if info.status == "running")
        
        return {
            'deployment': self.deployment,
            'running': self._running,
            'total_services': len(status),
            'healthy_services': healthy,
            'total_restarts': total_restarts,
            'services': {name: info.to_dict() for name, info in status.items()}
        }
