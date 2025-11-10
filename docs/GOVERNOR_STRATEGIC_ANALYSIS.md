---
title: Governor Strategic Analysis
tags:
  - exploration
  - planning
  - architecture
status: exploration
date: 2025-11-10
---

# Governor Strategic Analysis - Resource-Constrained & Distributed Systems

**Date**: 2025-11-10  
**Status**: STRATEGIC EXPLORATION - NO DEV UNTIL RESOLVED

## Executive Summary

Strategic questions about ProcessGovernor/Orchestrator role in:
1. **Resource-constrained environments** (low RAM, CPU conservation, cold starts)
2. **Staged/tiered processing** with optional telemetry
3. **Remote handler assistance** - can governor help handlers on other systems?
4. **Ecosystem viability** - is this a niche tool or core component?

**Current Telemetry Status**: ✅ **COMPLETE** - Job execution logging fully implemented!

---

## Question 1: Telemetry Status - What Do We Have?

### ✅ Job Execution Telemetry (COMPLETE)

**Full implementation in place:**

```python
# JobExecutionLog class (src/schedule_zero/job_execution_log.py)
- Captures: job_id, handler_id, method_name, timing, status, result, error, attempts
- Circular buffer: 1000 records in-memory (configurable)
- Thread-safe with locking
- Status tracking: running, success, error, timeout
```

**API Endpoints** (see `docs/EXECUTION_LOGGING_API.md`):
- `GET /api/executions` - Query history with filters (handler_id, job_id, status, limit)
- `GET /api/executions/stats` - Aggregated statistics, success rates, by-handler metrics
- `GET /api/executions/errors` - Recent failures with error details
- `POST /api/executions/clear` - Clear history (admin operation)

**Metrics Available**:
```json
{
  "total_executions": 1523,
  "lifetime_executions": 15234,  // Total since server start
  "success_count": 1489,
  "error_count": 34,
  "success_rate": 97.77,
  "avg_duration_ms": 245.3,
  "by_handler": {
    "dingdong": {
      "total": 823,
      "success": 823,
      "error": 0,
      "success_rate": 100.0,
      "avg_duration_ms": 123.4
    }
  },
  "buffer_size": 1000,
  "buffer_utilization": 0.85
}
```

**Telemetry Details**:
- ✅ **Start time** - When job execution began (UTC timestamp)
- ✅ **Completion time** - When finished (success or error)
- ✅ **Duration** - Milliseconds from start to completion
- ✅ **Result** - Handler return value (dict)
- ✅ **Error** - Exception message if failed
- ✅ **Retry tracking** - Attempt number (1-3), max_attempts
- ✅ **Parameters** - Summary of job params (truncated to 50 chars)

### ❓ ProcessGovernor/Handler Telemetry - BASIC

**Governor has basic metrics** (`governor_base.py: get_metrics()`):
```python
{
  'deployment': 'production',
  'running': True,
  'total_services': 5,
  'healthy_services': 4,
  'total_restarts': 12,
  'services': {
    'server': {
      'name': 'server',
      'pid': 12345,
      'status': 'running',
      'restart_count': 0,
      'last_error': None
    },
    'handler-dingdong': {
      'name': 'handler-dingdong',
      'pid': 12346,
      'status': 'running',
      'restart_count': 3,
      'last_error': 'ZMQ socket error'
    }
  }
}
```

**Current Governor Metrics**:
- ✅ Process status (running, stopped, crashed, restarting)
- ✅ PID tracking
- ✅ Restart count
- ✅ Last error message
- ❌ **NO** resource usage (CPU, memory, network)
- ❌ **NO** handler-specific metrics (ZMQ stats, queue depth, response times)
- ❌ **NO** historical trends
- ❌ **NO** health scores
- ❌ **NO** external monitoring integration (Prometheus, StatsD)

**Conclusion**: Job execution telemetry is complete and excellent. Governor/handler telemetry is basic (PID tracking, restart counts) but could be significantly enhanced.

---

## Question 2: Resource-Constrained Environments

### Scenario: Low RAM, CPU Conservation, Cold Starts

**Use Cases**:
1. **Raspberry Pi / Edge Devices** - 512MB-2GB RAM, limited CPU
2. **Shared VPS** - Multiple apps competing for resources
3. **Lambda/Serverless** - Cold start penalty, pay-per-execution
4. **Container Quotas** - Kubernetes memory/CPU limits
5. **High Handler Count** - 50+ handlers, but only 2-3 active at once

