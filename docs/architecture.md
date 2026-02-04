# ScheduleZero Architecture: Data Flow & Integration

## Overview

ScheduleZero is a full-stack distributed task scheduling system built with:
- **Backend**: Python Tornado (async web framework)
- **Frontend**: HTMX + Web Components (islands architecture)
- **Build System**: Vite (JavaScript/TypeScript bundler)

This document explains how configuration files, assets, and code flow together to create the complete portal.

## Component Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIGURATION LAYER                       │
├─────────────────────────────────────────────────────────────┤
│ portal_config.yaml                                           │
│  ├─ Portal metadata (name, version)                         │
│  ├─ Microsite definitions (id, path, icon, enabled)         │
│  ├─ Component libraries (htmx, web-components)              │
│  └─ Theme settings (colors, nav style)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PYTHON BACKEND LAYER                      │
├─────────────────────────────────────────────────────────────┤
│ Tornado Application                                          │
│  ├─ portal_handler.py                                        │
│  │   └─ GET /api/portal/config → Reads portal_config.yaml  │
│  │       Filters enabled microsites, serves JSON            │
│  │                                                           │
│  ├─ Microsite Handlers (one per microsite)                  │
│  │   ├─ sz_dash/handlers.py                                 │
│  │   ├─ sz_schedules/handlers.py                            │
│  │   └─ sz_handlers/handlers.py                             │
│  │       └─ Each renders Jinja2 templates with data         │
│  │                                                           │
│  └─ Static File Handler                                     │
│      └─ Serves /static/* (JS, CSS components)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  TORNADO TEMPLATE LAYER                      │
├─────────────────────────────────────────────────────────────┤
│ Jinja2 Templates                                             │
│  ├─ _container/templates/layout.html (Portal wrapper)       │
│  │   ├─ Loads HTMX library                                  │
│  │   ├─ Loads sz-nav Web Component                          │
│  │   ├─ <sz-nav config-url="/api/portal/config">           │
│  │   └─ <main id="content">{% block content %}{% end %}</main>│
│  │                                                           │
│  └─ Microsite Templates (extend layout.html)                │
│      ├─ sz_dash/templates/dashboard.html                    │
│      ├─ sz_schedules/templates/schedules_list.html          │
│      └─ sz_handlers/templates/handlers_list.html            │
│          └─ Use HTMX attributes + Web Components            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 WEB COMPONENTS LAYER (Built by Vite)         │
├─────────────────────────────────────────────────────────────┤
│ schdulezero-islands/ (This Project)                         │
│  ├─ src/components/sz-nav.ts                                │
│  │   ├─ Fetches /api/portal/config                          │
│  │   ├─ Renders navigation with Shadow DOM                  │
│  │   └─ Integrates HTMX for SPA navigation                  │
│  │                                                           │
│  ├─ src/vanilla/ (Pure JS components)                       │
│  │   ├─ connection-status.js                                │
│  │   ├─ copy-button.js                                      │
│  │   └─ sz-flash.js                                         │
│  │                                                           │
│  └─ src/vuetify/ (Vue + Vuetify components)                 │
│      ├─ schedule-grid.js                                    │
│      ├─ schedule-form.js                                    │
│      ├─ handler-grid.js                                     │
│      └─ execution-log-grid.js                               │
│                                                              │
│  Vite Build Process:                                        │
│  └─ pnpm run build                                          │
│      ├─ Compiles TypeScript → JavaScript                    │
│      ├─ Bundles dependencies (Vue, Vuetify)                 │
│      ├─ Minifies code                                       │
│      └─ Outputs to dist/                                    │
│          ├─ components/sz-nav.min.js                        │
│          ├─ vanilla/*.min.js                                │
│          └─ vuetify/*.min.js                                │
│                                                              │
│  Deployment:                                                 │
│  └─ pnpm run deploy                                         │
│      └─ Copies dist/ → schedule-zero/.../assets/js/components/ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER RUNTIME LAYER                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Initial Page Load                                         │
│    ├─ Browser requests /dash                                │
│    ├─ Tornado renders layout.html + dashboard.html          │
│    └─ HTML sent to browser with <sz-nav>, HTMX attributes   │
│                                                              │
│ 2. Component Initialization                                  │
│    ├─ <sz-nav> Web Component loads                          │
│    ├─ Fetches /api/portal/config via fetch()                │
│    ├─ Receives JSON with microsite list                     │
│    └─ Renders navigation in Shadow DOM                      │
│                                                              │
│ 3. HTMX Interaction                                          │
│    ├─ User clicks nav link with hx-get="/schedules"         │
│    ├─ HTMX makes fetch request to /schedules                │
│    ├─ Tornado renders schedules_list.html                   │
│    ├─ HTMX swaps HTML into <main id="content">              │
│    └─ sz-nav updates active state                           │
│                                                              │
│ 4. Web Component Islands                                     │
│    ├─ <schedule-grid> loads, fetches /api/schedules         │
│    ├─ Renders data table with Vue + Vuetify                 │
│    ├─ User interactions emit custom events                  │
│    └─ HTMX handles server updates                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow: Step-by-Step

### 1. Configuration to Portal

**File:** `portal_config.yaml`
```yaml
microsites:
  - id: "sz_dash"
    name: "Dashboard"
    path: "/dash"
    enabled: true
```

**Python Handler:** `portal_handler.py`
```python
class PortalConfigHandler(RequestHandler):
    def get(self):
        config = yaml.safe_load(open('portal_config.yaml'))
        enabled = [ms for ms in config['microsites'] if ms['enabled']]
        self.write({'microsites': enabled})
```

**API Response:** `GET /api/portal/config`
```json
{
  "microsites": [
    {"id": "sz_dash", "name": "Dashboard", "path": "/dash", ...}
  ]
}
```

### 2. Portal to Navigation Component

**Template:** `layout.html`
```html
<sz-nav config-url="/api/portal/config" current-path="/dash"></sz-nav>
```

**Component:** `sz-nav.ts`
```typescript
async connectedCallback() {
  const response = await fetch('/api/portal/config');
  this.config = await response.json();
  this.render();  // Creates nav with Shadow DOM
}
```

**Shadow DOM Output:**
```html
#shadow-root
  <nav>
    <a href="/dash" hx-get="/dash" hx-target="#content">Dashboard</a>
    <a href="/schedules" hx-get="/schedules">Schedules</a>
  </nav>
```

### 3. Navigation to Microsite

**User Action:** Clicks "Schedules" link

**HTMX Behavior:**
```html
<a href="/schedules" 
   hx-get="/schedules" 
   hx-target="#content" 
   hx-push-url="true">
```

**Request:** `GET /schedules` (HTMX fetch)

**Tornado Handler:** `sz_schedules/handlers.py`
```python
class SchedulesHandler(RequestHandler):
    def get(self):
        schedules = self.db.query_schedules()
        self.render('schedules_list.html', schedules=schedules)
```

**Response:** HTML fragment
```html
<div class="schedules">
  <h1>Schedules</h1>
  <schedule-grid api-endpoint="/api/schedules"></schedule-grid>
</div>
```

**HTMX Action:** Swaps HTML into `<main id="content">`

### 4. Microsite to Web Component

**HTML in Page:**
```html
<schedule-grid api-endpoint="/api/schedules"></schedule-grid>
<script src="/static/js/components/vuetify/schedule-grid.min.js"></script>
```

**Component Loads:**
```javascript
class ScheduleGrid extends HTMLElement {
  connectedCallback() {
    const endpoint = this.getAttribute('api-endpoint');
    this.fetchData(endpoint);  // GET /api/schedules
  }
}
```

**API Request:** `GET /api/schedules`

**Tornado Handler:** `sz_schedules/api_handlers.py`
```python
class SchedulesAPIHandler(RequestHandler):
    def get(self):
        schedules = self.db.query_schedules()
        self.write({
            'schedules': [
                {'job_id': 'job-1', 'status': 'active', ...}
            ]
        })
```

**Component Renders:** Vue app with Vuetify data table

### 5. Component to Backend (User Action)

**User clicks "Edit" button in schedule-grid**

**Component emits event:**
```javascript
this.dispatchEvent(new CustomEvent('schedule:edit', {
  detail: {schedule_id: 'job-1'},
  bubbles: true
}));
```

**Template listens:**
```html
<schedule-grid 
  onschedule:edit="handleEdit(event)">
</schedule-grid>

<script>
function handleEdit(event) {
  htmx.ajax('GET', `/schedules/edit/${event.detail.schedule_id}`, {
    target: '#content'
  });
}
</script>
```

**OR use HTMX directly in component:**
```javascript
// Inside component
const editBtn = document.createElement('button');
editBtn.setAttribute('hx-get', `/schedules/edit/${schedule_id}`);
editBtn.setAttribute('hx-target', '#content');
htmx.process(editBtn);  // Make HTMX aware
```

## File Structure Mapping

### Configuration Files
```
schedule-zero/
├── portal_config.yaml          → Portal/microsite definitions
└── src/schedule_zero/
    └── microsites/
        ├── sz_dash/
        │   └── config.py           → Microsite-specific settings
        ├── sz_schedules/
        │   └── config.py
        └── sz_handlers/
            └── config.py
```

### Python Backend
```
schedule-zero/src/schedule_zero/
├── portal/
│   ├── handlers.py             → PortalConfigHandler
│   └── routes.py               → URL routing
├── microsites/
│   ├── _container/
│   │   ├── handlers.py         → Layout handler
│   │   └── templates/
│   │       └── layout.html     → Portal wrapper
│   ├── sz_dash/
│   │   ├── handlers.py         → Dashboard handlers
│   │   ├── api_handlers.py     → /api/stats/*
│   │   └── templates/
│   │       └── dashboard.html
│   ├── sz_schedules/
│   │   ├── handlers.py
│   │   ├── api_handlers.py     → /api/schedules/*
│   │   └── templates/
│   │       └── schedules_list.html
│   └── sz_handlers/
│       ├── handlers.py
│       ├── api_handlers.py     → /api/handlers/*
│       └── templates/
│           └── handlers_list.html
└── static/
    └── js/components/          → Deployed Web Components
        ├── components/
        │   └── sz-nav.min.js
        ├── vanilla/
        │   ├── connection-status.min.js
        │   ├── copy-button.min.js
        │   └── sz-flash.min.js
        └── vuetify/
            ├── schedule-grid.min.js
            ├── schedule-form.min.js
            ├── handler-grid.min.js
            └── execution-log-grid.min.js
```

### Frontend Source (This Project)
```
schdulezero-islands/
├── examples/
│   └── portal_config.yaml      → Example configuration
├── src/
│   ├── components/
│   │   └── sz-nav.ts           → Portal navigation (TypeScript)
│   ├── vanilla/
│   │   ├── connection-status.js
│   │   ├── copy-button.js
│   │   └── sz-flash.js
│   ├── vuetify/
│   │   ├── schedule-grid.js
│   │   ├── schedule-form.js
│   │   ├── handler-grid.js
│   │   └── execution-log-grid.js
│   └── types/
│       └── components.d.ts     → TypeScript interfaces
├── scripts/
│   ├── copy-to-python.js       → Deployment script
│   └── validate-html.js        → HTML validation tool
├── vite.config.js              → Build configuration
└── package.json                → Dependencies & scripts
```

## Build & Deployment Pipeline

### Development Workflow

```bash
# In schdulezero-islands/
pnpm install                    # Install dependencies
pnpm run build                  # Build components
pnpm run deploy                 # Copy to Python project

# In schedule-zero/
poetry run python -m schedule_zero.server  # Start Tornado
```

### Build Process Details

**Input:** `src/components/sz-nav.ts`
```typescript
class SzNav extends HTMLElement {
  async connectedCallback() {
    const response = await fetch('/api/portal/config');
    // ...
  }
}
```

**Vite Processing:**
1. TypeScript compilation (`.ts` → `.js`)
2. ES module bundling
3. Minification
4. Source map generation

**Output:** `dist/components/sz-nav.min.js` (ES module)
```javascript
class SzNav extends HTMLElement{async connectedCallback(){const t=await fetch("/api/portal/config");...}}customElements.define("sz-nav",SzNav);
```

**Deployment:**
```javascript
// scripts/copy-to-python.js
cpSync('dist/', '../schedule-zero/src/.../static/js/components/', {
  recursive: true
});
```

## Testing Strategy

### 1. Component Unit Tests (JavaScript)
```bash
# In schdulezero-islands/
pnpm run test:unit
```

### 2. Integration Tests (Python + JavaScript)
```python
# In schedule-zero/tests/
class TestPortalIntegration:
    def test_portal_config_api(self):
        response = self.fetch('/api/portal/config')
        assert response.code == 200
        config = json.loads(response.body)
        assert 'microsites' in config
    
    def test_navigation_loads(self):
        response = self.fetch('/dash')
        assert '<sz-nav' in response.body.decode()
        assert 'config-url="/api/portal/config"' in response.body.decode()
```

### 3. End-to-End Tests (Selenium/Playwright)
```python
def test_full_navigation_flow(browser):
    browser.get('http://localhost:8888/dash')
    
    # Wait for sz-nav to load config
    WebDriverWait(browser, 10).until(
        lambda d: d.execute_script(
            "return document.querySelector('sz-nav').shadowRoot !== null"
        )
    )
    
    # Click schedules nav item
    nav = browser.find_element(By.TAG_NAME, 'sz-nav')
    shadow_root = browser.execute_script('return arguments[0].shadowRoot', nav)
    schedules_link = shadow_root.find_element(By.CSS_SELECTOR, 'a[href="/schedules"]')
    schedules_link.click()
    
    # Verify HTMX swapped content
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'schedule-grid'))
    )
```

## Component Communication Patterns

### Pattern 1: Configuration Flow (Top-Down)
```
portal_config.yaml → Python API → sz-nav component → User sees navigation
```

### Pattern 2: User Action (Bottom-Up)
```
User clicks button → Component emits event → HTMX request → Python handler → HTML response
```

### Pattern 3: Data Binding (Bidirectional)
```
Python renders template with data → Component displays data
Component modifies data → HTMX POST → Python updates database → HTMX returns updated HTML
```

### Pattern 4: Real-time Updates (Server Push)
```
Python WebSocket → Component receives event → Component re-fetches data → Re-renders
```

## Key Interfaces

### TypeScript Component Interface
```typescript
interface ScheduleGridElement extends HTMLElement {
  'api-endpoint'?: string;  // Input: where to fetch data
  
  // Output: events
  addEventListener('schedule:edit', (e: CustomEvent) => void);
  addEventListener('schedule:delete', (e: CustomEvent) => void);
}
```

### Python API Contract
```python
# GET /api/schedules
Response: {
  "schedules": [
    {
      "job_id": str,
      "handler": str,
      "status": "active" | "paused" | "error",
      "next_run": ISO8601 datetime string
    }
  ]
}
```

### HTMX Template Pattern
```html
<!-- Action button with HTMX -->
<button 
  hx-post="/api/schedules/{{ schedule.job_id }}/pause"
  hx-target="closest .schedule-card"
  hx-swap="outerHTML">
  Pause
</button>
```

## Troubleshooting Data Flow

### Problem: Navigation doesn't show microsites
**Check:**
1. `portal_config.yaml` exists and has `microsites` list
2. `/api/portal/config` returns JSON (not 404)
3. Browser console shows no fetch errors
4. `sz-nav` component loaded (`<script src="...sz-nav.min.js">`)

### Problem: Component can't fetch data
**Check:**
1. Component has correct `api-endpoint` attribute
2. Tornado has API handler registered for that route
3. CORS headers set (if needed)
4. Network tab shows request succeeding

### Problem: HTMX navigation doesn't work
**Check:**
1. HTMX library loaded (`<script src="htmx.min.js">`)
2. Elements have correct `hx-*` attributes
3. Target element exists (`hx-target="#content"`)
4. Backend returns HTML fragment (not full page)

---

*This document should be kept in sync with actual implementation. Last updated: 2025-11-21*
