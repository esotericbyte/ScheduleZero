"""
Pytest configuration and fixtures for ScheduleZero tests.

Provides fixtures for starting/stopping server and handler components.
"""
import pytest
import time
import subprocess
import requests
from pathlib import Path

@pytest.fixture(scope="session")
def server_process():
    """Start the ScheduleZero server for the test session."""
    import logging
    logger = logging.getLogger("conftest.server")
    logger.info("Starting ScheduleZero Server...")
    
    # Don't capture output - let it go to console so we can see errors
    proc = subprocess.Popen(
        ["poetry", "run", "python", "-m", "schedule_zero.server"],
        # stdout=subprocess.PIPE,
        # stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
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
            pytest.fail(f"Server process exited unexpectedly")
    
    if not server_ready:
        proc.terminate()
        pytest.fail("Server startup timeout")
    
    logger.info(f"Server ready (PID: {proc.pid})")
    
    yield proc
    
    # Teardown
    logger.info("Stopping server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    logger.info("Server stopped")


@pytest.fixture(scope="session")
def handler_process(server_process):
    """Start the test handler for the test session (depends on server)."""
    import logging
    logger = logging.getLogger("conftest.handler")
    logger.info("Starting Test Handler...")
    
    # Don't capture output - let it go to console
    proc = subprocess.Popen(
        ["poetry", "run", "python", "tests/test_handler.py"],
        # stdout=subprocess.PIPE,
        # stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
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
            pytest.fail(f"Handler process exited unexpectedly")
    
    if not handler_registered:
        proc.terminate()
        pytest.fail("Handler registration timeout")
    
    logger.info(f"Handler registered (PID: {proc.pid})")
    
    yield proc
    
    # Teardown
    logger.info("Stopping handler...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
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
    return Path("test_output")
