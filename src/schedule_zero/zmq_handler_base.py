"""
ZeroMQ Handler Base Classes

Provides base classes for creating job handlers that communicate with the
ScheduleZero server using ZeroMQ. No gevent, no monkey patching - clean
threading with ZeroMQ.
"""
import json
import threading
import time
import zmq
from typing import Callable, Dict

from .logging_config import get_logger

logger = get_logger(__name__, component="ZMQHandlerBase")


class ZMQHandlerBase:
    """
    Base class for job handlers using ZeroMQ.
    
    Handlers extend this class and implement methods that can be called remotely.
    The base class handles:
    - Registration with the server
    - Running a REP socket to receive job requests
    - Dispatching method calls to handler methods
    - Clean shutdown
    """
    
    def __init__(
        self,
        handler_id: str,
        handler_address: str,
        server_address: str,
        registration_retry_interval: int = 15,
        max_registration_retries: int = 5
    ):
        """
        Initialize the handler.
        
        Args:
            handler_id: Unique identifier for this handler
            handler_address: TCP address where this handler listens (e.g., "tcp://127.0.0.1:4244")
            server_address: TCP address of the ScheduleZero server (e.g., "tcp://127.0.0.1:4242")
            registration_retry_interval: Seconds between registration attempts
            max_registration_retries: Maximum registration attempts before giving up
        """
        self.handler_id = handler_id
        self.handler_address = handler_address
        self.server_address = server_address
        self.registration_retry_interval = registration_retry_interval
        self.max_registration_retries = max_registration_retries
        
        self.shutdown_event = threading.Event()
        self.registration_thread = None
        self.server_thread = None
        self.is_registered = False
        
        self.context = zmq.Context()
        self.handler_socket = None
        
        # Collect methods that can be called remotely
        self.methods = self._discover_methods()
        logger.info(f"Handler '{self.handler_id}' initialized with methods: {list(self.methods.keys())}")
    
    def _discover_methods(self) -> Dict[str, Callable]:
        """
        Discover methods that can be called remotely.
        
        Returns all public methods (not starting with _) as a dict.
        """
        methods = {}
        for name in dir(self):
            if not name.startswith('_') and callable(getattr(self, name)):
                # Exclude base class methods
                if name not in ['run', 'start', 'stop', 'ping']:
                    methods[name] = getattr(self, name)
        
        # Always include ping
        methods['ping'] = self.ping
        return methods
    
    def ping(self, params=None):
        """Health check method."""
        return {"success": True, "message": "pong", "handler_id": self.handler_id}
    
    def _handle_request(self, request: dict) -> dict:
        """
        Handle an incoming RPC request.
        
        Args:
            request: dict with 'method' and 'params' keys
            
        Returns:
            dict response
        """
        method_name = request.get("method")
        params = request.get("params", {})
        
        logger.debug(f"Handling request: method={method_name}, params={params}")
        
        if method_name not in self.methods:
            error_msg = f"Unknown method: {method_name}"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            method = self.methods[method_name]
            # Call method with params if it accepts arguments
            import inspect
            sig = inspect.signature(method)
            if len(sig.parameters) > 0:
                result = method(params)
            else:
                result = method()
            
            # Normalize result to dict with success flag
            if isinstance(result, dict):
                if "success" not in result:
                    result["success"] = True
                return result
            else:
                return {"success": True, "result": result}
                
        except Exception as e:
            logger.error(f"Error executing method '{method_name}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _run_handler_server(self):
        """Run the handler REP socket server (runs in thread)."""
        try:
            self.handler_socket = self.context.socket(zmq.REP)
            self.handler_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for polling
            self.handler_socket.bind(self.handler_address)
            logger.info("Handler server listening", method="_run_handler_server", 
                       address=self.handler_address)
            
            while not self.shutdown_event.is_set():
                try:
                    # Try to receive a message
                    logger.trace_event("socket_poll", method="_run_handler_server")
                    message = self.handler_socket.recv_string()
                    logger.info("Message received", method="_run_handler_server", 
                               message_len=len(message))
                    
                    # Parse request
                    try:
                        request = json.loads(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}", method="_run_handler_server")
                        response = {"success": False, "error": "Invalid JSON"}
                        self.handler_socket.send_string(json.dumps(response))
                        continue
                    
                    # Handle request
                    response = self._handle_request(request)
                    
                    # Send response
                    self.handler_socket.send_string(json.dumps(response))
                    logger.info("Response sent", method="_run_handler_server",
                               success=response.get("success"))
                    
                except zmq.Again:
                    # Timeout - just continue to check shutdown event
                    continue
                except Exception as e:
                    logger.error(f"Error processing request: {e}", method="_run_handler_server", 
                               exc_info=True)
                    # Try to send error response
                    try:
                        error_response = {"success": False, "error": str(e)}
                        self.handler_socket.send_string(json.dumps(error_response))
                    except Exception:
                        pass
        
        except Exception as e:
            logger.error(f"Failed to run handler server: {e}", method="_run_handler_server",
                        address=self.handler_address, exc_info=True)
        finally:
            logger.info("Handler server shutting down", method="_run_handler_server")
            if self.handler_socket:
                self.handler_socket.close()
    
    def _manage_registration(self):
        """Manage registration with the server (runs in thread)."""
        retry_count = 0
        reg_socket = None
        
        while not self.shutdown_event.is_set() and retry_count < self.max_registration_retries:
            if reg_socket is None:
                try:
                    logger.info(f"Attempting to connect to server at {self.server_address}... (attempt {retry_count + 1}/{self.max_registration_retries})")
                    reg_socket = self.context.socket(zmq.REQ)
                    reg_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                    reg_socket.setsockopt(zmq.SNDTIMEO, 10000)
                    reg_socket.connect(self.server_address)
                    
                    # Test connection with ping
                    ping_request = {"method": "ping"}
                    reg_socket.send_string(json.dumps(ping_request))
                    response_str = reg_socket.recv_string()
                    response = json.loads(response_str)
                    
                    if response.get("success"):
                        logger.info("Connected to server")
                        self.is_registered = False
                    else:
                        raise ConnectionError("Ping failed")
                        
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Failed to connect to server: {e}. Retrying in {self.registration_retry_interval}s... (attempt {retry_count}/{self.max_registration_retries})")
                    if reg_socket:
                        try:
                            reg_socket.close()
                        except Exception:
                            pass
                    reg_socket = None
                    if retry_count >= self.max_registration_retries:
                        logger.error(f"Max retries ({self.max_registration_retries}) reached. Giving up.")
                        return
                    self.shutdown_event.wait(self.registration_retry_interval)
                    continue
            
            if not self.is_registered and reg_socket:
                try:
                    logger.info(f"Attempting to register as '{self.handler_id}'...")
                    register_request = {
                        "method": "register",
                        "params": {
                            "handler_id": self.handler_id,
                            "address": self.handler_address,
                            "methods": list(self.methods.keys())
                        }
                    }
                    reg_socket.send_string(json.dumps(register_request))
                    response_str = reg_socket.recv_string()
                    response = json.loads(response_str)
                    
                    if response.get("success"):
                        self.is_registered = True
                        retry_count = 0  # Reset counter on success
                        logger.info(f"Registration successful: {response.get('message', 'OK')}")
                    else:
                        logger.warning("Registration failed. Retrying connection...")
                        if reg_socket:
                            try:
                                reg_socket.close()
                            except Exception:
                                pass
                        reg_socket = None
                        self.shutdown_event.wait(self.registration_retry_interval)
                        
                except Exception as e:
                    logger.warning(f"Registration attempt failed: {e}. Will retry connection.")
                    self.is_registered = False
                    if reg_socket:
                        try:
                            reg_socket.close()
                        except Exception:
                            pass
                    reg_socket = None
                    self.shutdown_event.wait(self.registration_retry_interval)
                    continue
            
            if self.is_registered and reg_socket:
                # Health check interval
                wait_interval = self.registration_retry_interval * 2
                logger.debug(f"Registered. Checking connection in {wait_interval}s...")
                shutdown_signaled = self.shutdown_event.wait(wait_interval)
                if shutdown_signaled:
                    break
                
                # Ping server for health check
                if not self.shutdown_event.is_set() and reg_socket:
                    try:
                        logger.debug("Pinging server for health check...")
                        ping_request = {"method": "ping"}
                        reg_socket.send_string(json.dumps(ping_request))
                        response_str = reg_socket.recv_string()
                        response = json.loads(response_str)
                        if response.get("success"):
                            logger.debug("Server ping successful")
                        else:
                            raise ConnectionError("Ping returned failure")
                    except Exception as e:
                        logger.warning(f"Server connection lost: {e}. Will attempt to re-register.")
                        self.is_registered = False
                        if reg_socket:
                            try:
                                reg_socket.close()
                            except Exception:
                                pass
                        reg_socket = None
        
        # Shutdown sequence
        logger.info("Registration thread stopping...")
        if self.is_registered and reg_socket:
            try:
                logger.info("Reporting 'offline' status to server...")
                status_request = {
                    "method": "report_status",
                    "params": {
                        "handler_id": self.handler_id,
                        "status": "offline"
                    }
                }
                reg_socket.send_string(json.dumps(status_request))
                response_str = reg_socket.recv_string()
                logger.info("Successfully reported 'offline' status")
            except Exception as e:
                logger.warning(f"Could not report offline status: {e}")
        
        if reg_socket:
            try:
                reg_socket.close()
                logger.info("Registration socket closed")
            except Exception as e:
                logger.warning(f"Error closing registration socket: {e}")
        
        logger.info("Registration thread finished")
    
    def start(self):
        """Start the handler server and registration threads."""
        logger.info(f"Starting handler '{self.handler_id}'...")
        
        # Start handler server thread
        self.server_thread = threading.Thread(target=self._run_handler_server, daemon=True)
        self.server_thread.start()
        
        # Give server a moment to start
        time.sleep(0.5)
        
        # Start registration thread
        self.registration_thread = threading.Thread(target=self._manage_registration, daemon=True)
        self.registration_thread.start()
        
        logger.info(f"Handler '{self.handler_id}' started")
    
    def run(self):
        """Start the handler and block until shutdown."""
        self.start()
        
        try:
            # Block until shutdown is signaled
            self.shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the handler and cleanup."""
        if self.shutdown_event.is_set():
            return
        
        logger.info(f"Stopping handler '{self.handler_id}'...")
        self.shutdown_event.set()
        
        # Wait for threads to finish
        if self.registration_thread and self.registration_thread.is_alive():
            self.registration_thread.join(timeout=10)
            if self.registration_thread.is_alive():
                logger.warning("Registration thread did not exit cleanly")
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
            if self.server_thread.is_alive():
                logger.warning("Server thread did not exit cleanly")
        
        # Cleanup ZMQ context
        if self.context:
            try:
                self.context.term()
            except Exception as e:
                logger.warning(f"Error terminating ZMQ context: {e}")
        
        logger.info(f"Handler '{self.handler_id}' stopped")
