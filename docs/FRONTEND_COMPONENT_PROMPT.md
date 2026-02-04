# Frontend Component Build Prompt - Schedule-Zero-Islands

## Context

You are working in the **schedule-zero-islands** frontend project to build web components for the ScheduleZero portal. The backend is ready and waiting at `http://localhost:8888` with proper CORS configured.

## Required Components

### 1. sz-nav (Navigation Component) - CRITICAL

**Purpose**: Portal navigation that fetches microsite config and renders clickable navigation with HTMX attributes.

**File**: `src/components/sz-nav.ts` (TypeScript Web Component)

**Requirements**:
```typescript
// Custom element: <sz-nav>
// Attributes:
//   - config-url: URL to fetch portal config (e.g., "/api/portal/config")
//   - current-path: Current page path for highlighting (e.g., "/dash")

interface PortalConfig {
  portal: {
    name: string;
    version: string;
  };
  microsites: Array<{
    id: string;
    name: string;
    icon: string;
    path: string;
    type: string;
    description?: string;
  }>;
  theme: {
    css_variables: Record<string, string>;
    stylesheet: string;
    component_styles?: Record<string, string>;
  };
}

class SzNav extends HTMLElement {
  // On connectedCallback():
  //   1. Fetch config from config-url attribute
  //   2. Render navigation sidebar/header
  //   3. Add HTMX attributes to links:
  //      hx-get="{path}"
  //      hx-target="#content"
  //      hx-push-url="true"
  //   4. Highlight current-path
  //   5. Listen for custom events to update active state

  // Shadow DOM recommended for style encapsulation
  // Apply theme CSS variables from config
  // Responsive: collapse to hamburger on mobile
}
```

**API Endpoint** (already implemented):
```
GET /api/portal/config
Response:
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
      "type": "htmx",
      "description": "System overview"
    }
  ],
  "theme": {
    "css_variables": {
      "primary_color": "#1976D2",
      "secondary_color": "#424242"
    },
    "stylesheet": "/static/css/theme.css"
  }
}
```

**HTML Output Example**:
```html
<sz-nav config-url="/api/portal/config" current-path="/dash">
  #shadow-root
    <nav class="sz-nav">
      <div class="nav-header">
        <h2>ScheduleZero</h2>
        <span class="version">v1.0.0</span>
      </div>
      <ul class="nav-items">
        <li class="nav-item active">
          <a href="/dash" 
             hx-get="/dash" 
             hx-target="#content"
             hx-push-url="true">
            <span class="icon">📊</span>
            <span class="label">Dashboard</span>
          </a>
        </li>
        <!-- More microsites... -->
      </ul>
    </nav>
</sz-nav>
```

**Styling**:
- Fixed sidebar on desktop (250px width)
- Collapsible hamburger menu on mobile
- Highlight active route
- Use theme CSS variables from config
- Smooth transitions

**Build Output**: `dist/components/sz-nav.min.js`

---

### 2. sz-flash (Flash Messages Component)

**Purpose**: Display temporary success/error/info messages triggered by server or client events.

**File**: `src/components/sz-flash.ts`

**Requirements**:
```typescript
// Custom element: <sz-flash>
// Methods:
//   - show(message, type, duration)
// Event listeners:
//   - HX-Trigger events from server

class SzFlash extends HTMLElement {
  show(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', duration = 3000) {
    // Create toast notification
    // Auto-dismiss after duration
    // Support multiple simultaneous messages
    // Accessible (ARIA live region)
  }

  // Listen for htmx:afterRequest and htmx:responseError
  // Listen for custom HX-Trigger events from server
}
```

**Usage**:
```html
<sz-flash></sz-flash>

<script>
  // Client-side trigger
  document.querySelector('sz-flash').show('Schedule created!', 'success');
  
  // Server can trigger via HX-Trigger header:
  // HX-Trigger: {"showMessage": {"text": "Job scheduled", "type": "success"}}
</script>
```

**Styling**:
- Toast notifications in top-right corner
- Color-coded by type (green=success, red=error, blue=info, yellow=warning)
- Slide-in animation
- Stack multiple messages
- Dismiss button
- Auto-fade out

**Build Output**: `dist/components/sz-flash.min.js`

---

### 3. Placeholder Components (Optional for Testing)

If full components aren't ready yet, create minimal placeholders:

**sz-nav-placeholder.js**:
```javascript
class SzNavPlaceholder extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <nav style="width: 250px; background: #1976D2; color: white; padding: 20px;">
        <h2>ScheduleZero</h2>
        <ul style="list-style: none; padding: 0;">
          <li><a href="/dash" style="color: white; display: block; padding: 10px;">📊 Dashboard</a></li>
          <li><a href="/schedules" style="color: white; display: block; padding: 10px;">📅 Schedules</a></li>
          <li><a href="/handlers" style="color: white; display: block; padding: 10px;">⚙️ Handlers</a></li>
        </ul>
      </nav>
    `;
  }
}
customElements.define('sz-nav', SzNavPlaceholder);
```

---

## Build Configuration

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    lib: {
      entry: {
        'sz-nav': './src/components/sz-nav.ts',
        'sz-flash': './src/components/sz-flash.ts',
      },
      formats: ['es'],
      fileName: (format, entryName) => `${entryName}.min.js`
    },
    outDir: 'dist/components',
    rollupOptions: {
      external: [], // Bundle dependencies
      output: {
        // Minify for production
        compact: true,
      }
    },
    minify: 'terser',
    sourcemap: false
  }
});
```

