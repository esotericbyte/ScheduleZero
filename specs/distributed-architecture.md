# Distributed ScheduleZero Architecture

## Vision

**ScheduleZero as a modular, distributed system with replication topology and zone-based security.**

## Core Concepts

### 1. Node Types

**Master Node** (Admin/Scheduler):
- Full APScheduler core (creates schedules, executes jobs)
- Tornado with full CRUD API
- ZMQ handler registration
- Read-write database
- Publishes state changes via ZMQ

**Replica Node** (Reporter/Viewer):
- Read-only Tornado API (view schedules, history, metrics)
- Subscribes to master via ZMQ
- Read-only replicated database
- No scheduler (or passive scheduler for local handlers)
- Public-facing (DMZ) or internal

**Handler-Only Node**:
- No Tornado web server
- No APScheduler core
- Pure ZMQ handler process
- Receives job requests, executes, returns results
- Lightweight, runs anywhere

### 2. Replication Topology

```
Zone 1: Admin (Behind Firewall/VPN)
┌──────────────────────────────────────┐
│  Master Node (10.88.88.1)            │
│  ┌──────────────────────────────────┐│
│  │ Tornado: Full Admin API          ││
│  │ - POST /api/schedules (create)   ││
│  │ - PUT /api/schedules (update)    ││
│  │ - DELETE /api/schedules (delete) ││
│  ├──────────────────────────────────┤│
│  │ APScheduler: Master Scheduler    ││
│  │ - Executes all scheduled jobs    ││
│  │ - Dispatches to handlers         ││
│  ├──────────────────────────────────┤│
│  │ ZMQ Replication Publisher        ││
│  │ - PUB socket on tcp://*:5560     ││
│  │ - Publishes state changes:       ││
│  │   * schedule.created             ││
│  │   * schedule.updated             ││
│  │   * schedule.deleted             ││
│  │   * job.executed                 ││
│  │   * handler.registered           ││
│  └──────────────────────────────────┘│
│  Primary DB: schedules.db (RW)       │
└──────────┬───────────────────────────┘
           │ ZMQ PUB (tcp://10.88.88.1:5560)
           │
           ├─────────────────────────────┐
           │                             │
           ↓                             ↓
           
Zone 2: DMZ (Public Internet)      Zone 3: Regional Office
┌─────────────────────────────┐    ┌──────────────────────────┐
│  Reporter Node (public IP)  │    │  Local Replica           │
│  ┌─────────────────────────┐│    │  ┌──────────────────────┐│
│  │ Tornado: Read-Only API  ││    │  │ Tornado: Read-Only   ││
│  │ - GET /api/schedules    ││    │  │ - GET /api/schedules ││
│  │ - GET /api/history      ││    │  │ - Local handlers     ││
│  │ - GET /api/metrics      ││    │  └──────────────────────┘│
│  │ (No mutations allowed)  ││    │  Replicated DB (RO)      │
│  ├─────────────────────────┤│    └──────────────────────────┘
│  │ ZMQ Replication Sub     ││
│  │ - SUB socket            ││
│  │ - Receives state updates││
│  │ - Applies to local DB   ││
│  └─────────────────────────┘│
│  Replicated DB (RO)         │
└─────────────────────────────┘
```

### 3. Security Zones

**Zone 1: Admin/Control Plane** (WireGuard VPN)
- Master scheduler node
- Full admin API access
- Create/update/delete schedules
- Handler registration
- Audit logs
- **Access**: VPN only (WireGuard 10.88.88.0/24)

**Zone 2: Public/DMZ** (Internet-Facing)
- Read-only reporter nodes
- Public dashboard
- Metrics/status endpoints
- Execution history (sanitized)
- **Access**: Public internet (with WAF)
- **Replication filter**: Only safe data (no secrets, no handler internals)

**Zone 3: Regional/Branch** (Private Networks)
- Local replica nodes
- Regional handlers
- Reduced latency for local operations
- **Access**: Site-to-site VPN or private network

## Implementation

### ZMQ Replication Protocol

**Master publishes events:**

