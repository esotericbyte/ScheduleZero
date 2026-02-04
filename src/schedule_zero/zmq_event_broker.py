"""
ZeroMQ Event Broker for APScheduler 4.x

Provides distributed event coordination using ZeroMQ pub/sub pattern.
Standalone ScheduleZero implementation - imports from PyPI APScheduler.

Architecture:
- One scheduler per ScheduleZero instance (publisher)
- PUB/SUB pattern for event broadcasting
- No central broker required (brokerless)
- Direct instance-to-instance communication

Event Flow:
1. Scheduler A creates/modifies a schedule → publishes event
2. All subscribed instances receive event via ZMQ
3. Each instance updates its local datastore
4. Consistent view across all instances

Process Coordination (PID Management):
- Each instance registers its PID with heartbeat
- Leader election for distributed coordination
- Dead instance detection via missed heartbeats
- Automatic failover on instance failure
"""
from __future__ import annotations

import asyncio
import base64
import os
import time
from asyncio import CancelledError
from contextlib import AsyncExitStack
from logging import Logger
from typing import Any

import attrs
import zmq
import zmq.asyncio

# Import from PyPI APScheduler (no fork needed!)
try:
    # APScheduler 4.x
    from apscheduler._events import Event
    from apscheduler.eventbrokers.base import BaseExternalEventBroker
except ImportError:
    raise ImportError(
        "ZMQEventBroker requires APScheduler 4.x. "
        "Install with: pip install 'apscheduler>=4.0.0a5'"
    )


@attrs.define(eq=False, repr=False)
class ZMQEventBroker(BaseExternalEventBroker):
    """
    ZeroMQ-based event broker for distributed APScheduler coordination.
    
    Features:
    - Pub/Sub event distribution  
    - Process heartbeat and PID tracking
    - Leader election for coordination
    - Zero external dependencies (no Redis/MQTT)
    
    :param publish_address: ZMQ address to publish events (e.g., "tcp://0.0.0.0:5555")
    :param subscribe_addresses: List of ZMQ addresses to subscribe to (other instances)
    :param instance_id: Unique identifier for this scheduler instance
    :param heartbeat_interval: Seconds between heartbeats (default: 5)
    :param stop_check_interval: Interval to check if should stop (default: 1)
    """
    
    publish_address: str = attrs.field(validator=attrs.validators.instance_of(str))
    subscribe_addresses: list[str] = attrs.field(
        kw_only=True, factory=list, validator=attrs.validators.instance_of(list)
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
        return (
            f"ZMQEventBroker(publish_address={self.publish_address!r}, "
            f"instance_id={self.instance_id!r})"
        )
    
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
        
        # Initial leader election (for single-instance case)
        await self._check_leader_election()
        
        self._logger.info(
            "ZMQ Event Broker started (instance=%s, publish=%s, pid=%d, leader=%s)",
            self.instance_id,
            self.publish_address,
            self._pid,
            self._is_leader
        )
    
    async def publish(self, event: Event) -> None:
        """Publish an APScheduler event to all subscribed instances."""
        notification = self.generate_notification(event)
        
        # Wrap with metadata for PID tracking
        # Base64 encode the bytes payload for JSON serialization
        message = {
            "type": "event",
            "instance_id": self.instance_id,
            "pid": self._pid,
            "payload": base64.b64encode(notification).decode('ascii')
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
                if isinstance(payload, str):
                    # Decode base64 payload back to bytes
                    payload_bytes = base64.b64decode(payload)
                    event = self.reconstitute_event(payload_bytes)
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
    
    async def _publish_shutdown(self) -> None:
        """Send shutdown message to other instances."""
        message = {
            "type": "shutdown",
            "instance_id": self.instance_id,
            "pid": self._pid
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
        new_leader_status = (leader_pid == self._pid)
        
        self._logger.debug(
            "Leader election: my_pid=%d, all_pids=%s, leader_pid=%d, was=%s, new=%s",
            self._pid, all_pids, leader_pid, was_leader, new_leader_status
        )
        
        if new_leader_status != was_leader:
            object.__setattr__(self, "_is_leader", new_leader_status)
            
            if new_leader_status:
                self._logger.info(
                    "Instance %s (PID %d) elected as leader",
                    self.instance_id, self._pid
                )
            else:
                self._logger.info(
                    "Instance %s (PID %d) no longer leader (leader PID: %d)",
                    self.instance_id, self._pid, leader_pid
                )
    
    @property
    def is_leader(self) -> bool:
        """Check if this instance is the elected leader."""
        return self._is_leader
    
    def get_alive_instances(self) -> dict[str, dict[str, Any]]:
        """Get currently alive instances."""
        return self._alive_instances.copy()
