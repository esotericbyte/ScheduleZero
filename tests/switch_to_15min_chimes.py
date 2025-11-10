"""
Switch from hourly bongs to 15-minute chimes only.

This script:
1. Gets all current schedules
2. Deletes only the hour bong schedules (job IDs starting with "bong_")
3. Keeps existing quarter chimes (every 15, 30, 45 minutes)
4. Adds new chimes for :00 minutes (completing the 15-minute cycle)

This way you get chimes every 15 minutes instead of hourly bongs.
"""
import requests
import sys
import os
from datetime import datetime, timedelta, timezone

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


def get_all_schedules():
    """Get all current schedules."""
    try:
        response = requests.get(f"{API_BASE}/api/schedules", timeout=5)
        if response.status_code == 200:
            return response.json().get('schedules', [])
        else:
            print(f"❌ Failed to get schedules: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting schedules: {e}")
        return None


def delete_schedule(schedule_id):
    """Delete a schedule by ID."""
    try:
        response = requests.delete(f"{API_BASE}/api/schedules/{schedule_id}", timeout=5)
        if response.status_code in [200, 204]:
            return True
        else:
            # Print error for debugging
            try:
                error_data = response.json()
                print(f"    ⚠️  Failed to delete {schedule_id}: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"    ⚠️  Failed to delete {schedule_id}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"    ⚠️  Error deleting {schedule_id}: {e}")
        return False


def schedule_on_the_hour_chime(chime_time, job_id):
    """Schedule a chime at :00 minutes (top of the hour)."""
    job_data = {
        "handler_id": HANDLER_ID,
        "job_method": "play_quarter_chime",
        "job_params": {
            "quarter": 0  # Special: :00 minutes
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
        print(f"Error scheduling :00 chime: {e}")
        return False


def main():
    """Main entry point."""
    print()
    print("=" * 80)
    print(f"🔄 SWITCHING TO 15-MINUTE CHIMES ({MODE_NAME} MODE)")
    print("=" * 80)
    print(f"Handler ID: {HANDLER_ID}")
    print()
    
    # Get current schedules
    print("📋 Fetching current schedules...")
    schedules = get_all_schedules()
    
    if schedules is None:
        print("❌ Cannot proceed without schedule data")
        sys.exit(1)
    
    print(f"✓ Found {len(schedules)} total schedules")
    print()
    
    # Filter to find hour bongs (job IDs starting with "bong_")
    hour_bongs = [s for s in schedules if s.get('id', '').startswith('bong_')]
    quarter_chimes = [s for s in schedules if s.get('id', '').startswith('chime_')]
    
    print(f"Hour bongs to delete:  {len(hour_bongs)}")
    print(f"Quarter chimes to keep: {len(quarter_chimes)}")
    print()
    
    if not hour_bongs:
        print("ℹ️  No hour bongs found - already using 15-minute chimes?")
        print()
    
    # Delete hour bongs
    if hour_bongs:
        print("🗑️  Deleting hour bongs...")
        deleted_count = 0
        failed = []
        
        for schedule in hour_bongs:
            schedule_id = schedule.get('id')
            if delete_schedule(schedule_id):
                deleted_count += 1
                if deleted_count <= 3 or deleted_count > len(hour_bongs) - 3:
                    print(f"  ✓ Deleted: {schedule_id}")
            else:
                failed.append(schedule_id)
        
        print(f"✓ Deleted {deleted_count} hour bong schedules")
        if failed:
            print(f"⚠️  Failed to delete {len(failed)} schedules")
        print()
    
    # Add :00 minute chimes to complete 15-minute cycle
    print("➕ Adding :00 minute chimes...")
    
    # Start from the next whole hour in UTC
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc.replace(minute=0, second=0, microsecond=0)
    
    # If we're past the hour mark, start from next hour
    if now_utc.minute > 0 or now_utc.second > 0:
        start_time += timedelta(hours=1)
    
    scheduled_count = 0
    errors = []
    
    # Schedule :00 chimes for the next 48 hours
    for hour_offset in range(48):
        chime_time = start_time + timedelta(hours=hour_offset)
        job_id = f"chime_{chime_time.strftime('%Y%m%d_%H%M')}_q0"
        
        result = schedule_on_the_hour_chime(chime_time, job_id)
        if result:
            scheduled_count += 1
            if hour_offset < 3 or hour_offset >= 45:
                print(f"  ✓ Scheduled: {chime_time.strftime('%Y-%m-%d %H:%M %Z')}")
        else:
            errors.append(f"Failed at {chime_time}")
    
    print(f"✓ Added {scheduled_count} :00 minute chimes")
    if errors:
        print(f"⚠️  {len(errors)} errors encountered")
    print()
    
    # Summary
    print("=" * 80)
    print("✅ CONVERSION COMPLETE!")
    print("=" * 80)
    print()
    print("Your clock now chimes every 15 minutes:")
    print("  :00 - Single chime (newly added)")
    print("  :15 - Single chime (existing)")
    print("  :30 - Single chime (existing)")
    print("  :45 - Single chime (existing)")
    print()
    print("Changes made:")
    print(f"  - Removed: {len(hour_bongs)} hourly bong schedules")
    print(f"  - Added:   {scheduled_count} :00 minute chimes")
    print(f"  - Kept:    {len(quarter_chimes)} existing quarter chimes")
    print()
    print("To check the chime log:")
    print(f"  Check: tests/ding_dong_logs/chime_log.txt")
    print()


if __name__ == "__main__":
    main()
