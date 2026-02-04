# ZMQ Event Broker Design for ScheduleZero

## Overview

The ZMQ Event Broker enables multiple ScheduleZero instances to coordinate schedules without a central message broker (like Redis/MQTT).

## Architecture Decision: Standalone Module

**Keep ZMQ Event Broker in ScheduleZero, NOT in APScheduler fork**

Reasons:
- ✅ No fork dependency - use stable APScheduler from PyPI
- ✅ Full control over implementation
- ✅ Faster iteration and testing
- ✅ Can still extend `BaseExternalEventBroker` from APScheduler

```python
# In ScheduleZero
from apscheduler.eventbrokers.base import BaseExternalEventBroker

class ZMQEventBroker(BaseExternalEventBroker):
    # ScheduleZero-specific implementation
```

## Communication Separation

### Handler Communication (Existing - Keep As-Is)

**Purpose:** Execute jobs on remote handlers
**Pattern:** REQ/REP (request-response)
**Files:** `zmq_client.py`, `zmq_registration_server.py`, `zmq_handler_base.py`

```
┌─────────────┐  REQ: execute_job()  ┌─────────────┐
│  Scheduler  │ ──────────────────►  │   Handler   │
│             │ ◄────────────────── │             │
└─────────────┘  REP: result         └─────────────┘
```

**Keep this!** It works well for job execution.

### Event Broker (New - PUB/SUB)

**Purpose:** Synchronize schedules across multiple scheduler instances
**Pattern:** PUB/SUB (broadcast)
**Files:** `zmq_event_broker.py`

```
┌──────────────┐ PUB: schedule_added  ┌──────────────┐
│ Scheduler A  │ ───────────────────► │ Scheduler B  │
│              │                       │              │
│              │                       │ Scheduler C  │
└──────────────┘                       └──────────────┘
```

## Memory & Persistence Strategy

### 1. In-Memory State (Already Implemented)

```python
_alive_instances: dict[str, dict[str, Any]] = {
    "scheduler-123": {
        "pid": 5678,
        "address": "tcp://10.0.0.5:5555",
        "last_seen": 1732089234.5
    }
}
```

**What to add:**
- Heartbeat history (last 10 heartbeats for timing analysis)
- Event metrics (events sent/received counts)
- Leadership transition history

### 2. Persistent State (Optional - Recommendations)

**Option A: SQLite State Store** (Recommended for ScheduleZero)

Store in deployment-specific database:
```
deployments/{deployment}/broker_state.db
```

**Tables:**
```sql
-- Instance registry (survives restarts)
CREATE TABLE instances (
    instance_id TEXT PRIMARY KEY,
    pid INTEGER,
    publish_address TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    is_active BOOLEAN
);

-- Leadership history (audit trail)
CREATE TABLE leadership_log (
    timestamp TIMESTAMP,
    instance_id TEXT,
    pid INTEGER,
    event_type TEXT  -- 'elected', 'resigned', 'timeout'
);

-- Event delivery metrics
CREATE TABLE event_metrics (
    timestamp TIMESTAMP,
    event_type TEXT,
    instance_id TEXT,
    count INTEGER
);
```

**Option B: Shared Datastore** (If using distributed SQL)

APScheduler already has SQLAlchemy datastore - extend it:
```python
# Add to existing schedulezero_jobs.db
CREATE TABLE broker_instances (
    instance_id TEXT PRIMARY KEY,
    ...
);
```

**Option C: Redis Cache** (Not recommended - adds dependency)

Only if you already have Redis for other reasons.

### 3. Event Log (Audit Trail)

**Recommendation: Rotating JSON log**

```
deployments/{deployment}/logs/broker_events.jsonl
```

Log format:
```json
{"ts": "2025-11-20T10:30:00Z", "type": "schedule_added", "instance": "scheduler-1", "schedule_id": "job-123"}
{"ts": "2025-11-20T10:30:01Z", "type": "heartbeat_received", "from": "scheduler-2", "pid": 5678}
{"ts": "2025-11-20T10:30:05Z", "type": "instance_timeout", "instance": "scheduler-3", "last_seen": "2025-11-20T10:29:45Z"}
{"ts": "2025-11-20T10:30:06Z", "type": "leader_elected", "instance": "scheduler-1", "pid": 1234}
```

Benefits:
- Debugging distributed issues
- Understanding event ordering
- Performance analysis
- Incident investigation

### 4. Configuration Persistence

Store broker topology configuration:

```yaml
# deployments/production/config.yaml
event_broker:
  enabled: true
  publish_address: "tcp://0.0.0.0:5555"
  subscribe_addresses:
    - "tcp://instance-2:5555"
    - "tcp://instance-3:5555"
  heartbeat_interval: 5
  persistence:
    enabled: true
    database: "deployments/production/broker_state.db"
    event_log: "deployments/production/logs/broker_events.jsonl"
    log_rotation: "daily"
```

