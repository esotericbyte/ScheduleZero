"""
Schedule quick tests for the DingAling handler.

This script schedules rapid feedback tests using the lightweight
DingAling handler for fast development iteration.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Configuration - Connect to CLOCK deployment
CLOCK_SERVER_URL = "http://127.0.0.1:8889"
HANDLER_ID = "ding-aling"

def schedule_quick_test():
    """Schedule a series of quick tests."""
    print("🚀 Scheduling DingAling rapid tests...")
    
    base_time = datetime.now() + timedelta(seconds=10)
    
    tests = [
        # Quick feedback loop tests
        {
            "time": base_time,
            "method": "visual_ping",
            "args": {"message": "Development test started!"},
            "name": "Visual Start"
        },
        {
            "time": base_time + timedelta(seconds=5),
            "method": "quick_aling",
            "args": {"message": "First quick test"},
            "name": "Quick Aling"
        },
        {
            "time": base_time + timedelta(seconds=10),
            "method": "double_aling", 
            "args": {"message": "Double test"},
            "name": "Double Aling"
        },
        {
            "time": base_time + timedelta(seconds=15),
            "method": "counter_test",
            "args": {"increment": 5},
            "name": "Counter Test"
        },
        {
            "time": base_time + timedelta(seconds=20),
            "method": "test_sequence",
            "args": {"sequence_name": "rapid_dev_test"},
            "name": "Test Sequence"
        },
        {
            "time": base_time + timedelta(seconds=25),
            "method": "triple_aling",
            "args": {"message": "Final test"},
            "name": "Triple Aling"
        },
        {
            "time": base_time + timedelta(seconds=30),
            "method": "visual_ping",
            "args": {"message": "Development test completed!"},
            "name": "Visual End"
        }
    ]
    
    # Schedule each test
    scheduled_count = 0
    for test in tests:
        try:
            payload = {
                "handler_id": HANDLER_ID,
                "method": test["method"],
                "args": test["args"],
                "trigger_type": "date",
                "trigger_args": {
                    "run_date": test["time"].isoformat()
                }
            }
            
            response = requests.post(f"{CLOCK_SERVER_URL}/api/schedule", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {test['name']:15} scheduled at {test['time'].strftime('%H:%M:%S')} (ID: {result.get('job_id', 'unknown')})")
                scheduled_count += 1
            else:
                print(f"❌ Failed to schedule {test['name']}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error scheduling {test['name']}: {e}")
    
    print(f"\n🎯 Scheduled {scheduled_count}/{len(tests)} rapid tests")
    print(f"⏰ Tests start at: {base_time.strftime('%H:%M:%S')}")
    print(f"📊 Total duration: ~35 seconds")
    print(f"🎵 Watch the DingAling handler for rapid feedback!")
    
    return scheduled_count


def schedule_rapid_iteration():
    """Schedule tests every 30 seconds for rapid development."""
    print("⚡ Scheduling rapid iteration tests (every 30 seconds)...")
    
    base_time = datetime.now() + timedelta(seconds=5)
    
    # Create 10 rapid tests, 30 seconds apart
    methods = ["quick_aling", "double_aling", "visual_ping", "counter_test", "test_sequence"]
    scheduled_count = 0
    
    for i in range(10):
        method = methods[i % len(methods)]
        run_time = base_time + timedelta(seconds=i * 30)
        
        try:
            payload = {
                "handler_id": HANDLER_ID,
                "method": method,
                "args": {"message": f"Rapid test #{i+1}"},
                "trigger_type": "date", 
                "trigger_args": {
                    "run_date": run_time.isoformat()
                }
            }
            
            response = requests.post(f"{CLOCK_SERVER_URL}/api/schedule", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Test #{i+1:2d}: {method:15} at {run_time.strftime('%H:%M:%S')} (ID: {result.get('job_id', 'unknown')})")
                scheduled_count += 1
            else:
                print(f"❌ Failed to schedule test #{i+1}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error scheduling test #{i+1}: {e}")
    
    print(f"\n⚡ Scheduled {scheduled_count} rapid iteration tests")
    print(f"🕒 One test every 30 seconds for {scheduled_count * 30 // 60} minutes")
    
    return scheduled_count


def schedule_stress_test():
    """Schedule rapid-fire tests for stress testing."""
    print("🔥 Scheduling stress test (rapid-fire alings)...")
    
    base_time = datetime.now() + timedelta(seconds=5)
    scheduled_count = 0
    
    # 20 tests, 3 seconds apart
    for i in range(20):
        run_time = base_time + timedelta(seconds=i * 3)
        
        try:
            payload = {
                "handler_id": HANDLER_ID,
                "method": "quick_aling",
                "args": {"message": f"Stress test #{i+1}"},
                "trigger_type": "date",
                "trigger_args": {
                    "run_date": run_time.isoformat()
                }
            }
            
            response = requests.post(f"{CLOCK_SERVER_URL}/api/schedule", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Stress #{i+1:2d}: {run_time.strftime('%H:%M:%S')} (ID: {result.get('job_id', 'unknown')})")
                scheduled_count += 1
            else:
                print(f"❌ Failed to schedule stress test #{i+1}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error scheduling stress test #{i+1}: {e}")
    
    print(f"\n🔥 Scheduled {scheduled_count} stress tests")
    print(f"⏱️  One test every 3 seconds for 1 minute")
    
    return scheduled_count


def main():
    """Main entry point."""
    print(f"""
🎯 DingAling Test Scheduler
══════════════════════════

Server: {CLOCK_SERVER_URL}
Handler: {HANDLER_ID}

Available test patterns:
  1. Quick Test     - 7 tests over 35 seconds
  2. Rapid Iteration - 10 tests every 30 seconds  
  3. Stress Test    - 20 tests every 3 seconds
  4. Exit

""")
    
    while True:
        try:
            choice = input("Select test pattern (1-4): ").strip()
            
            if choice == "1":
                schedule_quick_test()
                break
            elif choice == "2":
                schedule_rapid_iteration()
                break
            elif choice == "3":
                schedule_stress_test()
                break
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break


if __name__ == "__main__":
    main()