# Portal Structures for schedule-zero-islands

## Overview
With Vite as the build system, portal content lives in `schedule-zero-islands` and gets built/synced to `schedule-zero`.

## Directory Structure

```
schedule-zero-islands/
├── src/
│   ├── portal1/              # Default portal
│   │   ├── index.html
│   │   ├── static/
│   │   │   ├── main.js
│   │   │   └── styles.css
│   │   └── microsites/
│   │       ├── _container/   # Shared components
│   │       ├── sz_dash/
│   │       ├── sz_schedules/
│   │       ├── sz_handlers/
│   │       └── mkdocs/
│   │
│   └── portal2/              # Alternative portal
│       ├── index.html        # Different layout
│       ├── static/
│       └── microsites/       # Different microsite selection
│
├── dist/                     # Vite build output
│   ├── portal1/              # Built portal1 → synced to schedule-zero
│   └── portal2/              # Built portal2 → synced to schedule-zero
│
└── vite.config.js            # Builds both portals
```

## portal1/ - Default Administrative Portal

**Purpose:** Full-featured admin interface with all microsites

### src/portal1/index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}ScheduleZero Admin{% end %}</title>
  <link rel="stylesheet" href="/static/styles.css">
  <script src="/static/assets/htmx.min.js"></script>
</head>
<body>
  <sz-nav current-page="{{ current_page }}"></sz-nav>
  
  <main class="container">
    {% block content %}
    <h1>Welcome to ScheduleZero</h1>
    <p>Admin portal for managing schedules and handlers</p>
    {% end %}
  </main>
  
  <script type="module" src="/static/main.js"></script>
</body>
</html>
```

### src/portal1/microsites/
```
portal1/microsites/
├── _container/
│   └── assets/
│       └── js/
│           ├── htmx.min.js
│           └── components/
│               └── sz-nav.js         # Shared navigation component
│
├── sz_dash/
│   ├── templates/
│   │   ├── dashboard.html            # Main dashboard
│   │   └── component_test.html       # Component diagnostics
│   └── assets/
│       ├── dashboard.js              # Dashboard island
│       └── dashboard.css
│
├── sz_schedules/
│   ├── templates/
│   │   ├── schedules_list.html       # Schedule management
│   │   └── schedule_detail.html
│   └── assets/
│       ├── schedules.js
│       └── schedules.css
│
├── sz_handlers/
│   ├── templates/
│   │   ├── handlers_list.html        # Handler registry
│   │   └── handler_detail.html
│   └── assets/
│       ├── handlers.js
│       └── handlers.css
│
└── mkdocs/
    ├── templates/
    │   └── docs_wrapper.html         # MkDocs iframe wrapper
    └── assets/
        └── docs.css
```

### Corresponding portal_config.yaml (in schedule-zero)
```yaml
portal_name: "ScheduleZero Default Portal"
portal_root: "../schedule-zero-islands/dist/portal1"

component_library:
  - htmx
  - web-components

microsites:
  - name: "Dashboard"
    url_prefix: "/dash"
    routes_module: "schedule_zero.microsites.sz_dash.routes"
    templates_path: "microsites/sz_dash/templates"
    assets_path: "microsites/sz_dash/assets"
    enabled: true
    
  - name: "Schedules Manager"
    url_prefix: "/schedules"
    routes_module: "schedule_zero.microsites.sz_schedules.routes"
    templates_path: "microsites/sz_schedules/templates"
    assets_path: "microsites/sz_schedules/assets"
    enabled: true
    
  - name: "Handlers Registry"
    url_prefix: "/handlers"
    routes_module: "schedule_zero.microsites.sz_handlers.routes"
    templates_path: "microsites/sz_handlers/templates"
    assets_path: "microsites/sz_handlers/assets"
    enabled: true
    
  - name: "Documentation"
    url_prefix: "/docs"
    routes_module: "schedule_zero.microsites.mkdocs.routes"
    templates_path: "microsites/mkdocs/templates"
    assets_path: "microsites/mkdocs/assets"
    enabled: true
```

## portal2/ - Operations-Focused Portal

**Purpose:** Simplified operations dashboard with monitoring focus

### src/portal2/index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}ScheduleZero Ops{% end %}</title>
  <link rel="stylesheet" href="/static/ops-theme.css">
  <script src="/static/assets/htmx.min.js"></script>
</head>
<body class="ops-theme">
  <header class="ops-header">
    <h1>ScheduleZero Operations</h1>
    <sz-nav current-page="{{ current_page }}"></sz-nav>
  </header>
  
  <main class="ops-container">
    {% block content %}
    <div class="ops-dashboard">
      <h2>System Status</h2>
      <div hx-get="/api/health" hx-trigger="load, every 5s"></div>
    </div>
    {% end %}
  </main>
  
  <script type="module" src="/static/ops.js"></script>
</body>
</html>
```

### src/portal2/microsites/
```
portal2/microsites/
├── _container/              # Shared with portal1
│   └── assets/
│       └── js/
│           └── components/
│               └── sz-nav.js
│
├── sz_dash/
│   ├── templates/
│   │   └── ops_dashboard.html    # Different template than portal1
│   └── assets/
│       ├── ops_dashboard.js      # Ops-focused dashboard
│       └── ops_dashboard.css
│
├── sz_handlers/
│   ├── templates/
│   │   └── handlers_monitor.html # Monitoring view only
│   └── assets/
│       └── handlers_monitor.js
│
└── mkdocs/
    ├── templates/
    │   └── docs_wrapper.html
    └── assets/
        └── docs.css
```

