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

**ScheduleZero is in early development and depends on pre-release software.**

- **Core Engine**: Built on [APScheduler 4.0](https://github.com/agronholm/apscheduler) (pre-release)
- **Development Stage**: Alpha - features subject to change
- **Testing**: Coverage mapping and verification in progress
- **Upstream Contributions**: Planning to contribute back to APScheduler project
- **Production Use**: Not recommended for critical workloads yet

> 📝 **Note**: The feature profile differs from traditional APScheduler projects—broader in some areas, more focused in others.

<!-- TODO: Add link to working demo instance when deployed -->

<!-- 
================================================================================
  WHY SCHEDULEZERO?
  Key differentiators from traditional task queue systems
================================================================================
-->

**Why ScheduleZero? Target features include:**
- 🪶 **Lightweight**: No message broker required (no RabbitMQ/Redis). Direct ZMQ communication.
- 🚀 **Fast**: Built on modern async Python (asyncio, Tornado)
- 🔄 **Distributed**: Separate process worker handlers with observability
- 💾 **Persistent**: SQLite-based job storage (or PostgreSQL/MySQL via APScheduler)
- 🎨 **Modern UI**: Microsite architecture with HTMX + Vuetify islands
- 🛡️ **Reliable**: Built-in retry logic with exponential backoff + jitter
---

<!-- 
================================================================================
  FEATURES SECTION
  Organized by: Core, Advanced, UI, and Planned Integrations
================================================================================
-->

## ✨ Features

### Core Capabilities
- **🕐 Flexible Scheduling**: Date, interval, and cron triggers via APScheduler 4.x
- **📡 Remote Execution**: Distribute jobs across multiple handler processes via ZeroMQ
- **🔄 Auto-Discovery**: Handlers self-register with the central server
- **💪 Resilient**: Automatic retries with exponential backoff + jitter
- **📊 REST API**: Full HTTP API for programmatic control
- **💾 Persistent Storage**: Jobs survive restarts via SQLite (or PostgreSQL/MySQL)
- **🔐 Thread-Safe**: Concurrent job execution with proper locking
 
### Advanced Features
- **Dynamic Handler Registration**: Add/remove workers on-the-fly via ZMQ
- **Method-Level Routing**: Route jobs to specific handler methods
- **Status Tracking**: Monitor handler availability and job execution
- **Execution Logging**: Complete job history with timing metrics and success/failure tracking
- **Configuration Management**: YAML-based deployment configurations
- **Multi-Deployment**: Support for dev, test, production, and custom deployments
- **Graceful Shutdown**: Clean termination of all components

### Web Interface (In Development)
- **🏗️ Microsite Architecture**: Modular, extensible web interface
- **⚡ HTMX-Powered**: Dynamic interactions without full page reloads
- **🎨 Vuetify Islands**: Rich UI components for complex interactions (data grids, forms)
- **📱 Responsive**: Works on desktop, tablet, and mobile
- **📖 Integrated Docs**: MkDocs documentation embedded in the UI with ScheduleZero branding

#### Microsites
- **Dashboard** (`/dash`): Overview of schedules, handlers, and recent executions
- **Schedules** (`/schedules`): Manage job schedules (create, edit, delete)
- **Handlers** (`/handlers`): Monitor connected handlers and their health
- **Documentation** (`/docs`): Complete MkDocs documentation with Material Design

### Planned Integrations
<!-- TODO: Document and link integrations after they are tested -->
- Discord bot integration (examples available in `examples/discord_*.py`)
- Prometheus metrics export
- WebSocket support for real-time updates
- More TBD after testing
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

<!-- 
================================================================================
  ARCHITECTURE OVERVIEW
  Core: Tornado + APScheduler 4.x + ZMQ
  Frontend: Microsite architecture with HTMX + Vuetify Islands
================================================================================
-->

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               ScheduleZero Central Server (port 8888)           │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Tornado        │  │  APScheduler │  │   ZMQ            │  │
│  │   Web Server     │──│   4.x Async  │──│   Registration   │  │
│  │   + Microsites   │  │   Scheduler  │  │   Server :4242   │  │
│  │   + REST API     │  │              │  │                  │  │
│  └──────────────────┘  └──────────────┘  └──────────────────┘  │
│         │                      │                    │            │
│         │                      │                    │            │
│    ┌────▼──────┐         ┌────▼──────┐       ┌────▼──────┐    │
│    │ Microsite │         │  SQLite   │       │ Handler   │    │
│    │ Registry  │         │  JobStore │       │ Registry  │    │
│    │           │         │           │       │           │    │
│    │ • dash    │         │ (or PG/   │       │ • Methods │    │
│    │ • docs    │         │  MySQL)   │       │ • Ports   │    │
│    │ • handlers│         │           │       │ • Status  │    │
│    └───────────┘         └───────────┘       └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │  ZeroMQ (tcp)
                                  │  Request/Reply Pattern
                ┌─────────────────┴─────────────────┐
                │                                   │
                ▼                                   ▼
        ┌───────────────┐                   ┌───────────────┐
        │   Handler 1   │                   │   Handler 2   │
        │   :5001       │                   │   :5002       │
        │               │                   │               │
        │  • do_work()  │                   │  • process()  │
        │  • backup()   │                   │  • analyze()  │
        │  • status()   │                   │  • report()   │
        └───────────────┘                   └───────────────┘
```

### Frontend Architecture (HTMX + Islands)

```
┌─────────────────────────────────────────────────────────┐
│              Microsite Container (_container)           │
│  • Common layout, navigation (sz-nav web component)     │
│  • HTMX for SPA-like navigation                        │
│  • Shared CSS (brand colors, fonts)                    │
└─────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        │             │             │             │
        ▼             ▼             ▼             ▼
   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌──────┐
   │  dash  │   │schedules│   │handlers │   │ docs │
   │        │   │         │   │         │   │      │
   │Server- │   │Vuetify  │   │Vuetify  │   │MkDocs│
   │rendered│   │islands  │   │islands  │   │+HTMX │
   │HTML +  │   │for data │   │for grids│   │      │
   │HTMX    │   │grids    │   │         │   │iframe│
   └────────┘   └─────────┘   └─────────┘   └──────┘

Islands (JavaScript Components):
  • Vanilla JS (~20 LOC): connection-status, copy-button, sz-flash
  • Vuetify: schedule-grid, handler-grid, execution-log-grid
  • Built separately with Vite, copied as .min.js assets
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Tornado 6.5+ | Async web server & HTTP API |
| **Scheduler** | APScheduler 4.x | Job scheduling & execution |
| **RPC Layer** | ZeroMQ (pyzmq) | Lightweight, brokerless communication |
| **Persistence** | SQLite + SQLAlchemy | Job storage & retrieval |
| **Transport** | ZeroMQ REQ/REP | High-performance messaging pattern |
| **Serialization** | JSON | Human-readable job data |
| **Configuration** | PyYAML | Human-readable config files |
| **Frontend** | HTMX 2.0 | Declarative interactivity |
| **UI Components** | Vuetify 3 | Material Design components (islands) |
| **Documentation** | MkDocs Material | Integrated documentation |

### Why These Choices?

#### 🌪️ **Tornado**
- Native `asyncio` support for APScheduler 4.x integration
- Efficient async I/O for handling many connections
- Built-in web server—no external dependencies
- Easy microsite architecture with route handlers

#### 📅 **APScheduler 4.x**
- Modern async-first design
- Flexible trigger types (date, interval, cron)
- Persistent job storage with datastore abstraction
- Event-driven architecture for monitoring

#### 🔌 **ZeroMQ (Not zerorpc)**
- **No message broker required** (unlike Celery with RabbitMQ/Redis)
- Minimal memory footprint (< 1MB typical)
- Request/Reply pattern for RPC-style communication
- Built-in connection management and reconnection
- Battle-tested, used by financial systems and HPC

#### 💾 **SQLite (Default)**
- Zero configuration database
- Low memory usage (< 1MB typical)
- Perfect for embedded/edge deployments
- ACID transactions for reliability
- Can upgrade to PostgreSQL/MySQL for production

#### ⚡ **HTMX + Islands Architecture**
- **No build step for main app** - HTMX is a 14KB script
- Progressive enhancement - works without JavaScript
- **Islands for complex UI** - Only load Vuetify where needed
- Separate build for islands (`schedulezero-islands` repo)
- Fast initial page loads, rich interactivity where needed

---

<!-- 
================================================================================
  DOCUMENTATION & PROJECT STRUCTURE
================================================================================
-->

## 📖 Documentation

### Project Structure

```
schedule-zero/
├── src/schedule_zero/
│   ├── tornado_app_server.py         # Main server entry point
│   ├── app_configuration.py          # App config & environment vars
│   ├── deployment_config.py          # Multi-deployment support
│   ├── handler_registry.py           # Handler registration & clients
│   ├── job_executor.py               # Job execution with retries
│   ├── job_execution_log.py          # Execution history tracking
│   ├── zmq_registration_server.py    # ZMQ server for handler registration
│   ├── zmq_handler_base.py           # Base class for ZMQ handlers
│   ├── zmq_client.py                 # ZMQ client for job execution
│   │
│   ├── api/                          # REST API endpoints
│   │   ├── job_scheduling_api.py     # Schedule/run job endpoints
│   │   ├── handler_list_api.py       # Handler listing endpoints
│   │   ├── job_execution_log_api.py  # Execution history endpoints
│   │   ├── remove_schedule_api.py    # Schedule deletion endpoint
│   │   └── config_api.py             # Configuration endpoint
│   │
│   ├── microsites/                   # Web UI microsites
│   │   ├── __init__.py               # Microsite registry
│   │   ├── _container/               # Shared layout & components
│   │   │   ├── templates/
│   │   │   │   └── layout.html       # Master layout with navigation
│   │   │   └── assets/
│   │   │       ├── css/layout.css    # Brand colors, fonts
│   │   │       └── js/
│   │   │           ├── htmx.min.js   # HTMX 2.0
│   │   │           └── components/
│   │   │               └── sz-nav.js # Navigation web component
│   │   │
│   │   ├── sz_dash/                  # Dashboard microsite
│   │   │   ├── routes.py
│   │   │   └── templates/
│   │   │
│   │   ├── mkdocs/                   # Documentation microsite
│   │   │   ├── routes.py
│   │   │   └── templates/
│   │   │       └── docs_wrapper.html # MkDocs iframe wrapper
│   │   │
│   │   └── (sz_schedules, sz_handlers - planned)
│   │
│   └── handlers/                     # Handler implementations
│       ├── zmq_handler_base.py       # Abstract base class
│       └── handler_example.py        # Example handler
│
├── docs_site/                        # MkDocs documentation source
│   ├── index.md                      # Documentation homepage
│   ├── getting-started/
│   ├── concepts/
│   ├── deployment/
│   ├── api/
│   ├── examples/
│   ├── assets/
│   │   └── logo.svg                  # ScheduleZero logo
│   └── stylesheets/
│       └── extra.css                 # Custom Material Design styling
│
├── docs_site_build/                  # Built MkDocs HTML (served at /docs-content/*)
├── examples/                         # Integration examples
│   ├── discord_handler.py            # Discord bot with asyncio handler
│   ├── discord_handler_threaded.py   # Discord bot with threaded handler
│   ├── discord_bot_with_cogs.py      # Discord bot with cog architecture
│   └── cogs/
│       ├── schedulezero_cog.py       # ScheduleZero Discord cog
│       └── sprockets/                # Pluggable job modules
│
├── tests/                            # Test suite
├── config.yaml                       # Application configuration
├── handler_registry.yaml             # Handler registry storage
├── mkdocs.yml                        # MkDocs configuration
└── pyproject.toml                    # Poetry dependencies

```

### Documentation Files

- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Detailed refactoring notes and architecture decisions
- **[TESTING_STATUS.md](TESTING_STATUS.md)** - Current testing status & known issues
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Multi-deployment configuration guide
- **[docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md)** - Microsite + HTMX + Islands architecture
- **[docs/COMPONENT_SPECS.md](docs/COMPONENT_SPECS.md)** - Web component specifications
- **[docs/EXECUTION_LOGGING_API.md](docs/EXECUTION_LOGGING_API.md)** - Job execution logging API
- **[docs/PORT_ZERO_BINDING.md](docs/PORT_ZERO_BINDING.md)** - ZMQ port 0 (dynamic port) usage
- **[examples/README.md](examples/README.md)** - Integration examples overview
- **[examples/DISCORD_INTEGRATION.md](examples/DISCORD_INTEGRATION.md)** - Discord bot integration guide
- **[examples/COG_SPROCKET_ARCHITECTURE.md](examples/COG_SPROCKET_ARCHITECTURE.md)** - Discord cog + sprocket pattern

### Web Documentation

The complete documentation is available in the web interface at `/docs`, featuring:
- Material Design theme with ScheduleZero branding
- Light/dark mode toggle
- Full-text search
- Code syntax highlighting with copy buttons
- Responsive mobile design
- Mermaid diagrams for architecture visualization

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

<!-- 
================================================================================
  ROADMAP
  ✅ = Completed | 🚧 = In Progress | 📋 = Planned
================================================================================
-->

## 🛣️ Roadmap

### Core System
- [x] ✅ APScheduler 4.x async integration
- [x] ✅ ZeroMQ handler communication
- [x] ✅ Dynamic handler registration
- [x] ✅ REST API for job scheduling
- [x] ✅ Job execution logging with metrics
- [x] ✅ Multi-deployment support
- [x] ✅ Graceful shutdown handling
- [ ] 📋 Authentication & authorization
- [ ] 📋 Handler health monitoring with heartbeats
- [ ] 📋 Job dependency management (DAGs)
- [ ] 📋 Multi-instance clustering

### Web Interface
- [x] ✅ Microsite architecture foundation
- [x] ✅ HTMX navigation system
- [x] ✅ Container layout with web components
- [x] ✅ MkDocs integration with branding
- [x] ✅ Dashboard microsite (basic)
- [ ] 🚧 Dashboard with real APScheduler data
- [ ] 🚧 Vuetify islands for data grids
- [ ] 📋 Schedule management microsite
- [ ] 📋 Handler management microsite
- [ ] 📋 Execution log viewer with filtering
- [ ] 📋 Real-time updates via WebSocket

### Developer Experience
- [x] ✅ Poetry-based dependency management
- [x] ✅ Comprehensive documentation (MkDocs)
- [x] ✅ Discord bot integration examples
- [ ] 📋 Docker containerization
- [ ] 📋 Docker Compose for full stack
- [ ] 📋 PyPI package publication
- [ ] 📋 CI/CD pipeline (GitHub Actions)
- [ ] 📋 Automated testing suite

### Operations & Monitoring
- [ ] 📋 Prometheus metrics export
- [ ] 📋 Structured logging (JSON output)
- [ ] 📋 OpenTelemetry tracing
- [ ] 📋 Health check endpoints
- [ ] 📋 Performance benchmarks

### Integrations
- [x] ✅ Discord bot (examples)
- [ ] 📋 Slack bot integration
- [ ] 📋 Telegram bot integration
- [ ] 📋 Webhook notifications
- [ ] 📋 Email notifications

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
