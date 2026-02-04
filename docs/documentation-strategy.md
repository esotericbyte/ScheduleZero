# Documentation Integration Strategy

## Overview

ScheduleZero is evolving from a single application to a **platform/framework**. Documentation strategy should support:
- Core platform development
- Custom portal deployments
- Independent component ecosystems (especially handlers)
- Commercial SaaS offerings

See [platform-vision.md](platform-vision.md) for the full platform architecture.

## Three Documentation Strategies

### Strategy 1: Unified Build (Phase 1 - Now)
- **Each project owns its documentation** (in its own `docs/` folder)
- **Main project builds unified site** (schedule-zero orchestrates)
- **Single documentation portal** (one search, one navigation, one theme)

## Directory Structure

```
schedule-zero/                          ← Main project (integration point)
├── docs/
│   ├── index.md                        ← Landing page for all docs
│   ├── portal/                         ← Portal architecture docs
│   │   ├── index.md
│   │   ├── tornado-integration.md
│   │   └── htmx-patterns.md
│   ├── frontend/                       ← Symlink to schdulezero-islands/docs
│   │   → ../../../schdulezero-islands/docs/
│   └── handlers/                       ← Symlink to handlers project
│       → ../../../schdulezero-handlers-python/docs/
├── mkdocs.yml                          ← Master configuration
└── scripts/
    └── build-docs.sh                   ← Build script

schdulezero-islands/                    ← Frontend project (owns docs)
├── docs/
│   ├── index.md
│   ├── architecture.md
│   ├── component-patterns.md
│   └── ...
└── mkdocs.yml                          ← Local dev config (optional)

schdulezero-handlers-python/           ← Handler project (owns docs)
├── docs/
│   ├── index.md
│   ├── api/
│   └── examples/
└── mkdocs.yml                          ← Local dev config (optional)
```

## Implementation

### Step 1: Create Symlinks (Schedule-Zero Project)

**File:** `schedule-zero/scripts/setup-docs.sh`

```bash
#!/bin/bash
# Creates symlinks to pull in docs from other projects

cd "$(dirname "$0")/.."

# Create symlinks to external project docs
ln -sf ../../schdulezero-islands/docs docs/frontend
ln -sf ../../schdulezero-handlers-python/docs docs/handlers

echo "✓ Documentation symlinks created"
```

### Step 2: Master MkDocs Config (Schedule-Zero)

**File:** `schedule-zero/mkdocs.yml`

```yaml
site_name: ScheduleZero Documentation
site_description: Complete ScheduleZero platform documentation
site_author: ScheduleZero Team
site_url: https://schedulezero.dev/docs

docs_dir: docs
site_dir: static/docs

theme:
  name: material
  palette:
    primary: blue
    accent: blue
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.tabs.link

nav:
  - Home: index.md
  
  - Portal Architecture:
      - Overview: portal/index.md
      - Tornado Integration: portal/tornado-integration.md
      - HTMX Patterns: portal/htmx-patterns.md
      - Microsite System: portal/microsite-system.md
  
  - Frontend Components:
      - Overview: frontend/index.md
      - Architecture: frontend/architecture.md
      - Microsite Templates: frontend/microsite-templates.md
      - Component Patterns: frontend/component-patterns.md
      - Build Pipeline: frontend/build-pipeline.md
      - sz-nav Component: frontend/components/sz-nav.md
      - Development:
          - Setup: frontend/development/setup.md
          - Building: frontend/development/building.md
          - Testing: frontend/development/testing.md
  
  - Handler Development:
      - Overview: handlers/index.md
      - Getting Started: handlers/getting-started.md
      - API Reference:
          - Base Handler: handlers/api/base-handler.md
          - HTTP Handler: handlers/api/http-handler.md
      - Examples: handlers/examples/simple-http.md

markdown_extensions:
  - admonition
  - codehilite
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.tabbed:
      alternate_style: true
  - attr_list
  - md_in_html
  - toc:
      permalink: true

plugins:
  - search:
      lang: en
  - mermaid2

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/schedulezero
```

### Step 3: Build Script (Schedule-Zero)

**File:** `schedule-zero/scripts/build-docs.sh`

