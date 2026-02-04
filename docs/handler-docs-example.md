# Example Handler Project Documentation Structure

This shows how a handler project (e.g., `schdulezero-handlers-python`) would organize its documentation to integrate with the ScheduleZero portal.

## Directory Structure

```
schdulezero-handlers-python/
├── src/
│   └── handlers/
│       ├── __init__.py
│       ├── http_handler.py
│       ├── email_handler.py
│       └── webhook_handler.py
├── tests/
├── docs/                    ← Documentation folder
│   ├── mkdocs.yml           ← MkDocs config for this project
│   ├── index.md             ← Handler overview
│   ├── getting-started.md   ← Quick start guide
│   ├── api/
│   │   ├── base-handler.md
│   │   ├── http-handler.md
│   │   ├── email-handler.md
│   │   └── webhook-handler.md
│   ├── examples/
│   │   ├── simple-http.md
│   │   ├── retry-logic.md
│   │   └── custom-handler.md
│   └── deployment/
│       ├── configuration.md
│       └── monitoring.md
├── README.md
└── pyproject.toml
```

## MkDocs Configuration

**File:** `docs/mkdocs.yml`

```yaml
site_name: ScheduleZero Python Handlers
site_description: Python handler implementation guide
site_author: ScheduleZero Team

# This will be built to schedule-zero/static/docs/handlers/python/
docs_dir: .
site_dir: ../schedule-zero/static/docs/handlers/python

theme:
  name: material
  palette:
    primary: green
    accent: light-green
  features:
    - navigation.tabs
    - search.suggest

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference:
      - Base Handler: api/base-handler.md
      - HTTP Handler: api/http-handler.md
      - Email Handler: api/email-handler.md
      - Webhook Handler: api/webhook-handler.md
  - Examples:
      - Simple HTTP Call: examples/simple-http.md
      - Retry Logic: examples/retry-logic.md
      - Custom Handler: examples/custom-handler.md
  - Deployment:
      - Configuration: deployment/configuration.md
      - Monitoring: deployment/monitoring.md

markdown_extensions:
  - admonition
  - codehilite
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.tabbed
  - toc:
      permalink: true

plugins:
  - search
```

## Sample Documentation Pages

### docs/index.md

```markdown
# ScheduleZero Python Handlers

Python implementation of ScheduleZero handlers for executing scheduled tasks.

## What are Handlers?

Handlers are Python classes that execute scheduled jobs. Each handler implements a specific type of task (HTTP requests, email sending, webhooks, etc.).

## Available Handlers

- **HTTP Handler** - Make HTTP/HTTPS requests
- **Email Handler** - Send emails via SMTP
- **Webhook Handler** - Trigger webhooks with payload

## Quick Example

\`\`\`python
from schedule_zero.handlers import HttpHandler

class MyApiHandler(HttpHandler):
    def execute(self, context):
        response = self.get('https://api.example.com/data')
        return response.json()
\`\`\`

## Next Steps

- [Getting Started](getting-started.md) - Install and configure
- [API Reference](api/base-handler.md) - Handler API documentation
- [Examples](examples/simple-http.md) - Code examples
```

### docs/getting-started.md

```markdown
# Getting Started

## Installation

\`\`\`bash
pip install schdulezero-handlers-python
\`\`\`

## Configuration

Create a `handlers.yaml` file:

\`\`\`yaml
handlers:
  - id: "api_fetch"
    class: "handlers.http_handler.HttpHandler"
    config:
      url: "https://api.example.com/data"
      method: "GET"
      timeout: 30
\`\`\`

## First Handler

\`\`\`python
from schedule_zero.handlers import BaseHandler

class HelloHandler(BaseHandler):
    def execute(self, context):
        print(f"Hello from schedule: {context.schedule_id}")
        return {"status": "success"}
\`\`\`

## Register Handler

\`\`\`python
from schedule_zero.client import Client

client = Client("http://localhost:8888")
client.register_handler("hello", HelloHandler)
\`\`\`
```

## Portal Integration

### Portal Configuration

**File:** `schedule-zero/portal_config.yaml`

```yaml
microsites:
  - id: "sz_docs_handlers_python"
    name: "Python Handlers"
    icon: "🐍"
    path: "/docs/handlers/python"
    enabled: true
    microsite_type: "mkdocs"
    docs_source: "schdulezero-handlers-python/docs"
    site_dir: "schedule-zero/static/docs/handlers/python"
    description: "Python handler development guide"
    
  - id: "sz_docs_handlers_rust"
    name: "Rust Handlers"
    icon: "🦀"
    path: "/docs/handlers/rust"
    enabled: true
    microsite_type: "mkdocs"
    docs_source: "schdulezero-handlers-rust/docs"
    site_dir: "schedule-zero/static/docs/handlers/rust"
    description: "Rust handler development guide"
```