```python
# src/schedule_zero/replication/publisher.py
import zmq
import json
from typing import Dict, Any

class ReplicationPublisher:
    def __init__(self, bind_address: str = "tcp://*:5560"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(bind_address)
    
    def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish replication event to subscribers"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Topic-based filtering (subscribers can filter by event type)
        topic = event_type.encode('utf-8')
        payload = json.dumps(event).encode('utf-8')
        
        self.socket.send_multipart([topic, payload])
    
    def schedule_created(self, schedule: Schedule):
        """Notify replicas of new schedule"""
        self.publish_event("schedule.created", {
            "id": schedule.id,
            "task_id": schedule.task_id,
            "trigger": schedule.trigger.marshal(),
            "metadata": schedule.metadata,
            # Don't replicate sensitive fields (API keys, secrets)
        })
    
    def schedule_updated(self, schedule: Schedule):
        self.publish_event("schedule.updated", {
            "id": schedule.id,
            "task_id": schedule.task_id,
            "trigger": schedule.trigger.marshal(),
            "metadata": schedule.metadata,
        })
    
    def schedule_deleted(self, schedule_id: str):
        self.publish_event("schedule.deleted", {
            "id": schedule_id
        })
    
    def job_executed(self, job_id: str, result: Any, duration: float):
        """Publish job execution result (for history/metrics)"""
        self.publish_event("job.executed", {
            "job_id": job_id,
            "result": result,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def handler_registered(self, handler_id: str, methods: list):
        self.publish_event("handler.registered", {
            "handler_id": handler_id,
            "methods": methods,
        })


# Integrate into APScheduler callbacks
class ReplicatedScheduler:
    def __init__(self, scheduler: AsyncScheduler, replication: ReplicationPublisher):
        self.scheduler = scheduler
        self.replication = replication
    
    async def add_schedule(self, *args, **kwargs):
        """Wrap add_schedule to publish replication event"""
        schedule = await self.scheduler.add_schedule(*args, **kwargs)
        self.replication.schedule_created(schedule)
        return schedule
    
    async def remove_schedule(self, schedule_id: str):
        await self.scheduler.remove_schedule(schedule_id)
        self.replication.schedule_deleted(schedule_id)
```

**Replica subscribes to events:**

```python
# src/schedule_zero/replication/subscriber.py
import zmq
import json
import asyncio
from apscheduler import AsyncScheduler

class ReplicationSubscriber:
    def __init__(
        self,
        master_address: str,
        scheduler: AsyncScheduler,
        topics: list[str] = None
    ):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(master_address)
        
        # Subscribe to specific topics (or all)
        if topics:
            for topic in topics:
                self.socket.subscribe(topic.encode('utf-8'))
        else:
            self.socket.subscribe(b"")  # Subscribe to all
        
        self.scheduler = scheduler
    
    async def start(self):
        """Start replication subscriber loop"""
        while True:
            # Non-blocking receive with timeout
            if self.socket.poll(timeout=100):
                topic, payload = self.socket.recv_multipart()
                event = json.loads(payload.decode('utf-8'))
                await self.handle_event(event)
            
            await asyncio.sleep(0.01)
    
    async def handle_event(self, event: dict):
        """Apply replicated event to local scheduler"""
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "schedule.created":
            # Add schedule to local replica (passive mode)
            await self.scheduler.add_schedule(
                id=data["id"],
                task_id=data["task_id"],
                trigger=data["trigger"],
                metadata=data["metadata"],
                # Set to paused mode (don't execute on replica)
                paused=True
            )
        
        elif event_type == "schedule.updated":
            # Update local replica
            await self.scheduler.remove_schedule(data["id"])
            await self.scheduler.add_schedule(
                id=data["id"],
                task_id=data["task_id"],
                trigger=data["trigger"],
                metadata=data["metadata"],
                paused=True
            )
        
        elif event_type == "schedule.deleted":
            await self.scheduler.remove_schedule(data["id"])
        
        elif event_type == "job.executed":
            # Store in execution log (for history)
            await self.store_execution_log(data)
        
        # Add more handlers as needed
    
    async def store_execution_log(self, data: dict):
        """Store job execution history in local DB"""
        # Implementation depends on your log storage
        pass
```

### Node Configuration

**Master Node (`config.master.yaml`):**

