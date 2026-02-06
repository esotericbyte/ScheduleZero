"""
Brief 3-minute test of DingDong Handler

Schedule:
- One "ding" every 15 seconds
- Two low-frequency "dongs" every 60 seconds (on the minute)
- Run for exactly 3 minutes
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.component_manager import ComponentManager, load_component_config
from schedule_zero.autonomous_handler import AutonomousHandler

# Simple test counter
execution_counts = {"ding": 0, "dong": 0}


class BriefDingDongHandler(AutonomousHandler):
    """Minimal ding-dong handler for quick testing"""
    
    def __init__(self, handler_id: str, config: dict):
        super().__init__(handler_id, config)
        
    def ding(self, params=None):
        """High frequency ding - every 15 seconds"""
        execution_counts["ding"] += 1
        print(f"🔔 DING #{execution_counts['ding']} at {datetime.now().strftime('%H:%M:%S')}")
        return {"status": "dinged", "count": execution_counts["ding"]}
    
    def dong(self, params=None):
        """Low frequency dong - every 60 seconds"""
        execution_counts["dong"] += 1
        print(f"🔔🔔 DONG #{execution_counts['dong']} at {datetime.now().strftime('%H:%M:%S')}")
        
        # Play low frequency beep if winsound available
        try:
            import winsound
            # Two low frequency dongs
            winsound.Beep(196, 600)  # G3 - 600ms
            asyncio.sleep(0.3)
            winsound.Beep(196, 600)  # G3 - 600ms
        except:
            pass
            
        return {"status": "donged", "count": execution_counts["dong"]}


async def test_brief_ding_dong():
    """Run 3-minute test with dings and dongs"""
    print("🧪 Starting Brief DingDong Handler Test (3 minutes)")
    print("=" * 60)
    print("Schedule:")
    print("  - DING every 15 seconds")
    print("  - DONG (x2) every 60 seconds (on the minute)")
    print("=" * 60)
    
    # Minimal config - in-memory everything, based on working test
    config = load_component_config(deployment='test')
    
    handler = BriefDingDongHandler("brief-test", config)
    
    # Start handler in background
    run_task = asyncio.create_task(handler.run())
    
    # Wait for handler to initialize (longer wait to ensure scheduler starts)
    await asyncio.sleep(2)
    
    # Schedule the dings (every 15 seconds)
    await handler.add_schedule(
        handler.ding,
        'interval',
        seconds=15
    )
    print("✅ Scheduled: DING every 15 seconds")
    
    # Schedule the dongs (every 60 seconds)
    await handler.add_schedule(
        handler.dong,
        'interval',
        seconds=60
    )
    print("✅ Scheduled: DONG every 60 seconds")
    print()
    
    # Run for 3 minutes
    start_time = datetime.now()
    
    while (datetime.now() - start_time).total_seconds() < 180:
        await asyncio.sleep(5)
        elapsed = int((datetime.now() - start_time).total_seconds())
        print(f"⏱️  {elapsed}s elapsed | Dings: {execution_counts['ding']} | Dongs: {execution_counts['dong']}")
    
    print()
    print("=" * 60)
    print("🏁 Test Complete!")
    print(f"Total DINGs: {execution_counts['ding']} (expected ~12)")
    print(f"Total DONGs: {execution_counts['dong']} (expected ~3)")
    print("=" * 60)
    
    # Stop handler
    handler.stop()
    await run_task


if __name__ == "__main__":
    try:
        asyncio.run(test_brief_ding_dong())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
