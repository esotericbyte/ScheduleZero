"""Handler registry management for ScheduleZero.

Manages registration, persistence, and status tracking of remote job handlers.
"""

import os
import threading
import yaml
import asyncio
from datetime import datetime

from . import app_configuration as cfg
from .zmq_client import ZMQClient
from .logging_config import get_logger

logger = get_logger(__name__, component="HandlerRegistry")


class RegistryManager:
    """Manages the handler registry with thread-safe operations."""
    
    def __init__(self, registry_path=None):
        """
        Initialize the registry manager.
        
        Args:
            registry_path: Path to registry YAML file (uses config default if None)
        """
        self.registry = {}
        self.lock = threading.Lock()
        self.registry_path = registry_path or cfg.get_registry_path()
        self.shutdown_event = threading.Event()
    
    def save(self):
        """Save the current handler registry to a YAML file."""
        with self.lock:
            try:
                # Prepare data for serialization (exclude client objects)
                serializable_registry = {}
                for handler_id, info in self.registry.items():
                    serializable_registry[handler_id] = {
                        'address': info['address'],
                        'methods': info['methods'],
                        'registered_at': info.get('registered_at', datetime.utcnow().isoformat()),
                        'last_updated': info.get('last_updated', datetime.utcnow().isoformat()),
                        'status': info.get('status', 'unknown')
                    }
                
                # Only create directory if path includes a directory component
                dir_name = os.path.dirname(self.registry_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                
                with open(self.registry_path, 'w') as f:
                    yaml.safe_dump(serializable_registry, f, default_flow_style=False)
                logger.debug("Registry saved", method="save", path=self.registry_path, 
                           count=len(serializable_registry))
            except Exception as e:
                logger.error(f"Failed to save registry: {e}", method="save", 
                           path=self.registry_path, exc_info=True)
    
    def load(self):
        """Load the handler registry from a YAML file."""
        if os.path.exists(self.registry_path):
            with self.lock:
                try:
                    with open(self.registry_path, 'r') as f:
                        loaded = yaml.safe_load(f) or {}
                    
                    # Reconstruct registry with proper structure
                    self.registry = {}
                    for handler_id, info in loaded.items():
                        self.registry[handler_id] = {
                            'address': info['address'],
                            'methods': info['methods'],
                            'registered_at': info.get('registered_at', datetime.utcnow().isoformat()),
                            'last_updated': info.get('last_updated', datetime.utcnow().isoformat()),
                            'status': info.get('status', 'unknown'),
                            'client': None  # Clients are created lazily
                        }
                    logger.info("Registry loaded", method="load", path=self.registry_path, 
                              count=len(self.registry))
                except Exception as e:
                    logger.error(f"Failed to load registry: {e}", method="load", 
                               path=self.registry_path, exc_info=True)
                    self.registry = {}
        else:
            logger.info("Registry file not found, starting empty", method="load", 
                       path=self.registry_path)
            self.registry = {}
    
    def get_client(self, handler_id: str) -> ZMQClient | None:
        """
        Get or create a ZMQ client for a handler.
        
        Args:
            handler_id: The unique identifier of the handler
            
        Returns:
            ZMQClient instance or None if handler not found
        """
        with self.lock:
            handler_info = self.registry.get(handler_id)
        
        if not handler_info:
            logger.error(f"Handler not found", method="get_client", handler_id=handler_id)
            return None
        
        client = handler_info.get('client')
        if client:
            # Test if existing client is still valid
            try:
                client.ping()
                logger.trace_event("client_reused", method="get_client")
                return client
            except Exception as e:
                logger.warning(f"Existing client invalid: {e}", method="get_client", 
                             handler_id=handler_id)
                # Close and remove invalid client
                try:
                    client.close()
                except Exception:
                    pass
                with self.lock:
                    handler_info['client'] = None
        
        # Create new client
        address = handler_info['address']
        try:
            # Convert timeout from seconds to milliseconds
            timeout_ms = int(cfg.RPC_TIMEOUT * 1000) if hasattr(cfg, 'RPC_TIMEOUT') else 30000
            new_client = ZMQClient(address, timeout=timeout_ms)
            new_client.connect()
            logger.info("Created ZMQ client", method="get_client", 
                       handler_id=handler_id, address=address)
            with self.lock:
                handler_info['client'] = new_client
            return new_client
        except Exception as e:
            logger.error(f"Failed to create client: {e}", method="get_client", 
                        handler_id=handler_id, address=address, exc_info=True)
            return None
    
    async def close_all_clients(self, loop=None):
        """
        Close all handler clients.
        
        Args:
            loop: Event loop for running blocking operations in executor
        """
        if loop is None:
            loop = asyncio.get_running_loop()
        
        clients_to_close = []
        with self.lock:
            clients_to_close = [
                (hid, info['client'])
                for hid, info in self.registry.items()
                if info.get('client')
            ]
            # Clear clients immediately inside lock
            for hid, _ in clients_to_close:
                if hid in self.registry:
                    self.registry[hid]['client'] = None
        
        close_tasks = []
        for handler_id, client in clients_to_close:
            logger.info("Closing client", method="close_all_clients", handler_id=handler_id)
            # Run close in executor as it might block
            close_tasks.append(loop.run_in_executor(None, self._safe_close_client, client))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
    
    @staticmethod
    def _safe_close_client(client):
        """Safely close a ZMQ client."""
        try:
            client.close()
        except Exception as e:
            logger.warning(f"Error closing client: {e}", method="_safe_close_client")


# Legacy global functions for backward compatibility
# TODO: These can be removed once schedule_zero.py is fully refactored
registered_handlers = {}
registry_lock = threading.Lock()


def save_registry():
    """Legacy function - creates a temporary RegistryManager."""
    mgr = RegistryManager()
    mgr.registry = registered_handlers
    mgr.lock = registry_lock
    mgr.save()


def load_registry():
    """Legacy function - loads into global registry."""
    global registered_handlers
    mgr = RegistryManager()
    mgr.load()
    with registry_lock:
        registered_handlers = mgr.registry


def get_legacy_client(handler_id: str) -> ZMQClient | None:
    """
    Get or create a ZMQ client for a handler (legacy function).
    
    Args:
        handler_id: The unique identifier of the handler
        
    Returns:
        ZMQClient instance or None if handler not found
    """
    with registry_lock:
        handler_info = registered_handlers.get(handler_id)
    
    if not handler_info:
        logger.error(f"Handler '{handler_id}' not found in registry.")
        return None
    
    client = handler_info.get('client')
    
    # Test if existing client is still valid
    if client:
        try:
            client.ping()
            logger.debug(f"Using existing client for handler '{handler_id}'")
            return client
        except Exception as e:
            logger.warning(
                f"Existing client for handler '{handler_id}' is invalid ({e}). "
                "Creating new connection."
            )
            try:
                client.close()
            except Exception:
                pass
            handler_info['client'] = None
            client = None

    if client is None:
        # Create new client
        try:
            address = handler_info['address']
            logger.info(f"Creating new ZMQ client for handler '{handler_id}' at {address}")
            timeout_ms = int(cfg.RPC_TIMEOUT * 1000) if hasattr(cfg, 'RPC_TIMEOUT') else 30000
            new_client = ZMQClient(address, timeout=timeout_ms)
            new_client.connect()
            
            # Test connection with ping
            new_client.ping()
            logger.info(f"Successfully connected to handler '{handler_id}'")
            
            with registry_lock:
                handler_info['client'] = new_client
                handler_info['status'] = 'Connected'
            
            return new_client
        except Exception as e:
            logger.error(
                f"Failed to create/connect client for handler '{handler_id}': {e}",
                exc_info=True
            )
            with registry_lock:
                handler_info['status'] = f'Connection failed: {e}'
            return None
    
    return None


def get_all_handlers() -> list[dict]:
    """Get list of all registered handlers with their status.
    
    Returns:
        List of dictionaries containing handler information
    """
    handlers_list = []
    with registry_lock:
        for handler_id, info in registered_handlers.items():
            handlers_list.append({
                'id': handler_id,
                'address': info['address'],
                'methods': info['methods'],
                'status': info.get('status', 'unknown'),
                'registered_at': info.get('registered_at'),
                'last_updated': info.get('last_updated')
            })
    return handlers_list


def close_all_clients():
    """Close all handler client connections."""
    clients_to_close = []
    with registry_lock:
        for handler_id, info in registered_handlers.items():
            client = info.get('client')
            if client:
                clients_to_close.append((handler_id, client))
                info['client'] = None
    
    for handler_id, client in clients_to_close:
        try:
            client.close()
            logger.info(f"Closed client connection for handler '{handler_id}'")
        except Exception as e:
            logger.warning(f"Error closing client for handler '{handler_id}': {e}")


class RegistrationService:
    """zerorpc service exposed by the main server for handlers to register/update."""
    
    def register_handler(self, handler_id: str, address: str, methods: list[str]) -> bool:
        """Register or update a remote job handler and persist the registry.
        
        Args:
            handler_id: Unique identifier for the handler
            address: TCP address where handler is listening
            methods: List of method names the handler provides
            
        Returns:
            True if registration successful, False otherwise
        """
        # Basic validation
        if not isinstance(handler_id, str) or not handler_id:
            logger.error("Invalid handler_id: must be non-empty string")
            return False
        if not isinstance(address, str) or not address.startswith("tcp://"):
            logger.error(f"Invalid address '{address}': must start with 'tcp://'")
            return False
        if not isinstance(methods, list):
            logger.error("Invalid methods: must be a list")
            return False

        with registry_lock:
            now = datetime.utcnow().isoformat()
            if handler_id in registered_handlers:
                # Update existing handler
                logger.info(f"Updating handler '{handler_id}' registration")
                existing_client = registered_handlers[handler_id].get('client')
                if existing_client:
                    try:
                        existing_client.close()
                    except Exception:
                        pass
                
                registered_handlers[handler_id].update({
                    'address': address,
                    'methods': methods,
                    'last_updated': now,
                    'status': 'Registered',
                    'client': None  # Will be created on first use
                })
            else:
                # New handler registration
                logger.info(f"Registering new handler '{handler_id}' at {address}")
                registered_handlers[handler_id] = {
                    'address': address,
                    'methods': methods,
                    'registered_at': now,
                    'last_updated': now,
                    'status': 'Registered',
                    'client': None
                }
        
        save_registry()
        return True

    def report_status(self, handler_id: str, status: str) -> bool:
        """Allow handlers to report status (e.g., 'offline', 'online').
        
        Args:
            handler_id: Unique identifier for the handler
            status: Status string to report
            
        Returns:
            True if status update successful, False otherwise
        """
        with registry_lock:
            if handler_id in registered_handlers:
                registered_handlers[handler_id]['status'] = status
                registered_handlers[handler_id]['last_updated'] = datetime.utcnow().isoformat()
                logger.info(f"Handler '{handler_id}' reported status: {status}")
                save_registry()
                return True
            else:
                logger.warning(f"Status report from unknown handler '{handler_id}'")
                return False

    def unregister_handler_persistent(self, handler_id: str) -> bool:
        """Explicitly unregister a handler and persist the change.
        
        Args:
            handler_id: Unique identifier for the handler
            
        Returns:
            True if unregistration successful, False otherwise
        """
        success = False
        with registry_lock:
            if handler_id in registered_handlers:
                client = registered_handlers[handler_id].get('client')
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
                del registered_handlers[handler_id]
                logger.info(f"Unregistered handler '{handler_id}'")
                success = True
            else:
                logger.warning(f"Attempted to unregister unknown handler '{handler_id}'")
        
        if success:
            save_registry()
        return success

    def ping(self) -> str:
        """Health check endpoint.
        
        Returns:
            "pong" string
        """
        return "pong"
