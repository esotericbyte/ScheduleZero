"""
ZeroMQ Event Broker for APScheduler 4.x

Provides distributed event coordination using ZeroMQ pub/sub pattern.
This is designed to be added to the APScheduler fork at:
  apscheduler/src/apscheduler/eventbrokers/zmq.py

Features:
- Pub/Sub event distribution across scheduler instances
- Process heartbeat with PID tracking
- Leader election for distributed coordination
- Dead instance detection via missed heartbeats
- Zero external dependencies (no Redis/MQTT broker needed)

Architecture:
- Each ScheduleZero instance runs one scheduler with ZMQ event broker
- PUB socket broadcasts events to other instances
- SUB socket receives events from other instances
- Direct instance-to-instance communication (brokerless)

Process Coordination:
- PID-based leader election (lowest PID wins)
- Heartbeat messages every N seconds
- Automatic failover when instance dies
"""
from __future__ import annotations

import asyncio
import os
import time
from asyncio import CancelledError
from contextlib import AsyncExitStack
from logging import Logger
from typing import Any

import attrs
import zmq
import zmq.asyncio
from attr.validators import instance_of

from .._events import Event
from .._utils import create_repr
from .base import BaseExternalEventBroker


@attrs.define(eq=False, repr=False)
class ZMQEventBroker(BaseExternalEventBroker):
    """
    ZeroMQ-based event broker for distributed APScheduler coordination.
    
    Requires the pyzmq_ library to be installed.

    .. _pyzmq: https://pypi.org/project/pyzmq/
    
    :param publish_address: ZMQ address to publish events (e.g., ``tcp://0.0.0.0:5555``)
    :param subscribe_addresses: List of ZMQ addresses to subscribe to (other instances)
    :param instance_id: Unique identifier for this scheduler instance
    :param heartbeat_interval: Seconds between heartbeats (default: 5)
    :param stop_check_interval: Interval to check if should stop (default: 1)
    
    Example::
    
        from apscheduler import AsyncScheduler
        from apscheduler.eventbrokers.zmq import ZMQEventBroker
        from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
        
        # Instance 1
        event_broker = ZMQEventBroker(
            publish_address="tcp://0.0.0.0:5555",
            subscribe_addresses=["tcp://other-instance:5555"],
            instance_id="scheduler-1"
        )
        datastore = SQLAlchemyDataStore("sqlite+aiosqlite:///scheduler1.db")
        scheduler = AsyncScheduler(datastore, event_broker=event_broker)
    """
    
    publish_address: str = attrs.field(validator=instance_of(str))
    subscribe_addresses: list[str] = attrs.field(
        kw_only=True, factory=list, validator=instance_of(list)
    )
    instance_id: str | None = attrs.field(kw_only=True, default=None)
    heartbeat_interval: int = attrs.field(kw_only=True, default=5)
    stop_check_interval: float = attrs.field(kw_only=True, default=1)
    
    _context: zmq.asyncio.Context = attrs.field(init=False)
    _pub_socket: zmq.asyncio.Socket = attrs.field(init=False)
    _sub_socket: zmq.asyncio.Socket | None = attrs.field(init=False, default=None)
    _pid: int = attrs.field(init=False, default=os.getpid())
    _alive_instances: dict[str, dict[str, Any]] = attrs.field(init=False, factory=dict)
    _is_leader: bool = attrs.field(init=False, default=False)
    _stopped: bool = attrs.field(init=False, default=True)
    
    def __attrs_post_init__(self) -> None:
        if self.instance_id is None:
            object.__setattr__(self, "instance_id", f"scheduler-{self._pid}")
    
    def __repr__(self) -> str:
        return create_repr(self, "publish_address", "instance_id")
    
    async def start(self, exit_stack: AsyncExitStack, logger: Logger) -> None:
        """Initialize ZMQ sockets and start background tasks."""
        await super().start(exit_stack, logger)
        
        self._context = zmq.asyncio.Context()
        exit_stack.callback(self._context.term)
        
        # Publisher socket (send events to other instances)
        self._pub_socket = self._context.socket(zmq.PUB)
        self._pub_socket.bind(self.publish_address)
        exit_stack.callback(self._pub_socket.close)
        
        # Subscriber socket (receive events from other instances)
        if self.subscribe_addresses:
            self._sub_socket = self._context.socket(zmq.SUB)
            for address in self.subscribe_addresses:
                self._sub_socket.connect(address)
            # Subscribe to all topics
            self._sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
            exit_stack.callback(self._sub_socket.close)
        
        object.__setattr__(self, "_stopped", False)
        exit_stack.callback(setattr, self, "_stopped", True)
        
        # Start background tasks
        if self._sub_socket:
            self._task_group.start_soon(
                self._subscriber_loop, name="ZMQ subscriber"
            )
        
        self._task_group.start_soon(
            self._heartbeat_loop, name="ZMQ heartbeat"
        )
        
        self._task_group.start_soon(
            self._cleanup_loop, name="ZMQ cleanup"
        )
        
        # Send initial registration
        await self._publish_heartbeat()
        
        self._logger.info(
            "ZMQ Event Broker started (instance=%s, publish=%s, pid=%d)",
            self.instance_id,
            self.publish_address,
            self._pid
        )
    
    async def publish(self, event: Event) -> None:
        """Publish an APScheduler event to all subscribed instances."""
        notification = self.generate_notification(event)
        
        # Wrap with metadata for PID tracking
        message = {
            "type": "event",
            "instance_id": self.instance_id,
            "pid": self._pid,
            "payload": notification
        }
        
        await self._pub_socket.send_json(message)
        
        # Also publish locally
        await self.publish_local(event)
    
    async def _subscriber_loop(self) -> None:
        """Background task: receive and process events from other instances."""
        assert self._sub_socket is not None
        
        while not self._stopped:
            try:
                # Check for messages with timeout
                if await self._sub_socket.poll(timeout=int(self.stop_check_interval * 1000)):
                    message = await self._sub_socket.recv_json()
                    await self._handle_message(message)
            except CancelledError:
                break
            except Exception:
                self._logger.exception("Error in ZMQ subscriber loop")
    
    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Process received ZMQ message."""
        msg_type = message.get("type")
        
        if msg_type == "event":
            # Another instance published an APScheduler event
            instance_id = message.get("instance_id")
            if instance_id != self.instance_id:  # Don't process our own events
                payload = message.get("payload")
                if isinstance(payload, bytes):
                    event = self.reconstitute_event(payload)
                    if event is not None:
                        await self.publish_local(event)
        
        elif msg_type == "heartbeat":
            # Another instance is alive
            instance_id = message.get("instance_id")
            if instance_id and instance_id != self.instance_id:
                self._alive_instances[instance_id] = {
                    "pid": message.get("pid"),
                    "address": message.get("address"),
                    "last_seen": time.time()
                }
                await self._check_leader_election()
        
        elif msg_type == "shutdown":
            # Another instance is shutting down
            instance_id = message.get("instance_id")
            if instance_id in self._alive_instances:
                del self._alive_instances[instance_id]
                await self._check_leader_election()
    
    async def _heartbeat_loop(self) -> None:
        """Background task: send periodic heartbeat messages."""
        while not self._stopped:
            await self._publish_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _publish_heartbeat(self) -> None:
        """Send heartbeat message to other instances."""
        message = {
            "type": "heartbeat",
            "instance_id": self.instance_id,
            "pid": self._pid,
            "address": self.publish_address
        }
        
        await self._pub_socket.send_json(message)
    
    async def _cleanup_loop(self) -> None:
        """Background task: remove dead instances."""
        while not self._stopped:
            await asyncio.sleep(self.heartbeat_interval * 2)
            
            now = time.time()
            timeout = self.heartbeat_interval * 3  # Consider dead after 3 missed heartbeats
            
            dead_instances = [
                instance_id
                for instance_id, info in self._alive_instances.items()
                if now - info["last_seen"] > timeout
            ]
            
            for instance_id in dead_instances:
                pid = self._alive_instances[instance_id]["pid"]
                del self._alive_instances[instance_id]
                self._logger.warning(
                    "Instance %s (PID %d) removed (heartbeat timeout)",
                    instance_id, pid
                )
            
            if dead_instances:
                await self._check_leader_election()
    
    async def _check_leader_election(self) -> None:
        """Determine leader based on lowest PID (simple election)."""
        all_pids = [self._pid] + [info["pid"] for info in self._alive_instances.values()]
        leader_pid = min(all_pids)
        
        was_leader = self._is_leader
        object.__setattr__(self, "_is_leader", leader_pid == self._pid)
        
        if self._is_leader and not was_leader:
            self._logger.info(
                "Instance %s (PID %d) elected as leader",
                self.instance_id, self._pid
            )
        elif not self._is_leader and was_leader:
            self._logger.info(
                "Instance %s (PID %d) no longer leader",
                self.instance_id, self._pid
            )
    
    @property
    def is_leader(self) -> bool:
        """Check if this instance is the elected leader."""
        return self._is_leader
    
    def get_alive_instances(self) -> dict[str, dict[str, Any]]:
        """Get currently alive scheduler instances with their PIDs and addresses."""
        return self._alive_instances.copy()
