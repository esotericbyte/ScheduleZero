# Microsite Toolkit

## Overview

The ScheduleZero microsite architecture is a lightweight framework for building modular web portals with **Islands of Interactivity**. This toolkit could be extracted into the `schedule-zero-islands` project as a reusable framework.

## Architecture Components

### 1. Backend (Python/Tornado)

**Core Framework**: `src/schedule_zero/microsites/`

```
microsites/
├── __init__.py          # MicrositeRegistry, Microsite class
├── base.py              # MicrositeHandler base class
├── _container/          # Shared layout & navigation
│   ├── templates/
│   │   └── layout.html  # Bootstrap 5 base layout
│   └── assets/
│       ├── css/
│       └── js/
└── sz_dash/             # Example microsite
    ├── routes.py        # Tornado handlers
    ├── templates/       # Microsite-specific templates
    └── assets/          # Microsite-specific assets
```

**Key Classes**:
- `Microsite`: Configuration for a microsite (name, url_prefix, routes, assets)
- `MicrositeRegistry`: Central registry for all microsites
- `MicrositeHandler`: Base handler with HTMX-aware rendering

### 2. Frontend Stack

#### Base Layer: Bootstrap 5
- **Why**: Battle-tested, accessible, extensive components
- **CDN**: Fast loading, no build step for base styles
- **Usage**: Layout, navigation, cards, tables, forms

#### Interactivity Layers (Islands)

**Decision Tree**:
```
Need interaction?
├─ Simple link/form → HTMX
├─ Button click → Vanilla JS
└─ Complex table/form → Vue + Vuetify
```

**Layer 1: HTMX** (No JavaScript)
```html
<!-- Swap content without page reload -->
<a href="/schedules/" 
   hx-get="/schedules/" 
   hx-target="#content" 
   hx-push-url="true">
```

**Layer 2: Vanilla JS** (Web Components)
```javascript
// Simple, self-contained islands
class CopyButton extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `<button>Copy</button>`;
        this.onclick = () => navigator.clipboard.writeText(this.dataset.text);
    }
}
```

**Layer 3: Vue + Vuetify** (Complex Islands)
```vue
<!-- Data tables with sorting, filtering, pagination -->
<schedule-grid :schedules="data" @edit="handleEdit" />
```

### 3. Template System

**Tornado Templates**: Server-side HTML generation

```python
# Tornado template syntax
{% extends "../../_container/templates/layout.html" %}

{% block content %}
<h1>{{ title }}</h1>
{% for item in items %}
    <div>{{ item['name'] }}</div>
{% end %}
{% end %}
```

**Key Features**:
- Template inheritance
- Partial rendering for HTMX
- Dictionary access: `{{ dict['key'] }}` (not `dict.key`)

## Configuration

### Portal Config (`portal_config.yaml`)

```yaml
portal_name: "My Custom Portal"
portal_root: "src/my_portal"

microsites:
  - name: "Dashboard"
    url_prefix: "/dash"
    routes_module: "my_portal.microsites.dashboard.routes"
    templates_path: "microsites/dashboard/templates"
    assets_path: "microsites/dashboard/assets"
    enabled: true
```

### Route Registration

```python
# In your microsite routes.py
from ..base import MicrositeHandler

class MyHandler(MicrositeHandler):
    async def get(self):
        data = await self.fetch_data()
        self.render_microsite(
            'microsites/my_site/templates/page',
            data=data
        )

routes = [
    (r"/", MyHandler),
]
```

## Islands Strategy

### When to Use Each Layer

| Feature | HTMX | Vanilla JS | Vue+Vuetify |
|---------|------|------------|-------------|
| Page navigation | ✅ | ❌ | ❌ |
| Form submit | ✅ | ❌ | ❌ |
| Button click | ❌ | ✅ | ❌ |
| Copy to clipboard | ❌ | ✅ | ❌ |
| Flash messages | ❌ | ✅ | ❌ |
| Data table (sort/filter) | ❌ | ❌ | ✅ |
| Complex form validation | ❌ | ❌ | ✅ |
| Real-time updates | ❌ | ✅ | ✅ |

### Progressive Enhancement

1. **Start with HTMX**: No JavaScript, works everywhere
2. **Add Vanilla JS**: Simple interactions as needed
3. **Reach for Vue**: Only for complex components

## Extraction to schedule-zero-islands

### What Should Move

**Core Framework** (`microsites/` → `sz-islands/backend/`):
- `__init__.py` - MicrositeRegistry, Microsite
- `base.py` - MicrositeHandler
- `_container/` - Shared layout & components

**Frontend Components** (Already in schedule-zero-islands):
- Vue components (schedule-grid, handler-grid, etc.)
- Vanilla JS islands (copy-button, flash, etc.)
- Build pipeline (Vite config)

**Documentation**:
- This file
- Component patterns
- Integration guide

### What Stays in ScheduleZero

**Application-Specific**:
- `sz_dash/` - Dashboard microsite
- `sz_schedules/` - Schedules microsite
- `sz_handlers/` - Handlers microsite
- APScheduler integration
- ZMQ handler registry

### Integration Model

```python
# In ScheduleZero project
from sz_islands.backend import Microsite, MicrositeRegistry, MicrositeHandler
from sz_islands.frontend import build_components

# Define app-specific microsites
class DashboardHandler(MicrositeHandler):
    async def get(self):
        # App logic here
        pass

# Register with framework
registry = MicrositeRegistry()
registry.register(Microsite(
    name="Dashboard",
    url_prefix="/dash",
    routes=[...],
    assets_path="..."
))
```

## Benefits of Extraction

### For ScheduleZero
- Cleaner separation of framework vs application
- Easier to test core functionality
- Can use islands framework as a dependency

### For schedule-zero-islands
- Becomes a reusable framework
- Other projects can use the microsite pattern
- Clear API boundaries
- Independent versioning

### For Community
- Framework can be documented independently
- Examples become more generic
- Easier to contribute to framework vs app

## Migration Plan

1. **Phase 1**: Document current architecture (this file)
2. **Phase 2**: Extract core framework to schedule-zero-islands
3. **Phase 3**: Publish as `sz-islands` package
4. **Phase 4**: ScheduleZero depends on `sz-islands`

## Example Projects Using Framework

Potential users of extracted framework:
- **LogStream**: Log aggregation portal
- **AI Workflows**: ML pipeline management
- **Custom Dashboards**: Internal tools
- **Admin Panels**: CRUD interfaces with islands

Each would define microsites using the framework while keeping application logic separate.
