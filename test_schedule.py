"""
Simple test script to verify ScheduleZero end-to-end functionality.
Run this after starting the server and handler in separate terminals.
"""
import time
import requests
from datetime import datetime, timedelta

SERVER_URL = "http://127.0.0.1:8888"

def test_handlers_list():
    """Test that we can list registered handlers."""
    print("\n=== Testing Handlers List ===")
    response = requests.get(f"{SERVER_URL}/api/handlers")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {len(data['handlers'])} handlers:")
    for handler in data['handlers']:
        print(f"  - {handler['id']}: {handler['methods']} [{handler['status']}]")
    return data['handlers']

def test_schedule_job(handler_id):
    """Test scheduling a job to run in 10 seconds."""
    print(f"\n=== Testing Job Scheduling ===")
    run_time = (datetime.now() + timedelta(seconds=10)).isoformat()
    
    payload = {
        "handler_id": handler_id,
        "method_name": "do_work",
        "job_params": {
            "message": "Hello from test script!",
            "test_value": 42
        },
        "trigger_config": {
            "type": "date",
            "run_date": run_time
        }
    }
    
    print(f"Scheduling job for {run_time}")
    response = requests.post(f"{SERVER_URL}/api/schedule", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")
    
    if response.status_code == 201:
        schedule_id = data.get('schedule_id')
        print(f"✓ Job scheduled successfully with ID: {schedule_id}")
        return schedule_id
    else:
        print(f"✗ Failed to schedule job: {data}")
        return None

def test_run_now(handler_id):
    """Test running a job immediately."""
    print(f"\n=== Testing Run Now ===")
    
    payload = {
        "handler_id": handler_id,
        "method_name": "another_task",
        "job_params": {
            "param1": "test",
            "param2": 123
        }
    }
    
    print("Requesting immediate execution...")
    response = requests.post(f"{SERVER_URL}/api/run_now", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")
    
    if response.status_code == 200:
        print(f"✓ Job executed successfully")
        print(f"  Result: {data.get('result')}")
        return True
    else:
        print(f"✗ Failed to run job: {data}")
        return False

def main():
    print("=" * 60)
    print("ScheduleZero End-to-End Test")
    print("=" * 60)
    print("\nMake sure you have:")
    print("  1. Server running: poetry run schedule-zero-server")
    print("  2. Handler running: poetry run schedule-zero-handler")
    print("\nWaiting 2 seconds for connections...")
    time.sleep(2)
    
    try:
        # Test 1: List handlers
        handlers = test_handlers_list()
        if not handlers:
            print("\n✗ No handlers found. Make sure handler is running!")
            return
        
        # Use the first handler for testing
        handler_id = handlers[0]['id']
        print(f"\nUsing handler: {handler_id}")
        
        # Test 2: Run now
        test_run_now(handler_id)
        
        # Test 3: Schedule job
        schedule_id = test_schedule_job(handler_id)
        
        if schedule_id:
            print("\n" + "=" * 60)
            print("✓ All tests passed!")
            print("The scheduled job should execute in ~10 seconds.")
            print("Check the handler terminal for execution logs.")
            print("=" * 60)
        else:
            print("\n✗ Some tests failed")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to server. Is it running?")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
