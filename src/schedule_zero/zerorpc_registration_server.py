"""
zerorpc Registration and Status Server

Handles handler registration, status reporting, and maintains the handler registry.
Runs in a separate thread with gevent for proper RPC handling.
"""
import logging
import threading
import os
import yaml
import gevent
import zerorpc

logger = logging.getLogger(__name__)


class RegistrationService:
    """zerorpc service for handler registration and status reporting."""
    
    def __init__(self, registry, registry_lock, registry_path, save_registry_callback):
        """
        Initialize the registration service.
        
        Args:
            registry: Dictionary of registered handlers (shared with main process)
            registry_lock: Threading lock for registry access
            registry_path: Path to registry YAML file
            save_registry_callback: Function to call to persist registry
        """
        self.registry = registry
        self.registry_lock = registry_lock
        self.registry_path = registry_path
        self.save_registry_callback = save_registry_callback
    
    def register(self, handler_id: str, address: str, methods: list) -> dict:
        """Register a new handler or update existing handler information."""
        logger.info(f"[REGISTER] Starting registration for '{handler_id}'")
        with self.registry_lock:
            if handler_id in self.registry:
                logger.info(f"Re-registering handler '{handler_id}' at {address}")
                status = "re-registered"
            else:
                logger.info(f"Registering new handler '{handler_id}' at {address} with methods: {methods}")
                status = "registered"
            
            self.registry[handler_id] = {
                "address": address,
                "methods": methods,
                "client": None  # Will be created on-demand
            }
        
        # Call save OUTSIDE the lock to avoid deadlock
        self.save_registry_callback()
        
        # Return a proper response object instead of just True
        result = {
            "success": True,
            "handler_id": handler_id,
            "address": address,
            "status": status,
            "methods": methods,
            "message": f"Handler '{handler_id}' {status} successfully"
        }
        logger.info(f"[REGISTER] About to return result: {result}")
        return result
    
    def register_handler(self, handler_id: str, address: str, methods: list) -> bool:
        """Legacy registration method for backward compatibility - returns boolean."""
        result = self.register(handler_id, address, methods)
        return result.get("success", False)
    
    def report_status(self, handler_id: str, status: str) -> bool:
        """Update handler status (online/offline)."""
        with self.registry_lock:
            if handler_id not in self.registry:
                logger.warning(f"Status report from unknown handler '{handler_id}'")
                return False
            
            if status == "offline":
                logger.info(f"Handler '{handler_id}' reported offline status")
                # Keep in registry but mark as disconnected
                # Client will be None or closed
                if self.registry[handler_id].get("client"):
                    try:
                        self.registry[handler_id]["client"].close()
                    except Exception:
                        pass
                    self.registry[handler_id]["client"] = None
            else:
                logger.debug(f"Handler '{handler_id}' status: {status}")
        return True
    
    def ping(self) -> str:
        """Health check endpoint."""
        return "pong"


class ZeroRPCServer:
    """Manages the zerorpc server lifecycle in a separate thread."""
    
    def __init__(self, address, registry, registry_lock, registry_path, save_registry_callback, shutdown_event):
        """
        Initialize the zerorpc server.
        
        Args:
            address: TCP address to bind to (e.g., "tcp://127.0.0.1:4242")
            registry: Dictionary of registered handlers
            registry_lock: Threading lock for registry access
            registry_path: Path to registry YAML file
            save_registry_callback: Function to persist registry
            shutdown_event: Threading event to signal shutdown
        """
        self.address = address
        self.registry = registry
        self.registry_lock = registry_lock
        self.registry_path = registry_path
        self.save_registry_callback = save_registry_callback
        self.shutdown_event = shutdown_event
        self.server = None
        self.thread = None
    
    def _run_server(self):
        """Internal method to run the zerorpc server (runs in thread)."""
        try:
            service = RegistrationService(
                self.registry,
                self.registry_lock,
                self.registry_path,
                self.save_registry_callback
            )
            self.server = zerorpc.Server(service)
            self.server.bind(self.address)
            logger.info(f"zerorpc Registration/Status Server listening on {self.address}")
            
            # Run server - it will block until close() is called
            self.server.run()
            
        except Exception as e:
            logger.error(f"Failed to bind or run zerorpc server on {self.address}: {e}", exc_info=True)
        finally:
            logger.info("zerorpc Server shutting down.")
            if self.server:
                try:
                    self.server.close()
                except Exception as e:
                    logger.error(f"Error closing zerorpc server: {e}")
    
    def start(self):
        """Start the zerorpc server in a daemon thread."""
        if self.thread and self.thread.is_alive():
            logger.warning("zerorpc server thread is already running")
            return
        
        logger.info("Starting zerorpc server thread...")
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the zerorpc server."""
        if self.server:
            logger.info("Closing zerorpc server...")
            try:
                self.server.close()
            except Exception as e:
                logger.error(f"Error closing zerorpc server: {e}")
    
    def wait_for_shutdown(self, timeout=5):
        """Wait for the server thread to exit after shutdown signal."""
        if self.thread and self.thread.is_alive():
            logger.info("Waiting for zerorpc server thread to exit...")
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                logger.warning(f"zerorpc server thread did not exit cleanly after {timeout} seconds.")
            else:
                logger.info("zerorpc server thread exited cleanly.")
