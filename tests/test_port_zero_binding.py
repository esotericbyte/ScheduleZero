"""
Test that handlers correctly use port 0 binding (OS-assigned ports).

This verifies that multiple handlers can start simultaneously without
port conflicts.
"""
import sys
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.zmq_handler_base import ZMQHandlerBase

class SimpleHandler(ZMQHandlerBase):
    """Minimal test handler."""
    
    def test_method(self, params):
        """Simple test method."""
        return {"success": True, "message": "Test method called"}

def test_multiple_handlers_no_conflicts():
    """Test that multiple handlers can bind without port conflicts."""
    
    print("\n" + "="*60)
    print("Testing Port 0 Binding (OS-Assigned Ports)")
    print("="*60 + "\n")
    
    handlers = []
    server_address = "tcp://127.0.0.1:4242"  # Doesn't need to exist for this test
    
    try:
        # Create 5 handlers - all with same "hint" address
        print("Creating 5 handlers with same address hint...")
        for i in range(5):
            handler = SimpleHandler(
                handler_id=f"test_handler_{i}",
                handler_address="tcp://127.0.0.1:5000",  # Same hint for all
                server_address=server_address,
                max_registration_retries=0  # Don't try to register (no server running)
            )
            handlers.append(handler)
        
        print("✓ All handlers created\n")
        
        # Start all handlers (just the server thread, not registration)
        print("Starting handler servers...")
        for handler in handlers:
            # Start just the server thread
            handler.server_thread = threading.Thread(
                target=handler._run_handler_server, 
                daemon=True
            )
            handler.server_thread.start()
        
        # Wait for all to bind
        time.sleep(1)
        
        # Check all got unique addresses
        print("\nHandler addresses:")
        addresses = []
        ports = []
        
        for handler in handlers:
            if handler.handler_address:
                print(f"  {handler.handler_id}: {handler.handler_address}")
                addresses.append(handler.handler_address)
                
                # Extract port
                port = handler.handler_address.split(":")[-1]
                ports.append(port)
            else:
                print(f"  {handler.handler_id}: FAILED TO BIND")
        
        # Verify all bound successfully
        assert len(addresses) == 5, f"Expected 5 handlers to bind, got {len(addresses)}"
        print(f"\n✓ All 5 handlers bound successfully")
        
        # Verify all got different ports
        unique_ports = set(ports)
        assert len(unique_ports) == 5, f"Expected 5 unique ports, got {len(unique_ports)}: {ports}"
        print(f"✓ All handlers got unique ports: {sorted(ports)}")
        
        # Verify all ports are in ephemeral range (typically > 1024)
        for port in ports:
            port_num = int(port)
            assert port_num > 1024, f"Port {port_num} is not in ephemeral range"
        print(f"✓ All ports in valid ephemeral range (>1024)")
        
        print("\n" + "="*60)
        print("✅ Port 0 binding test PASSED!")
        print("="*60 + "\n")
        
        print("Summary:")
        print(f"  - Created 5 handlers with identical address hints")
        print(f"  - All bound successfully without conflicts")
        print(f"  - OS assigned unique ports: {', '.join(sorted(ports))}")
        print(f"  - No race conditions, no retries needed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        for handler in handlers:
            handler.shutdown_event.set()
            if handler.server_thread and handler.server_thread.is_alive():
                handler.server_thread.join(timeout=2)
        print("✓ Cleanup complete")

if __name__ == "__main__":
    success = test_multiple_handlers_no_conflicts()
    sys.exit(0 if success else 1)
