# ScheduleZero Refactored File Structure

## New Descriptive File Names ✨

### Main Module (`src/schedule_zero/`)

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `config.py` | **`app_configuration.py`** | Application-wide configuration management, environment variables, constants |
| `registry.py` | **`handler_registry.py`** | Handler registry management, persistence, client connections |
| `scheduler.py` | **`job_executor.py`** | Job execution logic with retry and error handling |
| `rpc_server.py` | **`zerorpc_registration_server.py`** | zerorpc server for handler registration and status |
| `main.py` | **`tornado_app_server.py`** | Main Tornado application server orchestration |
| `server.py` | **`server.py`** | CLI entry point (simplified to delegate to tornado_app_server) |

### API Module (`src/schedule_zero/api/`)

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `base.py` | **`tornado_base_handlers.py`** | Base Tornado request handlers, JSON utilities, error handling |
| `handlers.py` | **`handler_list_api.py`** | API endpoint for listing registered handlers |
| `jobs.py` | **`job_scheduling_api.py`** | API endpoints for scheduling and running jobs |
| `config.py` | **`config_api.py`** | API endpoint for server configuration |

### Handlers Module (`src/schedule_zero/handlers/`)

| File | Purpose |
|------|---------|
| `base.py` | Abstract base class for handler implementations |
| `example.py` | Example handler implementation |

### Unchanged

| File | Purpose |
|------|---------|
| `schedule_zero.py` | Legacy monolithic module (to be deprecated) |
| `handler_example.py` | Legacy example handler (to be deprecated) |
| `__init__.py` | Package initialization |

## Benefits of New Names

### 1. **Self-Documenting** 📚
- `tornado_app_server.py` - Immediately clear it's the Tornado application server
- `zerorpc_registration_server.py` - Obviously handles zerorpc registration
- `job_executor.py` - Clear it executes jobs (not just "scheduler")
- `handler_registry.py` - Specific about managing handler registry

### 2. **Technology-Specific** 🔧
- Names include technology used: `tornado`, `zerorpc`, `apscheduler`
- Makes it easy to understand dependencies
- Helps new developers understand architecture

### 3. **Purpose-Driven** 🎯
- `app_configuration` vs generic `config`
- `job_scheduling_api` vs vague `jobs`
- `tornado_base_handlers` vs ambiguous `base`
- `handler_list_api` vs unclear `handlers`

### 4. **Namespace Collision Prevention** 🛡️
- `handler_registry.py` won't collide with Python's `registry`
- `app_configuration.py` more specific than `config`
- API modules clearly prefixed/suffixed

### 5. **Easier Navigation** 🧭
- File list is self-explanatory
- Don't need to open files to understand their role
- IDE search becomes more effective

## Import Examples

### Old Way (Generic Names)
```python
from .config import load_config
from .registry import RegistryManager
from .scheduler import JobExecutor
from .rpc_server import ZeroRPCServer
from .api.base import BaseAPIHandler
from .api.jobs import ScheduleJobHandler
```

### New Way (Descriptive Names)
```python
from .app_configuration import load_config
from .handler_registry import RegistryManager
from .job_executor import JobExecutor
from .zerorpc_registration_server import ZeroRPCServer
from .api.tornado_base_handlers import BaseAPIHandler
from .api.job_scheduling_api import ScheduleJobHandler
```

**Result**: Imports tell a story about what each module does!

## Module Responsibilities

### `app_configuration.py`
- Load YAML configuration files
- Environment variable management
- Default constants (ports, timeouts, paths)
- Configuration validation

### `handler_registry.py`
- `RegistryManager` class for thread-safe registry operations
- Handler registration and persistence (YAML)
- zerorpc client creation and caching
- Client lifecycle management

### `job_executor.py`
- `JobExecutor` class callable by APScheduler
- Remote job execution with retries
- Exponential backoff with jitter
- Error handling and logging

### `zerorpc_registration_server.py`
- `RegistrationService` RPC endpoint class
- `ZeroRPCServer` thread management
- Handler registration/status reporting
- Graceful shutdown via event signaling

### `tornado_app_server.py`
- Application initialization and startup
- Tornado route configuration
- Component orchestration (APScheduler, zerorpc, Tornado)
- Signal handling and graceful shutdown

### API Modules
- **`tornado_base_handlers.py`**: Common functionality for all API handlers
- **`handler_list_api.py`**: GET /api/handlers endpoint
- **`job_scheduling_api.py`**: POST /api/schedule, /api/run_now, GET /api/schedules
- **`config_api.py`**: GET /api/config endpoint

## Architecture at a Glance

```
tornado_app_server.py (main orchestrator)
├── app_configuration.py (config loading)
├── handler_registry.py (registry management)
│   └── zerorpc.Client connections
├── job_executor.py (job execution logic)
│   └── calls handlers via registry
├── zerorpc_registration_server.py (RPC server thread)
│   └── handles handler registration
└── api/ (Tornado HTTP handlers)
    ├── tornado_base_handlers.py (base classes)
    ├── handler_list_api.py (handler endpoints)
    ├── job_scheduling_api.py (job endpoints)
    └── config_api.py (config endpoint)
```

## Migration Notes

### For Developers
1. Update imports in your code to use new module names
2. Old `schedule_zero.py` is now legacy - use `tornado_app_server.py`
3. Entry point is still `server.py` (now simplified)

### Backwards Compatibility
- Legacy `schedule_zero.py` still exists for transition period
- Will be deprecated and removed in future version
- CLI entry points remain unchanged (`schedule-zero-server`)

## Next Steps

1. ✅ Refactor complete with descriptive names
2. ⏳ Test all imports and functionality
3. ⏳ Update documentation to reference new names
4. ⏳ Deprecate legacy `schedule_zero.py`
5. ⏳ Remove old monolithic file once fully migrated
