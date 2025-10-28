"""
ZeroMQ Registration and Status Server

Handles handler registration, status reporting, and maintains the handler registry.
Uses asyncio with pyzmq for clean integration with Tornado's event loop.
No gevent, no monkey patching - just clean async Python.
"""
import asyncio
import json
import zmq
import zmq.asyncio

from .logging_config import get_logger

logger = get_logger(__name__, component="ZMQRegistrationServer")


class RegistrationService:
    """Service for handler registration and status reporting."""
    
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
        logger.debug("Registration request received", method="register", handler_id=handler_id)
        with self.registry_lock:
            if handler_id in self.registry:
                logger.info("Re-registering handler", method="register", 
                          handler_id=handler_id, address=address)
                status = "re-registered"
            else:
                logger.info("Registering new handler", method="register", 
                          handler_id=handler_id, address=address, methods=methods)
                status = "registered"
            
            self.registry[handler_id] = {
                "address": address,
                "methods": methods,
                "client": None  # Will be created on-demand
            }
        
        # Call save OUTSIDE the lock to avoid deadlock
        self.save_registry_callback()
        
        result = {
            "success": True,
            "handler_id": handler_id,
            "address": address,
            "status": status,
            "methods": methods,
            "message": f"Handler '{handler_id}' {status} successfully"
        }
        logger.info("Registration successful", method="register", handler_id=handler_id, 
                   status=status)
        return result
    
    def report_status(self, handler_id: str, status: str) -> dict:
        """Update handler status (online/offline)."""
        with self.registry_lock:
            if handler_id not in self.registry:
                logger.warning("Status report from unknown handler", method="report_status", 
                             handler_id=handler_id)
                return {"success": False, "error": "Handler not registered"}
            
            if status == "offline":
                logger.info("Handler reported offline", method="report_status", 
                          handler_id=handler_id)
                # Keep in registry but mark as disconnected
                if self.registry[handler_id].get("client"):
                    self.registry[handler_id]["client"] = None
            else:
                logger.trace_event("status_update", method="report_status")
        
        return {"success": True, "handler_id": handler_id, "status": status}
    
    def ping(self) -> dict:
        """Health check endpoint."""
        return {"success": True, "message": "pong"}
    
    def handle_request(self, request: dict) -> dict:
        """
        Route incoming requests to appropriate methods.
        
        Args:
            request: dict with 'method' and 'params' keys
            
        Returns:
            dict response
        """
        method = request.get("method")
        params = request.get("params", {})
        
        logger.trace_event("request_received", method="handle_request")
        
        try:
            if method == "register":
                return self.register(
                    params.get("handler_id"),
                    params.get("address"),
                    params.get("methods", [])
                )
            elif method == "report_status":
                return self.report_status(
                    params.get("handler_id"),
                    params.get("status")
                )
            elif method == "ping":
                return self.ping()
            else:
                logger.warning(f"Unknown method: {method}", method="handle_request")
                return {"success": False, "error": f"Unknown method: {method}"}
        except Exception as e:
            logger.error(f"Error handling request: {e}", method="handle_request", 
                        exc_info=True)
            return {"success": False, "error": str(e)}


class ZMQRegistrationServer:
    """Manages the ZeroMQ registration server using asyncio."""
    
    def __init__(self, address, registry, registry_lock, registry_path, save_registry_callback):
        """
        Initialize the ZMQ registration server.
        
        Args:
            address: TCP address to bind to (e.g., "tcp://127.0.0.1:4242")
            registry: Dictionary of registered handlers
            registry_lock: Threading lock for registry access
            registry_path: Path to registry YAML file
            save_registry_callback: Function to persist registry
        """
        self.address = address
        self.registry = registry
        self.registry_lock = registry_lock
        self.registry_path = registry_path
        self.save_registry_callback = save_registry_callback
        self.service = RegistrationService(
            registry, registry_lock, registry_path, save_registry_callback
        )
        self.context = None
        self.socket = None
        self.task = None
        self.running = False
    
    async def _run_server(self):
        """Internal method to run the ZMQ server (async)."""
        try:
            # Create ZMQ context and REP socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(self.address)
            logger.info("ZMQ server listening", method="_run_server", address=self.address)
            
            self.running = True
            
            # Process requests
            while self.running:
                try:
                    # Receive request with timeout (use polling to allow shutdown checks)
                    if await self.socket.poll(timeout=1000):  # 1 second timeout
                        message = await self.socket.recv_string()
                        logger.trace_event("message_received", method="_run_server")
                        
                        # Parse request
                        try:
                            request = json.loads(message)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON: {e}", method="_run_server")
                            response = {"success": False, "error": "Invalid JSON"}
                            await self.socket.send_string(json.dumps(response))
                            continue
                        
                        # Handle request
                        response = self.service.handle_request(request)
                        
                        # Send response
                        await self.socket.send_string(json.dumps(response))
                        logger.trace_event("response_sent", method="_run_server")
                
                except asyncio.CancelledError:
                    logger.info("Server task cancelled", method="_run_server")
                    break
                except Exception as e:
                    logger.error(f"Error processing request: {e}", method="_run_server", 
                               exc_info=True)
                    # Try to send error response
                    try:
                        error_response = {"success": False, "error": str(e)}
                        await self.socket.send_string(json.dumps(error_response))
                    except Exception:
                        pass
        
        except Exception as e:
            logger.error(f"Failed to run ZMQ server: {e}", method="_run_server", 
                        address=self.address, exc_info=True)
        finally:
            logger.info("ZMQ server shutting down", method="_run_server")
            if self.socket:
                self.socket.close()
            if self.context:
                self.context.term()
    
    def start(self, loop=None):
        """
        Start the ZMQ server as an asyncio task.
        
        Args:
            loop: Optional event loop. If not provided, uses current loop.
        """
        if self.task and not self.task.done():
            logger.warning("Server task already running", method="start")
            return
        
        if loop is None:
            loop = asyncio.get_event_loop()
        
        logger.info("Starting ZMQ server task", method="start", address=self.address)
        self.task = loop.create_task(self._run_server())
    
    async def stop(self):
        """Stop the ZMQ server."""
        logger.info("Stopping ZMQ server", method="stop")
        self.running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("ZMQ server stopped", method="stop")
