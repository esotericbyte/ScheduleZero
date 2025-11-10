"""
Schedule 2 days worth of clock chimes!

Schedules:
- Hour bongs: Every hour on the hour (00:00, 01:00, 02:00, ..., 23:00)
- Quarter chimes: At 15, 30, and 45 minutes past every hour

All times are UTC (as proper clock scheduling should be!)
This creates 48 hour bongs and 144 quarter chimes = 192 total scheduled events over 2 days.

MODES:
- TEST mode: Uses "ding-dong-test" handler on port 4246 (for development)
- DEPLOY mode: Uses "ding-dong-handler" handler on port 4245 (for long-term clock)

Set DING_DONG_DEPLOY=true for deployment mode.
"""
import requests
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuration - check deployment mode
DEPLOYMENT_MODE = os.environ.get("DING_DONG_DEPLOY", "false").lower() == "true"

if DEPLOYMENT_MODE:
    HANDLER_ID = "ding-dong-handler"
    API_BASE = "http://127.0.0.1:8889"  # Clock deployment web server
    MODE_NAME = "DEPLOYMENT"
else:
    HANDLER_ID = "ding-dong-test"
    API_BASE = "http://127.0.0.1:8888"  # Default deployment web server
    MODE_NAME = "TEST"

def schedule_chimes():
    """Schedule all the dings and dongs for 2 days."""
    
    # Start from the next whole hour in UTC
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc.replace(minute=0, second=0, microsecond=0)
    
    # If we're past the hour mark, start from next hour
    if now_utc.minute > 0 or now_utc.second > 0:
        start_time += timedelta(hours=1)
    
    print("=" * 80)
    print(f"🔔 SCHEDULING DING DONG HANDLER FOR 2 DAYS! ({MODE_NAME} MODE)")
    print("=" * 80)
    print(f"Handler ID:        {HANDLER_ID}")
    print(f"Current UTC time:  {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Starting from:     {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Ending at:         {(start_time + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    print(f"Current local time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    scheduled_count = 0
    errors = []
    
    # Schedule for 48 hours (2 days)
    for hour_offset in range(48):
        base_time = start_time + timedelta(hours=hour_offset)
        hour_24 = base_time.hour
        
        # Schedule hour BONG at XX:00
        bong_time = base_time
        job_id = f"bong_{bong_time.strftime('%Y%m%d_%H%M')}"
        
        result = schedule_hour_bong(bong_time, hour_24, job_id)
        if result:
            scheduled_count += 1
            if hour_offset < 3 or hour_offset >= 45:  # Print first 3 and last 3
                print(f"✓ Hour bong scheduled: {bong_time.strftime('%Y-%m-%d %H:%M %Z')} ({hour_24 if hour_24 > 0 else 24} bongs)")
        else:
            errors.append(f"Failed to schedule hour bong at {bong_time}")
        
        # Schedule quarter chimes at :15, :30, :45
        for quarter in [1, 2, 3]:
            chime_time = base_time + timedelta(minutes=quarter * 15)
            job_id = f"chime_{chime_time.strftime('%Y%m%d_%H%M')}_q{quarter}"
            
            result = schedule_quarter_chime(chime_time, quarter, job_id)
            if result:
                scheduled_count += 1
                if hour_offset == 0:  # Print first hour's quarters
                    print(f"✓ Quarter chime scheduled: {chime_time.strftime('%Y-%m-%d %H:%M %Z')} (quarter {quarter})")
            else:
                errors.append(f"Failed to schedule quarter chime at {chime_time}")
    
    print()
    print("=" * 80)
    print(f"✅ SCHEDULING COMPLETE!")
    print(f"Total scheduled: {scheduled_count} events")
    print(f"Errors: {len(errors)}")
    if errors:
        print("\nErrors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
    print("=" * 80)
    print()
    print("🎵 Your clock will now chime for the next 2 days!")
    print()
    print("To check the chime log:")
    print(f"  Check: tests/ding_dong_logs/chime_log.txt")
    print()
    print("To view all schedules:")
    print(f"  curl {API_BASE}/api/schedules")
    

def schedule_hour_bong(bong_time, hour, job_id):
    """Schedule a single hour bong."""
    job_data = {
        "handler_id": HANDLER_ID,
        "job_method": "play_hour_bongs",
        "job_params": {
            "hour": hour
        },
        "trigger": {
            "type": "date",
            "run_date": bong_time.timestamp()  # Unix timestamp (UTC)
        },
        "job_id": job_id
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/schedule", json=job_data, timeout=5)
        return response.status_code == 201
    except Exception as e:
        print(f"Error scheduling hour bong: {e}")
        return False


def schedule_quarter_chime(chime_time, quarter, job_id):
    """Schedule a single quarter chime."""
    job_data = {
        "handler_id": HANDLER_ID,
        "job_method": "play_quarter_chime",
        "job_params": {
            "quarter": quarter
        },
        "trigger": {
            "type": "date",
            "run_date": chime_time.timestamp()  # Unix timestamp (UTC)
        },
        "job_id": job_id
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/schedule", json=job_data, timeout=5)
        return response.status_code == 201
    except Exception as e:
        print(f"Error scheduling quarter chime: {e}")
        return False


def check_handler_status():
    """Check if the DingDongHandler is registered."""
    try:
        response = requests.get(f"{API_BASE}/api/handlers", timeout=5)
        if response.status_code == 200:
            handlers = response.json().get('handlers', [])
            for handler in handlers:
                if handler.get('id') == HANDLER_ID:
                    print(f"✓ DingDongHandler ({HANDLER_ID}) is registered and ready!")
                    print(f"   Mode: {MODE_NAME}")
                    return True
            
            print(f"❌ DingDongHandler not found!")
            print(f"   Looking for: {HANDLER_ID}")
            print(f"   Available handlers: {[h.get('id') for h in handlers]}")
            print()
            print("Please start the handler first:")
            if DEPLOYMENT_MODE:
                print("  $env:DING_DONG_DEPLOY='true'")
                print("  poetry run python tests/ding_dong_handler.py")
            else:
                print("  poetry run python tests/ding_dong_handler.py")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print()
        print("Please start the server first:")
        print("  poetry run python -m schedule_zero.server")
        return False


def main():
    """Main entry point."""
    print()
    
    # Check if handler is ready
    if not check_handler_status():
        sys.exit(1)
    
    print()
    
    # Schedule all the chimes!
    schedule_chimes()


if __name__ == "__main__":
    main()
