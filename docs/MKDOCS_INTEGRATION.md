# MkDocs Integration - Documentation Microsite

## Overview

The MkDocs documentation is **built statically** and served as a microsite by the Tornado server. 

**You do NOT need to run `mkdocs serve`** - the docs are integrated into ScheduleZero's portal.

## Architecture

```
docs_site/              → Source markdown files
mkdocs.yml             → MkDocs configuration
  ↓ mkdocs build
docs_site_build/       → Built static HTML site
  ↓ Tornado serves
http://localhost:8888/docs/  → Docs microsite
```

## Build Process

### Initial Build
```bash
# Install MkDocs (if not already)
pip install mkdocs-material

# Build documentation
mkdocs build

# Output: docs_site_build/
```

### Tornado Integration

**File**: `src/schedule_zero/tornado_app_server.py`

```python
# Automatically registers docs microsite
microsite_registry.register(Microsite(
    name="Documentation",
    url_prefix="/docs",
    routes=mkdocs.routes.routes,
    assets_path="...",
    templates_path="..."
))
```

**Routes**: `src/schedule_zero/microsites/mkdocs/routes.py`

- Serves built HTML from `docs_site_build/`
- Handles index.html for directories
- Sets caching headers appropriately

## Development Workflow

### 1. Edit Documentation
```bash
# Edit markdown files in docs_site/
code docs_site/getting-started/installation.md
```

### 2. Rebuild
```bash
# Rebuild static site
mkdocs build

# Or use watch mode during heavy editing
mkdocs serve --dev-addr localhost:8001
# (But remember: production uses Tornado, not mkdocs serve)
```

### 3. View in ScheduleZero
```bash
# Start ScheduleZero server
poetry run python -m schedule_zero.server

# Visit http://localhost:8888/docs/
```

## Configuration

**File**: `mkdocs.yml`

```yaml
site_name: ScheduleZero
site_description: Dynamic job scheduling with ZMQ handlers

docs_dir: docs_site        # Source markdown
site_dir: docs_site_build  # Built HTML (served by Tornado)

theme:
  name: material
  # ... Material theme config
```

## Fallback Mode

When **no portal_config.yaml** exists:
- Tornado automatically registers `/docs` microsite
- Serves documentation without full portal chrome
- Accessible from minimal landing page

When **portal_config.yaml exists**:
- Docs integrated as microsite in portal
- Listed in navigation
- Full portal layout with HTMX navigation

## File Structure

```
schedule-zero/
├── docs_site/                    # Source markdown
│   ├── index.md
│   ├── getting-started/
│   ├── concepts/
│   └── api/
├── docs_site_build/              # Built static site (gitignored)
│   ├── index.html
│   ├── getting-started/
│   ├── assets/
│   └── ...
├── mkdocs.yml                    # MkDocs config
└── src/schedule_zero/
    └── microsites/
        └── mkdocs/
            ├── routes.py         # Tornado routes
            └── templates/        # Wrapper templates (if needed)
```

## Static File Serving

**Handler**: `DocsContentHandler` (extends `StaticFileHandler`)

Features:
- Serves HTML, CSS, JS, images from `docs_site_build/`
- Handles directory index (`index.html`)
- Cache headers:
  - **Assets** (CSS/JS/images): 1 hour cache
  - **HTML pages**: No cache (allows instant updates)
- Security: Validates paths stay within docs directory

## Updating Documentation

### Add New Page
```bash
# 1. Create markdown file
code docs_site/new-section/new-page.md

# 2. Add to navigation in mkdocs.yml
# nav:
#   - New Section:
#     - New Page: new-section/new-page.md

# 3. Rebuild
mkdocs build

# 4. Restart Tornado (or just refresh - no cache on HTML)
```

### Update Existing Page
```bash
# 1. Edit markdown
code docs_site/api/rest.md

# 2. Rebuild
mkdocs build

# 3. Refresh browser (no restart needed)
```

## Production Deployment

### CI/CD Pipeline
```yaml
# .github/workflows/docs.yml
name: Build Docs
on:
  push:
    paths:
      - 'docs_site/**'
      - 'mkdocs.yml'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install MkDocs
        run: pip install mkdocs-material
      - name: Build docs
        run: mkdocs build
      - name: Deploy docs_site_build/ to server
        # ... rsync or similar
```

### Docker Build
```dockerfile
# Include MkDocs build in Docker image
FROM python:3.11
WORKDIR /app

# Install MkDocs
RUN pip install mkdocs-material

# Copy source
COPY docs_site/ docs_site/
COPY mkdocs.yml .

# Build docs
RUN mkdocs build

# Copy application
COPY src/ src/
# ...

# Tornado will serve docs_site_build/
```

## Comparison: mkdocs serve vs Tornado

| Feature | `mkdocs serve` | Tornado Integration |
|---------|----------------|---------------------|
| Purpose | Development preview | Production serving |
| Port | Separate (8000) | Same as app (8888) |
| Auto-reload | Yes (rebuilds on save) | No (manual rebuild) |
| Portal integration | No | Yes (unified navigation) |
| Production ready | No | Yes |
| HTMX navigation | No | Optional |

## Common Issues

### "Documentation not found" Error

**Cause**: `docs_site_build/` doesn't exist

**Fix**:
```bash
mkdocs build
```

### Docs Not Updating

**Cause**: Browser caching HTML

**Fix**:
- Hard refresh (Ctrl+Shift+R)
- Or rebuild: `mkdocs build`

### 404 on Assets

**Cause**: Broken paths in markdown

**Fix**:
- Use relative paths: `../images/diagram.png`
- Or absolute from site root: `/assets/diagram.png`

## Best Practices

1. ✅ **Build before commit**: Always run `mkdocs build` before committing docs changes
2. ✅ **Gitignore build output**: `docs_site_build/` should be in `.gitignore`
3. ✅ **Preview during heavy editing**: Use `mkdocs serve` on different port for live reload
4. ✅ **Test in Tornado**: Always verify docs work in actual Tornado server
5. ✅ **Version docs with code**: Keep docs in sync with codebase versions

## Summary

- ✅ MkDocs **builds** to `docs_site_build/`
- ✅ Tornado **serves** from `docs_site_build/`
- ❌ **Do NOT** run `mkdocs serve` in production
- ✅ Rebuild with `mkdocs build` after doc changes
- ✅ Docs accessible at `http://localhost:8888/docs/`
- ✅ Integrated as microsite in portal
