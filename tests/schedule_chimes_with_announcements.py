"""
Schedule chimes every 15 minutes + hourly time announcements.

Schedules:
- Quarter chimes: Every 15 minutes (:00, :15, :30, :45)
- Time announcements: Every hour on the hour (speaks the time and date)
"""
import requests
import sys
import os
from datetime import datetime, timedelta, timezone

# Configuration
DEPLOYMENT_MODE = os.environ.get("DING_DONG_DEPLOY", "false").lower() == "true"

if DEPLOYMENT_MODE:
    HANDLER_ID = "ding-dong-handler"
    API_BASE = "http://127.0.0.1:8889"
    MODE_NAME = "DEPLOYMENT"
else:
    HANDLER_ID = "ding-dong-test"
    API_BASE = "http://127.0.0.1:8888"
    MODE_NAME = "TEST"


def schedule_quarter_chime(chime_time, quarter, job_id):
    """Schedule a single quarter chime."""
    job_data = {
        "handler_id": HANDLER_ID,
        "job_method": "play_quarter_chime",
        "job_params": {"quarter": quarter},
        "trigger": {
            "type": "date",
            "run_date": chime_time.timestamp()
        },
        "job_id": job_id
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/schedule", json=job_data, timeout=5)
        return response.status_code == 201
    except Exception as e:
        print(f"Error scheduling quarter chime: {e}")
        return False


def schedule_time_announcement(announce_time, job_id):
    """Schedule an hourly time announcement."""
    job_data = {
        "handler_id": HANDLER_ID,
        "job_method": "announce_time",
        "job_params": {},
        "trigger": {
            "type": "date",
            "run_date": announce_time.timestamp()
        },
        "job_id": job_id
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/schedule", json=job_data, timeout=5)
        return response.status_code == 201
    except Exception as e:
        print(f"Error scheduling time announcement: {e}")
        return False


def main():
    """Schedule chimes and announcements for 2 days."""
    print()
    print("=" * 80)
    print(f"SCHEDULING CHIMES + TIME ANNOUNCEMENTS ({MODE_NAME} MODE)")
    print("=" * 80)
    print(f"Handler ID: {HANDLER_ID}")
    print()
    
    # Check handler status
    try:
        response = requests.get(f"{API_BASE}/api/handlers", timeout=5)
        if response.status_code == 200:
            handlers = response.json().get('handlers', [])
            if not any(h.get('id') == HANDLER_ID for h in handlers):
                print(f"❌ Handler '{HANDLER_ID}' not registered!")
                print("Please start the handler first:")
                print(f"  $env:DING_DONG_DEPLOY='{str(DEPLOYMENT_MODE).lower()}'")
                print(f"  poetry run python tests/ding_dong_handler.py")
                sys.exit(1)
        else:
            print(f"❌ Cannot connect to server at {API_BASE}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking handler: {e}")
        sys.exit(1)
    
    print(f"✓ Handler '{HANDLER_ID}' is registered\n")
    
    # Start from next whole hour
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc.replace(minute=0, second=0, microsecond=0)
    if now_utc.minute > 0 or now_utc.second > 0:
        start_time += timedelta(hours=1)
    
    print(f"Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Starting from: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    chime_count = 0
    announce_count = 0
    errors = []
    
    # Schedule for 48 hours
    for hour_offset in range(48):
        base_time = start_time + timedelta(hours=hour_offset)
        
        # Schedule hourly time announcement at :00
        announce_job_id = f"announce_{base_time.strftime('%Y%m%d_%H%M')}"
        if schedule_time_announcement(base_time, announce_job_id):
            announce_count += 1
            if hour_offset < 3:
                print(f"✓ Announcement: {base_time.strftime('%Y-%m-%d %H:%M')} UTC")
        else:
            errors.append(f"Failed announcement at {base_time}")
        
        # Schedule quarter chimes at :00, :15, :30, :45
        for quarter in [0, 1, 2, 3]:
            chime_time = base_time + timedelta(minutes=quarter * 15)
            job_id = f"chime_{chime_time.strftime('%Y%m%d_%H%M')}_q{quarter}"
            
            if schedule_quarter_chime(chime_time, quarter, job_id):
                chime_count += 1
            else:
                errors.append(f"Failed chime at {chime_time}")
    
    print()
    print("=" * 80)
    print("✅ SCHEDULING COMPLETE!")
    print("=" * 80)
    print(f"Quarter chimes:       {chime_count} scheduled (every 15 min)")
    print(f"Time announcements:   {announce_count} scheduled (hourly)")
    print(f"Total:                {chime_count + announce_count} events")
    print(f"Errors:               {len(errors)}")
    print()
    print("Your clock will now:")
    print("  🔔 Chime every 15 minutes (:00, :15, :30, :45)")
    print("  🗣️  Announce the time and date every hour (via text-to-speech)")
    print()
    print("Note: Install pyttsx3 for time announcements to work:")
    print("  poetry add pyttsx3")
    print()


if __name__ == "__main__":
    main()
