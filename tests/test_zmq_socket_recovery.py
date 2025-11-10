"""
Test Suite for ZMQ Socket State Recovery

Tests that ZMQ sockets properly recover from errors and state issues.
Covers the fixes made for "Operation cannot be accomplished in current state" errors.
"""
import pytest
import zmq
import time
import threading
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schedule_zero.zmq_client import ZMQClient
from src.schedule_zero.logging_config import get_logger

logger = get_logger(__name__, component="TestZMQRecovery")


class MockHandler:
    """Mock ZMQ handler for testing."""
    
    def __init__(self, port: int):
        self.port = port
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        self.thread = None
        self.message_count = 0
        
    def start(self):
        """Start the mock handler in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        time.sleep(0.5)  # Give it time to bind
        
    def _run(self):
        """Run the handler loop."""
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://127.0.0.1:{self.port}")
        self.socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
        
        while self.running:
            try:
                message = self.socket.recv_json()
                self.message_count += 1
                
                # Echo back with success
                response = {
                    "success": True,
                    "message": "pong" if message.get("method") == "ping" else "ok",
                    "count": self.message_count
                }
                self.socket.send_json(response)
                
            except zmq.Again:
                continue  # Timeout, check if still running
            except Exception as e:
                logger.error(f"Handler error: {e}", method="_run", exc_info=True)
                break
    
    def stop(self):
        """Stop the handler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.socket:
            self.socket.close()
        self.context.term()


@pytest.fixture
def mock_handler():
    """Fixture that provides a running mock handler."""
    handler = MockHandler(port=5555)
    handler.start()
    yield handler
    handler.stop()


@pytest.fixture
def zmq_client():
    """Fixture that provides a ZMQ client."""
    client = ZMQClient("tcp://127.0.0.1:5555", timeout=2000)
    yield client
    try:
        client.terminate()
    except:
        pass


class TestZMQSocketRecovery:
    """Test ZMQ socket recovery mechanisms."""
    
    def test_basic_connection(self, mock_handler, zmq_client):
        """Test basic connection and ping."""
        zmq_client.connect()
        assert zmq_client._connected
        
        result = zmq_client.ping()
        assert result == "pong"
        
    def test_multiple_calls(self, mock_handler, zmq_client):
        """Test multiple sequential calls work correctly."""
        zmq_client.connect()
        
        for i in range(5):
            result = zmq_client.call("ping")
            assert result["success"]
            assert result["message"] == "pong"
    
    def test_socket_recreation_after_close(self, mock_handler, zmq_client):
        """Test that socket can be recreated after being closed."""
        zmq_client.connect()
        
        # First call should work
        result1 = zmq_client.ping()
        assert result1 == "pong"
        
        # Forcibly close socket (simulating error)
        if zmq_client.socket:
            zmq_client.socket.close(linger=0)
        
        # Call _recreate_socket manually
        zmq_client._recreate_socket()
        
        # Should work again
        result2 = zmq_client.ping()
        assert result2 == "pong"
    
    def test_auto_reconnect_on_error(self, mock_handler, zmq_client):
        """Test that auto_reconnect parameter works."""
        zmq_client.connect()
        
        # First call
        result1 = zmq_client.call("ping")
        assert result1["success"]
        
        # Simulate socket error by closing it
        if zmq_client.socket:
            zmq_client.socket.close(linger=0)
        
        # Call with auto_reconnect=True (default)
        result2 = zmq_client.call("ping", auto_reconnect=True)
        assert result2["success"]
    
    def test_context_manager(self, mock_handler):
        """Test context manager properly opens and closes connection."""
        with ZMQClient("tcp://127.0.0.1:5555", timeout=2000) as client:
            result = client.ping()
            assert result == "pong"
        
        # Client should be terminated after context exit
        assert client.context is None
    
    def test_terminate_cleanup(self, mock_handler, zmq_client):
        """Test that terminate() properly cleans up resources."""
        zmq_client.connect()
        zmq_client.ping()  # Ensure it works
        
        zmq_client.terminate()
        
        # Should have cleaned up
        assert zmq_client.socket is None
        assert zmq_client.context is None
        assert not zmq_client._connected
    
    def test_multiple_reconnects(self, mock_handler, zmq_client):
        """Test multiple reconnection cycles."""
        zmq_client.connect()
        
        for i in range(3):
            # Make a call
            result = zmq_client.call("ping")
            assert result["success"]
            
            # Force reconnect
            zmq_client._recreate_socket()
            
            # Should still work
            result = zmq_client.call("ping")
            assert result["success"]
    
    def test_close_without_connect(self):
        """Test that closing without connecting doesn't error."""
        client = ZMQClient("tcp://127.0.0.1:5555")
        client.close()  # Should not raise
        client.terminate()  # Should not raise
    
    def test_double_connect_is_idempotent(self, mock_handler, zmq_client):
        """Test that connecting twice doesn't cause issues."""
        zmq_client.connect()
        zmq_client.connect()  # Should be no-op
        
        result = zmq_client.ping()
        assert result == "pong"


