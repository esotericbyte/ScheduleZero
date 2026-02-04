# ScheduleZero Backend Integration - Prompt for schedule-zero Project

## Context

You are working on the **schedule-zero** Python Tornado backend project. A companion frontend project (**schdulezero-islands**) has been built with Web Components and comprehensive documentation. Your task is to implement the backend integration to support the portal architecture.

## What the Frontend Has Built

### 1. Portal Configuration Schema
Location: `../schdulezero-islands/examples/portal_config.yaml`

```yaml
portal:
  name: "ScheduleZero"
  version: "1.0.0"

microsites:
  - id: "sz_dash"
    name: "Dashboard"
    icon: "📊"
    path: "/dash"
    enabled: true
    microsite_type: "htmx"
  
  - id: "sz_schedules"
    name: "Schedules"
    path: "/schedules"
    microsite_type: "htmx"
  
  - id: "sz_docs_frontend"
    name: "Frontend Components"
    path: "/docs/frontend"
    microsite_type: "mkdocs"

component_library:
  - htmx
  - web-components

theme:
  css_variables:
    primary_color: "#1976D2"
  stylesheet: "/static/css/theme.css"
  component_styles:
    sz-nav: "/static/css/components/sz-nav.css"
```

### 2. TypeScript Navigation Component (sz-nav)
Built with Shadow DOM, expects this API:

**GET /api/portal/config**
```json
{
  "portal": {
    "name": "ScheduleZero",
    "version": "1.0.0"
  },
  "microsites": [
    {
      "id": "sz_dash",
      "name": "Dashboard",
      "icon": "📊",
      "path": "/dash",
      "type": "htmx"
    }
  ],
  "theme": {
    "css_variables": {...},
    "component_styles": {...}
  }
}
```

Component uses this to render navigation with HTMX attributes:
```html
<a href="/dash" 
   hx-get="/dash" 
   hx-target="#content"
   hx-push-url="true">
  📊 Dashboard
</a>
```

### 3. Web Components Built
Located in: `dist/components/` (after build)

- `sz-nav.min.js` - Navigation component (TypeScript, Shadow DOM)
- `vanilla/*.min.js` - Simple components (copy-button, sz-flash, connection-status)
- `vuetify/*.min.js` - Data grids (schedule-grid, handler-grid)

### 4. Documentation Created
Comprehensive docs at: `../schdulezero-islands/docs/`

- `architecture.md` - Complete data flow
- `platform-vision.md` - ScheduleZero as framework
- `component-patterns.md` - HTMX + Web Components integration

## HTMX + Tornado Best Practices (from Research)

### Request Detection
```python
class BaseHandler(RequestHandler):
    def is_htmx_request(self):
        return self.request.headers.get('HX-Request') == 'true'
    
    def render_response(self, template, **kwargs):
        if self.is_htmx_request():
            # Return just the fragment
            self.render(f'{template}_partial.html', **kwargs)
        else:
            # Return full page with layout
            self.render(f'{template}.html', **kwargs)
```

### Response Headers
```python
# Trigger client-side events
self.set_header('HX-Trigger', 'refreshNav')

# Client-side redirect
self.set_header('HX-Redirect', '/success')

# Update browser URL
self.set_header('HX-Push-Url', '/schedules/123')
```

### Template Structure
```html
<!-- layout.html (portal wrapper) -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <sz-nav config-url="/api/portal/config" current-path="{{ current_path }}"></sz-nav>
    
    <main id="content">
        {% block content %}{% end %}
    </main>
    
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="/static/js/components/sz-nav.min.js"></script>
</body>
</html>

<!-- schedules.html (full page) -->
{% extends "layout.html" %}
{% block content %}
    <div class="schedules">
        <h1>Schedules</h1>
        <schedule-grid api-endpoint="/api/schedules"></schedule-grid>
    </div>
{% endblock %}

<!-- schedules_partial.html (HTMX fragment) -->
<div class="schedules">
    <h1>Schedules</h1>
    <schedule-grid api-endpoint="/api/schedules"></schedule-grid>
</div>
```

## Tasks to Implement

### Task 1: Project Structure Setup

**Create settings file** to point to portal config:
```python
# src/schedule_zero/settings.py
import os
from pathlib import Path

# Portal configuration
PORTAL_CONFIG_PATH = os.getenv(
    'PORTAL_CONFIG_PATH',
    '../schdulezero-islands/examples/portal_config.yaml'
)

# If no portal config, use basic mode (no fancy UI)
PORTAL_ENABLED = Path(PORTAL_CONFIG_PATH).exists()
```

