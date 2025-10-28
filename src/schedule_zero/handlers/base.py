"""Base handler class for ScheduleZero handlers.

This module provides an abstract base class that all ScheduleZero handlers should inherit from.
"""

import zerorpc
import logging
import signal
import threading
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Abstract base class for ScheduleZero handlers.
    
    Handlers should inherit from this class and implement their job methods.
    All public methods (not starting with _) will be automatically registered
    with the ScheduleZero server.
    
    Example:
        class MyHandler(BaseHandler):
            def process_data(self, params: dict) -> dict:
                data = params.get("data")
                # Process the data
                return {"status": "success", "result": data}
    """
    
    def __init__(
        self,
        handler_id: str | None = None,
        handler_host: str | None = None,
        handler_port: int | None = None,
        server_host: str | None = None,
        server_port: int | None = None,
        registration_retry_interval: int = 15,
    ):
        """Initialize the handler.
        
        Args:
            handler_id: Unique identifier for this handler (default: uses PID)
            handler_host: Host to bind the handler server (default: 127.0.0.1)
            handler_port: Port to bind the handler server (default: 4243)
            server_host: ScheduleZero server host (default: 127.0.0.1)
            server_port: ScheduleZero server port (default: 4242)
            registration_retry_interval: Seconds between registration retries (default: 15)
        """
        self.handler_host = handler_host or os.environ.get(
            "SCHEDULEZERO_HANDLER_HOST", "127.0.0.1"
        )
        self.handler_port = handler_port or int(
            os.environ.get("SCHEDULEZERO_HANDLER_PORT", 4243)
        )
        self.handler_id = handler_id or os.environ.get(
            "SCHEDULEZERO_HANDLER_ID", f"example-handler-{self.handler_host}-{self.handler_port}"
        )
        self.handler_address = f"tcp://{self.handler_host}:{self.handler_port}"
        
        self.server_host = server_host or os.environ.get(
            "SCHEDULEZERO_SERVER_HOST", "127.0.0.1"
        )
        self.server_port = server_port or int(
            os.environ.get("SCHEDULEZERO_SERVER_PORT", 4242)
        )
        self.server_address = f"tcp://{self.server_host}:{self.server_port}"
        
        self.registration_retry_interval = registration_retry_interval
        
        # Internal state
        self._shutdown_event = threading.Event()
        self._registration_thread = None
        self._is_registered = False
        self._handler_server = None
        self._logger = logging.getLogger(self.handler_id)
    
    def get_registered_methods(self) -> List[str]:
        """Get list of methods to register with the server.
        
        Returns all public methods (not starting with _) except the base class methods.
        """
        methods = [
            name for name in dir(self)
            if callable(getattr(self, name))
            and not name.startswith("_")
            and name not in [
                "get_registered_methods", "run", "shutdown", "ping",
                "manage_registration", "handle_signal"
            ]
        ]
        return methods
    
    def ping(self) -> str:
        """Health check endpoint for the server.
        
        Returns:
            "pong" string to indicate handler is alive
        """
        self._logger.debug("Received ping")
        return "pong"
    
    def manage_registration(self):
        """Runs in a thread to register/maintain registration with the server."""
        client = None
        methods_to_register = self.get_registered_methods()
        self._logger.info(f"Handler methods to register: {methods_to_register}")

        while not self._shutdown_event.is_set():
            if client is None:
                try:
                    self._logger.info(
                        f"Attempting to connect to server at {self.server_address} for registration..."
                    )
                    client = zerorpc.Client(timeout=10, heartbeat=5)
                    client.connect(self.server_address)
                    client.ping(timeout=5)
                    self._is_registered = False
                    self._logger.info("Connected to server.")
                except (zerorpc.TimeoutExpired, ConnectionRefusedError, Exception) as e:
                    self._logger.warning(
                        f"Failed to connect or ping server for registration: {e}. "
                        f"Retrying in {self.registration_retry_interval}s..."
                    )
                    if client:
                        try:
                            client.close()
                        except Exception:
                            pass
                    client = None
                    self._shutdown_event.wait(self.registration_retry_interval)
                    continue

            # If connected but not registered, try to register
            if not self._is_registered and client:
                try:
                    self._logger.info(
                        f"Attempting to register as '{self.handler_id}' at {self.handler_address}..."
                    )
                    success = client.register(
                        self.handler_id, self.handler_address, methods_to_register
                    )
                    if success:
                        self._is_registered = True
                        self._logger.info("Registration successful.")
                    else:
                        self._logger.warning(
                            "Registration reported failed by server. Retrying connection..."
                        )
                        try:
                            client.close()
                        except Exception:
                            pass
                        client = None
                        self._shutdown_event.wait(self.registration_retry_interval)

                except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
                    self._logger.warning(
                        f"Registration attempt failed (timeout/lost remote): {e}. "
                        "Assuming disconnected, will retry connection."
                    )
                    self._is_registered = False
                    if client:
                        try:
                            client.close()
                        except Exception:
                            pass
                    client = None
                    self._shutdown_event.wait(self.registration_retry_interval)
                    continue

            # If registered and connected, periodically ping to check connection health
            if self._is_registered and client:
                wait_interval = self.registration_retry_interval * 2
                self._logger.debug(f"Registered. Checking connection in {wait_interval}s...")
                shutdown_signaled = self._shutdown_event.wait(wait_interval)
                if shutdown_signaled:
                    break

                if not self._shutdown_event.is_set() and client:
                    try:
                        self._logger.debug("Pinging server for health check...")
                        client.ping(timeout=5)
                        self._logger.debug("Server ping successful.")
                    except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
                        self._logger.warning(
                            f"Server connection lost or ping failed: {e}. "
                            "Will attempt to re-register."
                        )
                        self._is_registered = False
                        if client:
                            try:
                                client.close()
                            except Exception:
                                pass
                        client = None

        # Shutdown sequence for this thread
        self._logger.info("Registration thread stopping...")
        if self._is_registered and client:
            try:
                self._logger.info("Attempting to report 'offline' status to server...")
                client.report_status(self.handler_id, 'offline', timeout=5)
                self._logger.info("Successfully reported 'offline' status.")
            except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
                self._logger.warning(f"Could not report offline status during shutdown: {e}")
        if client:
            try:
                client.close()
                self._logger.info("Registration client connection closed.")
            except Exception as e:
                self._logger.warning(f"Error closing registration client connection: {e}")
        self._logger.info("Registration thread finished.")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if not self._shutdown_event.is_set():
            self._logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
            self._shutdown_event.set()

    def run(self):
        """Start the handler server and registration process.
        
        This method blocks until the handler is shut down via signal or error.
        """
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

        self._logger.info(f"Starting registration thread for handler '{self.handler_id}'...")
        self._registration_thread = threading.Thread(
            target=self.manage_registration, daemon=True
        )
        self._registration_thread.start()

        self._logger.info(f"Starting zerorpc handler server on {self.handler_address}...")
        self._handler_server = zerorpc.Server(self)
        try:
            self._handler_server.bind(self.handler_address)
        except Exception as e:
            self._logger.critical(
                f"Failed to bind handler server to {self.handler_address}: {e}",
                exc_info=True
            )
            self._shutdown_event.set()
            if self._registration_thread and self._registration_thread.is_alive():
                self._registration_thread.join(timeout=5)
            sys.exit(1)

        # Run the server loop
        import gevent
        
        try:
            self._logger.info(f"Handler server running. Press Ctrl+C to stop.")
            
            # Start the zerorpc server in a greenlet
            server_greenlet = gevent.spawn(self._handler_server.run)
            
            # Monitor for shutdown
            while not self._shutdown_event.is_set():
                gevent.sleep(0.5)
                
                # Check if server greenlet died
                if server_greenlet.dead:
                    if server_greenlet.exception:
                        self._logger.error(
                            f"Handler server greenlet died with exception: {server_greenlet.exception}"
                        )
                    break
            
            # Shutdown - stop the server greenlet
            if not server_greenlet.dead:
                server_greenlet.kill()
            
        except KeyboardInterrupt:
            self._logger.info("Keyboard interrupt received.")
        except Exception as e:
            self._logger.error(f"Unhandled exception in server run: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown of the handler."""
        self._logger.info("Handler server loop finished or interrupted.")
        self._shutdown_event.set()

        if self._handler_server:
            try:
                self._handler_server.close()
                self._logger.info("Handler server closed.")
            except Exception as e:
                self._logger.error(f"Error closing handler server: {e}", exc_info=True)

        self._logger.info("Waiting for registration thread to finish...")
        if self._registration_thread and self._registration_thread.is_alive():
            self._registration_thread.join(timeout=10)
            if self._registration_thread.is_alive():
                self._logger.warning("Registration thread did not exit cleanly.")

        self._logger.info(f"Handler '{self.handler_id}' shut down.")