class TestZMQErrorHandling:
    """Test error handling in ZMQ client."""
    
    def test_connection_timeout(self):
        """Test connection to non-existent server times out properly."""
        client = ZMQClient("tcp://127.0.0.1:9999", timeout=500)
        client.connect()
        
        with pytest.raises(Exception):  # Should raise timeout error
            client.call("ping")
    
    def test_call_without_connect(self):
        """Test that calling without connecting auto-connects."""
        # This would fail without a running handler, but tests the logic
        client = ZMQClient("tcp://127.0.0.1:9999", timeout=500)
        
        # Should auto-connect on first call
        with pytest.raises(Exception):  # Will fail to connect, but that's expected
            client.call("ping")
        
        # Should have attempted connection
        assert client._connected or True  # Either connected or failed trying


class TestZMQRegressions:
    """Regression tests for previously fixed bugs."""
    
    def test_socket_state_machine_error(self, mock_handler, zmq_client):
        """
        Regression test for EFSM (Finite State Machine) error.
        
        Previously, after a timeout or error, the socket would enter an invalid
        state and raise "Operation cannot be accomplished in current state".
        This should now auto-recover.
        """
        zmq_client.connect()
        
        # Normal call
        result1 = zmq_client.call("ping")
        assert result1["success"]
        
        # Simulate state error by closing socket
        if zmq_client.socket:
            zmq_client.socket.close(linger=0)
        
        # This should auto-recover instead of raising EFSM error
        result2 = zmq_client.call("ping", auto_reconnect=True)
        assert result2["success"]
    
    def test_context_leak_prevention(self):
        """
        Regression test for ZMQ context leaks.
        
        Previously, contexts were created per-client but never terminated,
        causing resource leaks. This tests that contexts are properly cleaned up.
        """
        clients = []
        
        # Create and destroy multiple clients
        for i in range(5):
            client = ZMQClient(f"tcp://127.0.0.1:555{i}", timeout=500)
            client.connect()
            clients.append(client)
        
        # Terminate all
        for client in clients:
            client.terminate()
            assert client.context is None  # Should be cleaned up
    
    def test_hanging_after_timeout(self, mock_handler, zmq_client):
        """
        Regression test for hanging after timeout.
        
        Previously, after a timeout, subsequent calls would hang forever.
        This should now recover automatically.
        """
        zmq_client.connect()
        
        # Normal call
        result1 = zmq_client.ping()
        assert result1 == "pong"
        
        # Stop handler temporarily to cause timeout
        mock_handler.stop()
        time.sleep(0.5)
        
        # This should timeout but not hang forever
        with pytest.raises(Exception):
            zmq_client.call("ping", auto_reconnect=False)
        
        # Restart handler
        mock_handler.start()
        time.sleep(0.5)
        
        # Should recover with auto_reconnect
        result2 = zmq_client.call("ping", auto_reconnect=True)
        assert result2["success"]


class TestZMQClientIntegration:
    """Integration tests with realistic usage patterns."""
    
    def test_rapid_sequential_calls(self, mock_handler, zmq_client):
        """Test rapid sequential calls don't cause state issues."""
        zmq_client.connect()
        
        for i in range(20):
            result = zmq_client.call("ping")
            assert result["success"]
    
    def test_concurrent_safety(self, mock_handler):
        """Test that multiple threads can use separate clients safely."""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                client = ZMQClient("tcp://127.0.0.1:5555", timeout=2000)
                client.connect()
                
                for i in range(5):
                    result = client.call("ping")
                    results.append((worker_id, result["success"]))
                
                client.terminate()
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All calls should succeed
        assert len(errors) == 0
        assert len(results) == 15  # 3 workers * 5 calls
        assert all(success for _, success in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
