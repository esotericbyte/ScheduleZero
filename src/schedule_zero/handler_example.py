import zerorpc
import time
import logging
import signal
import threading
import random
import os
import sys
from datetime import datetime

# --- Configuration ---
HANDLER_ID = os.environ.get("SCHEDULEZERO_HANDLER_ID", f"example_handler_{os.getpid()}") # More unique ID by default
HANDLER_HOST = os.environ.get("SCHEDULEZERO_HANDLER_HOST", "127.0.0.1") # Changed from 0.0.0.0
HANDLER_PORT = int(os.environ.get("SCHEDULEZERO_HANDLER_PORT", 4243))
HANDLER_ADDRESS = f"tcp://{HANDLER_HOST}:{HANDLER_PORT}" # Address this handler listens on

SERVER_HOST = os.environ.get("SCHEDULEZERO_SERVER_HOST", "127.0.0.1") # Central server host
SERVER_PORT = int(os.environ.get("SCHEDULEZERO_SERVER_PORT", 4242)) # Central server port
SERVER_ADDRESS = f"tcp://{SERVER_HOST}:{SERVER_PORT}" # Address of the central ScheduleZero server

REGISTRATION_RETRY_INTERVAL = 15 # Seconds

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(HANDLER_ID)

# --- Global State ---
shutdown_event = threading.Event()
registration_thread = None
is_registered = False
handler_server = None # Global reference to the server instance

# --- Job Functions ---
class HandlerService:
    def do_work(self, params: dict):
        """Example job method that receives parameters as a dictionary."""
        data = params.get("data", "No data")
        number = params.get("number", 0)
        logger.info(f"Received job 'do_work': data='{data}', number={number}. Simulating work...")
        # Simulate work that might fail sometimes
        if random.random() < 0.1: # 10% chance of failure
            logger.error("'do_work' encountered a simulated error!")
            raise ValueError("Simulated processing error in do_work")
        time.sleep(random.uniform(1, 3)) # Simulate work duration
        logger.info("'do_work' finished successfully.")
        return {"status": "completed", "result": f"Processed '{data}' with number {number}", "timestamp": datetime.utcnow().isoformat()}

    def another_task(self, params: dict):
        """Another example task."""
        task_id = params.get("task_id", "unknown")
        logger.info(f"Received job 'another_task': task_id='{task_id}'. Simulating short work...")
        time.sleep(0.5)
        logger.info("'another_task' finished.")
        return {"status": "ok", "task_id": task_id}

    def ping(self) -> str:
        """Simple ping for health checks from the server."""
        logger.debug("Received ping")
        return "pong"

# --- Registration Logic ---
def manage_registration():
    """Runs in a thread to register/maintain registration with the server."""
    global is_registered
    client = None
    # Dynamically find methods in HandlerService to register
    methods_to_register = [
        name for name, func in HandlerService.__dict__.items()
        if callable(func) and not name.startswith("_")
    ]
    logger.info(f"Handler methods to register: {methods_to_register}")

    while not shutdown_event.is_set():
        if client is None:
            try:
                logger.info(f"Attempting to connect to server at {SERVER_ADDRESS} for registration...")
                # Add a timeout for the connection attempt itself
                client = zerorpc.Client(timeout=10, heartbeat=5) # RPC timeout 10s, heartbeat 5s
                # Connect might block, consider wrapping if this thread needs responsiveness
                client.connect(SERVER_ADDRESS)
                # Verify connection with a ping immediately
                client.ping(timeout=5)
                is_registered = False # Reset flag on new connection attempt
                logger.info("Connected to server.")
            except (zerorpc.TimeoutExpired, ConnectionRefusedError, Exception) as e:
                logger.warning(f"Failed to connect or ping server for registration: {e}. Retrying in {REGISTRATION_RETRY_INTERVAL}s...")
                if client: try: client.close()
                except Exception: pass
                client = None # Ensure client is None if connect/ping fails
                # Wait for interval or until shutdown is signaled
                shutdown_event.wait(REGISTRATION_RETRY_INTERVAL)
                continue # Go back to start of loop to retry connection

        # If connected but not registered, try to register
        if not is_registered and client:
            try:
                logger.info(f"Attempting to register as '{HANDLER_ID}' at {HANDLER_ADDRESS}...")
                success = client.register_handler(HANDLER_ID, HANDLER_ADDRESS, methods_to_register)
                if success:
                    is_registered = True
                    logger.info("Registration successful.")
                else:
                    logger.warning("Registration reported failed by server. Retrying connection...")
                    # Close client and retry connection after delay
                    try: client.close()
                    except Exception: pass
                    client = None
                    shutdown_event.wait(REGISTRATION_RETRY_INTERVAL)

            except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
                logger.warning(f"Registration attempt failed (timeout/lost remote): {e}. Assuming disconnected, will retry connection.")
                is_registered = False
                if client:
                    try: client.close()
                    except Exception: pass
                client = None
                # Wait before retrying connection in the next loop iteration
                shutdown_event.wait(REGISTRATION_RETRY_INTERVAL)
                continue # Go back to start of loop

        # If registered and connected, periodically ping to check connection health
        if is_registered and client:
            wait_interval = REGISTRATION_RETRY_INTERVAL * 2 # Check less frequently once registered
            logger.debug(f"Registered. Checking connection in {wait_interval}s...")
            # Wait for the interval OR until shutdown is signaled
            shutdown_signaled = shutdown_event.wait(wait_interval)
            if shutdown_signaled: break # Exit loop immediately if shutdown requested

            # If loop continues (no shutdown), perform a health check ping
            if not shutdown_event.is_set() and client:
                try:
                    logger.debug("Pinging server for health check...")
                    client.ping(timeout=5)
                    logger.debug("Server ping successful.")
                except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
                     logger.warning(f"Server connection lost or ping failed: {e}. Will attempt to re-register.")
                     is_registered = False
                     if client:
                         try: client.close()
                         except Exception: pass
                     client = None
                     # No need to wait here, loop will retry connection immediately next iteration

    # Shutdown sequence for this thread
    logger.info("Registration thread stopping...")
    if is_registered and client:
        try:
            logger.info("Attempting to report 'offline' status to server...")
            # Use a shorter timeout for the final status report
            client.report_status(HANDLER_ID, status='offline', timeout=5)
            logger.info("Successfully reported 'offline' status.")
        except (zerorpc.TimeoutExpired, zerorpc.LostRemote, Exception) as e:
            logger.warning(f"Could not report offline status during shutdown: {e}")
    if client:
        try:
             client.close()
             logger.info("Registration client connection closed.")
        except Exception as e:
            logger.warning(f"Error closing registration client connection: {e}")
    logger.info("Registration thread finished.")


