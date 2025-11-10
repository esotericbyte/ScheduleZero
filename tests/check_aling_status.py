"""
Check DingAling handler status and recent activity.

Quick status checker for the rapid development workflow.
"""
import sys
import requests
from pathlib import Path
from datetime import datetime

# Configuration
CLOCK_SERVER_URL = "http://127.0.0.1:8889"
HANDLER_ID = "ding-aling"

def check_handler_status():
    """Check if the DingAling handler is registered and responsive."""
    print("🔍 Checking DingAling handler status...")
    
    try:
        response = requests.get(f"{CLOCK_SERVER_URL}/api/handler_list")
        
        if response.status_code != 200:
            print(f"❌ Failed to connect to server: {response.status_code}")
            return False
            
        handlers = response.json()
        
        # Find our handler
        aling_handler = None
        for handler in handlers:
            if handler.get("handler_id") == HANDLER_ID:
                aling_handler = handler
                break
        
        if aling_handler:
            print(f"✅ DingAling handler is registered!")
            print(f"   ID: {aling_handler.get('handler_id')}")
            print(f"   Address: {aling_handler.get('address')}")
            print(f"   Methods: {len(aling_handler.get('methods', []))} available")
            
            # Show methods
            methods = aling_handler.get('methods', [])
            if methods:
                print(f"   Available methods:")
                for method in methods:
                    print(f"     • {method}")
            
            return True
        else:
            print(f"❌ DingAling handler ({HANDLER_ID}) not found!")
            print(f"   Registered handlers: {[h.get('handler_id') for h in handlers]}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking handler status: {e}")
        return False


def check_scheduled_jobs():
    """Check for scheduled jobs targeting the DingAling handler."""
    print("\n📅 Checking scheduled jobs...")
    
    try:
        response = requests.get(f"{CLOCK_SERVER_URL}/api/schedules")
        
        if response.status_code != 200:
            print(f"❌ Failed to get schedules: {response.status_code}")
            return
            
        schedules = response.json()
        
        # Filter for our handler
        aling_jobs = []
        for job in schedules:
            if job.get("handler_id") == HANDLER_ID:
                aling_jobs.append(job)
        
        if aling_jobs:
            print(f"✅ Found {len(aling_jobs)} scheduled DingAling jobs:")
            
            # Sort by next run time
            aling_jobs.sort(key=lambda x: x.get("next_run_time", ""))
            
            for i, job in enumerate(aling_jobs[:10]):  # Show first 10
                job_id = job.get("id", "unknown")
                method = job.get("method", "unknown")
                next_run = job.get("next_run_time", "unknown")
                
                # Parse next run time for display
                if next_run and next_run != "unknown":
                    try:
                        next_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                        next_display = next_dt.strftime('%H:%M:%S')
                    except:
                        next_display = next_run
                else:
                    next_display = "unknown"
                
                print(f"   {i+1:2d}. {method:15} at {next_display:8} (ID: {job_id})")
            
            if len(aling_jobs) > 10:
                print(f"   ... and {len(aling_jobs) - 10} more jobs")
                
        else:
            print("ℹ️  No scheduled DingAling jobs found")
            
    except Exception as e:
        print(f"❌ Error checking schedules: {e}")


def check_recent_executions():
    """Check recent job executions (if execution logging is available)."""
    print("\n📊 Checking recent activity...")
    
    try:
        # Try to get execution log (this might not exist depending on configuration)
        response = requests.get(f"{CLOCK_SERVER_URL}/api/execution_log")
        
        if response.status_code == 200:
            executions = response.json()
            
            # Filter for our handler
            aling_executions = []
            for exec in executions:
                if exec.get("handler_id") == HANDLER_ID:
                    aling_executions.append(exec)
            
            if aling_executions:
                # Sort by execution time (most recent first)
                aling_executions.sort(key=lambda x: x.get("executed_at", ""), reverse=True)
                
                print(f"✅ Recent DingAling executions ({len(aling_executions)} total):")
                
                for i, exec in enumerate(aling_executions[:5]):  # Show last 5
                    method = exec.get("method", "unknown")
                    status = exec.get("status", "unknown")
                    executed_at = exec.get("executed_at", "unknown")
                    
                    # Parse execution time
                    if executed_at and executed_at != "unknown":
                        try:
                            exec_dt = datetime.fromisoformat(executed_at.replace('Z', '+00:00'))
                            exec_display = exec_dt.strftime('%H:%M:%S')
                        except:
                            exec_display = executed_at
                    else:
                        exec_display = "unknown"
                    
                    status_icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
                    print(f"   {status_icon} {method:15} at {exec_display:8} ({status})")
                    
            else:
                print("ℹ️  No recent DingAling executions found")
                
        else:
            print("ℹ️  Execution log not available")
            
    except Exception as e:
        print(f"ℹ️  Could not check recent executions: {e}")


def main():
    """Main status check."""
    print(f"""
🎯 DingAling Handler Status Check
═══════════════════════════════

Server: {CLOCK_SERVER_URL}
Handler: {HANDLER_ID}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

""")
    
    # Check handler registration
    handler_ok = check_handler_status()
    
    if handler_ok:
        # Check scheduled jobs
        check_scheduled_jobs()
        
        # Check recent executions
        check_recent_executions()
        
        print(f"""
🎵 DingAling handler is ready for rapid testing!

Quick commands:
  • poetry run python tests/schedule_aling_tests.py  # Schedule tests
  • poetry run python tests/check_aling_status.py   # Check status
  • poetry run python tests/ding_aling_handler.py   # Start handler
        """)
    else:
        print(f"""
❌ DingAling handler not available!

To start the handler:
  poetry run python tests/ding_aling_handler.py

Make sure the clock server is running:
  poetry run python governor.py start clock
        """)


if __name__ == "__main__":
    main()