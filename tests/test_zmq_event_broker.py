"""Test ZMQ Event Broker functionality."""
import asyncio
import pytest
from contextlib import AsyncExitStack

from apscheduler import AsyncScheduler
from apscheduler.datastores.memory import MemoryDataStore
from schedule_zero.zmq_event_broker import ZMQEventBroker


def dummy_task():
    """Dummy task for testing schedule creation."""
    print("test")


@pytest.mark.asyncio
async def test_broker_imports_and_initialization():
    """Test that ZMQEventBroker can be imported and initialized."""
    broker = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15555",
        subscribe_addresses=[],
        instance_id="test-broker-1"
    )
    
    assert broker.publish_address == "tcp://127.0.0.1:15555"
    assert broker.instance_id == "test-broker-1"
    assert broker.heartbeat_interval == 5
    assert not broker.is_leader  # Not started yet


@pytest.mark.asyncio
async def test_broker_with_scheduler():
    """Test that broker can be used with AsyncScheduler."""
    broker = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15556",
        subscribe_addresses=[],
        instance_id="test-scheduler-1"
    )
    
    async with AsyncScheduler(
        data_store=MemoryDataStore(),
        event_broker=broker
    ) as scheduler:
        # Scheduler should start and accept broker
        assert scheduler.event_broker is broker
        
        # After starting, broker should be initialized
        assert broker._stopped is False
        
        # Wait for leader election to complete
        await asyncio.sleep(0.5)
        assert broker.is_leader  # Only instance, should be leader


@pytest.mark.asyncio
async def test_broker_heartbeat_and_pid():
    """Test that broker tracks PID and sends heartbeats."""
    broker = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15557",
        subscribe_addresses=[],
        instance_id="test-pid-broker",
        heartbeat_interval=1  # Fast heartbeat for testing
    )
    
    # Check PID is captured
    import os
    assert broker._pid == os.getpid()
    
    async with AsyncScheduler(
        data_store=MemoryDataStore(),
        event_broker=broker
    ):
        # Wait a bit for heartbeat loop to start
        await asyncio.sleep(0.5)
        
        # Should be leader (only instance)
        assert broker.is_leader
        
        # No other instances
        assert len(broker.get_alive_instances()) == 0


@pytest.mark.asyncio
async def test_two_brokers_discover_each_other():
    """Test that two brokers can discover each other via heartbeats."""
    # Broker 1
    broker1 = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15558",
        subscribe_addresses=["tcp://127.0.0.1:15559"],  # Subscribe to broker2
        instance_id="scheduler-1",
        heartbeat_interval=1
    )
    # Force different PIDs for testing (in real deployment, these would be actual process PIDs)
    import os
    actual_pid = os.getpid()
    object.__setattr__(broker1, "_pid", actual_pid - 100)  # Lower PID
    
    # Broker 2
    broker2 = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15559",
        subscribe_addresses=["tcp://127.0.0.1:15558"],  # Subscribe to broker1
        instance_id="scheduler-2",
        heartbeat_interval=1
    )
    object.__setattr__(broker2, "_pid", actual_pid + 100)  # Higher PID
    
    async with AsyncScheduler(
        data_store=MemoryDataStore(),
        event_broker=broker1
    ) as scheduler1:
        async with AsyncScheduler(
            data_store=MemoryDataStore(),
            event_broker=broker2
        ) as scheduler2:
            # Wait for heartbeats to exchange
            await asyncio.sleep(3)
            
            # Each broker should see the other
            alive1 = broker1.get_alive_instances()
            alive2 = broker2.get_alive_instances()
            
            print(f"Broker1 (PID {broker1._pid}) sees: {list(alive1.keys())}, is_leader={broker1.is_leader}")
            print(f"Broker2 (PID {broker2._pid}) sees: {list(alive2.keys())}, is_leader={broker2.is_leader}")
            
            assert "scheduler-2" in alive1, f"Broker1 should see broker2, got: {alive1}"
            assert "scheduler-1" in alive2, f"Broker2 should see broker1, got: {alive2}"
            
            # Leader election should have occurred (lowest PID wins)
            # Both should agree on who is leader
            assert broker1.is_leader != broker2.is_leader, "Exactly one should be leader"
            assert broker1.is_leader, f"Broker1 has lower PID ({broker1._pid} < {broker2._pid}), should be leader"


@pytest.mark.asyncio
async def test_broker_without_subscribers():
    """Test broker works fine with no subscribe addresses (single instance)."""
    broker = ZMQEventBroker(
        publish_address="tcp://127.0.0.1:15560",
        subscribe_addresses=[],  # No subscribers
        instance_id="solo-scheduler"
    )
    
    async with AsyncScheduler(
        data_store=MemoryDataStore(),
        event_broker=broker
    ) as scheduler:
        await asyncio.sleep(1)
        
        # Should be leader (only instance)
        assert broker.is_leader
        
        # Can add schedules normally
        from apscheduler.triggers.interval import IntervalTrigger
        await scheduler.add_schedule(
            dummy_task,
            IntervalTrigger(seconds=60),
            id="test-job"
        )
        
        schedules = await scheduler.get_schedules()
        assert len(schedules) == 1
        assert schedules[0].id == "test-job"


if __name__ == "__main__":
    # Run tests manually for debugging
    asyncio.run(test_broker_imports_and_initialization())
    print("✓ Import and initialization test passed")
    
    asyncio.run(test_broker_with_scheduler())
    print("✓ Broker with scheduler test passed")
    
    asyncio.run(test_broker_heartbeat_and_pid())
    print("✓ Heartbeat and PID test passed")
    
    asyncio.run(test_two_brokers_discover_each_other())
    print("✓ Two brokers discovery test passed")
    
    asyncio.run(test_broker_without_subscribers())
    print("✓ Single broker test passed")
    
    print("\n✅ All tests passed!")