### Task 2: Portal Config API Handler

**Create `/api/portal/config` endpoint:**

```python
# src/schedule_zero/portal/handlers.py
import yaml
from tornado.web import RequestHandler
from ..settings import PORTAL_CONFIG_PATH, PORTAL_ENABLED

class PortalConfigHandler(RequestHandler):
    """Serves portal configuration to sz-nav component"""
    
    def get(self):
        if not PORTAL_ENABLED:
            # Fallback: basic config
            self.write({
                'portal': {'name': 'ScheduleZero', 'version': '1.0.0'},
                'microsites': []
            })
            return
        
        try:
            with open(PORTAL_CONFIG_PATH) as f:
                config = yaml.safe_load(f)
            
            # Filter enabled microsites only
            enabled_microsites = [
                ms for ms in config.get('microsites', [])
                if ms.get('enabled', True)
            ]
            
            # Transform for frontend
            response = {
                'portal': config.get('portal', {}),
                'microsites': [
                    {
                        'id': ms['id'],
                        'name': ms['name'],
                        'icon': ms.get('icon', ''),
                        'path': ms['path'],
                        'type': ms.get('microsite_type', 'htmx'),
                        'description': ms.get('description', '')
                    }
                    for ms in enabled_microsites
                ],
                'theme': config.get('theme', {})
            }
            
            self.set_header('Content-Type', 'application/json')
            self.write(response)
            
        except Exception as e:
            self.set_status(500)
            self.write({'error': str(e)})
```

### Task 3: HTMX-Aware Base Handler

**Create base handler for microsites:**

```python
# src/schedule_zero/microsites/base.py
from tornado.web import RequestHandler

class MicrositeHandler(RequestHandler):
    """Base handler for all microsite pages"""
    
    def is_htmx_request(self):
        """Check if request came from HTMX"""
        return self.request.headers.get('HX-Request') == 'true'
    
    def render_microsite(self, template, **kwargs):
        """Render full page or partial based on HTMX request"""
        kwargs['current_path'] = self.request.path
        
        if self.is_htmx_request():
            # HTMX request: render just the content fragment
            self.render(f'{template}_partial.html', **kwargs)
        else:
            # Normal request: render full page with layout
            self.render(f'{template}.html', **kwargs)
    
    def trigger_client_event(self, event_name, data=None):
        """Trigger client-side event via HX-Trigger header"""
        if data:
            import json
            self.set_header('HX-Trigger', json.dumps({event_name: data}))
        else:
            self.set_header('HX-Trigger', event_name)
```

### Task 4: Dashboard Microsite Example

**Implement dashboard with HTMX:**

```python
# src/schedule_zero/microsites/sz_dash/handlers.py
from ..base import MicrositeHandler

class DashboardHandler(MicrositeHandler):
    async def get(self):
        # Fetch data
        stats = await self.get_system_stats()
        active_schedules = await self.get_active_schedules()
        
        self.render_microsite(
            'dashboard',
            stats=stats,
            schedules=active_schedules
        )
    
    async def get_system_stats(self):
        # Return dashboard stats
        return {
            'total_schedules': 42,
            'active_handlers': 5,
            'jobs_today': 128
        }
    
    async def get_active_schedules(self):
        # Return recent schedules
        return []
```

**Templates:**

```html
<!-- microsites/sz_dash/templates/dashboard.html -->
{% extends "layout.html" %}
{% block content %}
    {% include "dashboard_content.html" %}
{% endblock %}

<!-- microsites/sz_dash/templates/dashboard_partial.html -->
{% include "dashboard_content.html" %}

<!-- microsites/sz_dash/templates/dashboard_content.html -->
<div class="dashboard">
    <h1>Dashboard</h1>
    
    <div class="stats">
        <div class="stat-card">
            <h3>{{ stats.total_schedules }}</h3>
            <p>Total Schedules</p>
        </div>
        <div class="stat-card">
            <h3>{{ stats.active_handlers }}</h3>
            <p>Active Handlers</p>
        </div>
    </div>
    
    <div class="recent-schedules">
        <h2>Recent Schedules</h2>
        <button hx-get="/api/schedules/refresh" 
                hx-target="#schedule-list"
                hx-swap="innerHTML">
            Refresh
        </button>
        <div id="schedule-list">
            {% for schedule in schedules %}
                <div class="schedule-card">{{ schedule.name }}</div>
            {% endfor %}
        </div>
    </div>
</div>
```

