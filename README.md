<div align="center">

# ⏰ ScheduleZero

### Lightweight Distributed Task Scheduling for Python

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#-features) •
[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Documentation](#-documentation) •
[API](#-api-reference)

</div>

---

## 🎯 Overview

**ScheduleZero** is a resource-conscious, distributed task scheduling system built entirely in Python. Perfect for scenarios where heavyweight solutions like Celery are overkill—especially on memory-constrained systems like small VMs or edge devices.

**Why ScheduleZero?**
- 🪶 **Lightweight**: No message broker required (RabbitMQ/Redis)
- 🚀 **Fast**: Built on modern async Python (asyncio, Tornado)
- 🔄 **Distributed**: Scale horizontally with worker handlers
- 💾 **Persistent**: SQLite-based job storage with file logging
- 🎨 **Beautiful UI**: TUI-inspired web control panel
- 🔌 **Brokerless**: Direct ZMQ communication (no RabbitMQ/Redis)
- � **Rich Logging**: Full context (file:line:function) in every log
- 🎯 **Governor Process**: Single command to manage all components

---

## ✨ Features

### Core Capabilities
- **🕐 Flexible Scheduling**: Date, interval, and cron triggers via APScheduler 4.x
- **📡 Remote Execution**: Distribute jobs across multiple handler processes
- **🔄 Auto-Discovery**: Handlers self-register with the central server
- **💪 Resilient**: Automatic retries with exponential backoff + jitter
- **📊 REST API**: Full HTTP API for programmatic control
- **🎛️ Web Dashboard**: Real-time monitoring and job management
- **💾 Persistent Storage**: Jobs survive restarts via SQLite
- **🔐 Thread-Safe**: Concurrent job execution with proper locking

### Advanced Features
- **Dynamic Handler Registration**: Add/remove workers on-the-fly
- **Method-Level Routing**: Route jobs to specific handler methods
- **Status Tracking**: Monitor handler availability and job execution
- **Configuration Management**: YAML-based instance configuration
- **Graceful Shutdown**: Clean termination of all components
- **Exponential Backoff**: Smart retry logic for failed jobs

---

## 🚀 Quick Start

### Installation

```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -r requirements.txt
```

### Configuration

Create `config.yaml` in your project root:

```yaml
instance_name: "My ScheduleZero Instance"
description: "Production task scheduler"
admin_contact: "admin@example.com"
version: "1.0.0"
```

### Running with Governor (Recommended)

**Start the entire system:**
```bash
poetry run python governor.py start
# Starts server + handlers as supervised subprocesses
# All output goes to logs/ directory
# Web UI: http://127.0.0.1:8889 (clock deployment)
```

**Stop the system:**
```bash
poetry run python governor.py stop
```

**Check status:**
```bash
poetry run python governor.py status
```

**Key Features:**
- ✅ Single command to start/stop everything
- ✅ All output goes to structured log files
- ✅ Automatic process supervision and restart on crash
- ✅ No terminal juggling required
- ✅ Full context logging (file:line:function in every log)

### Access the Dashboard

Open your browser to **http://localhost:8889** (clock deployment) or **http://localhost:8888** (default deployment)

---

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│               ScheduleZero Central Server               │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Tornado    │  │  APScheduler │  │     ZMQ      │  │
│  │  Web Server  │──│   4.x Async  │──│Registration  │  │
│  │   :8889      │  │   Scheduler  │  │Server :4243  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
│         │                  │                  │          │
│    ┌────▼─────┐      ┌────▼──────┐     ┌────▼──────┐  │
│    │   HTTP   │      │  SQLite   │     │ Handler   │  │
│    │   API    │      │  JobStore │     │ Registry  │  │
│    └──────────┘      └───────────┘     └───────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │  ZMQ REQ/REP (tcp)
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌───────────────┐                   ┌───────────────┐
│   Handler 1   │                   │   Handler 2   │
│   :4245       │                   │   :4246       │
│               │                   │               │
│  • do_work()  │                   │  • process()  │
│  • backup()   │                   │  • analyze()  │
└───────────────┘                   └───────────────┘
        │                                   │
        ├─ logs/handlers/handler1/          │
        └─ Full context logging             └─ logs/handlers/handler2/
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Tornado 6.5+ | Async web server & HTTP API |
| **Scheduler** | APScheduler 4.x | Job scheduling & execution |
| **RPC Layer** | ZeroMQ (pyzmq) | Direct, brokerless communication |
| **Persistence** | SQLite + SQLAlchemy | Job storage & retrieval |
| **Logging** | File-based | Structured logs with full context |
| **Serialization** | JSON | Simple, debuggable data encoding |
| **Configuration** | PyYAML | Human-readable config files |
| **Process Management** | Governor | Supervisor for server & handlers |

### Why These Choices?

#### 🌪️ **Tornado**
- Native `asyncio` support for APScheduler 4.x integration
- Efficient async I/O for handling many connections
- Built-in web server—no external dependencies

#### 📅 **APScheduler 4.x**
- Modern async-first design
- Flexible trigger types (date, interval, cron)
- Persistent job storage with datastore abstraction

#### 🔌 **ZeroMQ**
- No message broker required (unlike Celery)
- Direct socket communication (REQ/REP pattern)
- Minimal memory footprint
- Built-in connection management

#### 💾 **SQLite**
- Zero configuration database
- Low memory usage (< 1MB typical)
- Perfect for embedded/edge deployments
- ACID transactions for reliability

---

## 📖 Documentation

### File Structure (After Refactoring)

```
src/schedule_zero/
├── app_configuration.py          # App config & environment vars
├── deployment_config.py           # Multi-deployment support
├── handler_registry.py            # Handler registration & ZMQ clients
├── job_executor.py                # Job execution logic
├── logging_config.py              # Rich logging with full context
├── zmq_handler_base.py            # Base class for ZMQ handlers
├── zmq_registration_server.py     # ZMQ registration server
├── tornado_app_server.py          # Main server orchestration
├── api/
│   ├── tornado_base_handlers.py   # Base Tornado handlers
│   ├── handler_list_api.py        # Handler endpoints
│   ├── job_scheduling_api.py      # Job scheduling endpoints
│   └── config_api.py              # Configuration endpoint
├── portal/
│   ├── index.html                 # TUI-inspired control panel
│   └── static/                    # CSS/JS assets
└── handlers/
    └── [deprecated - use zmq_handler_base.py]

logs/
├── [deployment]/
│   ├── server/                    # Server logs
│   ├── handlers/                  # Handler-specific logs
│   │   └── [handler-id]/
│   │       ├── handler.log        # Handler lifecycle
│   │       └── errors.log         # Errors only
│   └── governor/                  # Governor logs
```

**Documentation Files:**
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - Multi-deployment setup
- [`TESTING_STATUS.md`](TESTING_STATUS.md) - Testing status & known issues
- [`docs/EXECUTION_LOGGING_API.md`](docs/EXECUTION_LOGGING_API.md) - Job logging API
- [`examples/DISCORD_INTEGRATION.md`](examples/DISCORD_INTEGRATION.md) - Discord bot examples

---

## 🔌 API Reference

### Handler Management

#### List Handlers
```http
GET /api/handlers
```

**Response:**
```json
{
  "handlers": [
    {
      "id": "handler_12345",
      "address": "tcp://127.0.0.1:4243",
      "methods": ["do_work", "backup", "process"],
      "status": "Connected"
    }
  ]
}
```

### Job Scheduling

#### Schedule a Job
```http
POST /api/schedule
Content-Type: application/json

{
  "handler_id": "handler_12345",
  "method_name": "do_work",
  "job_params": {
    "input_file": "/data/file.txt",
    "output_dir": "/results/"
  },
  "trigger_config": {
    "type": "interval",
    "hours": 1
  }
}
```

**Response:**
```json
{
  "status": "success",
  "schedule_id": "job_67890"
}
```

#### Run Job Immediately
```http
POST /api/run_now
Content-Type: application/json

{
  "handler_id": "handler_12345",
  "method_name": "do_work",
  "job_params": {
    "message": "Hello World"
  }
}
```

#### List Schedules
```http
GET /api/schedules
```

**Response:**
```json
{
  "schedules": [
    {
      "id": "job_67890",
      "next_fire_time": "2025-10-27T15:30:00Z",
      "trigger": "interval[1:00:00]",
      "args": ["handler_12345", "do_work", {...}]
    }
  ],
  "count": 1
}
```

### Configuration

#### Get Server Config
```http
GET /api/config
```

#### Health Check
```http
GET /api/health
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULEZERO_DEPLOYMENT` | `default` | Deployment name (default/clock/production/test) |
| `SCHEDULEZERO_CONFIG_PATH` | `config.yaml` | Config file path |
| `SCHEDULEZERO_LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Deployments

ScheduleZero supports multiple simultaneous deployments with separate configs:

| Deployment | Web Port | ZMQ Port | Purpose |
|------------|----------|----------|---------|
| `default` | 8888 | 4242 | Development |
| `clock` | 8889 | 4243 | Time announcements (DingDong handler) |
| `production` | 8890 | 4244 | Production workloads |
| `test` | 8891 | 4245 | Testing |

Set deployment with: `export SCHEDULEZERO_DEPLOYMENT=clock`

### Trigger Types

#### Date Trigger (Run Once)
```json
{
  "type": "date",
  "run_date": "2025-10-27T15:30:00"
}
```

#### Interval Trigger (Repeating)
```json
{
  "type": "interval",
  "hours": 1,
  "minutes": 30
}
```

#### Cron Trigger (Schedule)
```json
{
  "type": "cron",
  "hour": "*/2",
  "minute": "0"
}
```

---

## 🧪 Testing

```bash
# Start server and handler in separate terminals, then:
poetry run python test_schedule.py

# Expected output:
# ✓ Handlers listed successfully
# ✓ Job executed immediately
# ✓ Job scheduled for future execution
```

---

## 🛣️ Roadmap

- [ ] Authentication & authorization
- [ ] Job execution history & logs
- [ ] Advanced UI with charts & graphs
- [ ] Docker containerization
- [ ] Handler health monitoring
- [ ] Job dependency management
- [ ] Multi-instance clustering
- [ ] Prometheus metrics export
- [ ] WebSocket support for real-time updates

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with these excellent libraries:
- [Tornado](https://www.tornadoweb.org/) - Async web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Job scheduling
- [ZeroMQ (pyzmq)](https://zeromq.org/) - High-performance messaging
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [PyYAML](https://pyyaml.org/) - YAML parser

---

<div align="center">

**Made with ❤️ and Python**

[⬆ Back to Top](#-schedulezero)

</div>
