"""
Check the status of the DingDong clock chimes!

Shows:
- Handler status (registered or not)
- Number of schedules
- Chime log summary
- Next upcoming chimes
- Statistics
"""
import requests
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

# Configuration
DEPLOYMENT_MODE = os.environ.get("DING_DONG_DEPLOY", "false").lower() == "true"

if DEPLOYMENT_MODE:
    HANDLER_ID = "ding-dong-handler"
    API_BASE = "http://127.0.0.1:8889"  # Clock deployment web server
    LOG_DIR = "ding_dong_logs"
    MODE_NAME = "DEPLOYMENT"
else:
    HANDLER_ID = "ding-dong-test"
    API_BASE = "http://127.0.0.1:8888"  # Default deployment web server
    LOG_DIR = "ding_dong_logs_test"
    MODE_NAME = "TEST"


def print_header(title):
    """Print a formatted header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_handler_status():
    """Check if the handler is registered."""
    try:
        response = requests.get(f"{API_BASE}/api/handlers", timeout=5)
        if response.status_code == 200:
            handlers = response.json().get('handlers', [])
            for handler in handlers:
                if handler.get('id') == HANDLER_ID:
                    print(f"✅ Handler Status: REGISTERED")
                    print(f"   Handler ID: {HANDLER_ID}")
                    print(f"   Mode: {MODE_NAME}")
                    return True
            
            print(f"❌ Handler Status: NOT REGISTERED")
            print(f"   Looking for: {HANDLER_ID}")
            print(f"   Available: {[h.get('id') for h in handlers]}")
            return False
    except Exception as e:
        print(f"❌ Handler Status: CANNOT CONNECT")
        print(f"   Error: {e}")
        return False


def check_schedules():
    """Check how many schedules exist."""
    try:
        response = requests.get(f"{API_BASE}/api/schedules", timeout=5)
        if response.status_code == 200:
            data = response.json()
            schedules = data.get('schedules', [])
            
            # Filter for our handler
            our_schedules = [s for s in schedules if s.get('args', {}).get('handler_id') == HANDLER_ID]
            
            print(f"\n📅 Schedules:")
            print(f"   Total in system: {len(schedules)}")
            print(f"   For {HANDLER_ID}: {len(our_schedules)}")
            
            if our_schedules:
                # Count by type
                bongs = [s for s in our_schedules if 'bong' in s.get('id', '')]
                chimes = [s for s in our_schedules if 'chime' in s.get('id', '')]
                
                print(f"   Hour bongs: {len(bongs)}")
                print(f"   Quarter chimes: {len(chimes)}")
                
                # Find next 3 upcoming
                now = datetime.now(timezone.utc)
                upcoming = []
                for sched in our_schedules:
                    trigger = sched.get('trigger', {})
                    if trigger.get('type') == 'date':
                        run_time_str = trigger.get('run_time')
                        if run_time_str:
                            run_time = datetime.fromisoformat(run_time_str.replace('Z', '+00:00'))
                            if run_time > now:
                                upcoming.append((run_time, sched))
                
                upcoming.sort(key=lambda x: x[0])
                
                if upcoming:
                    print(f"\n   Next 3 chimes:")
                    for i, (run_time, sched) in enumerate(upcoming[:3], 1):
                        job_id = sched.get('id', 'unknown')
                        time_until = (run_time - now).total_seconds()
                        minutes = int(time_until / 60)
                        seconds = int(time_until % 60)
                        
                        chime_type = "BONG" if 'bong' in job_id else "chime"
                        print(f"      {i}. {run_time.strftime('%Y-%m-%d %H:%M')} UTC ({minutes}m {seconds}s) - {chime_type}")
            
            return True
    except Exception as e:
        print(f"❌ Cannot get schedules: {e}")
        return False


def check_chime_log():
    """Check the chime log."""
    log_path = Path(__file__).parent / LOG_DIR / "chime_log.txt"
    
    print(f"\n📝 Chime Log:")
    print(f"   Path: {log_path}")
    
    if not log_path.exists():
        print(f"   Status: No log file yet (no chimes have played)")
        return False
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    print(f"   Total entries: {len(lines)}")
    
    if lines:
        # Count by type
        bongs = sum(1 for line in lines if 'HOUR BONG' in line)
        chimes = sum(1 for line in lines if 'QUARTER CHIME' in line)
        
        print(f"   Hour bongs played: {bongs}")
        print(f"   Quarter chimes played: {chimes}")
        
        # Show last 5
        print(f"\n   Last 5 chimes:")
        for line in lines[-5:]:
            print(f"      {line.strip()}")
    
    return True


def main():
    """Main entry point."""
    print_header(f"🔔 DING DONG CLOCK STATUS - {MODE_NAME} MODE")
    
    print(f"\nCurrent time:")
    print(f"   UTC:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check status
    print()
    check_handler_status()
    check_schedules()
    check_chime_log()
    
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
