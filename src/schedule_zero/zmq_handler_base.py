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

from .logging_config import get_logger, setup_logging
from pathlib import Path

# Setup logging for handlers
def setup_handler_logging(handler_id: str, log_level: str = "INFO"):
    """Setup file-based logging for a handler."""
    # Create handler-specific log directory
    log_dir = Path("logs") / "handlers" / handler_id
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "handler.log"
    setup_logging(level=log_level, log_file=str(log_file), format_style="detailed")
    
    return log_file


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
            handler_address: TCP address hint where handler should listen (e.g., "tcp://127.0.0.1:5000")
                           If port is non-zero, it will be used as a hint, but binding will use port 0
                           and let the OS assign an available port. The actual address will be determined
                           after binding and used for registration.
            server_address: TCP address of the ScheduleZero server (e.g., "tcp://127.0.0.1:4242")
            registration_retry_interval: Seconds between registration attempts
            max_registration_retries: Maximum registration attempts before giving up
        """
        self.handler_id = handler_id
        self.handler_address_hint = handler_address  # Store the hint for host extraction
        self.handler_address = None  # Will be set after binding
        self.server_address = server_address
        self.registration_retry_interval = registration_retry_interval
        self.max_registration_retries = max_registration_retries
        
        self.shutdown_event = threading.Event()
        self.registration_thread = None
        self.server_thread = None
        self.is_registered = False
        
        self.context = zmq.Context()
        self.handler_socket = None
        
        # Setup instance logger with handler ID
        self.logger = get_logger(__name__, component="Handler", obj_id=handler_id)
        
        # Collect methods that can be called remotely
        self.methods = self._discover_methods()
        self.logger.info(f"Initialized with methods: {list(self.methods.keys())}", method="__init__")
    
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
        
        self.logger.debug(f"Handling request: method={method_name}, params={params}")
        
        if method_name not in self.methods:
            error_msg = f"Unknown method: {method_name}"
            self.logger.warning(error_msg)
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
            self.logger.error(f"Error executing method '{method_name}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _run_handler_server(self):
        """Run the handler REP socket server (runs in thread)."""
        try:
            self.handler_socket = self.context.socket(zmq.REP)
            self.handler_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for polling
            
            # Use the configured address directly - no more port 0!
            bind_address = self.handler_address_hint
            
            self.handler_socket.bind(bind_address)
            
            # Verify the bound address
            self.handler_address = self.handler_socket.getsockopt_string(zmq.LAST_ENDPOINT)
            
            self.logger.info("Handler server listening", method="_run_handler_server", 
                       address=self.handler_address, 
                       note="configured port")
            
            while not self.shutdown_event.is_set():
                try:
                    # Try to receive a message
                    self.logger.trace_event("socket_poll", method="_run_handler_server")
                    message = self.handler_socket.recv_string()
                    self.logger.info("Message received", method="_run_handler_server", 
                               message_len=len(message))
                    
                    # Parse request
                    try:
                        request = json.loads(message)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON: {e}", method="_run_handler_server")
                        response = {"success": False, "error": "Invalid JSON"}
                        self.handler_socket.send_string(json.dumps(response))
                        continue
                    
                    # Handle request
                    response = self._handle_request(request)
                    
                    # Send response
                    self.handler_socket.send_string(json.dumps(response))
                    self.logger.info("Response sent", method="_run_handler_server",
                               success=response.get("success"))
                    
                except zmq.Again:
                    # Timeout - just continue to check shutdown event
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}", method="_run_handler_server", 
                               exc_info=True)
                    # Try to send error response
                    try:
                        error_response = {"success": False, "error": str(e)}
                        self.handler_socket.send_string(json.dumps(error_response))
                    except Exception:
                        pass
        
        except Exception as e:
            self.logger.error(f"Failed to run handler server: {e}", method="_run_handler_server",
                        address=self.handler_address or self.handler_address_hint, exc_info=True)
        finally:
            self.logger.info("Handler server shutting down", method="_run_handler_server")
            if self.handler_socket:
                self.handler_socket.close()
    
    def _manage_registration(self):
        """Manage registration with the server (runs in thread)."""
        # Wait for handler server to bind and set actual address
        max_wait = 10  # 10 seconds max wait
        wait_count = 0
        while self.handler_address is None and wait_count < max_wait:
            if self.shutdown_event.is_set():
                return
            time.sleep(0.1)
            wait_count += 1
        
        if self.handler_address is None:
            self.logger.error("Handler server failed to bind within timeout", 
                        method="_manage_registration")
            return
        
        self.logger.info("Handler bound to address, starting registration", 
                   method="_manage_registration",
                   address=self.handler_address)
        
        retry_count = 0
        reg_socket = None
        
        while not self.shutdown_event.is_set() and retry_count < self.max_registration_retries:
            if reg_socket is None:
                try:
                    self.logger.info(f"Attempting to connect to server at {self.server_address}... (attempt {retry_count + 1}/{self.max_registration_retries})")
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
                        self.logger.info("Connected to server")
                        self.is_registered = False
                    else:
                        raise ConnectionError("Ping failed")
                        
                except Exception as e:
                    retry_count += 1
                    self.logger.warning(f"Failed to connect to server: {e}. Retrying in {self.registration_retry_interval}s... (attempt {retry_count}/{self.max_registration_retries})")
                    if reg_socket:
                        try:
                            reg_socket.close()
                        except Exception:
                            pass
                    reg_socket = None
                    if retry_count >= self.max_registration_retries:
                        self.logger.error(f"Max retries ({self.max_registration_retries}) reached. Giving up.")
                        return
                    self.shutdown_event.wait(self.registration_retry_interval)
                    continue
            
            if not self.is_registered and reg_socket:
                try:
                    self.logger.info(f"Attempting to register as '{self.handler_id}'...")
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
                        self.logger.info(f"Registration successful: {response.get('message', 'OK')}")
                    else:
                        self.logger.warning("Registration failed. Retrying connection...")
                        if reg_socket:
                            try:
                                reg_socket.close()
                            except Exception:
                                pass
                        reg_socket = None
                        self.shutdown_event.wait(self.registration_retry_interval)
                        
                except Exception as e:
                    self.logger.warning(f"Registration attempt failed: {e}. Will retry connection.")
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
                self.logger.debug(f"Registered. Checking connection in {wait_interval}s...")
                shutdown_signaled = self.shutdown_event.wait(wait_interval)
                if shutdown_signaled:
                    break
                
                # Ping server for health check
                if not self.shutdown_event.is_set() and reg_socket:
                    try:
                        self.logger.debug("Pinging server for health check...")
                        ping_request = {"method": "ping"}
                        reg_socket.send_string(json.dumps(ping_request))
                        response_str = reg_socket.recv_string()
                        response = json.loads(response_str)
                        if response.get("success"):
                            self.logger.debug("Server ping successful")
                        else:
                            raise ConnectionError("Ping returned failure")
                    except Exception as e:
                        self.logger.warning(f"Server connection lost: {e}. Will attempt to re-register.")
                        self.is_registered = False
                        if reg_socket:
                            try:
                                reg_socket.close()
                            except Exception:
                                pass
                        reg_socket = None
        
        # Shutdown sequence
        self.logger.info("Registration thread stopping...")
        if self.is_registered and reg_socket:
            try:
                self.logger.info("Reporting 'offline' status to server...")
                status_request = {
                    "method": "report_status",
                    "params": {
                        "handler_id": self.handler_id,
                        "status": "offline"
                    }
                }
                reg_socket.send_string(json.dumps(status_request))
                response_str = reg_socket.recv_string()
                self.logger.info("Successfully reported 'offline' status")
            except Exception as e:
                self.logger.warning(f"Could not report offline status: {e}")
        
        if reg_socket:
            try:
                reg_socket.close()
                self.logger.info("Registration socket closed")
            except Exception as e:
                self.logger.warning(f"Error closing registration socket: {e}")
        
        self.logger.info("Registration thread finished")
    
    def start(self):
        """Start the handler server and registration threads."""
        self.logger.info(f"Starting handler '{self.handler_id}'...")
        
        # Start handler server thread
        self.server_thread = threading.Thread(target=self._run_handler_server, daemon=True)
        self.server_thread.start()
        
        # Give server a moment to start
        time.sleep(0.5)
        
        # Start registration thread
        self.registration_thread = threading.Thread(target=self._manage_registration, daemon=True)
        self.registration_thread.start()
        
        self.logger.info(f"Handler '{self.handler_id}' started")
    
    def run(self):
        """Start the handler and block until shutdown."""
        self.start()
        
        try:
            # Block until shutdown is signaled
            self.shutdown_event.wait()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the handler and cleanup."""
        if self.shutdown_event.is_set():
            return
        
        self.logger.info(f"Stopping handler '{self.handler_id}'...")
        self.shutdown_event.set()
        
        # Wait for threads to finish
        if self.registration_thread and self.registration_thread.is_alive():
            self.registration_thread.join(timeout=10)
            if self.registration_thread.is_alive():
                self.logger.warning("Registration thread did not exit cleanly")
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
            if self.server_thread.is_alive():
                self.logger.warning("Server thread did not exit cleanly")
        
        # Cleanup ZMQ context
        if self.context:
            try:
                self.context.term()
            except Exception as e:
                self.logger.warning(f"Error terminating ZMQ context: {e}")
        
        self.logger.info(f"Handler '{self.handler_id}' stopped")