### Build All Docs Script

**File:** `schedule-zero/scripts/build-docs.sh`

```bash
#!/bin/bash
set -e

echo "Building ScheduleZero documentation..."

# Portal docs
cd docs/portal
mkdocs build --site-dir ../../static/docs/portal
echo "✓ Portal docs built"

# Frontend docs
cd ../../schdulezero-islands
mkdocs build --site-dir ../schedule-zero/static/docs/frontend
echo "✓ Frontend docs built"

# Python handlers docs
cd ../schdulezero-handlers-python/docs
mkdocs build --site-dir ../../schedule-zero/static/docs/handlers/python
echo "✓ Python handlers docs built"

# Rust handlers docs
cd ../../schdulezero-handlers-rust/docs
mkdocs build --site-dir ../../schedule-zero/static/docs/handlers/rust
echo "✓ Rust handlers docs built"

echo "✓ All documentation built successfully"
```

### Tornado Static Routes

**File:** `schedule-zero/src/schedule_zero/portal/routes.py`

```python
from tornado.web import StaticFileHandler

def get_routes():
    return [
        # Documentation sites (all MkDocs instances)
        (r"/docs/portal/(.*)", StaticFileHandler, {
            "path": "static/docs/portal",
            "default_filename": "index.html"
        }),
        (r"/docs/frontend/(.*)", StaticFileHandler, {
            "path": "static/docs/frontend",
            "default_filename": "index.html"
        }),
        (r"/docs/handlers/python/(.*)", StaticFileHandler, {
            "path": "static/docs/handlers/python",
            "default_filename": "index.html"
        }),
        (r"/docs/handlers/rust/(.*)", StaticFileHandler, {
            "path": "static/docs/handlers/rust",
            "default_filename": "index.html"
        }),
    ]
```

## Development Workflow

### For Handler Developers

```bash
# Clone handler project
git clone <handler-repo>
cd schdulezero-handlers-python

# Install dependencies
poetry install

# Write documentation
vim docs/api/my-new-handler.md

# Preview locally
cd docs
mkdocs serve
# Open http://localhost:8000

# Build for portal
mkdocs build --site-dir ../../schedule-zero/static/docs/handlers/python

# Commit
git add docs/
git commit -m "Add documentation for new handler"
```

### For Portal Maintainers

```bash
# Update portal config to add new docs
vim schedule-zero/portal_config.yaml

# Add new microsite:
# - id: "sz_docs_handlers_elixir"
#   microsite_type: "mkdocs"
#   docs_source: "schdulezero-handlers-elixir/docs"

# Build all docs
./scripts/build-docs.sh

# Start portal
poetry run python -m schedule_zero.server

# Navigate to http://localhost:8888
# Click "Elixir Handlers" in nav → opens docs in new tab
```

## Benefits of This Structure

### 1. **Separation of Concerns**
Each handler project owns its documentation:
```
handlers-python/docs/  ← Python team maintains
handlers-rust/docs/    ← Rust team maintains
handlers-go/docs/      ← Go team maintains
```

### 2. **Independent Development**
Teams work independently:
- Update docs without affecting other projects
- Preview docs locally with `mkdocs serve`
- Build and deploy independently

### 3. **Portal Integration**
Portal automatically integrates all docs:
- Read `portal_config.yaml` for enabled microsites
- Build all MkDocs sites with single command
- Serve from unified `/docs/` hierarchy
- Navigation shows all doc sites

### 4. **Version Consistency**
Documentation stays with code:
```
handlers-python/
├── src/handlers/http_handler.py  ← Code
└── docs/api/http-handler.md      ← Docs for that code
```
When code changes, docs are right there to update.

### 5. **Search Across All Docs**
MkDocs search can be configured to search across all doc sites:

```yaml
# In portal's main mkdocs.yml
plugins:
  - search:
      prebuild_index: true
  - multirepo:
      repos:
        - path: handlers/python
        - path: handlers/rust
        - path: frontend
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docs.yml
name: Build Documentation

on:
  push:
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install MkDocs
        run: pip install mkdocs-material
      
      - name: Build docs
        run: |
          cd docs
          mkdocs build --site-dir ../../schedule-zero/static/docs/handlers/python
      
      - name: Deploy to portal
        run: |
          rsync -avz ../schedule-zero/static/docs/handlers/python/ \
            user@portal:/var/www/schedulezero/docs/handlers/python/
```

## Summary

This structure enables:
- **Distributed documentation** - Each project owns its docs
- **Centralized access** - Portal serves all docs unified
- **Template reuse** - MkDocs template used across projects
- **Independent development** - Teams work autonomously
- **Automatic integration** - Configuration-driven, no custom code

The microsite template pattern makes this all work seamlessly!