```yaml
node:
  type: master
  name: sz-master-01
  zone: admin

network:
  bind_address: "10.88.88.1"  # VPN IP
  port: 8888
  
replication:
  enabled: true
  mode: publisher
  bind_address: "tcp://*:5560"
  
scheduler:
  mode: active  # Executes jobs
  database: "postgresql://localhost/schedulezero_master"
  
api:
  read_only: false  # Allow mutations
  require_auth: true
  allowed_origins: ["https://admin.schedulezero.local"]
```

**Replica Node (`config.replica.yaml`):**

```yaml
node:
  type: replica
  name: sz-replica-dmz-01
  zone: dmz

network:
  bind_address: "0.0.0.0"  # Public (behind WAF)
  port: 8888
  
replication:
  enabled: true
  mode: subscriber
  master_address: "tcp://10.88.88.1:5560"
  topics:
    - "schedule.*"
    - "job.executed"
    # Don't subscribe to sensitive events
  
scheduler:
  mode: passive  # Don't execute jobs, just store schedules
  database: "sqlite:///schedules_replica.db"
  
api:
  read_only: true  # Block mutations
  require_auth: false  # Public access
  allowed_origins: ["*"]
```

**Handler-Only Node (`config.handler.yaml`):**

```yaml
node:
  type: handler
  name: sz-handler-discord-01
  zone: regional

network:
  # No web server
  bind_address: null
  port: null
  
replication:
  enabled: false  # Handlers don't need replication
  
scheduler:
  enabled: false  # No scheduler
  
zmq:
  registration_server: "tcp://10.88.88.1:5555"
  handler_methods:
    - send_discord_message
    - schedule_raid_announcement
```

### Tornado API Layer (Zone-Aware)

```python
# src/schedule_zero/api/zone_aware_handler.py
from tornado.web import HTTPError

class ZoneAwareHandler(tornado.web.RequestHandler):
    def prepare(self):
        """Enforce zone security policies"""
        node_config = self.application.config["node"]
        api_config = self.application.config["api"]
        
        # Block mutations on read-only nodes
        if api_config["read_only"] and self.request.method in ["POST", "PUT", "DELETE"]:
            raise HTTPError(403, "This node is read-only. Mutations must be performed on admin node.")
        
        # Enforce authentication on admin nodes
        if node_config["zone"] == "admin" and api_config["require_auth"]:
            if not self.get_current_user():
                raise HTTPError(401, "Authentication required for admin zone")


class ScheduleHandler(ZoneAwareHandler):
    async def get(self):
        """Read schedules (allowed on all nodes)"""
        schedules = await self.application.scheduler.get_schedules()
        self.write({"schedules": schedules})
    
    async def post(self):
        """Create schedule (admin zone only)"""
        # ZoneAwareHandler.prepare() already blocked this if read_only=true
        data = tornado.escape.json_decode(self.request.body)
        
        schedule = await self.application.scheduler.add_schedule(**data)
        
        # Master node publishes replication event
        if self.application.replication:
            self.application.replication.schedule_created(schedule)
        
        self.write({"schedule": schedule})
```

### Replication Security Filter

```python
# src/schedule_zero/replication/security_filter.py
class ReplicationSecurityFilter:
    """Filter sensitive data from replication stream"""
    
    def __init__(self, zone: str):
        self.zone = zone
    
    def filter_schedule(self, schedule: dict) -> dict:
        """Sanitize schedule data based on target zone"""
        filtered = schedule.copy()
        
        if self.zone == "dmz":
            # Remove sensitive metadata for public nodes
            if "metadata" in filtered:
                filtered["metadata"] = self.sanitize_metadata(filtered["metadata"])
            
            # Remove handler-specific config
            filtered.pop("handler_config", None)
            filtered.pop("api_keys", None)
            filtered.pop("secrets", None)
        
        return filtered
    
    def sanitize_metadata(self, metadata: dict) -> dict:
        """Remove sensitive keys from metadata"""
        sensitive_keys = ["api_key", "token", "password", "secret", "webhook_url"]
        return {
            k: v for k, v in metadata.items()
            if not any(sensitive in k.lower() for sensitive in sensitive_keys)
        }


# Use in publisher
class ZoneAwarePublisher(ReplicationPublisher):
    def __init__(self, bind_address: str, zone_filters: dict):
        super().__init__(bind_address)
        self.zone_filters = zone_filters  # {"dmz": filter, "regional": filter}
    
    def publish_event(self, event_type: str, data: dict):
        """Publish with zone-specific filtering"""
        for zone, filter_obj in self.zone_filters.items():
            filtered_data = filter_obj.filter_schedule(data)
            
            # Publish to zone-specific topic
            topic = f"{zone}.{event_type}".encode('utf-8')
            payload = json.dumps({
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": filtered_data
            }).encode('utf-8')
            
            self.socket.send_multipart([topic, payload])
```

