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

<!-- 
================================================================================
  PROJECT STATUS: EARLY DEVELOPMENT
  - Built on APScheduler 4.x (pre-release)
  - Active development by single developer
  - Features subject to change
  - Testing coverage in progress
================================================================================
-->

## ⚠️ Project Status

**⛔ NOT PRODUCTION READY - EXPERIMENTAL SOFTWARE ⛔**

**ScheduleZero is in early development (Alpha stage) - ALL CODE SUBJECT TO CHANGE**

- **Project Status**: ⚠️ **EXPERIMENTAL - DO NOT USE IN PRODUCTION**
- **API Stability**: ❌ NO API STABILITY GUARANTEES - Breaking changes expected
- **Code Status**: All code is subject to change without notice or deprecation warnings
- **Core Dependency**: Built on [APScheduler 4.0.0a6](https://github.com/agronholm/apscheduler) ⚠️ **ALPHA SOFTWARE**
- **APScheduler Status**: Currently in alpha, API may change, not recommended for production deployments
- **Security**: ⚠️ **No authentication/authorization** - See [SECURITY_AND_NETWORKING.md](docs/SECURITY_AND_NETWORKING.md)
- **Production**: ❌ **ABSOLUTELY NOT RECOMMENDED** - requires APScheduler 4.0 stable release + authentication implementation
- **Intended Use**: Development, testing, proof-of-concept, learning purposes ONLY

> ⛔ **CRITICAL WARNING**: This is experimental software in active development. The entire codebase may be refactored, renamed, or restructured at any time. Features may be added, changed, or removed without notice. DO NOT depend on this code for anything critical.

> ⚠️ **Critical Dependencies**: This project depends on APScheduler 4.0 which is currently in alpha (4.0.0a6). The APScheduler team has not declared it production-ready. Use in production environments at your own risk.

> 🔒 **Security Note**: Current implementation has no access control. Authentication & authorization are **top priority** before any public deployment.

<!-- 
================================================================================
  WHY SCHEDULEZERO?
  Key differentiators from traditional task queue systems
================================================================================
-->

**Why ScheduleZero?**
- 🪶 **Lightweight**: No message broker (no RabbitMQ/Redis) - just ZeroMQ
- 🚀 **Fast**: Modern async Python (asyncio, Tornado, APScheduler 4.x)
- 🔄 **Distributed**: Separate process handlers with observability
- 💾 **Flexible Storage**: SQLite (default) or PostgreSQL/MySQL
- 🎨 **Modern UI**: HTMX + Vuetify islands architecture
- 🛡️ **Resilient**: Automatic retries with exponential backoff
---

<!-- 
================================================================================
  FEATURES SECTION
  Organized by: Core, Advanced, UI, and Planned Integrations
================================================================================
-->

## ✨ Key Features

- **🕐 Flexible Scheduling**: Date, interval, and cron triggers
- **📡 ZMQ Communication**: Lightweight handler communication (see [networking options](docs/SECURITY_AND_NETWORKING.md#zmq-network-architecture--nat-traversal))
- **🔄 Auto-Discovery**: Handlers self-register with central server
- ** REST API**: Full HTTP API for programmatic control
- **🎨 Modern Web UI**: Microsite architecture with HTMX + Vuetify ([see architecture](docs/FRONTEND_ARCHITECTURE.md))
- **📖 Integrated Docs**: MkDocs Material embedded in UI
- **📈 Execution Logging**: Complete job history with metrics
- **🔧 Multi-Deployment**: Separate configs for dev/test/production

> � **Detailed documentation**: See [/docs](docs/) directory and web UI at `/docs`
---

<!-- 
================================================================================
  QUICK START GUIDE
  TODO: Add common deployment patterns and local governor examples
================================================================================
-->

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- Poetry (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/esotericbyte/ScheduleZero.git
cd ScheduleZero

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

<!-- TODO: Document common deployment patterns with local governor -->

### Running the System

**Option 1: Quick Start (All-in-One)**
```bash
poetry run python -m schedule_zero.tornado_app_server
# Server starts on http://127.0.0.1:8888
# Web UI available at http://localhost:8888/dash
```

**Option 2: Distributed Setup**

**Terminal 1 - Start the Server:**
```bash
poetry run python -m schedule_zero.tornado_app_server
# Server starts on http://127.0.0.1:8888
# ZMQ registration server on tcp://127.0.0.1:4242
```

**Terminal 2 - Start a Handler:**
```bash
poetry run python -m schedule_zero.handler_example
# Handler auto-registers and starts listening
```

**Terminal 3 - Test the System:**
```bash
poetry run python test_schedule.py
# Runs end-to-end tests
```

### Access the Web Interface

Open your browser to:
- **Dashboard**: http://localhost:8888/dash
- **Documentation**: http://localhost:8888/docs
- **API Health**: http://localhost:8888/api/health

---

## 🏗️ Architecture

**High-Level Overview:**

```
┌──────────────────────────────────────┐
│  ScheduleZero Server (:8888)         │
│  • Tornado (Web + API)               │
│  • APScheduler 4.x (Jobs)            │
│  • ZMQ Server (:4242)                │
│  • SQLite/PostgreSQL (Storage)       │
└──────────────────────────────────────┘
              │
              │ ZeroMQ (tcp)
              │
    ┌─────────┴────────┐
    ▼                  ▼
┌─────────┐      ┌─────────┐
│Handler 1│      │Handler 2│
│ :5001   │      │ :5002   │
└─────────┘      └─────────┘
```

**Tech Stack:**
- **Backend**: Tornado (async web), APScheduler 4.x (scheduling), ZeroMQ (RPC)
- **Frontend**: HTMX 2.0 (interactions), Vuetify 3 (data grids), Vanilla JS (simple components)
- **Storage**: SQLite (default) or PostgreSQL/MySQL
- **Docs**: MkDocs Material (integrated at `/docs`)

> 📚 **Detailed Architecture**:
> - [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md) - Microsite + HTMX + Islands pattern
> - [Security & Networking](docs/SECURITY_AND_NETWORKING.md) - Auth, NAT traversal, ZMQ patterns
> - [Component Specs](docs/COMPONENT_SPECS.md) - Web component specifications

---

## 📖 Documentation

### Quick Links
- **[API Reference](#-api-reference)** - REST API endpoints (below)
- **[Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md)** - Microsite + HTMX + Islands
- **[Security & Networking](docs/SECURITY_AND_NETWORKING.md)** - Authentication roadmap, NAT traversal, ZMQ patterns
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Multi-deployment configurations
- **[Testing Status](TESTING_STATUS.md)** - Current test coverage and known issues
- **Web Docs**: Start server and visit http://localhost:8888/docs

### Key Files
- `src/schedule_zero/tornado_app_server.py` - Main server
- `src/schedule_zero/zmq_registration_server.py` - Handler registration
- `src/schedule_zero/microsites/` - Web UI microsites
- `docs_site/` - MkDocs documentation source

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

### 🔥 **Top Priority: Security for Demo Deployment**
- [ ] **Authentication & Authorization** (See [SECURITY_AND_NETWORKING.md](docs/SECURITY_AND_NETWORKING.md))
  - JWT authentication for API
  - Handler API key system
  - Role-based access control (admin/operator/viewer)
  - Rate limiting
- [ ] **Network Security**
  - HTTPS/TLS support
  - ZMQ CurveZMQ encryption option
  - ROUTER/DEALER pattern for better handler management

### ✅ Completed
- APScheduler 4.x async integration
- ZeroMQ handler communication
- Dynamic handler registration
- REST API for job scheduling
- Execution logging with metrics
- Microsite architecture with HTMX
- MkDocs integration with branding

### 🚧 In Progress
- Dashboard with real APScheduler data
- Vuetify islands for data grids

### 📋 Planned
- **Web Interface**: Schedule/handler management microsites, real-time updates
- **DevOps**: Docker, CI/CD, PyPI package
- **Monitoring**: Prometheus metrics, health checks
- **Integrations**: Slack, Telegram, webhooks

> � **Full roadmap** with detailed tasks: See [GitHub Projects](https://github.com/esotericbyte/ScheduleZero/projects) and [Discussions](https://github.com/esotericbyte/ScheduleZero/discussions)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<!-- 
================================================================================
  ACKNOWLEDGMENTS
  Built with excellent open-source libraries
================================================================================
-->

## 🙏 Acknowledgments

Built with these excellent libraries:
- [Tornado](https://www.tornadoweb.org/) - Async web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Advanced job scheduling (4.x pre-release)
- [ZeroMQ](https://zeromq.org/) - High-performance messaging library
- [pyzmq](https://pyzmq.readthedocs.io/) - Python bindings for ZeroMQ
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [HTMX](https://htmx.org/) - Declarative AJAX interactions
- [Vuetify](https://vuetifyjs.com/) - Material Design component framework
- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) - Documentation theme

Special thanks to:
- **Alex Grönholm** for the excellent APScheduler 4.x async rewrite
- The **ZeroMQ community** for battle-tested messaging patterns
- The **HTMX team** for bringing simplicity back to web development

---

<!-- 
================================================================================
  NOTE: Markdown supports HTML comments!
  
  You can use them for:
  - Section dividers (like this file does)
  - TODO notes that shouldn't appear in rendered output
  - Developer notes and explanations
  - Temporarily hiding content without deleting it
  
  Syntax: <!-- Your comment here -- >
  (Remove space before the closing >)
================================================================================
-->

---

<div align="center">

**Made with ❤️ and Python**

[⬆ Back to Top](#-schedulezero)

</div>
