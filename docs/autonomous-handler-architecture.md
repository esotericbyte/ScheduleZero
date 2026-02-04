# Autonomous Handler Architecture

## Overview

Autonomous handlers are self-contained ScheduleZero units that can operate independently with their own scheduler, event broker, and handlers. They can run "offline" (disconnected) and optionally reconnect to a central server.

## Use Cases

### 1. **Edge Computing / IoT Devices**
- Handler runs on edge device with spotty network
- Continues processing schedules during network outages
- Syncs with central server when connected

### 2. **Development / Testing**
- Spin up complete ScheduleZero instance for testing
- No need for separate server process
- Easier to debug in isolation

### 3. **Microservices Architecture**
- Each service has its own scheduler
- Services coordinate via ZMQ event broker when needed
- Graceful degradation if services go offline

### 4. **High Availability**
- Multiple autonomous instances with event broker
- Leader election ensures one active scheduler
- Automatic failover on instance failure

## Architecture Modes

### Mode 1: Full Server (Current Default)
```
┌─────────────────────────────────────┐
│      ScheduleZero Server            │
│                                     │
│  ┌──────────┐  ┌─────────────────┐ │
│  │ Tornado  │  │   APScheduler   │ │
│  │  Server  │  │   + Event       │ │
│  │          │  │     Broker      │ │
│  └──────────┘  └─────────────────┘ │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Handler Registry           │  │
│  │   - Remote (ZMQ)             │  │
│  │   - Local (Python funcs)     │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   ZMQ Registration Server    │  │
│  │   (for remote handlers)      │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         ▲
         │ ZMQ
         │
    ┌────┴─────┐
    │  Remote  │
    │ Handlers │
    └──────────┘
```

**Enabled Components:**
- ✅ Tornado Server (API + Portal)
- ✅ APScheduler
- ✅ ZMQ Event Broker (optional, for distributed)
- ✅ Handler Registry (local + remote)
- ✅ ZMQ Registration Server

