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

## Warning 
**SchdeuleZero database and scheduling API is the AppScheduler 4.0 project. The profile of features in this project is quite different, broader in some ways and more focused in others. ** 
Be aware that ScheduleZero is in ALPHA and depends intimently with AppSchduler 4.0 and it's event model. This is Pre-Release software.
ScheduleZero project intends to contribute upstream to AppScheduler. 
Features are subject to change and clarification. Maping of testing coverage, verification and a dev cycle that pulls from upstream regularly had not been implimented.


**Why ScheduleZero? target features include:**
- 🪶 **Lightweight**: No message broker required (RabbitMQ/Redis). Simplest deployment model only uses Direct RPC communication via ZeroMQ.
- 🚀 **Fast**: Built on modern async Python (asyncio, Tornado)
- 🔄 **Distributed**: Separate process worker handlers with observablity in the interface may also add some orchestration features and feedback/back-pressure. 
- 💾 **Persistent**: SQLite-based job storage
- 🎨 **Beautiful UI**: Modern modular extentable microsite web interface for dashboard and UX based on HTMX, html component api, and controls developed as Vuetify "islands".
- 🛡️ **Reliable**: Built-in retry logic with exponential backoff
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

### Target integrations
TBD (listed after they are working and tested)
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

### Running

// TODO: insert some common text harnesses with local govenor

**Terminal 1 - Start the Server:**
```bash
poetry run schedule-zero-server
# Server starts on http://127.0.0.1:8888
```

**Terminal 2 - Start a Handler:**
```bash
poetry run schedule-zero-handler
# Handler auto-registers and starts listening
```

**Terminal 3 - Test the System:**
```bash
poetry run python test_schedule.py
# Runs end-to-end tests
```

### Access the Dashboard

Open your browser to **http://localhost:8888**

---

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│               ScheduleZero Central Server               │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Tornado    │  │  APScheduler │  │   zerorpc    │  │
│  │  Web Server  │──│   4.x Async  │──│Registration  │  │
│  │   :8888      │  │   Scheduler  │  │Server :4242  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
│         │                  │                  │          │
│    ┌────▼─────┐      ┌────▼──────┐     ┌────▼──────┐  │
│    │   HTTP   │      │  SQLite   │     │ Handler   │  │
│    │   API    │      │  JobStore │     │ Registry  │  │
│    └──────────┘      └───────────┘     └───────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │  zerorpc (tcp)
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌───────────────┐                   ┌───────────────┐
│   Handler 1   │                   │   Handler 2   │
│   :4243       │                   │   :4244       │
│               │                   │               │
│  • do_work()  │                   │  • process()  │
│  • backup()   │                   │  • analyze()  │
└───────────────┘                   └───────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Tornado 6.5+ | Async web server & HTTP API |
| **Scheduler** | APScheduler 4.x | Job scheduling & execution |
| **RPC Layer** | zerorpc | Lightweight, brokerless communication |
| **Persistence** | SQLite + SQLAlchemy | Job storage & retrieval |
| **Transport** | ZeroMQ | High-performance messaging |
| **Serialization** | MessagePack | Efficient data encoding |
| **Configuration** | PyYAML | Human-readable config files |

### Why These Choices?

#### 🌪️ **Tornado**
- Native `asyncio` support for APScheduler 4.x integration
- Efficient async I/O for handling many connections
- Built-in web server—no external dependencies

#### 📅 **APScheduler 4.x**
- Modern async-first design
- Flexible trigger types (date, interval, cron)
- Persistent job storage with datastore abstraction

#### 🔌 **zerorpc**
- No message broker required (unlike Celery)
- Minimal memory footprint
- Built-in heartbeat and timeout handling
- Automatic serialization with MessagePack

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
├── handler_registry.py            # Handler registration & clients
├── job_executor.py                # Job execution with retries
├── zerorpc_registration_server.py # RPC server for registration
├── tornado_app_server.py          # Main server orchestration
├── server.py                      # CLI entry point
├── api/
│   ├── tornado_base_handlers.py   # Base Tornado handlers
│   ├── handler_list_api.py        # Handler endpoints
│   ├── job_scheduling_api.py      # Job scheduling endpoints
│   └── config_api.py              # Configuration endpoint
└── handlers/
    ├── base.py                    # Abstract handler base class
    └── example.py                 # Example handler implementation
```

**Documentation Files:**
- [`REFACTORING_SUMMARY.md`](REFACTORING_SUMMARY.md) - Detailed refactoring notes
- [`TESTING_STATUS.md`](TESTING_STATUS.md) - Current testing status & known issues

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
| `SCHEDULEZERO_TORNADO_ADDR` | `127.0.0.1` | Tornado bind address |
| `SCHEDULEZERO_TORNADO_PORT` | `8888` | Tornado HTTP port |
| `SCHEDULEZERO_ZRPC_HOST` | `127.0.0.1` | zerorpc server host |
| `SCHEDULEZERO_ZRPC_PORT` | `4242` | zerorpc server port |
| `SCHEDULEZERO_DATABASE_URL` | `sqlite:///schedulezero_jobs.db` | Database connection |
| `SCHEDULEZERO_CONFIG_PATH` | `config.yaml` | Config file path |
| `SCHEDULEZERO_REGISTRY_PATH` | `handler_registry.yaml` | Registry file path |

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
- [zerorpc](http://www.zerorpc.io/) - RPC framework
- [ZeroMQ](https://zeromq.org/) - Messaging library
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit

---

<div align="center">

**Made with ❤️ and Python**

[⬆ Back to Top](#-schedulezero)

</div>
