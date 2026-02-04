"""
Test ZMQ socket state recovery.

This script tests that ZMQ sockets properly recover from errors.
"""
import time
import sys
from src.schedule_zero.zmq_client import ZMQClient
from src.schedule_zero.logging_config import get_logger

logger = get_logger(__name__)

def test_socket_recovery():
    """Test that socket can recover from state errors."""
    # This assumes a handler is running on port 4244 (DingAling default)
    client = ZMQClient("tcp://127.0.0.1:4244", timeout=2000)
    
    try:
        # Connect
        logger.info("Connecting to handler...")
        client.connect()
        
        # First ping should work
        logger.info("First ping...")
        result = client.ping()
        logger.info(f"Ping result: {result}")
        
        # Simulate error by closing socket but not recreating
        logger.info("Simulating socket error by closing socket...")
        if client.socket:
            client.socket.close(linger=0)
        
        # Try to call - should auto-recover with auto_reconnect=True (default)
        logger.info("Attempting call after socket closed (should auto-recover)...")
        result = client.call("ping")
        logger.info(f"Recovery call result: {result}")
        
        # Should still work
        logger.info("Final ping after recovery...")
        result = client.ping()
        logger.info(f"Final ping result: {result}")
        
        logger.info("✅ Socket recovery test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Socket recovery test FAILED: {e}", exc_info=True)
        return False
    finally:
        logger.info("Cleaning up...")
        client.terminate()

if __name__ == "__main__":
    success = test_socket_recovery()
    sys.exit(0 if success else 1)