### Mode 2: Minimal Server (No Remote Handlers)
```
┌─────────────────────────────────────┐
│   ScheduleZero Minimal Server       │
│                                     │
│  ┌──────────┐  ┌─────────────────┐ │
│  │ Tornado  │  │   APScheduler   │ │
│  │  Server  │  │                 │ │
│  └──────────┘  └─────────────────┘ │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Local Handler Registry     │  │
│  │   (Python functions only)    │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Enabled Components:**
- ✅ Tornado Server
- ✅ APScheduler
- ❌ ZMQ Event Broker
- ✅ Local Handler Registry only
- ❌ ZMQ Registration Server

**Use Case:** Simple single-process deployment

### Mode 3: Autonomous Handler (Self-Contained)
```
┌─────────────────────────────────────┐
│     Autonomous Handler              │
│                                     │
│  ┌─────────────────┐                │
│  │  APScheduler    │                │
│  │  + Event Broker │                │
│  │   (optional)    │                │
│  └─────────────────┘                │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Local Handler Registry     │  │
│  │   (this handler's functions) │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   ZMQ Client (optional)      │  │
│  │   Connect to central server  │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         │ Optional ZMQ connection
         │ (syncs schedules when online)
         ▼
    ┌────────────┐
    │  Central   │
    │  Server    │
    └────────────┘
```

**Enabled Components:**
- ❌ Tornado Server (handler doesn't need web UI)
- ✅ APScheduler
- ✅ ZMQ Event Broker (optional, for multi-instance)
- ✅ Local Handler Registry
- ✅ ZMQ Client (optional, to report to server)

**Use Case:** Edge device, microservice, isolated handler

### Mode 4: Distributed Cluster
```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Instance 1     │  │   Instance 2     │  │   Instance 3     │
│                  │  │                  │  │                  │
│  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │
│  │  Scheduler │  │  │  │  Scheduler │  │  │  │  Scheduler │  │
│  │  + Broker  │◄─┼──┼─►│  + Broker  │◄─┼──┼─►│  + Broker  │  │
│  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │
│                  │  │                  │  │                  │
│  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │
│  │  Handlers  │  │  │  │  Handlers  │  │  │  │  Handlers  │  │
│  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                    ZMQ Event Broker PUB/SUB
                    (schedule sync + leader election)
```

**Enabled Components (per instance):**
- ✅ Tornado Server (each has own API)
- ✅ APScheduler
- ✅ ZMQ Event Broker (required for coordination)
- ✅ Handler Registry (local + remote)
- ❌ ZMQ Registration Server (not needed - handlers are local)

**Use Case:** High availability, load distribution

## Component Configuration Schema

### YAML Configuration Format

```yaml
# deployments/{deployment}/config.yaml

deployment:
  name: "production"
  mode: "full"  # full | minimal | autonomous | distributed
  
components:
  # Web Server
  tornado:
    enabled: true
    host: "0.0.0.0"
    port: 8888
    
  # Job Scheduler
  scheduler:
    enabled: true
    datastore:
      type: "sqlite"  # sqlite | postgresql | memory
      path: "deployments/production/schedulezero_jobs.db"
      # For PostgreSQL:
      # url: "postgresql+asyncpg://user:pass@localhost/schedules"
    
  # Event Broker (for distributed scheduling)
  event_broker:
    enabled: false  # true for distributed mode
    type: "zmq"  # zmq | redis | mqtt | local
    # ZMQ config
    publish_address: "tcp://0.0.0.0:5555"
    subscribe_addresses:
      - "tcp://instance-2:5555"
      - "tcp://instance-3:5555"
    heartbeat_interval: 5
    # Redis config (if type: redis)
    # redis_url: "redis://localhost:6379"
    
  # Handler Registry
  handlers:
    local:
      enabled: true
      # Import modules with @register_local decorators
      modules:
        - "my_app.handlers.tasks"
        - "my_app.handlers.notifications"
    
    remote:
      enabled: true
      registration_server:
        enabled: true
        address: "tcp://0.0.0.0:5556"
      
  # ZMQ Client (for autonomous handlers connecting to server)
  zmq_client:
    enabled: false
    server_address: "tcp://central-server:5556"
    handler_id: "edge-device-001"
    reconnect_interval: 30  # seconds

# Mode Presets (override components based on mode)
presets:
  full:
    components:
      tornado.enabled: true
      scheduler.enabled: true
      event_broker.enabled: false
      handlers.local.enabled: true
      handlers.remote.enabled: true
      zmq_client.enabled: false
      
  minimal:
    components:
      tornado.enabled: true
      scheduler.enabled: true
      event_broker.enabled: false
      handlers.local.enabled: true
      handlers.remote.enabled: false
      zmq_client.enabled: false
      
  autonomous:
    components:
      tornado.enabled: false
      scheduler.enabled: true
      event_broker.enabled: false  # can be true for multi-instance
      handlers.local.enabled: true
      handlers.remote.enabled: false
      zmq_client.enabled: true  # optional, for reporting to central
      
  distributed:
    components:
      tornado.enabled: true
      scheduler.enabled: true
      event_broker.enabled: true
      event_broker.type: "zmq"
      handlers.local.enabled: true
      handlers.remote.enabled: true
      zmq_client.enabled: false
```

## Implementation Strategy

### Phase 1: Configuration Loading ✅ (Already Have)
- [x] `app_configuration.py` - loads config files
- [x] `deployment_config.py` - deployment-specific settings
- [ ] Add component enable/disable flags

### Phase 2: Component Toggle System
Create `ComponentManager` class:

```python
class ComponentManager:
    """Manages conditional startup/shutdown of components."""
    
    def __init__(self, config: dict):
        self.config = config
        self.components = {}
    
    async def start_tornado(self):
        """Start Tornado server if enabled."""
        if not self.config['components']['tornado']['enabled']:
            return None
        # ... start tornado
    
    async def start_scheduler(self):
        """Start APScheduler if enabled."""
        if not self.config['components']['scheduler']['enabled']:
            return None
        # ... start scheduler with configured datastore
    
    async def start_event_broker(self):
        """Start event broker if enabled."""
        broker_config = self.config['components']['event_broker']
        if not broker_config['enabled']:
            return None
        
        broker_type = broker_config['type']
        if broker_type == 'zmq':
            return ZMQEventBroker(...)
        elif broker_type == 'redis':
            return RedisEventBroker(...)
        # ...
    
    async def start_all(self):
        """Start all enabled components."""
        self.components['scheduler'] = await self.start_scheduler()
        self.components['event_broker'] = await self.start_event_broker()
        self.components['tornado'] = await self.start_tornado()
        # ...
    
    async def stop_all(self):
        """Stop all running components."""
        # Stop in reverse order
        # ...
```

### Phase 3: Autonomous Handler Template

Create `AutonomousHandler` base class:

```python
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
            
            @self.register_handler
            async def collect_sensor_data(self):
                # ... collect data
                pass
            
            @self.register_handler
            async def process_data(self, data):
                # ... process offline
                pass
        
        # Run standalone
        handler = MyEdgeDevice()
        await handler.run()  # Starts scheduler, registers handlers, runs forever
    """
    
    def __init__(
        self,
        handler_id: str,
        deployment: str = "default",
        central_server: str | None = None,
        enable_event_broker: bool = False
    ):
        self.handler_id = handler_id
        self.deployment = deployment
        self.central_server = central_server
        
        # Create component manager with autonomous preset
        self.config = load_autonomous_config(deployment)
        self.manager = ComponentManager(self.config)
        
        # Local handler registry
        self.local_registry = LocalHandlerRegistry()
        
        # Optional ZMQ client for central server
        self.zmq_client = None
        if central_server:
            self.zmq_client = ZMQClient(central_server)
    
    def register_handler(self, func):
        """Decorator to register handler methods."""
        self.local_registry.register(
            handler_id=self.handler_id,
            func=func,
            methods=[func.__name__]
        )
        return func
    
    async def run(self):
        """Start autonomous handler (scheduler + handlers)."""
        # Start components
        await self.manager.start_all()
        
        # Connect to central server if configured
        if self.zmq_client:
            await self._connect_to_central()
        
        # Keep running
        await asyncio.Event().wait()  # Run forever
    
    async def _connect_to_central(self):
        """Connect to central server and register."""
        # Report status to central server
        # Sync schedules if needed
        pass
```

### Phase 4: Offline/Online Mode Switching

```python
class OfflineAwareHandler(AutonomousHandler):
    """Handler that gracefully handles network outages."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_online = False
        self.pending_syncs = []
    
    async def run(self):
        """Start with connection monitoring."""
        await super().run()
        
        # Start connection monitor
        asyncio.create_task(self._monitor_connection())
    
    async def _monitor_connection(self):
        """Periodically check connection to central server."""
        while True:
            try:
                if self.zmq_client:
                    self.zmq_client.ping()
                    if not self.is_online:
                        await self._on_connected()
                    self.is_online = True
            except Exception:
                if self.is_online:
                    await self._on_disconnected()
                self.is_online = False
            
            await asyncio.sleep(30)  # Check every 30s
    
    async def _on_connected(self):
        """Called when connection restored."""
        logger.info("Connected to central server")
        # Sync pending changes
        await self._sync_pending()
    
    async def _on_disconnected(self):
        """Called when connection lost."""
        logger.warning("Disconnected from central server - running offline")
        # Continue processing locally
    
    async def _sync_pending(self):
        """Sync changes made while offline."""
        for sync_item in self.pending_syncs:
            # Send to central server
            pass
        self.pending_syncs.clear()
```

## Example Deployments

### Example 1: Edge Device (Autonomous)

```yaml
# deployments/edge-device/config.yaml
deployment:
  name: "edge-device-001"
  mode: "autonomous"

components:
  tornado:
    enabled: false  # No web UI on edge device
  
  scheduler:
    enabled: true
    datastore:
      type: "sqlite"
      path: "deployments/edge-device/local.db"
  
  event_broker:
    enabled: false  # Single instance
  
  handlers:
    local:
      enabled: true
      modules:
        - "edge_device.handlers"
    remote:
      enabled: false
  
  zmq_client:
    enabled: true
    server_address: "tcp://central-server.local:5556"
    handler_id: "edge-device-001"
    reconnect_interval: 60
```

```python
# edge_device/handlers.py
from schedule_zero.autonomous import AutonomousHandler

class EdgeDevice(AutonomousHandler):
    @register_handler
    async def collect_temperature(self):
        temp = read_sensor()
        await self.store_locally(temp)
        
        if self.is_online:
            await self.send_to_central(temp)
    
    @register_handler
    async def check_alerts(self):
        # Process locally even when offline
        if temp > THRESHOLD:
            trigger_local_alarm()

# Run
handler = EdgeDevice(handler_id="edge-001", central_server="tcp://central:5556")
await handler.run()
```

### Example 2: Distributed Cluster (High Availability)

```yaml
# deployments/production-1/config.yaml
deployment:
  name: "production-1"
  mode: "distributed"

components:
  tornado:
    enabled: true
    port: 8888
  
  scheduler:
    enabled: true
    datastore:
      type: "postgresql"
      url: "postgresql+asyncpg://user:pass@db-cluster/schedules"
  
  event_broker:
    enabled: true
    type: "zmq"
    publish_address: "tcp://0.0.0.0:5555"
    subscribe_addresses:
      - "tcp://prod-2.internal:5555"
      - "tcp://prod-3.internal:5555"
  
  handlers:
    local:
      enabled: true
      modules:
        - "my_app.handlers"
    remote:
      enabled: false  # All handlers are local in this setup
```

**Result:** 3 instances, shared PostgreSQL datastore, ZMQ event broker keeps schedules in sync, leader election ensures only one runs jobs.

## Migration Path

### Current Users
1. **No changes needed** - default mode is "full" (current behavior)
2. **Config migration**: Add `components:` section to existing configs
3. **Gradual adoption**: Enable new features incrementally

### New Features
1. **Local handlers**: Add `@register_local` decorator
2. **Autonomous mode**: Set `mode: autonomous` in config
3. **Distributed**: Enable event broker, add subscribe addresses

## Testing Strategy

1. **Unit Tests**: Test ComponentManager start/stop logic
2. **Integration Tests**: Test each mode end-to-end
3. **Network Tests**: Test offline/online transitions
4. **Failure Tests**: Test leader election, failover

## Next Steps

1. ✅ ZMQ Event Broker implemented
2. ✅ Local Handler Registry implemented
3. ⏭️ Implement ComponentManager class
4. ⏭️ Add component enable/disable to config files
5. ⏭️ Create AutonomousHandler base class
6. ⏭️ Test distributed deployment
7. ⏭️ Document migration guide
