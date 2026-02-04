# ScheduleZero Platform Architecture

## Vision: Framework for Custom Portals

ScheduleZero is not just a single application - it's a **platform/framework** for building custom scheduling portals and microservices.

## Use Cases

### 1. Core ScheduleZero (Open Source)
**Base platform with essential microsites**

```yaml
# Vanilla portal_config.yaml
microsites:
  - sz_dash          # System dashboard
  - sz_schedules     # Job scheduling
  - sz_handlers      # Handler management
  - sz_docs          # Platform documentation
```

Target: DevOps teams, self-hosted task scheduling

---

### 2. LogStream Portal (Custom Build)
**Log aggregation and analysis service**

```yaml
# logstream_portal_config.yaml
portal:
  name: "LogStream Analytics"
  
microsites:
  # Core ScheduleZero microsites
  - sz_schedules     # Schedule log ingestion jobs
  - sz_handlers      # Custom log processors
  
  # Custom microsites
  - log_dashboard    # Real-time log visualization
  - log_search       # Full-text search interface
  - log_alerts       # Alert configuration
  - billing          # Usage-based billing
  
  # Documentation (separate sites)
  - logstream_docs   # Customer-facing docs
  - sz_handlers_docs # Handler development (for customers who extend)
```

Target: SaaS customers who need managed log aggregation

---

### 3. AI Workflow Portal (Enterprise)
**AI model scheduling and orchestration**

```yaml
# ai_portal_config.yaml
portal:
  name: "AI Workflow Engine"
  
microsites:
  # Core scheduling
  - sz_schedules     # Schedule ML pipeline jobs
  
  # AI-specific microsites
  - model_registry   # ML model versions
  - dataset_manager  # Training data management
  - experiment_logs  # MLflow integration
  - gpu_monitor      # Resource utilization
  
  # Multi-tenant features
  - tenant_admin     # Customer management
  - usage_dashboard  # Cost tracking
  
  # Separate doc sites
  - ai_portal_docs   # Product documentation
  - ml_handlers_docs # Custom handler docs
  - api_reference    # API documentation
```

Target: Enterprise ML teams, multi-tenant deployment

---

## Architectural Principles

### Principle 1: **Modular Documentation**

Each component/microsite can have independent documentation:

```
schedulezero-platform/
├── core-portal/
│   └── docs/              ← Core platform docs
├── handlers-python/
│   └── docs/              ← Python handler docs (independent)
├── handlers-rust/
│   └── docs/              ← Rust handler docs (independent)
├── handlers-go/
│   └── docs/              ← Go handler docs (independent)
└── microsites/
    ├── log-analytics/
    │   └── docs/          ← Log analytics docs (independent)
    └── ai-workflows/
        └── docs/          ← AI workflows docs (independent)
```

**Each can be:**
- Developed independently
- Versioned separately
- Deployed as separate doc sites OR merged into unified portal

### Principle 2: **Portal Configuration Flexibility**

Portal can choose documentation strategy:

#### Option A: Unified Docs (Small Teams)
```yaml
microsites:
  - id: "sz_docs"
    microsite_type: "mkdocs"
    path: "/docs"
    # Builds one unified site with symlinks to all projects
    docs_source: "portal/docs"  # Includes symlinks
```

#### Option B: Separate Doc Sites (Large Teams)
```yaml
microsites:
  - id: "sz_docs_core"
    microsite_type: "mkdocs"
    path: "/docs/core"
    docs_source: "schedulezero-core/docs"
    
  - id: "sz_docs_handlers_python"
    microsite_type: "mkdocs"
    path: "/docs/handlers/python"
    docs_source: "schedulezero-handlers-python/docs"
    
  - id: "sz_docs_handlers_rust"
    microsite_type: "mkdocs"
    path: "/docs/handlers/rust"
    docs_source: "schedulezero-handlers-rust/docs"
    
  - id: "sz_docs_logstream"
    microsite_type: "mkdocs"
    path: "/docs/logstream"
    docs_source: "logstream-microsite/docs"
```

#### Option C: External Doc Sites (Multi-Product)
```yaml
microsites:
  - id: "sz_docs_main"
    microsite_type: "external"
    path: "https://docs.schedulezero.io"
    description: "Main product documentation"
    
  - id: "sz_docs_handlers"
    microsite_type: "external"
    path: "https://handlers.schedulezero.io"
    description: "Handler development docs"
    
  - id: "api_reference"
    microsite_type: "external"
    path: "https://api.schedulezero.io"
    description: "API reference (Swagger/OpenAPI)"
```

