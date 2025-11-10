"""
Pytest configuration and fixtures for ScheduleZero tests.

Provides fixtures for starting/stopping server and handler components.
"""
import pytest
import time
import subprocess
import requests
import psutil
import sqlite3
from pathlib import Path


def cleanup_database():
    """Clean up the test database by removing all schedules and jobs."""
    db_path = Path("schedulezero_jobs.db")
    if not db_path.exists():
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear all schedules and jobs, but keep the schema
        cursor.execute("DELETE FROM job_results")
        cursor.execute("DELETE FROM jobs")
        cursor.execute("DELETE FROM schedules")
        # Don't delete tasks - those are persistent (like job_executor)
        
        conn.commit()
        conn.close()
    except Exception as e:
        # If cleanup fails, just delete the file
        try:
            db_path.unlink()
        except:
            pass


def terminate_process_tree(pid):
    """Terminate a process and all its children using the specific PID."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Terminate children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # Terminate parent
        parent.terminate()
        
        # Wait for termination
        gone, alive = psutil.wait_procs(children + [parent], timeout=5)
        
        # Force kill if still alive
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
                
    except psutil.NoSuchProcess:
        pass  # Process already dead


@pytest.fixture(scope="session")
def server_process():
    """Start the ScheduleZero server for the test session."""
    import logging
    logger = logging.getLogger("conftest.server")
    
    # Clean database before starting server
    logger.info("Cleaning database before test session...")
    cleanup_database()
    
    # Setup log file
    log_dir = Path(__file__).parent / "test_logs"
    log_dir.mkdir(exist_ok=True)
    server_log_file = log_dir / "server.log"
    
    logger.info(f"Starting ScheduleZero Server (logs: {server_log_file})...")
    
    # Capture output to log file
    with open(server_log_file, "w") as log_file:
        proc = subprocess.Popen(
            ["poetry", "run", "python", "-m", "schedule_zero.server"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Store the PID for proper cleanup
        server_pid = proc.pid
        logger.info(f"Server process started with PID: {server_pid}")
    
    # Wait for server to be ready
    max_wait = 30
    server_ready = False
    
    for waited in range(max_wait):
        time.sleep(1)
        
        try:
            response = requests.get("http://127.0.0.1:8888/", timeout=2)
            if response.status_code == 200:
                server_ready = True
                break
        except:
            pass
        
        if proc.poll() is not None:
            # Server died - print last lines of log
            with open(server_log_file) as f:
                log_lines = f.readlines()
                logger.error(f"Server process (PID {server_pid}) exited. Last 20 lines:")
                for line in log_lines[-20:]:
                    logger.error(line.rstrip())
            pytest.fail(f"Server process (PID {server_pid}) exited unexpectedly")
    
    if not server_ready:
        logger.error(f"Server startup timeout, terminating PID {server_pid}")
        terminate_process_tree(server_pid)
        # Print log tail
        with open(server_log_file) as f:
            log_lines = f.readlines()
            logger.error("Server log (last 20 lines):")
            for line in log_lines[-20:]:
                logger.error(line.rstrip())
        pytest.fail("Server startup timeout")
    
    logger.info(f"Server ready (PID: {server_pid})")
    
    yield proc
    
    # Teardown - use the specific PID to terminate
    logger.info(f"Stopping server (PID: {server_pid})...")
    terminate_process_tree(server_pid)
    logger.info("Server stopped")
    
    # Clean database after tests complete
    logger.info("Cleaning database after test session...")
    cleanup_database()


@pytest.fixture(scope="session")
def handler_process(server_process):
    """Start the test handler for the test session (depends on server)."""
    import logging
    logger = logging.getLogger("conftest.handler")
    
    # Setup log file
    log_dir = Path(__file__).parent / "test_logs"
    log_dir.mkdir(exist_ok=True)
    handler_log_file = log_dir / "handler.log"
    
    logger.info(f"Starting Test Handler (logs: {handler_log_file})...")
    
    # Capture output to log file
    with open(handler_log_file, "w") as log_file:
        proc = subprocess.Popen(
            ["poetry", "run", "python", "tests/test_handler.py"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Store the PID for proper cleanup
        handler_pid = proc.pid
        logger.info(f"Handler process started with PID: {handler_pid}")
    
    # Wait for handler to register
    max_wait = 20
    handler_registered = False
    
    for waited in range(max_wait):
        time.sleep(1)
        
        try:
            response = requests.get("http://127.0.0.1:8888/api/handlers", timeout=2)
            data = response.json()
            if any(h.get('id') == 'test-handler-001' for h in data.get('handlers', [])):
                handler_registered = True
                break
        except:
            pass
        
        if proc.poll() is not None:
            # Handler died - print last lines of log
            with open(handler_log_file) as f:
                log_lines = f.readlines()
                logger.error(f"Handler process (PID {handler_pid}) exited. Last 20 lines:")
                for line in log_lines[-20:]:
                    logger.error(line.rstrip())
            pytest.fail(f"Handler process (PID {handler_pid}) exited unexpectedly")
    
    if not handler_registered:
        logger.error(f"Handler registration timeout, terminating PID {handler_pid}")
        terminate_process_tree(handler_pid)
        # Print log tail
        with open(handler_log_file) as f:
            log_lines = f.readlines()
            logger.error("Handler log (last 20 lines):")
            for line in log_lines[-20:]:
                logger.error(line.rstrip())
        pytest.fail("Handler registration timeout")
    
    logger.info(f"Handler registered (PID: {handler_pid})")
    
    yield proc
    
    # Teardown - use the specific PID to terminate
    logger.info(f"Stopping handler (PID: {handler_pid})...")
    terminate_process_tree(handler_pid)
    logger.info("Handler stopped")


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API requests."""
    return "http://127.0.0.1:8888"


@pytest.fixture(scope="session")
def test_handler_id():
    """Test handler ID."""
    return "test-handler-001"


@pytest.fixture
def test_output_dir():
    """Directory for test output files."""
    return Path(__file__).parent / "test_output"