## Recommended Implementation Priority

### Phase 1: MVP (Current Implementation)
- ✅ PUB/SUB event distribution
- ✅ Heartbeat tracking
- ✅ Leader election
- ✅ In-memory instance tracking

### Phase 2: Observability
- [ ] Event logging (JSON Lines format)
- [ ] Metrics tracking (events sent/received)
- [ ] Leadership transition logging
- [ ] Add to execution log API

### Phase 3: Persistence
- [ ] SQLite state store for instance registry
- [ ] Leadership history table
- [ ] Instance startup/shutdown records
- [ ] Query API for broker state

### Phase 4: Advanced Features
- [ ] Network partition detection
- [ ] Split-brain prevention
- [ ] Automatic topology discovery
- [ ] Health check endpoints

## Integration with ScheduleZero

### Single Instance (Default)

```python
# No event broker needed - use local only
scheduler = AsyncScheduler(
    datastore=SQLAlchemyDataStore("sqlite+aiosqlite:///schedulezero_jobs.db")
)
# LocalEventBroker used by default
```

### Multi-Instance (Production)

```python
# Enable ZMQ event broker for distributed coordination
from schedule_zero.zmq_event_broker import ZMQEventBroker

event_broker = ZMQEventBroker(
    publish_address="tcp://0.0.0.0:5555",
    subscribe_addresses=["tcp://instance-2:5555", "tcp://instance-3:5555"],
    instance_id=f"scheduler-{DEPLOYMENT}",
    heartbeat_interval=5
)

scheduler = AsyncScheduler(
    datastore=SQLAlchemyDataStore(f"sqlite+aiosqlite:///{DEPLOYMENT}.db"),
    event_broker=event_broker
)
```

### Deployment Configuration

Each deployment can have different broker settings:

```
deployments/
  default/
    - broker disabled (single instance)
  
  production/
    - broker enabled
    - publish: tcp://0.0.0.0:5555
    - subscribes to: [instance-2, instance-3]
  
  clock/
    - broker enabled
    - publish: tcp://0.0.0.0:5556
    - different port to avoid conflicts
```

## Why This Design?

### Advantages

1. **No External Dependencies**
   - No Redis/MQTT broker to manage
   - No additional infrastructure
   - Works with existing ZMQ library

2. **Direct Communication**
   - Lower latency than broker-based
   - No single point of failure (brokerless)
   - Each instance publishes directly

3. **Gradual Adoption**
   - Single instance: works as-is (no broker)
   - Add instances: enable broker incrementally
   - No breaking changes to existing deployments

4. **ScheduleZero Integration**
   - Extends existing ZMQ usage
   - Uses same deployment structure
   - Fits governor process management

### Limitations

1. **Full Mesh Topology**
   - Each instance must know about others
   - Manual configuration (subscribe_addresses)
   - Could add discovery later

2. **Network Partition**
   - Leader election may split during partition
   - Need split-brain detection (Phase 4)

3. **Scaling**
   - N instances = N-1 connections each
   - Fine for 3-10 instances
   - Beyond that, consider hub topology

## Next Steps

1. **Fix Current Implementation**
   - Remove broken APScheduler imports
   - Make standalone ScheduleZero module
   - Test with single instance first

2. **Add Observability**
   - JSON event log
   - Metrics tracking
   - Integration with execution log API

3. **Test Multi-Instance**
   - Start two schedulers
   - Add schedule on instance A
   - Verify appears on instance B

4. **Production Hardening**
   - Persistence layer
   - Network error handling
   - Split-brain prevention

## Example Usage

### Start Instance 1
```bash
# In terminal 1
export SCHEDULEZERO_DEPLOYMENT=instance1
export SCHEDULEZERO_BROKER_PUBLISH="tcp://0.0.0.0:5555"
export SCHEDULEZERO_BROKER_SUBSCRIBE="tcp://localhost:5556"
poetry run python scripts/server.py start
```

### Start Instance 2
```bash
# In terminal 2
export SCHEDULEZERO_DEPLOYMENT=instance2
export SCHEDULEZERO_BROKER_PUBLISH="tcp://0.0.0.0:5556"
export SCHEDULEZERO_BROKER_SUBSCRIBE="tcp://localhost:5555"
poetry run python scripts/server.py start
```

### Test Synchronization
```bash
# Add schedule to instance 1
curl -X POST http://localhost:8888/api/schedule -d '{...}'

# Verify appears in instance 2
curl http://localhost:8889/api/schedules
# Should see the same schedule!
```
