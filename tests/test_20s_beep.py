"""Minimal test - 30 seconds to see one 20s interval execution."""
import asyncio
import sys
import winsound
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from schedule_zero.component_manager import ComponentManager, load_component_config

count = 0

async def beep_task():
    """Simple task that beeps."""
    global count
    count += 1
    timestamp = datetime.now().isoformat()
    print(f"\n{'='*60}")
    print(f"[{timestamp}] BEEP! Execution #{count}")
    print(f"{'='*60}\n")
    winsound.Beep(800, 300)

async def main():
    global count
    print("\n🔔 20-Second Interval Test")
    print("="*60)
    print("This will wait 30 seconds to see if the 20s task fires\n")
    
    config = load_component_config("test")
    config['components']['tornado']['enabled'] = False
    config['components']['handlers']['local']['enabled'] = False
    config['components']['handlers']['remote']['enabled'] = False
    
    manager = ComponentManager(config)
    
    async with manager:
        scheduler = manager.components.get('scheduler')
        print(f"✓ Scheduler started\n")
        
        # Add schedule
        from apscheduler.triggers.interval import IntervalTrigger
        from datetime import datetime, timedelta
        
        # Set start_time to 20 seconds from now (NOT immediate)
        start_time = datetime.now() + timedelta(seconds=20)
        
        schedule_id = await scheduler.add_schedule(
            beep_task,
            IntervalTrigger(seconds=20, start_time=start_time),
            id="beep-20s"
        )
        add_time = datetime.now()
        print(f"✓ Added schedule: {schedule_id}")
        print(f"✓ Schedule added at: {add_time.isoformat()}")
        print(f"✓ Start time set to: {start_time.isoformat()}")
        print(f"✓ Should fire in 20 seconds (NOT immediately!)\n")
        
        # Wait 30 seconds
        print("Waiting 30 seconds...\n")
        await asyncio.sleep(30)
        
        print(f"\n{'='*60}")
        print(f"Test complete! Executions: {count}")
        if count > 0:
            print("✅ SUCCESS - Task executed!")
            winsound.Beep(600, 200)
            winsound.Beep(800, 200)
        else:
            print("❌ FAIL - Task did NOT execute")
            winsound.Beep(200, 500)
        print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())
