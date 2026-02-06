"""Test ding-dong handler with pytest fixtures."""
import asyncio

import pytest

from schedule_zero.autonomous_handler import AutonomousHandler


# Global execution counters (APScheduler 4.x requires serializable functions)
_execution_counters = {
    "ding": 0,
    "dong": 0
}


def ding():
    """Ding task that runs every 15 seconds."""
    _execution_counters["ding"] += 1
    print(f"🔔 Ding! (count: {_execution_counters['ding']})")
    return f"ding_{_execution_counters['ding']}"


def dong():
    """Dong task that runs every minute."""
    _execution_counters["dong"] += 1
    print(f"🔔 DONG! (count: {_execution_counters['dong']})")
    return f"dong_{_execution_counters['dong']}"


class DingDongTestHandler(AutonomousHandler):
    """Test handler for ding-dong scheduling."""
    
    def __init__(self):
        super().__init__(
            handler_id="ding-dong-test",
            deployment="test",
            central_server=None,
            enable_event_broker=False
        )
    
    async def setup(self):
        """Register handlers and schedules."""
        # Register the module-level handlers
        self.register_handler(ding)
        self.register_handler(dong)
        
        # Add ding schedule (every 15 seconds)
        await self.add_schedule(
            ding,
            "interval",
            seconds=15
        )
        
        # Add dong schedule (every minute)
        await self.add_schedule(
            dong,
            "interval",
            seconds=60
        )


# Fixtures

@pytest.fixture
def reset_counters():
    """Reset execution counters before each test."""
    global _execution_counters
    _execution_counters["ding"] = 0
    _execution_counters["dong"] = 0
    yield _execution_counters


@pytest.fixture
async def ding_dong_handler():
    """Create and start ding-dong handler with cleanup."""
    handler = DingDongTestHandler()
    
    # Start handler
    run_task = asyncio.create_task(handler.run())
    
    # Wait for handler to initialize
    await asyncio.sleep(2)
    
    yield handler
    
    # Teardown: cancel handler task
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass


# Tests

async def test_ding_every_15_seconds(ding_dong_handler, reset_counters):
    """Test that ding executes every 15 seconds."""
    initial_ding = reset_counters["ding"]
    
    # Wait 45 seconds (should see 3 dings)
    await asyncio.sleep(45)
    
    dings = reset_counters["ding"] - initial_ding
    print(f"Ding executed {dings} times in 45 seconds")
    
    # Allow some tolerance (2-4 executions depending on timing)
    assert dings >= 2, f"Expected at least 2 dings, got {dings}"


async def test_dong_every_60_seconds(ding_dong_handler, reset_counters):
    """Test that dong executes every 60 seconds."""
    initial_dong = reset_counters["dong"]
    
    # Wait 90 seconds (should see at least 1 dong)
    await asyncio.sleep(90)
    
    dongs = reset_counters["dong"] - initial_dong
    print(f"Dong executed {dongs} times in 90 seconds")
    
    # Should execute at least once
    assert dongs >= 1, f"Expected at least 1 dong, got {dongs}"


@pytest.mark.slow
async def test_ding_dong_combined_3_minutes(ding_dong_handler, reset_counters):
    """Test ding-dong handler for full 3 minutes."""
    initial_ding = reset_counters["ding"]
    initial_dong = reset_counters["dong"]
    
    # Wait 180 seconds (3 minutes)
    await asyncio.sleep(180)
    
    dings = reset_counters["ding"] - initial_ding
    dongs = reset_counters["dong"] - initial_dong
    
    print(f"After 3 minutes: {dings} dings, {dongs} dongs")
    
    # In 3 minutes (180s):
    # - Dings (every 15s): expect ~12 (180/15)
    # - Dongs (every 60s): expect ~3 (180/60)
    assert dings >= 10, f"Expected at least 10 dings, got {dings}"
    assert dongs >= 2, f"Expected at least 2 dongs, got {dongs}"


async def test_handler_initialization(ding_dong_handler):
    """Test that handler initializes correctly."""
    # Check scheduler is running
    assert ding_dong_handler.scheduler is not None, "Scheduler should be initialized"
    
    # Check schedules were created
    schedules = await ding_dong_handler.scheduler.get_schedules()
    assert len(schedules) == 2, f"Expected 2 schedules, got {len(schedules)}"
    
    # Schedule IDs are prefixed with handler_id
    schedule_ids = {s.id for s in schedules}
    assert any("ding" in sid for sid in schedule_ids), "Ding schedule should exist"
    assert any("dong" in sid for sid in schedule_ids), "Dong schedule should exist"
    
    print(f"✓ Handler initialized with {len(schedules)} schedules")
