# Installation

## Requirements

- Python 3.12+
- Poetry (for dependency management)

## Install with Poetry

```bash
# Clone repository
git clone https://github.com/esotericbyte/ScheduleZero.git
cd ScheduleZero

# Install dependencies
poetry install

# Start server
poetry run python -m schedule_zero.tornado_app_server
```

## Verify Installation

```bash
# Check server is running
curl http://localhost:8888/api/health

# View web interface
open http://localhost:8888
```

## Next Steps

- [Quick Start Tutorial](quickstart.md) - Get started in 5 minutes
- [Core Concepts](../concepts/architecture.md) - Understand the system
