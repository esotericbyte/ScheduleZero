# ScheduleZero Development Roadmap

## Current Priority: Core Infrastructure

**Focus on practical, production-ready features that make ScheduleZero immediately useful.**

---

## Phase 1: Foundation (IN PROGRESS)

### ✅ Completed
- [x] APScheduler 4.x integration
- [x] ZMQ handler architecture (basic)
- [x] Tornado web server with API
- [x] Microsite architecture (HTMX + islands)
- [x] MkDocs documentation integration
- [x] Multi-deployment support

### 🔄 In Progress
- [ ] **Dashboard with real APScheduler data** (HIGH PRIORITY)
  - Connect sz_dash to actual scheduler state
  - Display active schedules, next run times
  - Show handler status and health
  - Execution history view

- [ ] **ZMQ Bug Fixes** (CRITICAL)
  - Socket cleanup issues
  - Proper shutdown sequences
  - Handler reconnection logic
  - Memory leak investigation

### 📋 Next Up
- [ ] **Built-in Handler Module** (APScheduler native pattern)
  - Register Python functions directly
  - No ZMQ required for simple use cases
  - Default mode: embedded handlers
  - Optional: External handlers via ZMQ

---

## Phase 2: Production Features

### Round-Robin Reporting & Load Balancing
**Track handler health and distribute load intelligently**

- [ ] Handler health monitoring
  - Heartbeat tracking (last seen, uptime)
  - Success/failure rates per handler
  - Average execution time
  - Current load (active jobs)

- [ ] Round-robin dispatcher
  - Distribute jobs across available handlers
  - Skip unhealthy handlers
  - Load-aware routing (avoid overloaded handlers)
  - Handler affinity (sticky sessions for stateful handlers)

- [ ] Reporting dashboard
  - Handler status grid (Vuetify data table)
  - Execution statistics per handler
  - Load distribution visualization
  - Historical metrics

**Implementation:**
```python
# src/schedule_zero/handlers/round_robin_dispatcher.py
class RoundRobinDispatcher:
    """Distribute jobs across handlers with health awareness"""
    
    def __init__(self):
        self.handlers = {}  # handler_id -> HandlerInfo
        self.current_index = 0
    
    def register_handler(self, handler_id: str, methods: list):
        self.handlers[handler_id] = HandlerInfo(
            id=handler_id,
            methods=methods,
            last_seen=datetime.now(),
            success_count=0,
            failure_count=0,
            avg_execution_time=0,
            active_jobs=0,
            status="healthy"
        )
    
    def get_next_handler(self, method: str) -> str:
        """Round-robin with health checks"""
        eligible = [
            h for h in self.handlers.values()
            if method in h.methods and h.status == "healthy"
        ]
        
        if not eligible:
            raise NoHealthyHandlersError(method)
        
        # Sort by load (prefer less-loaded handlers)
        eligible.sort(key=lambda h: (h.active_jobs, h.avg_execution_time))
        
        # Round-robin within least-loaded handlers
        handler = eligible[self.current_index % len(eligible)]
        self.current_index += 1
        
        return handler.id
    
    def record_execution(self, handler_id: str, success: bool, duration: float):
        """Update handler statistics"""
        handler = self.handlers[handler_id]
        
        if success:
            handler.success_count += 1
        else:
            handler.failure_count += 1
        
        # Update moving average
        handler.avg_execution_time = (
            handler.avg_execution_time * 0.9 + duration * 0.1
        )
        
        # Mark unhealthy if high failure rate
        if handler.failure_count > handler.success_count * 0.5:
            handler.status = "unhealthy"
```

---

### Governors (Resource Management)
**Control execution rates and prevent overload**

- [ ] Rate limiting
  - Per-handler rate limits
  - Global rate limits
  - Adaptive throttling based on success rates

- [ ] Concurrency limits
  - Max concurrent jobs per handler
  - Max concurrent jobs globally
  - Queue jobs when limits reached

- [ ] Backpressure mechanisms
  - Reject new schedules when overloaded
  - Pause scheduling when handlers unhealthy
  - Auto-resume when capacity available

**Implementation:**
```python
# src/schedule_zero/governors/rate_limiter.py
class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self.tokens = burst
        self.last_update = time.time()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens, return False if rate limited"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Refill tokens
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# src/schedule_zero/governors/concurrency_limiter.py
class ConcurrencyLimiter:
    """Limit concurrent job executions"""
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def acquire(self):
        """Wait for available slot"""
        await self.semaphore.acquire()
    
    def release(self):
        """Release slot"""
        self.semaphore.release()


# Usage in job executor
class GovernedExecutor:
    def __init__(self, rate_limiter: RateLimiter, concurrency_limiter: ConcurrencyLimiter):
        self.rate_limiter = rate_limiter
        self.concurrency_limiter = concurrency_limiter
    
    async def execute_job(self, job_func):
        # Check rate limit
        if not await self.rate_limiter.acquire():
            raise RateLimitExceededError("Rate limit exceeded")
        
        # Check concurrency limit
        await self.concurrency_limiter.acquire()
        
        try:
            result = await job_func()
            return result
        finally:
            self.concurrency_limiter.release()
```

---

### Dynamic Test Suite Interface
**Schedule and run tests through ScheduleZero itself**

- [ ] Test scenario registry
  - Define test scenarios as YAML
  - Load via API or dashboard
  - Version control test definitions

