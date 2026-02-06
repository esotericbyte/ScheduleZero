# ScheduleZero Port and Configuration Architecture Analysis

**Date:** 2026-02-06  
**Issue:** Port 4244 conflict causing test handler registration failure  
**Diagnostic:** Python process PID 266064 holding port 4244 (stale from previous test)

---

## Current Port Conflict

```
Port 4244: LISTENING (PID 266064 - python.exe)
Port 4242: Not in use (should be ZMQ registration server)
Port 8888: Not in use (should be Tornado web server)
```

**Problem:** Stale test handler process never cleaned up properly.

---

## ScheduleZero Architecture - Multiple Instances

### 1. **Full Server Stack** (Production/Development)
```
Component Stack:
├─ Tornado Web Server    → Port 8888 (configurable)
├─ ZMQ Registration Server → Port 4242 (configurable)
├─ APScheduler           → Database persistence
├─ Handler Registry      → handler_registry.yaml
└─ Portal UI             → portal_config.yaml
```

**Configuration Files:**
- `portal_config.yaml` - Portal and microsite configuration (REQUIRED for UI)
- `handler_registry.yaml` - Pre-registered handlers
- Environment variables for ports/addresses

**Ports:**
- `8888` - Tornado HTTP server (SCHEDULEZERO_TORNADO_PORT)
- `4242` - ZMQ registration server (SCHEDULEZERO_ZRPC_PORT)

---

### 2. **Test Server Stack** (pytest session fixtures)
```
Test Environment:
├─ Server Process (PID tracked)
│  ├─ Tornado → 127.0.0.1:8888
│  ├─ ZMQ Server → 127.0.0.1:4242
│  └─ Database → schedulezero_jobs.db (root dir)
│
└─ Handler Process (PID tracked)
   ├─ test_handler.py
   ├─ Listens on → 127.0.0.1:4244
   └─ Registers with → tcp://127.0.0.1:4242
```

**Started by:** `tests/conftest.py` session fixtures
- `server_process` fixture → launches `python -m schedule_zero.server`
- `handler_process` fixture → launches `python tests/test_handler.py`

**Cleanup:** Uses `psutil` to terminate process trees by PID

**Configuration:** Environment variables only
- `SCHEDULEZERO_TEST_HANDLER_ID` → "test-handler-001"
- `SCHEDULEZERO_HANDLER_PORT` → 4244 (hardcoded default)
- `SCHEDULEZERO_SERVER_PORT` → 4242

---

### 3. **Autonomous Handler Stack** (Standalone)
```
Autonomous Handler (pytest unit tests):
├─ AutonomousHandler instance
├─ ComponentManager (autonomous mode)
│  ├─ APScheduler only (no Tornado, no ZMQ server)
│  ├─ Local handler registry
│  └─ SQLite database → deployments/{deployment}/{handler_id}.db
```

**Used by:** 
- `test_autonomous_handler.py`
- `test_ding_dong_pytest.py` (4 tests)

**No ports used** - fully in-process, no network communication

**Configuration:** Passed as dict to `AutonomousHandler.__init__()`

---

### 4. **Deployment Instances** (deployments/)
```
deployments/
├─ default/      → Main development server (ports: 8888, 4242)
├─ production/   → Production deployment (custom ports?)
├─ clock/        → Clock handler deployment
└─ test/         → Test databases (database files only)
```

**Issue:** No clear port management across deployments!

---

## Port Allocation Problem

### Current Issues

1. **Hardcoded Ports**
   - Handler: `4244` (test_handler.py:27)
   - Server ZMQ: `4242` (app_configuration.py:19)
   - Tornado: `8888` (app_configuration.py:17)

2. **No Port Coordination**
   - Multiple test handlers would conflict
   - No way to run parallel test sessions
   - No cleanup of stale processes

3. **Process Lifecycle Gaps**
   - Test fixtures track PIDs but rely on `psutil.terminate()`
   - No PID file management
   - No port-to-process mapping
   - Stale processes accumulate (like PID 266064)

### Can Multiple Servers Run Simultaneously?

**Current Answer:** NO - Port conflicts!

**Same machine scenarios:**
```
❌ Two test sessions → Both try port 4244 for handlers
❌ Test + Development → Both use ports 8888, 4242, 4244
❌ Multiple deployments → No port isolation
```

**Should be possible:**
```
✅ Test session: Ports 8888, 4242, 4244
✅ Development: Ports 8889, 4243, 4245
✅ Production: Ports 8000, 5000, 5001-5010
```

---

## Component Manager & Process Tracking

### Current State