### Principle 3: **Handler Documentation Independence**

Handlers are complex enough to warrant separate docs:

```
schedulezero-handlers-python/
├── src/handlers/
├── tests/
├── docs/                      ← Standalone documentation
│   ├── mkdocs.yml
│   ├── index.md
│   ├── getting-started.md
│   ├── api-reference/
│   │   ├── base-handler.md
│   │   ├── http-handler.md
│   │   └── webhook-handler.md
│   ├── examples/
│   │   ├── retry-logic.md
│   │   └── custom-handlers.md
│   └── deployment/
│       ├── docker.md
│       └── kubernetes.md
└── README.md

# Can be deployed as:
# 1. Separate site: https://python-handlers.schedulezero.io
# 2. Portal path: /docs/handlers/python
# 3. Merged into unified docs via symlink
```

**Why independent handler docs?**
- Different audiences (core users vs. handler developers)
- Different release cycles (handlers update frequently)
- Different maintainers (language-specific teams)
- Can be reused across multiple portals (LogStream, AI Workflow, etc.)

## Platform Configuration Schema

### Enhanced `portal_config.yaml`

```yaml
# Platform identity
portal:
  name: "LogStream Analytics"         # Custom portal name
  version: "2.1.0"                    # Your version
  base_platform: "schedulezero"       # Built on ScheduleZero
  base_version: "1.5.0"               # ScheduleZero version

# Branding
branding:
  logo: "/static/img/logstream-logo.png"
  favicon: "/static/img/favicon.ico"
  primary_color: "#2E7D32"            # Green theme
  company_name: "LogStream Inc."

# Microsites (mix core + custom)
microsites:
  # Core ScheduleZero microsites
  - id: "sz_schedules"
    name: "Schedules"
    microsite_type: "htmx"
    source: "schedulezero-core"       # From base platform
    enabled: true
    
  - id: "sz_handlers"
    name: "Handlers"
    microsite_type: "htmx"
    source: "schedulezero-core"
    enabled: true
  
  # Custom microsites
  - id: "log_dashboard"
    name: "Logs"
    microsite_type: "htmx"
    source: "logstream-custom"        # Your custom code
    enabled: true
    
  - id: "log_search"
    name: "Search"
    microsite_type: "htmx"
    source: "logstream-custom"
    enabled: true

# Documentation strategy
documentation:
  strategy: "separate"  # "unified" or "separate" or "external"
  
  sites:
    # Product documentation
    - id: "logstream_docs"
      name: "LogStream Docs"
      path: "/docs"
      source: "logstream-portal/docs"
      priority: 1
      
    # Handler docs (for customers extending platform)
    - id: "handler_docs"
      name: "Handler Development"
      path: "/docs/handlers"
      source: "schedulezero-handlers-python/docs"
      priority: 2
      
    # API reference
    - id: "api_docs"
      name: "API Reference"
      path: "/api/docs"
      type: "openapi"
      source: "logstream-portal/openapi.yaml"
      priority: 3

# Multi-tenancy (for SaaS deployments)
multi_tenant:
  enabled: true
  tenant_isolation: "database"  # "database" or "schema" or "kubernetes"
  
# Monetization (for commercial offerings)
billing:
  enabled: true
  provider: "stripe"
  usage_metrics:
    - "schedules_executed"
    - "data_ingested_gb"
    - "api_calls"
```

## Directory Structure for Custom Portal

```
logstream-platform/
├── portal/
│   ├── portal_config.yaml         ← Custom portal config
│   ├── branding/
│   │   ├── logo.png
│   │   └── theme.css
│   └── docs/                      ← Product documentation
│       ├── mkdocs.yml
│       ├── index.md               ← Customer-facing docs
│       ├── getting-started.md
│       ├── log-ingestion.md
│       └── billing.md
│
├── microsites/
│   ├── log-dashboard/             ← Custom microsite
│   │   ├── handlers.py
│   │   ├── templates/
│   │   └── static/
│   └── log-search/                ← Custom microsite
│       ├── handlers.py
│       └── templates/
│
├── schedulezero-core/             ← Git submodule or dependency
│   ├── sz_schedules/
│   ├── sz_handlers/
│   └── sz_dash/
│
├── schedulezero-handlers-python/  ← Git submodule (optional)
│   ├── src/handlers/
│   └── docs/                      ← Independent handler docs
│       └── mkdocs.yml
│
└── frontend/
    ├── components/                ← Custom Web Components
    └── islands/                   ← From schdulezero-islands
```

