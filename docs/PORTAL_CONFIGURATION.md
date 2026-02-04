# Portal Configuration Summary

## What Changed

### ❌ OLD (Hardcoded Paths)
```python
# tornado_app_server.py - REMOVED
portal_path = os.path.join(os.path.dirname(__file__), 'portal')
microsite_path = os.path.join(os.path.dirname(__file__), 'microsites')

# Hardcoded microsite registration
from .microsites import sz_dash
microsite_registry.register(Microsite(
    name="Dashboard",
    routes=sz_dash.routes.routes,
    assets_path=os.path.join(microsite_path, 'sz_dash', 'assets'),
    ...
))
```

### ✅ NEW (Required Configuration)
```python
# tornado_app_server.py - NEW
from .portal_configuration import load_portal_config, PORTAL_CONFIG

# Load portal config (exits if missing/invalid)
PORTAL_CONFIG = load_portal_config()

# Dynamic microsite loading from config
for ms_config in PORTAL_CONFIG.get_enabled_microsites():
    routes_module = importlib.import_module(ms_config.routes_module)
    microsite = Microsite(
        name=ms_config.name,
        routes=routes_module.routes,
        assets_path=str(PORTAL_CONFIG.get_microsite_assets_path(ms_config)),
        ...
    )
```

## Required Files

### portal_config.yaml (REQUIRED)
```yaml
portal_name: "ScheduleZero Default Portal"
portal_root: "../schedule-zero-islands/dist/portal1"  # REQUIRED

component_library:      # For validation
  - htmx
  - web-components

microsites:            # REQUIRED
  - name: "Dashboard"
    url_prefix: "/dash"
    routes_module: "schedule_zero.microsites.sz_dash.routes"
    templates_path: "microsites/sz_dash/templates"
    assets_path: "microsites/sz_dash/assets"
    enabled: true

static_path: "static"
template_cache: true
fail_on_missing_portal: true  # Exit if portal_root doesn't exist
```

### portal_configuration.py (NEW)
- `PortalConfig` dataclass
- `MicrositeConfig` dataclass
- `load_portal_config()` - NO FALLBACKS, exits on error
- Validates paths, microsites, settings

## Server Behavior

### ✅ With Valid Config
```bash
$ poetry run python -m schedule_zero.server

[INFO] Loaded portal config: ScheduleZero Default Portal v1.0.0
[INFO] Portal root: /path/to/schedule-zero-islands/dist/portal1
[INFO] Component libraries: htmx, web-components
[INFO] Enabled microsites: 4/4
[INFO] Registered microsite: Dashboard at /dash
[INFO] Registered microsite: Schedules Manager at /schedules
...
[INFO] Tornado server ready
```

### ❌ Without Config
```bash
$ poetry run python -m schedule_zero.server

[ERROR] Portal configuration not found: portal_config.yaml
[ERROR] Create portal_config.yaml with required settings:
[ERROR]   - portal_root: Path to portal directory
[ERROR]   - microsites: List of microsite configurations
[ERROR]   - component_library: List of component libraries
[ERROR] See portal_config.yaml.example for template
Process exited with code 1
```

### ❌ With Invalid Config
```bash
$ poetry run python -m schedule_zero.server

[ERROR] Missing required fields in portal_config.yaml: portal_root
Process exited with code 1
```

### ❌ With Missing Portal Root
```bash
$ poetry run python -m schedule_zero.server

[ERROR] Portal root does not exist: /nonexistent/path
[ERROR] Set fail_on_missing_portal: false to allow missing portal during development
Process exited with code 1
```

## Multiple Portal Configurations

### Environment Variable
```bash
export SCHEDULEZERO_PORTAL_CONFIG=portal_config_portal2.yaml
poetry run python -m schedule_zero.server
```

### Deployment-Specific
```
deployments/
├── production/
│   ├── portal_config.yaml     # → portal1 (full admin)
│   └── ...
├── ops/
│   ├── portal_config.yaml     # → portal2 (ops focused)
│   └── ...
└── test/
    ├── portal_config.yaml     # → portal1 (dev mode)
    └── ...
```

## Component Library Configuration

### Purpose
Defines which custom HTML elements/attributes are valid for validation tools.

### In portal_config.yaml
```yaml
component_library:
  - htmx           # hx-get, hx-post, hx-swap, etc.
  - web-components # <sz-nav>, <sz-*>, any custom element with hyphen
  - vue            # v-if, v-for, <v-*>, Vuetify components
```

### Used By
- `sz_root_checker.py` - Skips warnings for recognized components
- Vite HTML validation - Configures html-validate ignore patterns
- ESLint plugins - Component-specific linting rules

## Development Workflow

### 1. Create Portal in schedule-zero-islands
```bash
cd schedule-zero-islands
mkdir -p src/portal1/{static,microsites}
# Add HTML, JS, CSS, microsite content
```

### 2. Configure Vite to Build Portal
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        'portal1': resolve(__dirname, 'src/portal1/index.html'),
        ...
      }
    }
  }
});
```

### 3. Build and Sync
```bash
npm run build
npm run sync  # Copies dist/ → schedule-zero/
```

### 4. Create portal_config.yaml
```bash
cd schedule-zero
cp portal_config.yaml.example portal_config.yaml
# Edit portal_root: "../schedule-zero-islands/dist/portal1"
# Configure microsites, component_library, etc.
```

### 5. Start Server
```bash
poetry run python -m schedule_zero.server
# Server validates config, loads portal, registers microsites
```

## Migration from Old Config

### config.yaml.old
```yaml
instance_name: "My ScheduleZero Instance"
description: "..."
admin_contact: "admin@example.com"
version: "0.1.0-alpha"
site_root: null  # REMOVED - now in portal_config.yaml
```

### portal_config.yaml (NEW)
```yaml
portal_name: "My ScheduleZero Instance"
description: "..."
admin_contact: "admin@example.com"
portal_version: "0.1.0-alpha"
portal_root: "../schedule-zero-islands/dist/portal1"  # REQUIRED
component_library: [...]                              # REQUIRED
microsites: [...]                                     # REQUIRED
```

## Benefits

✅ **No Hardcoded Paths** - Everything from configuration  
✅ **Multiple Portals** - Switch with env var or deployment  
✅ **Fail Fast** - Server won't start with invalid config  
✅ **Clear Errors** - Tells you exactly what's missing  
✅ **Flexible** - Easy to add new microsites/portals  
✅ **Vite Integration** - Portal lives in islands project  
✅ **Component Validation** - Knows which custom tags are valid  

## Next Steps

1. **Create portal1/ in schedule-zero-islands**
   - See `docs/MULTI_PORTAL_ARCHITECTURE.md`

2. **Build with Vite**
   - See `docs/SETUP_VITE_VALIDATION.md`

3. **Test Configuration**
   ```bash
   poetry run python sz_root_checker.py --default
   poetry run python -m schedule_zero.server
   ```

4. **Create Additional Portals** (optional)
   - portal2/, portal3/, etc.
   - Different UIs for different users/deployments