### Task 5: Portal Layout Template

**Create base layout with sz-nav:**

```html
<!-- microsites/_container/templates/layout.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ portal_name | default("ScheduleZero") }}</title>
    
    <!-- Theme CSS -->
    <link rel="stylesheet" href="/static/css/theme.css">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <!-- Portal Navigation -->
    <sz-nav 
        config-url="/api/portal/config" 
        current-path="{{ current_path }}">
    </sz-nav>
    
    <!-- Main Content Area (HTMX target) -->
    <main id="content" role="main">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Flash Messages -->
    <sz-flash></sz-flash>
    
    <!-- Web Components -->
    <script src="/static/js/components/components/sz-nav.min.js"></script>
    <script src="/static/js/components/vanilla/sz-flash.min.js"></script>
    
    <!-- HTMX Config -->
    <script>
        // Configure HTMX
        document.body.addEventListener('htmx:afterSwap', (event) => {
            // Update active nav after content swap
            const nav = document.querySelector('sz-nav');
            if (nav) {
                nav.setAttribute('current-path', window.location.pathname);
            }
        });
    </script>
</body>
</html>
```

### Task 6: Application Routes

**Wire everything together:**

```python
# src/schedule_zero/app.py
from tornado.web import Application
from .portal.handlers import PortalConfigHandler
from .microsites.sz_dash.handlers import DashboardHandler
from .microsites.sz_schedules.handlers import SchedulesHandler
from .microsites.sz_handlers.handlers import HandlersHandler

def make_app():
    return Application([
        # Portal API
        (r"/api/portal/config", PortalConfigHandler),
        
        # Microsites
        (r"/dash", DashboardHandler),
        (r"/schedules", SchedulesHandler),
        (r"/handlers", HandlersHandler),
        
        # Static files
        (r"/static/(.*)", StaticFileHandler, {"path": "static"}),
    ],
    template_path="microsites",
    debug=True)
```

### Task 7: CSS Theme

**Create theme stylesheet:**

```css
/* static/css/theme.css */
:root {
    --primary-color: #1976D2;
    --secondary-color: #424242;
    --accent-color: #FF5722;
    --background: #FFFFFF;
    --text-color: #212121;
    --nav-width: 250px;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-color);
    background: var(--background);
}

main#content {
    margin-left: var(--nav-width);
    padding: 2rem;
    min-height: 100vh;
}

/* HTMX loading indicator */
.htmx-swapping {
    opacity: 0;
    transition: opacity 200ms ease-in;
}
```

## Testing Plan

1. **Start Tornado server**
   ```bash
   poetry run python -m schedule_zero.server
   ```

2. **Test portal config API**
   ```bash
   curl http://localhost:8888/api/portal/config
   ```

3. **Test full page load**
   - Visit http://localhost:8888/dash
   - Should see layout + navigation + dashboard

4. **Test HTMX navigation**
   - Click navigation links
   - Content should swap without full page reload
   - URL should update in browser

5. **Test with missing portal config**
   - Rename or remove portal_config.yaml
   - Should fallback to basic mode

## Deliverables

1. ✅ Portal config API endpoint
2. ✅ HTMX-aware base handler
3. ✅ Layout template with sz-nav
4. ✅ At least one working microsite (dashboard)
5. ✅ Routing and application setup
6. ✅ Basic CSS theme
7. ✅ Settings file with portal config path

## Success Criteria

- `/api/portal/config` returns valid JSON
- sz-nav component loads and displays microsites
- Clicking nav links swaps content via HTMX (no full page reload)
- Full page loads work for direct URL access
- Browser back/forward buttons work correctly
- System works with or without portal config file

## Reference

- Frontend docs: `../schdulezero-islands/docs/architecture.md`
- Portal config: `../schdulezero-islands/examples/portal_config.yaml`
- HTMX docs: https://htmx.org/docs/
- Tornado docs: https://www.tornadoweb.org/

## Questions to Consider

1. Where should templates live? (microsites/_container/templates/ or separate?)
2. How to handle authentication with HTMX?
3. Should portal config be cached or read on every request?
4. How to handle errors in partial renders vs full page renders?

Good luck! The frontend is ready and waiting for this backend integration.