### Current State: Always-On Handlers

**ScheduleZero's default model**:
```
Server (Tornado + APScheduler) ────┬─→ Handler 1 (always running)
                                   ├─→ Handler 2 (always running)
                                   ├─→ Handler 3 (always running)
                                   └─→ Handler 4 (always running)
```

**Resource profile**:
- Each Python handler: ~30-50MB RAM baseline
- 10 handlers: 300-500MB just for idle handlers
- Plus server: ~100MB
- **Total: 400-600MB idle footprint**

### Proposed: Staged/Spin-Up Architecture

**Option A: Governor-Managed On-Demand Handlers**

```python
class StagedProcessGovernor(GovernorBase):
    """Governor that starts handlers on-demand and shuts them down after idle timeout."""
    
    def __init__(self, ...):
        self.idle_timeout = 300  # 5 minutes
        self.startup_timeout = 10  # 10 seconds max startup
        self.handler_last_used: Dict[str, datetime] = {}
        self.handler_state: Dict[str, str] = {}  # cold, warming, hot, cooling
    
    async def ensure_handler_ready(self, handler_id: str) -> bool:
        """
        Ensure handler is running before sending job.
        
        States:
        - cold: Not running, needs full startup
        - warming: Currently starting (wait for ready)
        - hot: Running and ready
        - cooling: Idle timeout reached, will shutdown soon
        """
        state = self.handler_state.get(handler_id, "cold")
        
        if state == "hot":
            # Already running, just update last used
            self.handler_last_used[handler_id] = datetime.now()
            return True
        
        elif state == "warming":
            # Wait for startup to complete (with timeout)
            return await self._wait_for_ready(handler_id, timeout=self.startup_timeout)
        
        elif state in ("cold", "cooling"):
            # Start the handler
            self.handler_state[handler_id] = "warming"
            logger.info(f"Starting on-demand handler: {handler_id}", method="ensure_handler_ready")
            
            if self.start_handler(handler_id):
                self.handler_state[handler_id] = "hot"
                self.handler_last_used[handler_id] = datetime.now()
                return True
            else:
                self.handler_state[handler_id] = "cold"
                return False
    
    async def _idle_monitor(self):
        """Background task: shutdown idle handlers."""
        while self._running:
            await asyncio.sleep(60)  # Check every minute
            
            now = datetime.now()
            for handler_id, last_used in list(self.handler_last_used.items()):
                if (now - last_used).total_seconds() > self.idle_timeout:
                    if self.handler_state.get(handler_id) == "hot":
                        logger.info(f"Handler idle timeout, shutting down: {handler_id}", 
                                   method="_idle_monitor", idle_seconds=(now - last_used).total_seconds())
                        
                        self.handler_state[handler_id] = "cooling"
                        self.stop_handler(handler_id)
                        self.handler_state[handler_id] = "cold"
```

**Integration with JobExecutor**:
```python
class JobExecutor:
    def __init__(self, zmq_client, execution_log, governor=None):
        self.zmq_client = zmq_client
        self.execution_log = execution_log
        self.governor = governor  # Optional staged governor
    
    async def __call__(self, job_id, handler_id, method_name, params):
        # If governor exists, ensure handler is ready
        if self.governor:
            ready = await self.governor.ensure_handler_ready(handler_id)
            if not ready:
                # Record startup failure
                record = self.execution_log.record_start(job_id, handler_id, method_name)
                self.execution_log.record_error(record, "Handler failed to start", is_final=True)
                return
        
        # Normal execution...
        record = self.execution_log.record_start(job_id, handler_id, method_name, params=params)
        # ... rest of execution
```

**Benefits**:
- 📉 **Reduced idle RAM**: Only active handlers consume memory
- 📉 **Lower CPU**: No idle processes churning
- ⚡ **Scalability**: Support 50+ handlers, run only 2-3 at once
- 💰 **Cost savings**: Serverless-like resource model on dedicated hardware

**Drawbacks**:
- ⏱️ **Cold start latency**: 2-10 seconds to start handler
- 🔧 **Complexity**: State machine for handler lifecycle
- 🐛 **Failure modes**: Startup failures, zombie processes
- 📊 **More telemetry needed**: Track startup times, idle periods

### Resource Metrics We'd Need