```bash
#!/bin/bash
set -e

echo "🔨 Building ScheduleZero unified documentation..."

cd "$(dirname "$0")/.."

# Verify symlinks exist
if [ ! -L "docs/frontend" ]; then
    echo "⚠️  Symlinks not set up. Run ./scripts/setup-docs.sh first"
    exit 1
fi

# Build unified documentation
mkdocs build --clean --strict

echo "✓ Documentation built to static/docs/"
echo "📖 Serve locally: mkdocs serve"
echo "🌐 Deploy: rsync -avz static/docs/ server:/var/www/schedulezero/docs/"
```

### Step 4: Local Dev Configs (Each Project)

Each project can have its own `mkdocs.yml` for local development:

**File:** `schdulezero-islands/mkdocs.yml` (local dev only)

```yaml
site_name: Frontend Components (Dev)
docs_dir: docs
site_dir: site

theme:
  name: material

nav:
  - Home: index.md
  - Architecture: architecture.md
  - Components: component-patterns.md

# Same extensions as master config
markdown_extensions:
  - pymdownx.superfences
  - admonition
```

Frontend developers can run:
```bash
cd schdulezero-islands
mkdocs serve  # Preview only frontend docs
```

## Workflows

### Frontend Developer: Edit Docs

```bash
# Work in islands project
cd schdulezero-islands
vim docs/component-patterns.md

# Preview locally (just frontend docs)
mkdocs serve
# Open http://localhost:8000

# Commit
git add docs/
git commit -m "Update component patterns"
git push
```

### Portal Maintainer: Build Unified Docs

```bash
# Pull latest from all projects
cd schedule-zero
git pull
cd ../schdulezero-islands && git pull && cd ../schedule-zero
cd ../schdulezero-handlers-python && git pull && cd ../schedule-zero

# Build unified docs (pulls from symlinks)
./scripts/build-docs.sh

# Preview unified site
mkdocs serve
# Open http://localhost:8000

# Deploy
rsync -avz static/docs/ server:/var/www/schedulezero/docs/
```

### CI/CD: Automated Build

**File:** `schedule-zero/.github/workflows/docs.yml`

```yaml
name: Build Documentation

on:
  push:
    branches: [main]
  repository_dispatch:
    types: [docs-update]  # Triggered by subprojects

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main project
        uses: actions/checkout@v3
        with:
          path: schedule-zero
      
      - name: Checkout islands project
        uses: actions/checkout@v3
        with:
          repository: schedulezero/schdulezero-islands
          path: schdulezero-islands
      
      - name: Checkout handlers project
        uses: actions/checkout@v3
        with:
          repository: schedulezero/schdulezero-handlers-python
          path: schdulezero-handlers-python
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install MkDocs
        run: pip install mkdocs-material pymdown-extensions
      
      - name: Setup symlinks
        run: |
          cd schedule-zero
          ./scripts/setup-docs.sh
      
      - name: Build docs
        run: |
          cd schedule-zero
          mkdocs build --strict
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: schedule-zero/static/docs
```

## Portal Integration

### Portal Serves One Unified Site

**File:** `schedule-zero/portal_config.yaml`

```yaml
microsites:
  # Single documentation microsite (unified)
  - id: "sz_docs"
    name: "Documentation"
    icon: "📖"
    path: "/docs"
    enabled: true
    microsite_type: "mkdocs"
    docs_source: "schedule-zero/docs"
    site_dir: "schedule-zero/static/docs"
    description: "Complete platform documentation"
```

**File:** `schedule-zero/src/schedule_zero/portal/routes.py`

```python
# Single route for all docs
(r"/docs/(.*)", StaticFileHandler, {
    "path": "static/docs",
    "default_filename": "index.html"
}),
```

Navigation:
- `/docs/` → Landing page with all sections
- `/docs/portal/` → Portal architecture
- `/docs/frontend/` → Frontend components
- `/docs/handlers/` → Handler development

## Benefits of This Approach

### ✅ Single Source of Truth
- One documentation site
- Unified search across all docs
- Consistent navigation and theme
- Cross-references work (`[portal](../portal/index.md)`)

### ✅ Distributed Ownership
- Frontend team owns `schdulezero-islands/docs/`
- Handler team owns `schdulezero-handlers-python/docs/`
- Portal team owns `schedule-zero/docs/portal/`