## Deployment Patterns

### Pattern 1: Single Master + Public Replica

```
Admin Zone (VPN):
  - Master Node (10.88.88.1) - Full control

DMZ (Public):
  - Replica Node (public-ip) - Read-only dashboard
  - NGINX + ModSecurity WAF
  - Filters sensitive data via replication
```

### Pattern 2: Multi-Region Replicas

```
HQ (Master):
  - Master Node - US East datacenter

Regional Offices (Replicas):
  - Replica Node - EU (read-only + local handlers)
  - Replica Node - APAC (read-only + local handlers)
  - Low-latency reads for local users
  - Handlers execute locally
```

### Pattern 3: HA Master with Failover

```
Active Master:
  - Master Node 1 - Primary scheduler (ZMQ PUB on 5560)

Standby Master:
  - Master Node 2 - Subscribes to events (ZMQ SUB)
  - Promotes to active if Master 1 fails
  - Uses shared PostgreSQL or Redis for state

Replicas:
  - Subscribe to both masters (failover)
```

## Comparison to Alternative Architectures

**Shared State Approach (e.g., external queue):**
```
Scheduler 1 → PostgreSQL/Redis ← Scheduler 2
            ↓
     Shared job store
     Leader election
     Both can execute jobs
```

**ScheduleZero's Replication Approach:**
```
Master (ZMQ PUB) → Replicas (ZMQ SUB)
    ↓                   ↓
Master DB          Replica DB (RO)
Executes jobs      View-only

Advantages:
- Simpler (no leader election)
- ZMQ replication (no external MQ)
- Zone-based security (DMZ replicas can't mutate)
- Flexible topology (pub/sub pattern)

Disadvantages:
- Master is SPOF (unless you add failover)
- Not true HA (replicas don't execute jobs)
```

## When to Use Each Pattern

**Monolithic (Current):**
- Single guild, small scale
- VPN-only access
- Simple deployment

**Single Master + DMZ Replica:**
- Want public dashboard
- Need read-only public access
- Admin operations via VPN

**Multi-Region Replicas:**
- Global users
- Low-latency reads required
- Regional handlers

**HA Masters + Replicas:**
- Mission-critical scheduling
- Can't tolerate downtime
- Need automatic failover

## Implementation Phases

**Phase 1: Replication Core** (2-3 weeks)
- ZMQ publisher/subscriber
- Event types (schedule.created, etc.)
- Basic replication protocol

**Phase 2: Zone-Aware API** (1 week)
- Read-only mode config
- Tornado handler refactor
- Security filters

**Phase 3: Node Types** (1-2 weeks)
- Master/replica/handler configs
- Deployment tooling
- Documentation

**Phase 4: HA Failover** (2-3 weeks)
- Master health checks
- Automatic promotion
- Shared state via PostgreSQL

## Benefits

✅ **Security**: DMZ replicas can't mutate schedules
✅ **Scalability**: Add read replicas as needed
✅ **Flexibility**: Choose topology per deployment
✅ **Zero External Dependencies**: Pure ZMQ, no Redis/RabbitMQ required
✅ **Zone Isolation**: Separate admin/public/regional nodes
✅ **Embeddable**: Like SQLite, but for schedulers

## Open Questions

1. **Conflict resolution**: What if master fails and replica promotes?
2. **Replication lag**: How to handle delays in event propagation?
3. **Partial replication**: Should replicas get all schedules or filtered subset?
4. **Handler affinity**: How to route jobs to specific regional handlers?
5. **Audit trail**: How to replicate audit logs without exposing sensitive data?

## Next Steps

- Prototype ZMQ replication publisher/subscriber
- Test latency and throughput
- Design conflict resolution strategy
- Document deployment patterns
- Build tooling for multi-node deployments