## Build Strategies per Use Case

### Strategy 1: Simple Portal (Unified Docs)
**Good for: Small teams, single product**

```bash
# Build one unified doc site
cd portal
./scripts/setup-docs.sh     # Create symlinks
mkdocs build                # Build unified site

# Result: /docs/ serves everything
```

### Strategy 2: Modular Portal (Separate Docs)
**Good for: Medium teams, clear separation**

```bash
# Build each doc site independently
cd portal/docs && mkdocs build --site-dir ../../static/docs/portal
cd ../../schedulezero-handlers-python/docs && mkdocs build --site-dir ../../static/docs/handlers
cd ../../logstream-custom/docs && mkdocs build --site-dir ../../static/docs/logstream

# Result:
# /docs/           → Portal docs
# /docs/handlers/  → Handler docs
# /docs/logstream/ → Custom microsite docs
```

### Strategy 3: Multi-Product (External Docs)
**Good for: Large organizations, multiple products**

```bash
# Each project hosts its own docs
# Portal just links to them

# schedulezero-core docs → https://docs.schedulezero.io
# handler docs → https://handlers.schedulezero.io
# logstream docs → https://docs.logstream.io
```

## Recommendation for ScheduleZero Platform

### Phase 1: Core Platform (Now)
**Unified docs make sense:**
```yaml
microsites:
  - id: "sz_docs"
    path: "/docs"
    # Includes: core, frontend, handlers via symlinks
```

**Reasoning:**
- Small team
- Cohesive product
- Easy to maintain
- Good UX (single search)

### Phase 2: Handlers Mature (Soon)
**Split handler docs:**
```yaml
microsites:
  - id: "sz_docs_core"
    path: "/docs"
    
  - id: "sz_docs_handlers"
    path: "/docs/handlers"
    # Separate site, can be versioned independently
```

**Reasoning:**
- Handler ecosystem grows
- Different audiences (users vs. developers)
- Multiple language implementations
- Frequent updates

### Phase 3: Custom Portals (Future)
**Each deployment chooses:**
```yaml
# LogStream chooses separate docs
documentation:
  strategy: "separate"
  sites: [product, handlers, api]

# Small customer chooses unified
documentation:
  strategy: "unified"
```

## Updated Portal Config Example

Let's update the example config to show flexibility:

```yaml
# portal_config.yaml

portal:
  name: "ScheduleZero"
  version: "1.0.0"
  type: "core"  # "core" or "custom" or "saas"

microsites:
  - id: "sz_dash"
    microsite_type: "htmx"
    
  - id: "sz_schedules"
    microsite_type: "htmx"
    
  - id: "sz_handlers"
    microsite_type: "htmx"

# Documentation Configuration
documentation:
  # Strategy: "unified" | "modular" | "external"
  strategy: "modular"  # Changed from single unified site
  
  # Define doc sites
  sites:
    # Core platform documentation
    - id: "sz_docs_core"
      name: "Core Documentation"
      icon: "📖"
      path: "/docs"
      microsite_type: "mkdocs"
      docs_source: "schedule-zero/docs/core"
      enabled: true
      nav_order: 1
      
    # Frontend/component documentation
    - id: "sz_docs_frontend"
      name: "Frontend Components"
      icon: "🧩"
      path: "/docs/frontend"
      microsite_type: "mkdocs"
      docs_source: "schdulezero-islands/docs"
      enabled: true
      nav_order: 2
      
    # Handler documentation (independent!)
    - id: "sz_docs_handlers"
      name: "Handler Development"
      icon: "🔌"
      path: "/docs/handlers"
      microsite_type: "mkdocs"
      docs_source: "schedulezero-handlers-python/docs"
      enabled: true
      nav_order: 3
      description: "Independent handler documentation for developers"
```

This allows:
- ✅ Core platform docs to evolve independently
- ✅ Handler docs to be fully separate (can be hosted elsewhere)
- ✅ Custom portals to include/exclude doc sites as needed
- ✅ Future scalability (add Rust handlers, Go handlers, etc.)

Perfect for your vision of ScheduleZero as a platform! 🚀