# --- Signal Handling ---
def handle_signal(signum, frame):
    if not shutdown_event.is_set():
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        shutdown_event.set()
        # Optionally try to stop the server from here if run_forever blocks hard
        # if handler_server:
        #     logger.info("Attempting to stop handler server from signal handler...")
        #     handler_server.stop() # zerorpc server doesn't have a simple stop, relies on loop exit

# --- Main Execution ---
if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info(f"Starting registration thread for handler '{HANDLER_ID}'...")
    registration_thread = threading.Thread(target=manage_registration, daemon=True)
    registration_thread.start()

    logger.info(f"Starting zerorpc handler server on {HANDLER_ADDRESS}...")
    handler_server = zerorpc.Server(HandlerService()) # Assign to global var
    try:
        handler_server.bind(HANDLER_ADDRESS)
    except Exception as e:
        logger.critical(f"Failed to bind handler server to {HANDLER_ADDRESS}: {e}", exc_info=True)
        # Signal registration thread to stop if it started
        shutdown_event.set()
        if registration_thread and registration_thread.is_alive():
             registration_thread.join(timeout=5)
        sys.exit(1) # Exit if cannot bind

    # Run the server loop, checking the shutdown event periodically
    try:
        logger.info(f"Handler server running. Press Ctrl+C to stop.")
        while not shutdown_event.is_set():
            # Use gevent loop with timeout if available, otherwise just check event
            try:
                # Get the gevent hub/loop associated with zerorpc
                gevent_core = zerorpc.core.get_hub().get_loop()
                # Run the loop for a short duration to process events & check shutdown
                gevent_core.run(timeout=1)
            except AttributeError:
                # Fallback if gevent hub isn't used or easily accessible
                # This might happen if zerorpc setup changes or gevent isn't main loop
                logger.debug("Gevent loop not directly accessible, using simple wait.")
                shutdown_event.wait(1.0) # Simple sleep check
            except Exception as loop_e:
                logger.error(f"Error in handler server loop: {loop_e}")
                # Avoid tight loop on repeated errors
                if not shutdown_event.is_set(): time.sleep(1)

    except Exception as e:
        logger.error(f"Unhandled exception in server run: {e}", exc_info=True)
    finally:
        logger.info("Handler server loop finished or interrupted.")
        # Ensure shutdown event is set if loop exited unexpectedly
        shutdown_event.set()

        # Close the server instance
        if handler_server:
            try:
                handler_server.close()
                logger.info("Handler server closed.")
            except Exception as e:
                logger.error(f"Error closing handler server: {e}", exc_info=True)

        # Wait for the registration thread to finish its cleanup
        logger.info("Waiting for registration thread to finish...")
        if registration_thread and registration_thread.is_alive():
             registration_thread.join(timeout=10) # Wait for registration thread cleanup
             if registration_thread.is_alive():
                 logger.warning("Registration thread did not exit cleanly.")

        logger.info(f"Handler '{HANDLER_ID}' shut down.")
        sys.exit(0)

