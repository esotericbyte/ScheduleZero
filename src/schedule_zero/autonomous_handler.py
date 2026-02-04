"""Autonomous Handler base class for self-contained ScheduleZero units.

Autonomous handlers can operate independently with their own scheduler,
event broker, and local handlers. Perfect for:
- Edge computing / IoT devices with spotty network
- Microservices that need local scheduling
- Development / testing without separate server
- High availability with multi-instance deployment
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Callable

from .component_manager import ComponentManager, load_component_config
from .local_handler_registry import LocalHandlerRegistry
from .zmq_client import ZMQClient
from .logging_config import get_logger

logger = get_logger(__name__, component="AutonomousHandler")


class AutonomousHandler:
    """Base class for autonomous self-scheduling handlers.
    
    Example:
        class MyEdgeDevice(AutonomousHandler):
            def __init__(self):
                super().__init__(
                    handler_id="edge-001",
                    deployment="edge",
                    central_server="tcp://central:5556"  # optional
                )
            
            async def setup(self):
                '''Called after components start, before run loop.'''
                # Register handlers
                self.register_handler(self.collect_data)
                
                # Add schedules
                await self.add_schedule(
                    self.collect_data,
                    "interval",
                    minutes=5
                )
            
            async def collect_data(self):
                data = await self.read_sensors()
                await self.store_locally(data)
                
                if self.is_online():
                    await self.send_to_central(data)
        
        # Run standalone
        handler = MyEdgeDevice()
        await handler.run()
    """
    
    def __init__(
        self,
        handler_id: str,
        deployment: str = "autonomous",
        central_server: str | None = None,
        enable_event_broker: bool = False,
        config: dict | None = None
    ):
        """Initialize autonomous handler.
        
        Args:
            handler_id: Unique identifier for this handler
            deployment: Deployment name (for config/logs)
            central_server: Optional TCP address of central server
            enable_event_broker: Enable ZMQ event broker for multi-instance
            config: Optional config dict (otherwise loads from file)
        """
        self.handler_id = handler_id
        self.deployment = deployment
        self.central_server = central_server
        
        # Load or use provided config
        if config is None:
            config = self._create_autonomous_config(
                deployment,
                enable_event_broker
            )
        self.config = config
        
        # Component manager
        self.manager = ComponentManager(self.config)
        
        # Will be set after start
        self.scheduler = None
        self.local_registry: LocalHandlerRegistry | None = None
        self.zmq_client: ZMQClient | None = None
        
        # Online status
        self._is_online = False
        self._connection_monitor_task: asyncio.Task | None = None
    
    def _create_autonomous_config(
        self,
        deployment: str,
        enable_event_broker: bool
    ) -> dict:
        """Create autonomous mode configuration.
        
        Args:
            deployment: Deployment name
            enable_event_broker: Whether to enable distributed event broker
            
        Returns:
            Configuration dict
        """
        config = {
            'deployment': {
                'name': deployment,
                'mode': 'autonomous'
            },
            'components': {
                'tornado': {
                    'enabled': False  # No web UI for autonomous handlers
                },
                'scheduler': {
                    'enabled': True,
                    'datastore': {
                        'type': 'sqlite',
                        'path': f'deployments/{deployment}/{self.handler_id}.db'
                    }
                },
                'event_broker': {
                    'enabled': enable_event_broker,
                    'type': 'zmq',
                    'instance_id': self.handler_id
                },
                'handlers': {
                    'local': {
                        'enabled': True,
                        'modules': []  # Handlers registered programmatically
                    },
                    'remote': {
                        'enabled': False  # Autonomous = local only
                    }
                },
                'zmq_client': {
                    'enabled': self.central_server is not None,
                    'server_address': self.central_server,
                    'handler_id': self.handler_id
                }
            }
        }
        return config
    
    def register_handler(self, func: Callable, methods: list[str] | None = None) -> Callable:
        """Register a handler function.
        
        Args:
            func: The function to register
            methods: Method names (defaults to [func.__name__])
            
        Returns:
            The original function (unchanged)
        """
        if self.local_registry is None:
            raise RuntimeError("Handler not started yet - call run() first")
        
        if methods is None:
            methods = [func.__name__]
        
        self.local_registry.register(self.handler_id, func, methods)
        logger.info("Registered handler method", method=func.__name__)
        
        return func
    
    async def add_schedule(
        self,
        func: Callable,
        trigger: Any | str,  # Can be trigger instance or string
        **trigger_args
    ) -> str:
        """Add a schedule for a handler function.
        
        Args:
            func: The function to schedule
            trigger: Trigger type ("interval", "cron", "date") or Trigger instance
            **trigger_args: Arguments for trigger (e.g., minutes=5)
            
        Returns:
            Schedule ID
        """
        if self.scheduler is None:
            raise RuntimeError("Scheduler not started yet - call run() first")
        
        # Import trigger classes
        if isinstance(trigger, str):
            if trigger == "interval":
                from apscheduler.triggers.interval import IntervalTrigger
                trigger_obj = IntervalTrigger(**trigger_args)
            elif trigger == "cron":
                from apscheduler.triggers.cron import CronTrigger
                trigger_obj = CronTrigger(**trigger_args)
            elif trigger == "date":
                from apscheduler.triggers.date import DateTrigger
                trigger_obj = DateTrigger(**trigger_args)
            else:
                raise ValueError(f"Unknown trigger type: {trigger}")
        else:
            trigger_obj = trigger
        
        schedule = await self.scheduler.add_schedule(
            func,
            trigger_obj,
            id=f"{self.handler_id}_{func.__name__}"
        )
        
        logger.info("Added schedule", function=func.__name__, trigger=trigger)
        return schedule  # Returns schedule ID string
    
    async def setup(self):
        """Override this method to register handlers and schedules.
        
        Called after components start, before run loop begins.
        
        Example:
            async def setup(self):
                self.register_handler(self.my_task)
                await self.add_schedule(self.my_task, "interval", minutes=5)
        """
        pass
    
    async def run(self):
        """Start autonomous handler and run forever.
        
        This will:
        1. Start all enabled components (scheduler, handlers, etc.)
        2. Call setup() for user initialization
        3. Start connection monitoring if central server configured
        4. Run until interrupted
        """
        logger.info("Starting autonomous handler", handler_id=self.handler_id)
        
        # Start components
        async with self.manager:
            self.scheduler = self.manager.components.get('scheduler')
            self.local_registry = self.manager.components.get('local_handlers')
            self.zmq_client = self.manager.components.get('zmq_client')
            
            # Call user setup
            await self.setup()
            
            # Start connection monitoring if central server configured
            if self.zmq_client:
                self._connection_monitor_task = asyncio.create_task(
                    self._monitor_connection()
                )
            
            logger.info("Autonomous handler running", handler_id=self.handler_id)
            
            # Run until interrupted
            try:
                await asyncio.Event().wait()  # Wait forever
            except asyncio.CancelledError:
                logger.info("Autonomous handler stopping", handler_id=self.handler_id)
            finally:
                if self._connection_monitor_task:
                    self._connection_monitor_task.cancel()
                    try:
                        await self._connection_monitor_task
                    except asyncio.CancelledError:
                        pass
    
    async def _monitor_connection(self):
        """Monitor connection to central server."""
        reconnect_interval = self.config['components']['zmq_client'].get(
            'reconnect_interval',
            30
        )
        
        while True:
            try:
                if self.zmq_client:
                    self.zmq_client.ping()
                    if not self._is_online:
                        await self._on_connected()
                    self._is_online = True
            except Exception as e:
                if self._is_online:
                    await self._on_disconnected()
                self._is_online = False
                logger.debug(
                    "Connection check failed (running offline)",
                    error=str(e)
                )
            
            await asyncio.sleep(reconnect_interval)
    
    async def _on_connected(self):
        """Called when connection to central server is established.
        
        Override this to implement custom behavior on connection.
        """
        logger.info("Connected to central server")
    
    async def _on_disconnected(self):
        """Called when connection to central server is lost.
        
        Override this to implement custom behavior on disconnection.
        """
        logger.warning("Disconnected from central server - running offline")
    
    def is_online(self) -> bool:
        """Check if connected to central server.
        
        Returns:
            True if online, False if offline
        """
        return self._is_online
    
    async def execute_handler(self, method: str, *args, **kwargs) -> Any:
        """Execute a registered handler method.
        
        Args:
            method: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from the handler
        """
        if self.local_registry is None:
            raise RuntimeError("Handler not started yet")
        
        return await self.local_registry.execute(
            self.handler_id,
            method,
            *args,
            **kwargs
        )