- [ ] Test execution via scheduling
  - Schedule test runs (one-time or recurring)
  - Parameterized tests (vary load, timing, etc.)
  - Test chains (dependencies between tests)

- [ ] Real-time test reporting
  - Live execution metrics
  - Pass/fail status
  - Performance graphs
  - Export results (JSON, CSV)

**Test Definition Format:**
```yaml
# tests/scenarios/schedule_storm.yaml
test:
  name: schedule_storm
  description: "Create and delete 1000 schedules rapidly"
  
  parameters:
    schedules_count: 1000
    interval_seconds: 10
    duration_seconds: 60
  
  steps:
    - name: create_schedules
      type: loop
      iterations: ${schedules_count}
      action:
        method: create_schedule
        args:
          task_id: noop
          trigger:
            type: interval
            seconds: ${interval_seconds}
    
    - name: wait
      type: sleep
      duration: ${duration_seconds}
    
    - name: delete_schedules
      type: loop
      iterations: ${schedules_count}
      action:
        method: delete_schedule
  
  metrics:
    - creation_rate: schedules/sec
    - deletion_rate: schedules/sec
    - memory_usage: MB
    - scheduler_latency: ms
  
  assertions:
    - creation_rate > 100
    - deletion_rate > 100
    - memory_usage < 500
```

**API Endpoints:**
```python
# POST /api/tests/load
# Load test scenario from YAML

# POST /api/tests/run
# Execute test scenario immediately

# POST /api/tests/schedule
# Schedule recurring test run

# GET /api/tests/results/{test_id}
# Get test execution results

# GET /api/tests/metrics/{test_id}
# Get real-time test metrics (WebSocket)
```

**Dashboard Integration:**
- Test library page (list available tests)
- Test configuration page (edit parameters)
- Test execution page (trigger runs, view live results)
- Test history page (past results, trends)

---

## Phase 3: Advanced Features (Later)

### Distributed ScheduleZero (ZMQ Replication)
- Master/replica topology
- Zone-based security
- Read-only reporter nodes
- *Deferred until core is stable*

### Multi-Tenancy
- Guild isolation
- Metadata-based filtering
- Per-tenant quotas
- *Deferred until single-tenant proven*

### Discord Bot Integration
- Cog + sprocket architecture
- Guild verification system
- Slash commands for scheduling
- *Examples exist, production later*

### Security Hardening
- Discord OAuth
- WireGuard VPN deployment
- WAF (ModSecurity + NGINX)
- Audit logging
- *Single-tenant + VPN for now*

---

## Architecture Decisions

### Built-in Handlers (Default)
**Most users don't need ZMQ complexity**

```python
# Simple embedded handler (no ZMQ)
from schedule_zero import ScheduleZero

sz = ScheduleZero()

# Register handler function directly
@sz.handler
async def send_notification(message: str):
    print(f"Notification: {message}")

# Schedule it
await sz.schedule(
    task_id="send_notification",
    trigger="cron",
    hour=9,
    args={"message": "Good morning!"}
)

# Run
await sz.start()
```

### Optional ZMQ Handlers
**For distributed deployments only**

```python
# External handler process (uses ZMQ)
from schedule_zero import ZMQHandler

handler = ZMQHandler("tcp://localhost:5555")

@handler.method
async def send_notification(message: str):
    print(f"Notification: {message}")

handler.start()
```

### Configuration
```yaml
# config.yaml
scheduler:
  mode: embedded  # or "distributed"
  
handlers:
  # Built-in handlers (embedded mode)
  builtin:
    - module: schedule_zero.handlers.notifications
      methods: [send_email, send_sms]
    - module: myapp.handlers
      methods: [process_data, backup_db]
  
  # ZMQ handlers (distributed mode)
  zmq:
    registration_server: "tcp://localhost:5555"
    timeout_seconds: 60

governors:
  rate_limit:
    enabled: true
    rate: 100  # per second
    burst: 200
  
  concurrency:
    enabled: true
    max_concurrent: 50
  
  per_handler_limits:
    send_email:
      rate: 10  # emails per second
      concurrent: 5

reporting:
  handler_health:
    enabled: true
    check_interval_seconds: 30
  
  metrics:
    enabled: true
    retention_days: 30
```

---

## Success Criteria

### Phase 1 (Foundation)
- ✅ Dashboard shows real scheduler state
- ✅ ZMQ handlers connect/disconnect cleanly
- ✅ Built-in handlers work without ZMQ
- ✅ No memory leaks in 24-hour test

### Phase 2 (Production)
- ✅ Round-robin load balancing working
- ✅ Governors prevent overload
- ✅ Test suite runs via dashboard
- ✅ Handler health monitoring accurate
- ✅ 1000+ schedules without degradation

### Phase 3 (Advanced)
- ✅ Multi-node replication stable
- ✅ Discord bot in production use
- ✅ Security audit passed
- ✅ Community adoption

---

## Timeline

**November 2024:** Foundation (dashboard, ZMQ fixes, built-in handlers)
**December 2024:** Production features (governors, round-robin, test suite)
**Q1 2025:** Polish, documentation, community testing
**Q2 2025:** Advanced features (distributed, multi-tenant, security)

---

## What We're NOT Building (Yet)

- ❌ Complex orchestration (Airflow-style DAGs)
- ❌ Visual workflow editor
- ❌ Multi-language handlers (Python only for now)
- ❌ Cloud-hosted SaaS
- ❌ Enterprise features (SSO, LDAP, etc.)

**Keep it simple. Ship working software.**