**Handler-level telemetry** (extended metrics):
```python
@dataclass
class HandlerMetrics:
    handler_id: str
    
    # Process metrics
    pid: Optional[int]
    cpu_percent: float  # psutil.Process().cpu_percent()
    memory_mb: float    # psutil.Process().memory_info().rss / 1024 / 1024
    
    # State tracking
    state: str  # cold, warming, hot, cooling
    uptime_seconds: float
    idle_seconds: float
    
    # Performance
    startup_time_ms: float  # How long to become ready
    total_jobs_executed: int
    avg_job_duration_ms: float
    last_job_at: Optional[datetime]
    
    # Health
    restart_count: int
    error_count: int
    last_error: Optional[str]
    health_score: float  # 0.0-1.0 based on success rate and uptime
```

**Governor-level telemetry**:
```python
{
  "resource_mode": "staged",  # always-on, staged, serverless
  "total_handlers_configured": 50,
  "handlers_currently_running": 3,
  "handlers_in_startup": 1,
  "total_memory_mb": 156.3,  # Sum of all running handlers + server
  "memory_saved_mb": 1843.7,  # Est. savings vs always-on
  "avg_cold_start_ms": 2341,
  "cold_starts_last_hour": 12,
  "handlers_by_state": {
    "cold": 45,
    "warming": 1,
    "hot": 3,
    "cooling": 1
  }
}
```

---

## Question 3: Governor as Remote Handler Assistant

### Can Governor Help Handlers on Other Systems?

**Scenario**: Distributed deployment with handlers on multiple machines:
```
┌─────────────────────────────────────────────────────┐
│ Server Machine (AWS us-east-1)                      │
│  ├─ ScheduleZero Server (port 4244)                │
│  └─ Governor (optional, only manages local)        │
└─────────────────────────────────────────────────────┘
           ↕ ZMQ over network
┌─────────────────────────────────────────────────────┐
│ Handler Machine 1 (AWS us-west-2)                   │
│  ├─ Discord Bot Handler (port 5555)                │
│  ├─ Governor? (could manage this machine's handlers)│
│  └─ Health Reporter (sends metrics to server)      │
└─────────────────────────────────────────────────────┘
           ↕ ZMQ over network
┌─────────────────────────────────────────────────────┐
│ Handler Machine 2 (On-premise)                      │
│  ├─ Database Backup Handler (port 5556)            │
│  └─ Governor? (manages local handlers)             │
└─────────────────────────────────────────────────────┘
```

### Option A: Autonomous Handlers (Current Recommended)

**Pattern**: Each handler machine manages its own processes.

```bash
# Handler Machine 1
systemd unit: schedulezero-discord-handler.service
  → Starts: python discord_handler.py
  → Restarts on failure
  → Reports status to journalctl

# Or with Supervisor (process control)
[program:discord-handler]
command=python discord_handler.py
autostart=true
autorestart=true
```

**Pros**:
- ✅ Simple, battle-tested (systemd/supervisor)
- ✅ No new infrastructure
- ✅ Works with existing deployment guide
- ✅ Handlers are truly autonomous

**Cons**:
- ❌ No centralized control
- ❌ Can't restart remote handler from server
- ❌ Manual coordination for updates

### Option B: Local Governors Per Machine

**Pattern**: Each handler machine runs a ProcessGovernor managing local handlers.

```bash
# Handler Machine 1
poetry run python governor.py start --deployment=production-west
  → Manages: discord-handler, webhook-handler
  → PID tracking, auto-restart, signal handling
  → Exposes status API (optional)

# Server machine can query governor API
curl http://handler-machine-1:9999/governor/status
→ {handlers: {...}, memory_mb: 156, ...}
```

**Pros**:
- ✅ Centralized telemetry collection
- ✅ Standardized process management
- ✅ Governor handles all complexity (PID, signals, restart)
- ✅ Can implement staged/on-demand locally

**Cons**:
- ➖ Adds governor as dependency on each machine
- ➖ More complex than systemd
- ➖ Governor becomes critical infrastructure

### Option C: Distributed Governor (New Architecture)

**Pattern**: Central Governor communicates with Agent processes on remote machines.

```
┌─────────────────────────────────────────────────────┐
│ Server Machine                                       │
│  ├─ ScheduleZero Server                            │
│  └─ DistributedGovernor (master)                   │
│      ├─ Tracks all handlers across all machines    │
│      ├─ API: /governor/restart/discord-handler     │
│      └─ Sends commands to Agents via ZMQ/gRPC      │
└─────────────────────────────────────────────────────┘
           ↕ Control channel (ZMQ/gRPC)
┌─────────────────────────────────────────────────────┐
│ Handler Machine 1                                    │
│  └─ GovernorAgent                                   │
│      ├─ Receives commands from master               │
│      ├─ Manages local handlers (start/stop/restart) │
│      └─ Reports metrics back to master              │
└─────────────────────────────────────────────────────┘
```