**Build Commands**:
```bash
# Development
npm run dev

# Production build
npm run build

# Output: dist/components/sz-nav.min.js, sz-flash.min.js
```

---

## Integration with Backend

### Portal Config (Backend Already Has This)

**File**: `portal_config.yaml`

```yaml
portal:
  name: "ScheduleZero"
  version: "1.0.0"
  # Point to built frontend assets
  portal_root: "../schedule-zero-islands/dist/portal1"

microsites:
  - id: "sz_dash"
    name: "Dashboard"
    icon: "📊"
    path: "/dash"
    url_prefix: "/dash"
    enabled: true
    microsite_type: "htmx"
    description: "System overview and statistics"
    routes_module: "schedule_zero.microsites.sz_dash.handlers"

  - id: "sz_schedules"
    name: "Schedules"
    icon: "📅"
    path: "/schedules"
    url_prefix: "/schedules"
    enabled: true
    microsite_type: "htmx"
    routes_module: "schedule_zero.microsites.sz_schedules.handlers"

  - id: "sz_handlers"
    name: "Handlers"
    icon: "⚙️"
    path: "/handlers"
    url_prefix: "/handlers"
    enabled: true
    microsite_type: "htmx"
    routes_module: "schedule_zero.microsites.sz_handlers.handlers"

component_library:
  - htmx
  - web-components

theme:
  css_variables:
    primary_color: "#1976D2"
    secondary_color: "#424242"
    accent_color: "#FF5722"
    background: "#FFFFFF"
    text_color: "#212121"
  stylesheet: "/static/css/theme.css"
  component_styles:
    sz-nav: "/static/css/components/sz-nav.css"
```

### Backend Layout (Already Implemented)

**File**: `src/schedule_zero/portal/templates/layout.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}ScheduleZero{% end %}</title>
    <link rel="stylesheet" href="/static/css/theme.css">
    {% block head %}{% end %}
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <!-- YOUR COMPONENT HERE -->
    <sz-nav 
        config-url="/api/portal/config" 
        current-path="{{ handler.request.path }}">
    </sz-nav>
    
    <main id="content" role="main">
        {% block content %}{% end %}
    </main>
    
    <!-- YOUR COMPONENT HERE -->
    <sz-flash></sz-flash>
    
    <!-- LOAD YOUR COMPONENTS -->
    <script type="module" src="/static/js/components/sz-nav.min.js"></script>
    <script type="module" src="/static/js/components/sz-flash.min.js"></script>
    
    <script>
        // Update nav after HTMX swap
        document.body.addEventListener('htmx:afterSwap', (event) => {
            const nav = document.querySelector('sz-nav');
            if (nav && event.detail.target.id === 'content') {
                nav.setAttribute('current-path', window.location.pathname);
            }
        });
    </script>
    
    {% block scripts %}{% end %}
</body>
</html>
```

---

## Testing Workflow

### 1. Backend Running
```bash
cd schedule-zero
poetry run python -m schedule_zero.server
# Listening on http://localhost:8888
```

### 2. Frontend Development
```bash
cd schedule-zero-islands
npm run dev
# Vite dev server on http://localhost:3000
```

### 3. CORS Testing
```bash
# Test portal config API with CORS
curl http://localhost:8888/api/portal/config \
  -H "Origin: http://localhost:3000" \
  -H "HX-Request: true" \
  -v

# Should see:
# Access-Control-Allow-Origin: *
# Access-Control-Expose-Headers: HX-Trigger, HX-Redirect, ...
```

### 4. Component Testing
```javascript
// In browser console at http://localhost:3000
fetch('http://localhost:8888/api/portal/config')
  .then(r => r.json())
  .then(config => console.log('Portal config:', config));

// Should work without CORS errors
```

---

## Deliverables

1. ✅ `sz-nav.min.js` - Navigation component with HTMX integration
2. ✅ `sz-flash.min.js` - Flash message component
3. ✅ TypeScript definitions in `src/components/`
4. ✅ Component styles (Shadow DOM or external CSS)
5. ✅ Build script that outputs to `dist/components/`
6. ✅ README with usage examples

---

## Success Criteria

- ✅ `sz-nav` fetches `/api/portal/config` without CORS errors
- ✅ Navigation renders with icons and labels from config
- ✅ Clicking nav links triggers HTMX (no full page reload)
- ✅ Active route is highlighted
- ✅ Browser URL updates on navigation
- ✅ `sz-flash` shows messages from server `HX-Trigger` header
- ✅ Components work with backend at `http://localhost:8888`
- ✅ Components are minified and production-ready

---

## Architecture Notes

**Backend Ready** ✅:
- `/api/portal/config` endpoint with CORS
- HTMX-aware handlers (full page vs partial)
- Layout template with component placeholders
- Dashboard microsite with stats

**Frontend Needed** 🔴:
- `sz-nav` web component (TypeScript)
- `sz-flash` web component (TypeScript)
- Build configuration (Vite)
- Output to `dist/components/`

**No Backend Changes Needed** - The backend is ready and waiting for your components!

---

## Reference

- **HTMX Docs**: https://htmx.org/docs/
- **Web Components**: https://developer.mozilla.org/en-US/docs/Web/Web_Components
- **Backend CORS Config**: `schedule-zero/docs/CORS_CONFIGURATION.md`
- **Backend Integration**: `schedule-zero/docs/BACKEND_INTEGRATION_PROMPT.md`

Build these two components and the portal will come alive! 🚀