### ✅ Local Development
- Each team can preview their docs locally
- Fast feedback (no waiting for full build)
- Independent git repos

### ✅ Easy Maintenance
- Update docs alongside code
- Same PR updates code + docs
- Version control for docs

### ✅ Unified Experience
- One URL for all docs
- One search index
- One navigation structure
- Professional appearance

## Alternative: Fully Independent Docs

If you prefer completely independent doc sites:

**portal_config.yaml:**
```yaml
microsites:
  - id: "sz_docs_portal"
    path: "/docs/portal"
    microsite_type: "mkdocs"
    
  - id: "sz_docs_frontend"
    path: "/docs/frontend"
    microsite_type: "mkdocs"
    
  - id: "sz_docs_handlers"
    path: "/docs/handlers"
    microsite_type: "mkdocs"
```

Each project builds independently to different paths. Trade-off: no unified search, separate navigation.

## Recommendation

**Use unified build approach** because:
1. Better user experience (single search, navigation)
2. Professional appearance
3. Easy cross-references between sections
4. Still maintains project ownership
5. Symlinks make it technically simple

The symlink approach gives you the best of both worlds!

---

### Strategy 2: Modular Build (Phase 2 - Recommended)

**When to use:** Growing platform, independent teams, handler ecosystem maturing

**Principle:**
- Each major component has independent documentation
- Each doc site can be built/deployed separately
- Portal serves all doc sites under `/docs/*` hierarchy
- Handlers can be reused across custom portals

**Directory Structure:**
```
schedule-zero/
├── docs/core/               ← Core platform docs
│   ├── mkdocs.yml
│   └── index.md
└── static/docs/
    ├── core/                ← Built docs
    ├── frontend/
    └── handlers/

schdulezero-islands/
└── docs/                    ← Independent frontend docs
    ├── mkdocs.yml
    └── index.md

schedulezero-handlers-python/
└── docs/                    ← Independent handler docs
    ├── mkdocs.yml
    └── index.md
```

**Portal Configuration:**
```yaml
microsites:
  - id: "sz_docs_core"
    path: "/docs"
    microsite_type: "mkdocs"
    docs_source: "schedule-zero/docs/core"
    
  - id: "sz_docs_frontend"
    path: "/docs/frontend"
    microsite_type: "mkdocs"
    docs_source: "schdulezero-islands/docs"
    
  - id: "sz_docs_handlers"
    path: "/docs/handlers"
    microsite_type: "mkdocs"
    docs_source: "schedulezero-handlers-python/docs"
```

**Build Process:**
```bash
# Each project builds independently
cd schedule-zero/docs/core && mkdocs build --site-dir ../../static/docs/core
cd schdulezero-islands && mkdocs build --site-dir ../schedule-zero/static/docs/frontend
cd schedulezero-handlers-python && mkdocs build --site-dir ../schedule-zero/static/docs/handlers
```

**Benefits:**
- ✅ Handler docs fully independent (can be hosted elsewhere)
- ✅ Each team controls their doc site
- ✅ Custom portals can pick which docs to include
- ✅ Different release cycles supported
- ✅ Easier to scale (add Rust handlers, Go handlers, etc.)

---

### Strategy 3: External Sites (Phase 3 - Enterprise)

**When to use:** Multiple products, large organization, commercial SaaS

**Principle:**
- Each component hosted on own subdomain
- Portal links to external doc sites
- Full independence and scalability

**Portal Configuration:**
```yaml
microsites:
  - id: "sz_docs_main"
    microsite_type: "external"
    path: "https://docs.schedulezero.io"
    
  - id: "sz_docs_handlers"
    microsite_type: "external"
    path: "https://handlers.schedulezero.io"
    
  - id: "api_reference"
    microsite_type: "external"
    path: "https://api.schedulezero.io"
```

---

## Recommendation Progression

**Now (Phase 1):** Unified build
- Fast to set up
- Good DX for small team
- Single search

**Soon (Phase 2):** Modular build ⭐ **RECOMMENDED**
- Handlers mature into ecosystem
- Custom portals emerging
- Teams scaling

**Future (Phase 3):** External sites
- Multiple products
- Commercial offerings
- Full independence

The modular approach (Phase 2) gives you flexibility for the platform vision!