### Corresponding portal_config_portal2.yaml
```yaml
portal_name: "ScheduleZero Ops Portal"
portal_root: "../schedule-zero-islands/dist/portal2"

component_library:
  - htmx
  - web-components
  - vue  # Uses Vuetify for data tables

microsites:
  - name: "Operations Dashboard"
    url_prefix: "/ops"
    routes_module: "schedule_zero.microsites.sz_dash.routes"
    templates_path: "microsites/sz_dash/templates"
    assets_path: "microsites/sz_dash/assets"
    enabled: true
    
  - name: "System Monitor"
    url_prefix: "/monitor"
    routes_module: "schedule_zero.microsites.sz_handlers.routes"
    templates_path: "microsites/sz_handlers/templates"
    assets_path: "microsites/sz_handlers/assets"
    enabled: true
    
  # Schedules microsite disabled in ops portal
  - name: "Schedules Manager"
    url_prefix: "/schedules"
    routes_module: "schedule_zero.microsites.sz_schedules.routes"
    templates_path: "microsites/sz_schedules/templates"
    assets_path: "microsites/sz_schedules/assets"
    enabled: false
    
  - name: "Documentation"
    url_prefix: "/docs"
    routes_module: "schedule_zero.microsites.mkdocs.routes"
    templates_path: "microsites/mkdocs/templates"
    assets_path: "microsites/mkdocs/assets"
    enabled: true
```

## Vite Configuration for Multi-Portal Build

### vite.config.js
```javascript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        // Portal 1 entries
        'portal1': resolve(__dirname, 'src/portal1/index.html'),
        'portal1-main': resolve(__dirname, 'src/portal1/static/main.js'),
        
        // Portal 2 entries
        'portal2': resolve(__dirname, 'src/portal2/index.html'),
        'portal2-ops': resolve(__dirname, 'src/portal2/static/ops.js'),
        
        // Shared components (both portals)
        'sz-nav': resolve(__dirname, 'src/portal1/microsites/_container/assets/js/components/sz-nav.js'),
        
        // Portal 1 microsites
        'dashboard': resolve(__dirname, 'src/portal1/microsites/sz_dash/assets/dashboard.js'),
        'schedules': resolve(__dirname, 'src/portal1/microsites/sz_schedules/assets/schedules.js'),
        'handlers': resolve(__dirname, 'src/portal1/microsites/sz_handlers/assets/handlers.js'),
        
        // Portal 2 microsites
        'ops-dashboard': resolve(__dirname, 'src/portal2/microsites/sz_dash/assets/ops_dashboard.js'),
        'handlers-monitor': resolve(__dirname, 'src/portal2/microsites/sz_handlers/assets/handlers_monitor.js'),
      },
      
      output: {
        dir: 'dist',
        entryFileNames: (chunkInfo) => {
          // Organize by portal
          if (chunkInfo.name.startsWith('portal1')) {
            return 'portal1/assets/[name]-[hash].js';
          } else if (chunkInfo.name.startsWith('portal2')) {
            return 'portal2/assets/[name]-[hash].js';
          }
          return 'shared/[name]-[hash].js';
        }
      }
    }
  }
});
```

## Running Different Portals

### Start with Portal 1 (Default)
```bash
cd schedule-zero
poetry run python -m schedule_zero.server
# Uses portal_config.yaml (points to portal1)
```

### Start with Portal 2
```bash
cd schedule-zero
export SCHEDULEZERO_PORTAL_CONFIG=portal_config_portal2.yaml
poetry run python -m schedule_zero.server
# Uses portal2 configuration
```

### Or use deployment-specific configs
```bash
# deployments/production/portal_config.yaml → portal1
# deployments/ops/portal_config.yaml → portal2
poetry run python -m schedule_zero.server --deployment production
poetry run python -m schedule_zero.server --deployment ops
```

## Benefits of Multi-Portal Architecture

✅ **Different UIs for different users** (admin vs ops vs developer)  
✅ **Different microsite combinations** per portal  
✅ **Different themes/branding** per portal  
✅ **Shared components** (_container) across portals  
✅ **Independent builds** can update portal1 without affecting portal2  
✅ **A/B testing** of new UI features  
✅ **Multi-tenant support** (different portal per customer)  

## Creating New Portals

1. **In schedule-zero-islands:**
   ```bash
   mkdir -p src/portal3/{static,microsites}
   # Copy from portal1 or portal2 as starting point
   ```

2. **In schedule-zero:**
   ```bash
   cp portal_config.yaml portal_config_portal3.yaml
   # Edit portal_root, microsites, etc.
   ```

3. **Build and test:**
   ```bash
   cd schedule-zero-islands
   npm run build
   npm run sync
   
   cd ../schedule-zero
   export SCHEDULEZERO_PORTAL_CONFIG=portal_config_portal3.yaml
   poetry run python -m schedule_zero.server
   ```

This architecture gives you maximum flexibility while maintaining clean separation between frontend (Vite/islands) and backend (Python/Tornado).
