"""
ZeroMQ Client Utilities

Provides simple ZMQ client wrapper for making RPC-style calls to handlers.
No gevent, no monkey patching - just clean synchronous ZeroMQ with JSON messages.
"""
import json
import zmq
from .logging_config import get_logger


class ZMQClient:
    """
    Simple ZeroMQ client for RPC-style communication with handlers.
    
    Uses REQ socket for request-response pattern with JSON serialization.
    """
    
    def __init__(self, address: str, timeout: int = 30000):
        """
        Initialize ZMQ client.
        
        Args:
            address: TCP address to connect to (e.g., "tcp://127.0.0.1:4244")
            timeout: Socket timeout in milliseconds (default: 30000ms = 30s)
        """
        self.address = address
        self.timeout = timeout
        self.context = zmq.Context()
        self.socket = None
        self._connected = False
        self.logger = get_logger(__name__, component="ZMQClient", obj_id=address)
    
    def connect(self):
        """Establish connection to the remote handler."""
        if self._connected:
            return
        
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout)
            self.socket.setsockopt(zmq.LINGER, 1000)  # 1 second linger on close
            self.socket.connect(self.address)
            self._connected = True
            self.logger.debug(f"Connected to {self.address}", method="connect")
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}", method="connect", exc_info=True)
            raise
    
    def call(self, method: str, params: dict = None) -> dict:
        """
        Make an RPC-style call to the remote handler.
        
        Args:
            method: Method name to call on the remote handler
            params: Dictionary of parameters to pass to the method
            
        Returns:
            dict: Response from the remote method
            
        Raises:
            ConnectionError: If not connected or connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        if not self._connected:
            raise ConnectionError("Client not connected. Call connect() first.")
        
        request = {
            "method": method,
            "params": params or {}
        }
        
        try:
            # Send request
            self.socket.send_string(json.dumps(request))
            self.logger.trace_event("zmq_request_sent", method="call")
            
            # Receive response
            response_str = self.socket.recv_string()
            response = json.loads(response_str)
            self.logger.trace_event("zmq_response_received", method="call")
            
            return response
            
        except zmq.Again as e:
            # Timeout
            self.logger.error(f"Request timeout after {self.timeout}ms: {method}", method="call")
            # Need to close and recreate socket after timeout in REQ/REP pattern
            self.close()
            raise TimeoutError(f"Request timeout: {method}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}", method="call", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Error calling {method}: {e}", method="call", exc_info=True)
            raise
    
    def ping(self) -> str:
        """
        Ping the remote handler to check connectivity.
        
        Returns:
            str: "pong" if successful
            
        Raises:
            Exception: If ping fails
        """
        response = self.call("ping")
        if response.get("success"):
            return response.get("message", "pong")
        raise ConnectionError(f"Ping failed: {response.get('error', 'Unknown error')}")
    
    def close(self):
        """Close the ZMQ socket and cleanup resources."""
        if self.socket:
            try:
                self.socket.close()
                self.logger.debug(f"Closed socket", method="close")
            except Exception as e:
                self.logger.warning(f"Error closing socket: {e}", method="close")
            finally:
                self.socket = None
                self._connected = False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
        if self.context:
            try:
                self.context.term()
            except Exception:
                pass
