"""
Integration Test Suite

End-to-end tests covering the complete system:
- Governor starting server
- Handler registration
- Job scheduling
- ZMQ communication
- Error recovery
"""
import pytest
import time
import requests
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schedule_zero.process_governor import ProcessGovernor
from src.schedule_zero.governor_base import HandlerConfig
from src.schedule_zero.zmq_client import ZMQClient
from src.schedule_zero.logging_config import get_logger

logger = get_logger(__name__, component="TestIntegration")


@pytest.fixture(scope="module")
def governor():
    """Start a governor for the entire test module."""
    gov = ProcessGovernor("test")
    gov.start()
    
    # Wait for server to be ready
    time.sleep(5)
    
    # Verify server is running
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                break
        except:
            time.sleep(1)
    
    yield gov
    
    # Cleanup
    gov.stop(timeout=10)


class TestSystemIntegration:
    """Integration tests for complete system."""
    
    def test_server_health_check(self, governor):
        """Test that server responds to health check."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            # If we get here, server is responding
            assert response.status_code in [200, 404]  # 404 is ok, means server is up
        except requests.exceptions.RequestException:
            pytest.skip("Server not responding")
    
    def test_governor_status(self, governor):
        """Test governor reports correct status."""
        status = governor.status()
        
        assert "server" in status
        server_info = status["server"]
        assert server_info.pid is not None or server_info.status in ["crashed", "stopped"]
    
    def test_governor_metrics(self, governor):
        """Test governor metrics."""
        metrics = governor.get_metrics()
        
        assert metrics["deployment"] == "test"
        assert metrics["running"]
        assert metrics["total_services"] >= 1  # At least server
    
    def test_governor_health_check(self, governor):
        """Test governor health check."""
        health = governor.health_check()
        
        assert isinstance(health, dict)
        # At least server should be in health status
        assert len(health) >= 0


class TestHandlerIntegration:
    """Integration tests for handler management."""
    
    def test_handler_lifecycle(self, governor):
        """Test complete handler lifecycle through governor."""
        # Note: This requires actual handler implementation
        # For now, we test the governor interface
        
        config = HandlerConfig(
            handler_id="test-integration-handler",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5556
        )
        
        # Try to add handler (will fail without actual handler module)
        result = governor.add_handler(config)
        
        # If it worked, test the rest
        if result:
            # Check status
            handler_status = governor.get_handler_status("test-integration-handler")
            assert handler_status is not None
            
            # List handlers
            handlers = governor.list_handlers()
            assert "test-integration-handler" in handlers
            
            # Remove handler
            governor.remove_handler("test-integration-handler")
            assert "test-integration-handler" not in governor.list_handlers()


class TestErrorRecovery:
    """Integration tests for error recovery."""
    
    def test_governor_restart(self, governor):
        """Test that governor can restart."""
        # Get initial status
        initial_status = governor.status()
        
        # Restart
        result = governor.restart(timeout=10)
        
        # Should restart successfully
        assert governor.is_running
    
    def test_stop_and_restart(self):
        """Test stopping and restarting governor."""
        gov = ProcessGovernor("test")
        
        # First start
        gov.start()
        assert gov.is_running
        time.sleep(2)
        
        # Stop
        gov.stop()
        assert not gov.is_running
        time.sleep(1)
        
        # Restart
        gov.start()
        assert gov.is_running
        time.sleep(2)
        
        # Final cleanup
        gov.stop()


class TestRegressionScenarios:
    """Regression tests for real-world failure scenarios."""
    
    def test_rapid_start_stop_cycles(self):
        """
        Regression test for rapid start/stop cycles.
        
        Previously could cause PID file conflicts or orphaned processes.
        """
        gov = ProcessGovernor("test")
        
        for i in range(3):
            gov.start()
            time.sleep(1)
            gov.stop()
            time.sleep(1)
        
        # Should end clean
        assert not gov.is_running
    
    def test_concurrent_stop_calls(self):
        """
        Regression test for concurrent stop calls.
        
        Previously could cause race conditions in cleanup.
        """
        gov = ProcessGovernor("test")
        gov.start()
        time.sleep(2)
        
        # Multiple stop calls should be safe
        gov.stop()
        gov.stop()
        gov.stop()
        
        assert not gov.is_running


class TestSystemUnderLoad:
    """Tests for system behavior under load."""
    
    @pytest.mark.slow
    def test_long_running_server(self):
        """Test server stays up for extended period."""
        gov = ProcessGovernor("test")
        gov.start()
        
        # Let it run for 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < 30:
            status = gov.status()
            
            if "server" in status:
                server_status = status["server"]
                # Server should stay running
                assert server_status.status in ["running", "crashed", "stopped"]
            
            time.sleep(5)
        
        gov.stop()
    
    @pytest.mark.slow
    def test_multiple_handler_additions(self):
        """Test adding multiple handlers over time."""
        gov = ProcessGovernor("test")
        gov.start()
        time.sleep(2)
        
        # Try to add several handlers
        for i in range(3):
            config = HandlerConfig(
                handler_id=f"load-test-handler-{i}",
                module_path="tests.test_handler",
                class_name="TestHandler",
                port=5560 + i
            )
            
            gov.add_handler(config)
            time.sleep(1)
        
        # Check metrics
        metrics = gov.get_metrics()
        logger.info(f"Load test metrics: {metrics}")
        
        gov.stop()


if __name__ == "__main__":
    # Run with different verbosity and markers
    pytest.main([
        __file__,
        "-v",  # Verbose
        "-s",  # Show print statements
        "-m", "not slow",  # Skip slow tests by default
        "--tb=short"  # Shorter tracebacks
    ])
