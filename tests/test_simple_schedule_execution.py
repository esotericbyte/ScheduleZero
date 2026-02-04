"""Simple test of automatic schedule execution with ComponentManager.

Tests that schedules execute automatically at 20s, 40s, and 120s intervals.
Each execution makes a beep sound and logs to console + file.

No complex wrapper classes - just ComponentManager + direct schedule adds.
"""
import asyncio
import sys
import winsound
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from schedule_zero.component_manager import ComponentManager, load_component_config
from schedule_zero.logging_config import get_logger

logger = get_logger(__name__)

# Global execution tracker
execution_log = []
task_20s_count = 0
task_40s_count = 0
task_120s_count = 0


def log_execution(interval: int, execution_count: int):
    """Log execution with timestamp, sound, and file output."""
    timestamp = datetime.now().isoformat()
    message = f"[{timestamp}] Executed {interval}s interval task (count: {execution_count})"
    
    # Log to console
    print(f"\n{'='*60}")
    print(message)
    print(f"{'='*60}\n")
    logger.info(f"Schedule executed: {interval}s interval", count=execution_count)
    
    # Make beep sound (frequency, duration in ms)
    if interval == 20:
        winsound.Beep(800, 200)  # High pitch, short
    elif interval == 40:
        winsound.Beep(600, 300)  # Medium pitch, medium
    else:  # 120s
        winsound.Beep(400, 500)  # Low pitch, long
    
    # Write to log file
    log_file = Path("test_output") / "schedule_execution.log"
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, 'a') as f:
        f.write(f"{message}\n")
    
    execution_log.append({
        'interval': interval,
        'timestamp': timestamp,
        'count': execution_count
    })


async def task_20_seconds():
    """Task that runs every 20 seconds."""
    global task_20s_count
    task_20s_count += 1
    log_execution(20, task_20s_count)


async def task_40_seconds():
    """Task that runs every 40 seconds."""
    global task_40s_count
    task_40s_count += 1
    log_execution(40, task_40s_count)


async def task_120_seconds():
    """Task that runs every 120 seconds (2 minutes)."""
    global task_120s_count
    task_120s_count += 1
    log_execution(120, task_120s_count)


async def test_simple_schedule_execution():
    """Test schedule execution with ComponentManager directly."""
    print("\n" + "🎵 " + "="*58 + " 🎵")
    print("SIMPLE SCHEDULE EXECUTION TEST")
    print("🎵 " + "="*58 + " 🎵\n")
    
    # Clear log file
    log_file = Path("test_output") / "schedule_execution.log"
    if log_file.exists():
        log_file.unlink()
    
    # Load config for test deployment (minimal mode - just scheduler)
    config = load_component_config("test")
    config['components']['tornado']['enabled'] = False
    config['components']['handlers']['local']['enabled'] = False
    config['components']['handlers']['remote']['enabled'] = False
    
    # Create component manager
    manager = ComponentManager(config)
    
    print("Starting scheduler...\n")
    
    async with manager:
        scheduler = manager.components.get('scheduler')
        
        if not scheduler:
            print("❌ Scheduler not started!")
            return False
        
        print("✓ Scheduler started")
        
        # Add schedules directly to the scheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from datetime import timedelta
        
        # Set start times to prevent immediate execution
        now = datetime.now()
        
        schedule_20 = await scheduler.add_schedule(
            task_20_seconds,
            IntervalTrigger(seconds=20, start_time=now + timedelta(seconds=20)),
            id="test-task-20s"
        )
        print(f"✓ Added 20-second schedule: {schedule_20}")
        
        schedule_40 = await scheduler.add_schedule(
            task_40_seconds,
            IntervalTrigger(seconds=40, start_time=now + timedelta(seconds=40)),
            id="test-task-40s"
        )
        print(f"✓ Added 40-second schedule: {schedule_40}")
        
        schedule_120 = await scheduler.add_schedule(
            task_120_seconds,
            IntervalTrigger(seconds=120, start_time=now + timedelta(seconds=120)),
            id="test-task-120s"
        )
        print(f"✓ Added 120-second schedule: {schedule_120}")
        
        print("\n" + "="*60)
        print("All schedules configured! Waiting for executions...")
        print("Expected timeline:")
        print("  20s  - First 20s task (high beep)")
        print("  40s  - First 40s task (medium beep) + Second 20s task")
        print("  60s  - Third 20s task")
        print("  80s  - Second 40s task + Fourth 20s task")
        print("  100s - Fifth 20s task")
        print("  120s - First 120s task (low beep) + Sixth 20s task + Third 40s task")
        print("="*60 + "\n")
        
        # Wait for schedules to execute
        test_duration = 150
        print(f"⏰ Running test for {test_duration} seconds...\n")
        print("Press Ctrl+C to stop early\n")
        
        try:
            await asyncio.sleep(test_duration)
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total executions: {len(execution_log)}")
    print(f"20s task executions: {task_20s_count}")
    print(f"40s task executions: {task_40s_count}")
    print(f"120s task executions: {task_120s_count}")
    print(f"\nLog file: {log_file.absolute()}")
    print("="*60 + "\n")
    
    # Validate
    if task_20s_count > 0:
        print("✅ 20-second task executed successfully!")
    else:
        print("❌ 20-second task did NOT execute")
    
    if task_40s_count > 0:
        print("✅ 40-second task executed successfully!")
    else:
        print("❌ 40-second task did NOT execute")
    
    if task_120s_count > 0:
        print("✅ 120-second task executed successfully!")
    else:
        print("❌ 120-second task did NOT execute")
    
    success = task_20s_count > 0 and task_40s_count > 0
    
    if success:
        print("\n🎉 Test PASSED! Background scheduler is working!")
        for freq in [400, 600, 800]:
            winsound.Beep(freq, 150)
    else:
        print("\n❌ Test FAILED! Schedules did not execute")
        winsound.Beep(200, 500)
    
    return success


if __name__ == "__main__":
    result = asyncio.run(test_simple_schedule_execution())
    sys.exit(0 if result else 1)