**Implementation sketch**:
```python
class GovernorAgent:
    """Runs on handler machines, receives commands from master."""
    
    def __init__(self, control_endpoint="tcp://server:4245"):
        self.control_socket = zmq.Context().socket(zmq.REP)
        self.control_socket.connect(control_endpoint)
        self.local_governor = ProcessGovernor(deployment="agent")
    
    async def run(self):
        """Listen for commands from master governor."""
        while True:
            command = await self.control_socket.recv_json()
            
            if command['action'] == 'start_handler':
                result = self.local_governor.start_handler(command['handler_id'])
            elif command['action'] == 'stop_handler':
                result = self.local_governor.stop_handler(command['handler_id'])
            elif command['action'] == 'get_metrics':
                result = self.local_governor.get_metrics()
            
            await self.control_socket.send_json({'status': 'ok', 'result': result})


class DistributedGovernor(GovernorBase):
    """Master governor that manages agents on remote machines."""
    
    def __init__(self, ...):
        self.agents: Dict[str, str] = {}  # agent_id → endpoint
        self.control_socket = zmq.Context().socket(zmq.REQ)
    
    def register_agent(self, agent_id: str, endpoint: str):
        """Register a remote agent."""
        self.agents[agent_id] = endpoint
    
    async def start_handler(self, handler_id: str):
        """Start handler on whichever agent owns it."""
        agent_id = self._get_agent_for_handler(handler_id)
        endpoint = self.agents[agent_id]
        
        self.control_socket.connect(endpoint)
        await self.control_socket.send_json({
            'action': 'start_handler',
            'handler_id': handler_id
        })
        response = await self.control_socket.recv_json()
        return response['status'] == 'ok'
    
    async def get_global_metrics(self) -> Dict:
        """Collect metrics from all agents."""
        metrics = {}
        for agent_id, endpoint in self.agents.items():
            agent_metrics = await self._query_agent(endpoint, 'get_metrics')
            metrics[agent_id] = agent_metrics
        return metrics
```

**Pros**:
- ✅ ✨ **Centralized control**: Restart any handler from one place
- ✅ ✨ **Global telemetry**: Single dashboard for all handlers
- ✅ ✨ **Coordinated operations**: Rolling restarts, blue/green deploys
- ✅ Enables staged/on-demand across machines

**Cons**:
- ❌ 🔥 **Significant complexity**: New distributed system to maintain
- ❌ 🔥 **Network dependency**: Control channel must be reliable
- ❌ 🔥 **Security**: Auth/encryption for control channel
- ❌ Split-brain scenarios if control channel fails

### Recommendation: Hybrid Approach

**For most deployments**: **Option B (Local Governors)**
- Run ProcessGovernor on each handler machine
- Optionally expose REST API for status (`/governor/status`, `/governor/metrics`)
- Server can poll these APIs for monitoring dashboard
- Handlers remain autonomous (governor is optional convenience)

**For advanced deployments**: **Option C (Distributed Governor)** becomes viable when:
- Managing 10+ handler machines
- Need coordinated operations (rolling restarts)
- Willing to invest in agent infrastructure
- Security and reliability requirements met

**Implementation phases**:
1. **Phase 1** (now): ProcessGovernor manages local machine only ✅
2. **Phase 2**: Add REST API to ProcessGovernor for status/metrics
3. **Phase 3**: Create monitoring dashboard that polls all governors
4. **Phase 4**: (Optional) DistributedGovernor for advanced use cases

---

## Question 4: Governor Viability - Niche vs. Core Ecosystem Component

### Current Position: Development/Testing Tool

From `docs/ARCHITECTURE_DECISION.md`:
> ProcessGovernor is essential for **testbed** but handlers should be **autonomous** in production (using systemd, Docker, K8s).

**Current thinking**: ProcessGovernor is a **niche** tool for:
- Development environments (quick start/stop)
- Testing (manage test fixtures)
- Simple single-machine deployments
- **NOT** recommended for distributed production

### Alternative Position: Core Ecosystem Component

