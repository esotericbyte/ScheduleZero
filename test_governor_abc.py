"""
Test the new ProcessGovernor ABC implementation.

This script demonstrates the governor ABC pattern and tests basic operations.
"""
import time
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.schedule_zero.process_governor import ProcessGovernor
from src.schedule_zero.governor_base import HandlerConfig


def test_process_governor_abc():
    """Test basic governor ABC operations."""
    print("=" * 70)
    print("Testing ProcessGovernor ABC Implementation")
    print("=" * 70)
    
    # Create governor for test deployment
    print("\n1. Creating ProcessGovernor for 'test' deployment...")
    governor = ProcessGovernor("test")
    print(f"   Governor created: {governor.__class__.__name__}")
    print(f"   Deployment: {governor.deployment}")
    print(f"   Is running: {governor.is_running}")
    
    # Start governor (will start server)
    print("\n2. Starting governor...")
    if governor.start():
        print("   ✅ Governor started successfully")
    else:
        print("   ❌ Failed to start governor")
        return False
    
    # Wait for server to stabilize
    print("\n3. Waiting for server to stabilize (5 seconds)...")
    time.sleep(5)
    
    # Check status
    print("\n4. Checking service status...")
    status = governor.status()
    for service_name, info in status.items():
        print(f"   {service_name}:")
        print(f"     Status: {info.status}")
        print(f"     PID: {info.pid}")
        print(f"     Restart count: {info.restart_count}")
        if info.last_error:
            print(f"     Last error: {info.last_error}")
    
    # Health check
    print("\n5. Running health check...")
    health = governor.health_check()
    for service, is_healthy in health.items():
        status_icon = "✅" if is_healthy else "❌"
        print(f"   {status_icon} {service}: {'healthy' if is_healthy else 'unhealthy'}")
    
    # Get metrics
    print("\n6. Getting metrics...")
    metrics = governor.get_metrics()
    print(f"   Deployment: {metrics['deployment']}")
    print(f"   Running: {metrics['running']}")
    print(f"   Total services: {metrics['total_services']}")
    print(f"   Healthy services: {metrics['healthy_services']}")
    print(f"   Total restarts: {metrics['total_restarts']}")
    
    # List handlers (should be empty initially)
    print("\n7. Listing handlers...")
    handlers = governor.list_handlers()
    print(f"   Handlers: {handlers if handlers else '(none)'}")
    
    # Stop governor
    print("\n8. Stopping governor...")
    if governor.stop(timeout=10):
        print("   ✅ Governor stopped successfully")
    else:
        print("   ❌ Failed to stop governor cleanly")
    
    # Final status check
    print("\n9. Final status check...")
    final_status = governor.status()
    all_stopped = all(info.status == "stopped" for info in final_status.values())
    if all_stopped:
        print("   ✅ All services stopped")
    else:
        print("   ⚠️  Some services still running:")
        for service_name, info in final_status.items():
            if info.status != "stopped":
                print(f"     {service_name}: {info.status}")
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = test_process_governor_abc()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
