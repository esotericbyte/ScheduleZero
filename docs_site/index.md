# ScheduleZero

**Dynamic job scheduling with ZMQ handlers**

ScheduleZero is a flexible job scheduling system that uses ZeroMQ for handler communication and APScheduler for job orchestration.

## Features

- **ZMQ-based handlers** - Handlers run as separate processes communicating via ZeroMQ
- **Dynamic scheduling** - Add/remove/modify schedules via REST API
- **Execution logging** - Complete job execution history with metrics
- **Multi-deployment** - Support for dev, test, and production configurations
- **Web portal** - Built-in UI for job management

## Quick Example

```python
# Schedule a job
import requests

response = requests.post("http://localhost:8888/api/schedule", json={
    "handler_id": "my_handler",
    "method_name": "my_method",
    "params": {"arg": "value"},
    "trigger": {
        "type": "interval",
        "minutes": 5
    }
})
```

## Architecture

```
ScheduleZero Server
    ├─ Tornado Web Server (REST API + Portal)
    ├─ APScheduler (Job scheduling)
    └─ ZMQ Client (Handler communication)

Handlers (Separate processes)
    ├─ Handler 1 (port 5001)
    ├─ Handler 2 (port 5002)
    └─ Handler N (port 500N)
```

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quickstart.md)
- [Core Concepts](concepts/architecture.md)