**If we enhance ProcessGovernor with**:
1. **Staged/on-demand handlers** → Resource efficiency
2. **Extended telemetry** → Observability
3. **REST API** → Remote monitoring
4. **Agent mode** → Distributed management (optional)

**Then it becomes a core component that**:
- ✅ Solves real problems (resource constraints, cold starts)
- ✅ Provides value beyond systemd/supervisor
- ✅ Differentiates ScheduleZero from other schedulers
- ✅ Enables advanced deployment patterns

### Comparison: What Do Other Schedulers Offer?

| Feature | Celery | APScheduler | ScheduleZero | ScheduleZero + Enhanced Governor |
|---------|--------|-------------|--------------|----------------------------------|
| **Process Management** | Supervisor/systemd | Manual | ProcessGovernor | ✨ StagedGovernor |
| **Resource Efficiency** | Always-on workers | Always-on | Always-on | ✨ On-demand handlers |
| **Telemetry** | Flower dashboard | None | Job execution logs ✅ | ✨ + Handler metrics |
| **Remote Management** | Celery CLI | None | None | ✨ Agent mode (optional) |
| **Cold Start Support** | ❌ | ❌ | ❌ | ✨ Yes |
| **Auto-scaling** | Manual | ❌ | ❌ | ✨ Yes (staged mode) |

### Value Proposition

**If we implement staged/on-demand governor**:

**Use Case 1: Edge Computing**
> "We have 50 Raspberry Pis in retail stores. Each needs 20 scheduled jobs, but they only have 512MB RAM. With ScheduleZero's staged governor, we run the server (100MB) + only the 2-3 active handlers (60MB), saving 400MB per device."

**Use Case 2: Multi-Tenant SaaS**
> "We have 200 customers, each with custom job handlers. Instead of running 200 handlers 24/7 (10GB RAM), we use staged mode and spin up handlers on-demand. Average RAM usage: 800MB, saving 90%."

**Use Case 3: Serverless-Like on Bare Metal**
> "We want serverless efficiency (only pay for what we use) but on our own hardware. ScheduleZero's governor gives us cold starts, auto-shutdown, and resource tracking without vendor lock-in."

### Decision Matrix: Core vs. Niche

| Criteria | Keep Niche | Make Core |
|----------|------------|-----------|
| **Development effort** | ✅ Low (done) | ❌ High (3-4 weeks) |
| **Maintenance burden** | ✅ Low | ⚠️ Medium |
| **User value** | ⚠️ Nice-to-have | ✅ Differentiator |
| **Competitive advantage** | ❌ None | ✅ Unique feature |
| **Market fit** | Limited | Edge/IoT/multi-tenant |
| **Documentation effort** | ✅ Already done | ⚠️ Significant |
| **Risk** | ✅ None | ⚠️ Complexity creep |

### Recommendation: **Make it Core, But Incrementally**

**Rationale**:
1. **Resource constraints are real** - Edge/IoT/multi-tenant need this
2. **Telemetry gap exists** - We have job logs, but no handler/governor metrics
3. **Differentiation opportunity** - No other scheduler does on-demand handlers
4. **Incremental approach** - Can build in phases, validate at each step

**Phased Implementation**:

**Phase 1: Enhanced Telemetry** (1 week)
- Add resource metrics (CPU, memory) to ProcessInfo
- Expose `/governor/metrics` REST endpoint
- Integrate with job execution log (link handler metrics to job performance)
- Document telemetry APIs

**Phase 2: Staged/On-Demand Mode** (2 weeks)
- Implement `StagedProcessGovernor` with cold start support
- Add idle timeout and auto-shutdown
- Track startup times, cold start metrics
- Add `--resource-mode=staged` flag to governor

**Phase 3: Remote Monitoring** (1 week)
- REST API for governor status
- Example monitoring dashboard (Grafana? Simple HTML?)
- Document multi-machine deployment pattern

**Phase 4: Agent Mode (Optional)** (2-3 weeks)
- Only implement if users request centralized control
- DistributedGovernor + GovernorAgent
- Secure control channel
- Coordinated operations (rolling restarts)

**User Choice at Each Phase**:
- Want simple? Use systemd (deployment guide already exists)
- Want convenience? Use ProcessGovernor always-on mode (current state)
- Want efficiency? Use StagedProcessGovernor with on-demand (Phase 2)
- Want centralized control? Use DistributedGovernor (Phase 4)

---

## Strategic Questions Answered

