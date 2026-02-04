# Documentation Integration - Quick Reference

## Architecture Decision

**Modular Build, Distributed Ownership** (Recommended for Phase 2)

- Each major component has **independent documentation**
- Handler docs are **fully separate** (can be reused across custom portals)
- Portal serves all doc sites but each builds independently
- Supports the platform vision: ScheduleZero as a framework

See [platform-vision.md](platform-vision.md) for the full platform strategy.

## Documentation Sites

### Core Platform
```
schedule-zero/docs/core/  →  /docs/
```
Platform architecture, API, deployment

### Frontend Components  
```
schdulezero-islands/docs/  →  /docs/frontend/
```
Web Components, islands, build pipeline (this project)

### Handler Development
```
schedulezero-handlers-python/docs/  →  /docs/handlers/
```
Handler API, examples, deployment (independent, reusable)

## For Frontend Developers

### Edit Docs
```bash
cd schdulezero-islands
vim docs/component-patterns.md
```

### Preview Locally
```bash
# Install mkdocs (first time only)
pip install mkdocs-material

# Serve locally
mkdocs serve
# Open http://localhost:8000
```

### Build for Portal
```bash
# Build to portal static dir
mkdocs build --site-dir ../schedule-zero/static/docs/frontend
```

### Commit
```bash
git add docs/
git commit -m "Update component docs"
git push
```

## For Portal Integration

Each doc site builds independently:

```bash
# Core docs
cd schedule-zero/docs/core
mkdocs build --site-dir ../../static/docs/core

# Frontend docs  
cd schdulezero-islands
mkdocs build --site-dir ../schedule-zero/static/docs/frontend

# Handler docs
cd schedulezero-handlers-python
mkdocs build --site-dir ../schedule-zero/static/docs/handlers
```

Portal serves all under `/docs/` hierarchy.

## Portal Configuration

**Modular strategy (recommended):**

```yaml
# portal_config.yaml
microsites:
  - id: "sz_docs_core"
    path: "/docs"
    microsite_type: "mkdocs"
    
  - id: "sz_docs_frontend"
    path: "/docs/frontend"
    microsite_type: "mkdocs"
    
  - id: "sz_docs_handlers"
    path: "/docs/handlers"
    microsite_type: "mkdocs"
```

## Benefits

✅ **Handler docs independent** - Can be reused across custom portals (LogStream, AI Workflows)  
✅ **Flexible integration** - Each portal chooses which docs to include  
✅ **Separate release cycles** - Frontend/handlers/core update independently  
✅ **Local development** - Teams preview docs independently  
✅ **Scalable** - Easy to add Rust handlers, Go handlers, custom microsites

## Platform Vision

ScheduleZero is a **platform/framework** for building custom scheduling portals:

- **Core ScheduleZero** - Base platform with essential microsites
- **LogStream Portal** - Custom log aggregation service
- **AI Workflow Portal** - ML pipeline orchestration
- **Your Custom Portal** - Built on ScheduleZero framework

Independent handler docs enable reuse across all these portals!
