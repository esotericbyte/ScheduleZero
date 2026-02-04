"""Quick debug test for two-broker leader election."""
import asyncio
import logging

from apscheduler import AsyncScheduler
from apscheduler.datastores.memory import MemoryDataStore
from schedule_zero.zmq_event_broker import ZMQEventBroker

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(message)s')

async def main():
    # Broker 1 - simulate lower PID
    broker1 = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:25558",
        subscribe_addresses=["tcp://127.0.0.1:25559"],
        instance_id="scheduler-1",
        heartbeat_interval=1
    )
    # Force lower PID for testing
    import os
    object.__setattr__(broker1, "_pid", 1000)
    
    # Broker 2 - simulate higher PID
    broker2 = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:25559",
        subscribe_addresses=["tcp://127.0.0.1:25558"],
        instance_id="scheduler-2",
        heartbeat_interval=1
    )
    object.__setattr__(broker2, "_pid", 2000)
    
    print(f"Broker1 PID: {broker1._pid}, Broker2 PID: {broker2._pid}")
    
    async with AsyncScheduler(
        data_store=MemoryDataStore(),
        event_broker=broker1
    ) as scheduler1:
        print(f"Scheduler1 started, broker1.is_leader: {broker1.is_leader}")
        
        async with AsyncScheduler(
            data_store=MemoryDataStore(),
            event_broker=broker2
        ) as scheduler2:
            print(f"Scheduler2 started, broker2.is_leader: {broker2.is_leader}")
            
            # Wait for heartbeats
            print("\nWaiting 3 seconds for heartbeat exchange...")
            await asyncio.sleep(3)
            
            print(f"\nAfter heartbeats:")
            print(f"  Broker1 (PID {broker1._pid}): is_leader={broker1.is_leader}")
            print(f"  Broker1 sees instances: {list(broker1.get_alive_instances().keys())}")
            print(f"  Broker2 (PID {broker2._pid}): is_leader={broker2.is_leader}")
            print(f"  Broker2 sees instances: {list(broker2.get_alive_instances().keys())}")
            
            # Test assertion
            if broker1.is_leader == broker2.is_leader:
                print(f"\n❌ FAIL: Both have same leader status ({broker1.is_leader})")
                return False
            
            if broker1.is_leader:
                print(f"\n✓ PASS: Broker1 (PID {broker1._pid}) is leader")
            else:
                print(f"\n✓ PASS: Broker2 (PID {broker2._pid}) is leader")
            
            return True

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