### Q1: "Did we cut job completion telemetry?"
**A**: ❌ No! It's ✅ **COMPLETE** and excellent. Full job execution logging with:
- Start/completion timestamps, duration, status, results, errors, retry tracking
- REST API with filtering and aggregation
- Per-handler statistics
- See `docs/EXECUTION_LOGGING_API.md`

### Q2: "Is there a place for staged processor with optional extended telemetry in resource-constrained environments?"
**A**: ✅ **Yes, absolutely!** This is a compelling use case:
- Edge devices, IoT, multi-tenant SaaS
- Current always-on model: 400-600MB idle RAM for 10 handlers
- Staged model: ~150MB (server + 2-3 active handlers)
- **Needs extended telemetry**: CPU, memory, startup times, idle tracking, health scores
- **Implementation**: `StagedProcessGovernor` with state machine (cold, warming, hot, cooling)

### Q3: "Can governor help handlers on remote systems?"
**A**: ✅ **Yes, with options**:
- **Simple**: Local ProcessGovernor per machine + systemd (recommended for most)
- **Advanced**: DistributedGovernor + Agents for centralized control (10+ machines)
- **Hybrid**: Local governors expose REST API, server polls for monitoring
- **Recommendation**: Start with local governors + monitoring API, add distributed later if needed

### Q4: "Is governor niche or viable core ecosystem component?"
**A**: ⚡ **Can be core, if we enhance it**:
- **Currently**: Niche (dev/testing tool)
- **With staged mode + telemetry**: Core differentiator
- **Value prop**: Resource efficiency, observability, auto-scaling on bare metal
- **Competitive advantage**: No other scheduler does on-demand handlers
- **Implementation**: 4-phase approach (1 week → 2 weeks → 1 week → optional 3 weeks)
- **Risk**: Manage complexity, keep it optional (systemd still works)

---

## Recommended Action Plan

### ✅ Immediate (This Sprint)
1. **Document current telemetry** ✅ (this document)
2. **Decide on enhancement path**:
   - Option A: Keep governor as niche tool (low effort, done)
   - Option B: Enhance with telemetry + staged mode (4 weeks, high value)
3. **Validate use cases**: Do users need resource efficiency? (Ask community, check similar projects)

### 🟡 Phase 1: Enhanced Telemetry (1 week, if pursuing Option B)
- Add psutil for CPU/memory tracking
- Extend ProcessInfo with resource metrics
- Add `/governor/metrics` REST endpoint
- Update docs with telemetry examples

### 🟢 Phase 2: Staged Mode (2 weeks, if Phase 1 successful)
- Implement `StagedProcessGovernor`
- State machine: cold → warming → hot → cooling
- Integration with JobExecutor
- Benchmark resource savings

### 🔵 Phase 3: Remote Monitoring (1 week, after Phase 2)
- REST API server in ProcessGovernor
- Multi-machine monitoring example
- Grafana dashboard or simple HTML

### 🟣 Phase 4: Distributed (Optional, 3 weeks, if users request)
- DistributedGovernor architecture
- GovernorAgent implementation
- Secure control channel
- Coordinated operations

---

## Decision Points

**Before proceeding with enhancement**:
1. **Validate market need**: Survey users, check GitHub issues
2. **Prototype cold start**: Test handler startup time (acceptable latency?)
3. **Benchmark resource savings**: Measure actual RAM/CPU reduction
4. **Estimate maintenance burden**: Can we support this long-term?

**Go/No-Go Criteria**:
- ✅ **GO if**: Users confirm need, cold start < 5s, savings > 50%, team capacity available
- ❌ **NO-GO if**: Limited interest, startup > 10s, maintenance concerns

**Fallback**: Keep governor as-is (niche tool), document systemd as primary production pattern

---

## Conclusion

**ProcessGovernor can evolve from niche tool to core differentiator** if we add:
1. Extended telemetry (CPU, memory, health)
2. Staged/on-demand handler mode
3. Remote monitoring API

**This unlocks**:
- Resource-constrained deployments (Edge, IoT, multi-tenant)
- Auto-scaling without Kubernetes
- Serverless-like efficiency on bare metal
- Competitive differentiation

**Risk**: Complexity and maintenance burden must be managed.

**Recommendation**: **Proceed with Phase 1 (telemetry)** as proof-of-concept, validate user interest, then decide on Phase 2 (staged mode).

**Next Steps**: User/stakeholder discussion to validate need before starting development.

---

**Status**: 🔴 **HOLD** - Awaiting strategic decision on enhancement path.
