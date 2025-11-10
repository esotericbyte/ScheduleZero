"""
Test the execution logging API endpoints.

This test uses the 'test' deployment to avoid interfering with
long-running production tests (like ding dong).
"""
import asyncio
import os
import signal
import subprocess
import sys
import time
import requests
from pathlib import Path

# Test deployment configuration
TEST_SERVER_HOST = "127.0.0.1"
TEST_SERVER_PORT = 8890  # Different from default 8888
TEST_ZMQ_PORT = 4299      # Different from default 4242 and test 4244
TEST_HANDLER_PORT = 5099  # Different from default 5000

# Test database (will be cleaned up)
TEST_DB_PATH = Path(__file__).parent / "test_execution_logging.db"

def setup_test_env():
    """Set up environment for test deployment."""
    os.environ["SCHEDULEZERO_DEPLOYMENT"] = "test"
    os.environ["SCHEDULEZERO_DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    os.environ["SCHEDULEZERO_TORNADO_HOST"] = TEST_SERVER_HOST
    os.environ["SCHEDULEZERO_TORNADO_PORT"] = str(TEST_SERVER_PORT)
    os.environ["SCHEDULEZERO_ZMQ_ADDRESS"] = f"tcp://{TEST_SERVER_HOST}:{TEST_ZMQ_PORT}"

def cleanup_test_env():
    """Clean up test environment."""
    if TEST_DB_PATH.exists():
        try:
            # Wait a moment for any file handles to be released
            time.sleep(2)
            TEST_DB_PATH.unlink()
            print(f"✓ Cleaned up test database: {TEST_DB_PATH}")
        except PermissionError:
            print(f"⚠ Could not delete test database (still in use): {TEST_DB_PATH}")
        except Exception as e:
            print(f"⚠ Error cleaning up database: {e}")

def start_server():
    """Start ScheduleZero test server."""
    setup_test_env()
    
    print(f"Starting test server on {TEST_SERVER_HOST}:{TEST_SERVER_PORT}...")
    print(f"Database: {TEST_DB_PATH}")
    print(f"ZMQ: tcp://{TEST_SERVER_HOST}:{TEST_ZMQ_PORT}")
    
    # Use poetry run to ensure we're in the right environment
    # Start server process
    process = subprocess.Popen(
        ["poetry", "run", "python", "-m", "schedule_zero.tornado_app_server"],
        env=os.environ.copy(),
        # Detach from parent on Windows
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    # Wait for server to be ready
    max_wait = 20
    
    for i in range(max_wait):
        # Check if process crashed
        if process.poll() is not None:
            raise RuntimeError(f"Test server crashed with exit code {process.returncode}")
        
        # Try to connect
        try:
            response = requests.get(f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}/api/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Test server ready after {i+1} seconds")
                return process
        except requests.RequestException:
            pass
        
        time.sleep(1)
    
    # Server didn't start in time
    process.kill()
    raise RuntimeError(f"Test server failed to start within {max_wait} seconds")

def stop_server(process):
    """Stop the test server."""
    print("Stopping test server...")
    
    try:
        if sys.platform == "win32":
            # On Windows, send CTRL_BREAK_EVENT to the process group
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGTERM)
        
        process.wait(timeout=5)
        print("✓ Test server stopped")
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        print("✓ Test server killed (timeout)")
    except Exception as e:
        print(f"Warning: Error stopping server: {e}")
        try:
            process.kill()
            process.wait()
        except:
            pass


def test_execution_logging_api():
    """Test all execution logging API endpoints."""
    
    print("\n" + "="*60)
    print("Testing Execution Logging API")
    print("="*60 + "\n")
    
    # Clean up any previous test artifacts
    cleanup_test_env()
    
    # Start test server
    server_process = None
    
    try:
        server_process = start_server()
        
        # Base URL for API requests
        base_url = f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}"
        
        # Give server a moment to fully initialize
        time.sleep(2)
        
        print("\n--- Test 1: Check initial state (should be empty) ---")
        
        response = requests.get(f"{base_url}/api/executions")
        assert response.status_code == 200, f"Get executions failed: {response.text}"
        
        data = response.json()
        print(f"✓ Initial execution count: {data['count']}")
        
        print("\n--- Test 2: Get initial statistics ---")
        
        response = requests.get(f"{base_url}/api/executions/stats")
        assert response.status_code == 200, f"Get stats failed: {response.text}"
        
        stats = response.json()
        print(f"✓ Total executions: {stats['total_executions']}")
        print(f"  Success count: {stats['success_count']}")
        print(f"  Error count: {stats['error_count']}")
        
        if stats['total_executions'] > 0:
            print(f"  Success rate: {stats.get('success_rate', 0):.2f}%")
            print(f"  Avg duration: {stats.get('average_duration_ms', 0):.2f}ms")
            
            if stats.get('by_handler'):
                print("\n  By handler:")
                for handler_id, handler_stats in stats['by_handler'].items():
                    print(f"    {handler_id}: {handler_stats['total']} executions, "
                          f"{handler_stats.get('success_rate', 0):.1f}% success")
        
        print("\n--- Test 3: Get errors (if any) ---")
        
        response = requests.get(f"{base_url}/api/executions/errors?limit=10")
        assert response.status_code == 200, f"Get errors failed: {response.text}"
        
        errors = response.json()
        print(f"✓ Found {errors['count']} errors")
        
        if errors['count'] > 0:
            print("\nRecent errors:")
            for error in errors['errors'][:3]:
                print(f"  - {error['job_id']}: {error.get('error', 'Unknown error')}")
        
        print("\n--- Test 4: Query with filters ---")
        
        # Try to query by handler (if we have any executions)
        if stats['total_executions'] > 0 and stats.get('by_handler'):
            first_handler = list(stats['by_handler'].keys())[0]
            response = requests.get(f"{base_url}/api/executions?handler_id={first_handler}&limit=5")
            assert response.status_code == 200, f"Query by handler failed: {response.text}"
            
            data = response.json()
            print(f"✓ Found {data['count']} executions for handler '{first_handler}'")
        else:
            print("✓ Skipping (no executions yet)")
        
        print("\n--- Test 5: Test pagination ---")
        
        response = requests.get(f"{base_url}/api/executions?limit=5")
        assert response.status_code == 200, f"Pagination test failed: {response.text}"
        
        data = response.json()
        print(f"✓ Requested limit=5, got {data['count']} records")
        
        print("\n--- Test 6: Clear execution history (admin operation) ---")
        
        # Get count before clearing
        response = requests.get(f"{base_url}/api/executions")
        before_count = response.json()['count']
        
        # Clear
        response = requests.post(f"{base_url}/api/executions/clear")
        assert response.status_code == 200, f"Clear history failed: {response.text}"
        
        result = response.json()
        print(f"✓ Cleared {result.get('records_cleared', 0)} records (had {before_count})")
        
        # Verify history is empty
        response = requests.get(f"{base_url}/api/executions")
        data = response.json()
        assert data['count'] == 0, f"History not empty after clear: {data['count']}"
        print(f"✓ Confirmed: 0 records remaining")
        
        print("\n--- Test 7: Verify API response format ---")
        
        # Check that all endpoints return proper JSON
        endpoints = [
            ("/api/executions", "GET"),
            ("/api/executions/stats", "GET"),
            ("/api/executions/errors", "GET"),
        ]
        
        for endpoint, method in endpoints:
            response = requests.request(method, f"{base_url}{endpoint}")
            assert response.status_code == 200, f"{endpoint} failed"
            assert response.headers.get('Content-Type', '').startswith('application/json'), \
                f"{endpoint} didn't return JSON"
            # Verify JSON is parseable
            data = response.json()
            print(f"✓ {endpoint}: Valid JSON response")
        
        print("\n" + "="*60)
        print("✅ All execution logging API tests passed!")
        print("="*60 + "\n")
        
        print("💡 Note: To test with actual job executions:")
        print("   1. Start a handler (e.g., DingDong)")
        print("   2. Schedule jobs via /api/schedule")
        print("   3. Watch execution data accumulate")
        print("   4. Query /api/executions to see the logs")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        if server_process:
            stop_server(server_process)
        
        # Clean up test database
        time.sleep(1)
        cleanup_test_env()

if __name__ == "__main__":
    success = test_execution_logging_api()
    sys.exit(0 if success else 1)
