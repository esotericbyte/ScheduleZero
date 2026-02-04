# Governor Architecture

## Overview
The Governor system provides a standardized interface for managing ScheduleZero server and handler processes/threads. The architecture uses an Abstract Base Class (ABC) pattern to enable multiple implementation strategies.

## Architecture Components

### 1. GovernorBase (Abstract Base Class)
Defines the standard interface that all governor implementations must follow.

**Key Methods:**
- `start()` - Start all managed services
- `stop(timeout)` - Graceful shutdown with timeout
- `restart(timeout)` - Restart all services
- `status()` - Get status of all services
- `add_handler(config)` - Dynamically add handler
- `remove_handler(handler_id)` - Remove and stop handler
- `restart_handler(handler_id)` - Restart specific handler
- `get_handler_status(handler_id)` - Get handler status
- `list_handlers()` - List all handler IDs

**Properties:**
- `is_running` - Boolean indicating if governor is active
- `health_check()` - Returns health status of all services
- `get_metrics()` - Returns operational metrics

### 2. HandlerConfig
Configuration data class for handler instances.

**Fields:**
- `handler_id` - Unique identifier
- `module_path` - Python module path (e.g., "tests.ding_dong_handler")
- `class_name` - Handler class name (e.g., "DingDongHandler")
- `port` - ZMQ REP socket port
- `auto_restart` - Enable automatic restart on failure
- `max_restarts` - Maximum restart attempts
- `restart_delay` - Delay between restart attempts
- `**kwargs` - Additional handler-specific config

### 3. ProcessInfo
Runtime information about a managed process/thread.

**Fields:**
- `name` - Process/thread name
- `pid` - Process ID (None for threads)
- `status` - Current status (running, stopped, crashed, restarting)
- `restart_count` - Number of times restarted
- `last_error` - Last error message if any

## Implementations

### ProcessGovernor (Production-Ready)
Process-based implementation suitable for production deployment.

**Features:**
- ✅ Separate OS processes for server and handlers
- ✅ PID file tracking (`deployments/{deployment}/pids/`)
- ✅ OS signal handling (SIGTERM, SIGINT, SIGQUIT)
- ✅ Graceful shutdown with timeout and force-kill fallback
- ✅ Process output logging to separate files
- ✅ Uses Poetry environment for subprocess execution
- ✅ Windows and Linux compatible

**Use Cases:**
- Production deployments
- Systemd service integration
- Container orchestration
- High availability requirements

### ThreadGovernor (Future)
Thread-based implementation for lighter-weight deployments.

**Features:**
- 🔮 Handlers run in threads within governor process
- 🔮 Lower resource overhead
- 🔮 Faster startup/shutdown
- 🔮 Shared memory space

**Use Cases:**
- Development environments
- Single-machine deployments
- Resource-constrained systems

### KubernetesGovernor (Future)
Kubernetes-native implementation.

**Features:**
- 🔮 Handlers as separate Pods
- 🔮 Kubernetes health checks
- 🔮 Auto-scaling support
- 🔮 ConfigMap integration

## Usage Examples

### Basic Usage
```python
from src.schedule_zero.process_governor import ProcessGovernor
from src.schedule_zero.governor_base import HandlerConfig

# Create governor for production deployment
governor = ProcessGovernor("production")

# Start server and existing handlers
governor.start()

# Add a new handler dynamically
config = HandlerConfig(
    handler_id="ding-aling-1",
    module_path="tests.ding_dong_handler",
    class_name="DingAlongHandler",
    port=4244,
    auto_restart=True,
    max_restarts=3
)
governor.add_handler(config)

# Check status
status = governor.status()
for service, info in status.items():
    print(f"{service}: {info.status} (PID: {info.pid})")

# Get metrics
metrics = governor.get_metrics()
print(f"Healthy services: {metrics['healthy_services']}/{metrics['total_services']}")

# Stop everything gracefully
governor.stop(timeout=30)
```

### Signal Handling
```python
import signal
import sys

governor = ProcessGovernor("production")
governor.start()

# Automatic signal handling built-in
# SIGTERM, SIGINT, SIGQUIT trigger graceful shutdown

# Or manually:
def cleanup(signum, frame):
    print("Shutting down...")
    governor.stop()
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
```

### Health Monitoring
```python
import time

governor = ProcessGovernor("production")
governor.start()

# Monitor health
while True:
    health = governor.health_check()
    unhealthy = [name for name, healthy in health.items() if not healthy]
    
    if unhealthy:
        print(f"Unhealthy services: {unhealthy}")
        for service in unhealthy:
            if service != "server":  # Don't restart server
                governor.restart_handler(service)
    
    time.sleep(60)  # Check every minute
```

## Design Principles

### 1. Interface Segregation
The ABC defines a complete but minimal interface. Implementations can add specific methods but must implement all abstract methods.

### 2. Fail-Safe Operations
All operations are idempotent where possible:
- Starting an already-running service is a no-op
- Stopping a non-running service succeeds silently
- Health checks always return valid data

### 3. Graceful Degradation
- Timeouts prevent indefinite hangs
- Force-kill as fallback for stuck processes
- Continue operations even if individual services fail

### 4. Observability
- Every operation logged with context
- Metrics available via `get_metrics()`
- Health checks for external monitoring
- PID files for systemd/monitoring tools

### 5. Extensibility
- Easy to add new governor implementations
- Handler-specific configuration via kwargs
- Pluggable process/thread management

## File Organization

```
src/schedule_zero/
├── governor_base.py           # ABC and data classes
├── process_governor.py         # Process-based implementation
└── thread_governor.py          # (Future) Thread-based implementation

deployments/
└── {deployment}/
    ├── pids/                   # PID files for monitoring
    │   ├── server.pid
    │   └── {handler_id}.pid
    └── logs/                   # Process output logs
        ├── governor.log
        ├── server.log
        └── {handler_id}.log
```

## Next Steps

1. ✅ **Abstract Base Class** - Completed
2. ✅ **ProcessGovernor** - Completed
3. 🔨 **ThreadGovernor** - Implement thread-based governor
4. 🔨 **Configuration Loading** - Load handler configs from YAML
5. 🔨 **Auto-Restart Logic** - Implement automatic restart on failure
6. 🔨 **Health Check API** - REST endpoint for health status
7. 🔨 **Systemd Integration** - Service files and documentation
8. 🔨 **Metrics Export** - Prometheus/StatsD integration

## Benefits

### For Operators
- **Standardized Management**: Same commands for all deployments
- **Process Isolation**: Failures don't cascade across services
- **Easy Monitoring**: PID files, logs, and health checks
- **Graceful Operations**: No abrupt process kills

### For Developers
- **Clear Interface**: ABC defines exact contract
- **Easy Testing**: Mock governor for unit tests
- **Flexible Implementation**: Choose process, thread, or container strategy
- **Type Safety**: Type hints throughout

### For Production
- **Reliability**: Automatic restart, health monitoring
- **Performance**: Minimal overhead, efficient resource use
- **Observability**: Comprehensive logging and metrics
- **Maintainability**: Clean separation of concerns