**ComponentManager** (`src/schedule_zero/component_manager.py`):
- Manages component lifecycle (scheduler, event broker, handlers, tornado)
- Tracks component **state** (started/stopped)
- **Does NOT track OS process IDs**
- **Does NOT manage ports**

**Test Fixtures** (`tests/conftest.py`):
- Track server PID and handler PID
- Use `psutil` for process termination
- **No PID files** written to disk
- **No port conflict detection**

### What's Missing?

1. **PID File Management**
   ```
   deployments/{deployment}/pids/
   ├─ server.pid
   ├─ handler_{handler_id}.pid
   └─ process_info.json
   ```

2. **Port Registry/Manager**
   ```python
   class PortManager:
       def allocate_port_range(deployment: str) -> PortConfig:
           """Allocate non-conflicting ports for a deployment"""
           
       def check_port_available(port: int) -> bool:
           """Check if port is free"""
           
       def register_process(deployment, component, pid, port):
           """Register running process"""
   ```

3. **Deployment Isolation**
   - Each deployment gets unique port range
   - Configurable via `deployments/{name}/config.yaml`
   - Environment variables for overrides

4. **Graceful Cleanup**
   - Write PID files on start
   - Check PID files before start (detect stale processes)
   - Clean shutdown removes PID files
   - Test fixtures check/clean PID files

---

## Recommendations

### Immediate Fix (Port Conflict)

**Kill stale process:**
```powershell
Stop-Process -Id 266064 -Force
```

**Prevent recurrence:**
1. Add port conflict detection to test fixtures
2. Force cleanup before starting new test session
3. Check for and kill processes holding required ports

### Short-Term Improvements

1. **PID File Management** (1 day)
   - Add PID file creation to server startup
   - Check PID files in test fixtures
   - Clean stale PID files before tests

2. **Port Conflict Detection** (0.5 day)
   - Check ports available before starting server/handler
   - Fail fast with clear error message
   - Suggest cleanup commands

3. **Better Test Cleanup** (0.5 day)
   - Always check/kill processes on test startup
   - Add port checks to conftest.py
   - Log all PIDs to test_logs/pids.json

### Long-Term Architecture (v0.4.0)

1. **Port Manager Service** (2-3 days)
   - Central port allocation for deployments
   - Detect conflicts automatically
   - Support parallel deployments

2. **Process Governor Enhancement** (2 days)
   - Integrate PID file management
   - Port coordination
   - Health checks on stored PIDs

3. **Deployment Configuration** (1 day)
   - Add `deployments/{name}/deployment.yaml`:
     ```yaml
     deployment_name: test
     ports:
       tornado: 8888
       zmq_server: 4242
       handler_base: 4244  # handlers get 4244, 4245, 4246...
     ```

4. **Test Isolation** (1 day)
   - Use random/dynamic ports for tests
   - Environment variable overrides
   - Parallel test execution support

---

## Configuration File Summary

### Production/Development
```
Root Directory:
├─ portal_config.yaml      # REQUIRED - Portal UI configuration
├─ handler_registry.yaml   # Pre-registered handlers (optional)
└─ config.yaml             # NOT FOUND - uses defaults from app_configuration.py

Environment Variables:
├─ SCHEDULEZERO_TORNADO_PORT → 8888
├─ SCHEDULEZERO_ZRPC_PORT → 4242
└─ SCHEDULEZERO_DATABASE_URL → sqlite+aiosqlite:///schedulezero_jobs.db
```

### Test Environment
```
No config files used!

Environment Variables (from test_handler.py):
├─ SCHEDULEZERO_TEST_HANDLER_ID → "test-handler-001"
├─ SCHEDULEZERO_HANDLER_HOST → "127.0.0.1"
├─ SCHEDULEZERO_HANDLER_PORT → 4244
├─ SCHEDULEZERO_SERVER_HOST → "127.0.0.1"
└─ SCHEDULEZERO_SERVER_PORT → 4242

Database: schedulezero_jobs.db (root directory, cleaned before/after tests)
```

### Autonomous Tests
```
No config files, no environment variables

Configuration passed as dict to AutonomousHandler:
- deployment name
- database path: deployments/{deployment}/{handler_id}.db
- component manager mode: "autonomous"
```

---

## Conclusion

**Current Issue:** Stale Python process (PID 266064) holding port 4244

**Root Causes:**
1. No PID file management
2. No port conflict detection
3. Incomplete process cleanup in tests
4. Hardcoded ports prevent parallel execution

**Quick Fix:** Kill PID 266064, add port checks to test fixtures

**Long-Term:** Need port manager, PID file system, and deployment isolation
