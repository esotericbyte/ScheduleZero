"""Test autonomous handler with automatic schedule execution.

Tests that schedules execute automatically at 20s, 40s, and 120s intervals.
Each execution makes a beep sound and logs to console + file.
"""
import asyncio
import sys
import winsound
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from schedule_zero.autonomous_handler import AutonomousHandler
from schedule_zero.logging_config import get_logger

logger = get_logger(__name__)

# Global execution tracker
execution_log = []


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
    # Different frequencies for different intervals
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
    
    # Track execution
    execution_log.append({
        'interval': interval,
        'timestamp': timestamp,
        'count': execution_count
    })


# Task execution counters
task_20s_count = 0
task_40s_count = 0
task_120s_count = 0


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


class ScheduleTestHandler(AutonomousHandler):
    """Test handler with three scheduled tasks at different intervals."""
    
    async def setup(self):
        """Register handlers and add schedules."""
        print("\n" + "="*60)
        print("Setting up ScheduleTestHandler...")
        print("="*60 + "\n")
        
        # Register handlers
        self.register_handler(task_20_seconds)
        self.register_handler(task_40_seconds)
        self.register_handler(task_120_seconds)
        
        # Add schedules with different intervals
        schedule_20 = await self.add_schedule(
            task_20_seconds,
            "interval",
            seconds=20
        )
        print(f"✓ Added 20-second schedule: {schedule_20}")
        
        schedule_40 = await self.add_schedule(
            task_40_seconds,
            "interval",
            seconds=40
        )
        print(f"✓ Added 40-second schedule: {schedule_40}")
        
        schedule_120 = await self.add_schedule(
            task_120_seconds,
            "interval",
            seconds=120
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


async def test_scheduler_execution():
    """Test that schedules execute automatically with background scheduler."""
    print("\n" + "🎵 " + "="*58 + " 🎵")
    print("SCHEDULE EXECUTION TEST WITH SOUNDS")
    print("🎵 " + "="*58 + " 🎵\n")
    
    # Clear log file
    log_file = Path("test_output") / "schedule_execution.log"
    if log_file.exists():
        log_file.unlink()
    
    # Create handler
    handler = ScheduleTestHandler(
        handler_id="schedule-test-001",
        deployment="test"
    )
    
    # Wait for schedules to execute
    # Run for 150 seconds to see:
    # - 20s task: 7 executions (20, 40, 60, 80, 100, 120, 140)
    # - 40s task: 3 executions (40, 80, 120)
    # - 120s task: 1 execution (120)
    test_duration = 150
    
    print(f"⏰ Running test for {test_duration} seconds...\n")
    print("Press Ctrl+C to stop early\n")
    
    # Start handler in background
    handler_task = asyncio.create_task(handler.run())
    
    try:
        # Wait for test duration
        await asyncio.sleep(test_duration)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    finally:
        # Stop handler
        print("\n\nStopping handler...")
        handler_task.cancel()
        try:
            await handler_task
        except asyncio.CancelledError:
            pass
    
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
    
    # Success if at least 20s and 40s tasks executed
    # (120s might not execute if test is stopped early)
    success = task_20s_count > 0 and task_40s_count > 0
    
    if success:
        print("\n🎉 Test PASSED! Background scheduler is working!")
        # Make success sound
        for freq in [400, 600, 800]:
            winsound.Beep(freq, 150)
    else:
        print("\n❌ Test FAILED! Schedules did not execute")
        # Make failure sound
        winsound.Beep(200, 500)
    
    return success


if __name__ == "__main__":
    result = asyncio.run(test_scheduler_execution())
    sys.exit(0 if result else 1)
