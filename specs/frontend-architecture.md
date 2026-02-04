# ScheduleZero Frontend Architecture

## Overview

**Islands of Interactivity + HTMX + Vuetify**

- **Server-first**: Tornado renders HTML
- **HTMX**: Handles most interactivity (forms, navigation, updates)
- **Vanilla JS Islands**: Small, focused Web Components (~20 LOC each)
- **Vuetify Islands**: Complex data grids and forms (Vue.js + Material Design)

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Server-Rendered HTML (Tornado Templates)       │
│ • Page structure, content, navigation                   │
│ • SEO-friendly, fast initial load                       │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: HTMX (Declarative Interactivity)              │
│ • Forms, buttons, navigation without page reloads       │
│ • Server communication via attributes                   │
│ • 14KB library, no build step                          │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Vanilla JS Islands (Minimal Client State)     │
│ • Countdowns, live status indicators                    │
│ • Copy buttons, time formatters                         │
│ • ~20 lines each, no framework                         │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Vuetify Islands (Complex UI)                  │
│ • Data grids (sort, filter, pagination)                │
│ • Rich forms with validation                            │
│ • Material Design components                            │
└─────────────────────────────────────────────────────────┘
```

---

## Component Inventory

### Vanilla JS Islands (6 components)

**Container** (`_container/assets/js/components/`)
- `sz-nav.js` - Navigation with HTMX integration ✅ Built
- `sz-flash.js` - Flash messages from HTMX response headers

**Dashboard** (`sz-dash/assets/js/components/`)
- `schedule-countdown.js` - Live countdown timer ✅ Built

**Handlers** (`sz-handlers/assets/js/components/`)
- `connection-status.js` - Live ZMQ connection ping

**Shared** (`shared/`)
- `delete-button.js` - Delete confirmation ✅ Built
- `copy-button.js` - Copy to clipboard with feedback

### Vuetify Islands (4 components)

**Schedules** (`sz-schedules/assets/js/islands/`)
- `schedule-grid.vue` - Sortable/filterable schedule table
- `schedule-form.vue` - Create/edit schedule form

**Handlers** (`sz-handlers/assets/js/islands/`)
- `handler-grid.vue` - Handler registry table

**Executions** (`sz-dash/assets/js/islands/`)
- `execution-log-grid.vue` - Execution history table

---

## Decision Tree: When to Use What?

```
Need interactivity?
  │
  ├─ Simple form/button/link?
  │   → Use HTMX attributes
  │
  ├─ Real-time updates (countdown, status)?
  │   → Vanilla JS Island (Web Component)
  │
  ├─ Complex table (sort/filter/page)?
  │   → Vuetify Island (v-data-table)
  │
  └─ Complex form (validation, multi-step)?
      → Vuetify Island (v-form)
```

---

## Example: Dashboard Page

```html
<!-- Tornado template: dashboard.html -->
{% extends "layout.html" %}

{% block content %}
<!-- Layer 1: Static HTML -->
<div class="dashboard">
    <h1>Dashboard</h1>
    
    <!-- Layer 2: HTMX - Refresh button -->
    <button hx-get="/api/schedules" 
            hx-target="#schedule-cards"
            hx-swap="innerHTML">
        Refresh
    </button>
    
    <div id="schedule-cards">
        {% for schedule in schedules %}
        <div class="schedule-card">
            <h3>{{ schedule.job_id }}</h3>
            
            <!-- Layer 3: Vanilla Island - Countdown -->
            <schedule-countdown next-run="{{ schedule.next_run }}">
            </schedule-countdown>
            
            <!-- Layer 2: HTMX - Delete button -->
            <button hx-delete="/api/schedules/{{ schedule.job_id }}"
                    hx-confirm="Delete?"
                    hx-target="closest .schedule-card">
                Delete
            </button>
        </div>
        {% end %}
    </div>
    
    <!-- Layer 4: Vuetify Island - Data grid -->
    <div id="execution-log"></div>
</div>
{% end %}

{% block microsite_js %}
<!-- Vanilla islands -->
<script src="/dash/static/js/components/schedule-countdown.js"></script>

<!-- Vuetify island -->
<script type="module">
import { createApp } from '/static/_container/js/vue.esm-browser.js'
import { createVuetify } from '/static/_container/js/vuetify.esm.js'
import ExecutionLogGrid from '/dash/static/js/islands/execution-log-grid.js'

createApp(ExecutionLogGrid, {
    executions: {{ executions|tojson }}
}).use(createVuetify()).mount('#execution-log')
</script>
{% end %}
```

---

## Separate JS Project Structure

```
schedulezero-islands/              # Separate Git repo
├── package.json
├── vite.config.js                 # Build config
├── src/
│   ├── vanilla/                   # Web Components (no framework)
│   │   ├── schedule-countdown.js
│   │   ├── connection-status.js
│   │   ├── delete-button.js
│   │   ├── copy-button.js
│   │   └── sz-flash.js
│   │
│   └── vuetify/                   # Vue SFCs
│       ├── schedule-grid.vue
│       ├── schedule-form.vue
│       ├── handler-grid.vue
│       └── execution-log-grid.vue
│
├── dist/                          # Built assets (copied to Python repo)
│   ├── vanilla/
│   │   ├── schedule-countdown.min.js
│   │   └── ...
│   └── vuetify/
│       ├── schedule-grid.js       # ESM module
│       └── ...
│
└── examples/                      # Component demos
    ├── schedule-countdown.html
    └── schedule-grid.html
```

---

## Integration with Python Repo

**Copy built assets:**
```bash
# In schedulezero-islands repo
npm run build

# Copy to Python repo
cp dist/vanilla/* ../schedule-zero/src/schedule_zero/microsites/_container/assets/js/components/
cp dist/vuetify/* ../schedule-zero/src/schedule_zero/microsites/sz-dash/assets/js/islands/
```

**Python treats them as opaque assets:**
```python
# No JS knowledge needed in Python repo
static_handlers.append((
    r"/dash/static/js/islands/(.*)",
    tornado.web.StaticFileHandler,
    {"path": "microsites/sz-dash/assets/js/islands"}
))
```

---

## Benefits Summary

✅ **Server-first** - Fast, SEO-friendly, works without JS  
✅ **Minimal JS** - Only load what you need per page  
✅ **No build step** (in Python repo) - Components are pre-built  
✅ **LLM-friendly** - Python repo has no JS context pollution  
✅ **Material Design** - Professional UI via Vuetify  
✅ **Testable** - JS components tested in separate repo  
✅ **Reusable** - Components can be used in other projects  

---

## Next Steps

1. ✅ Architecture defined
2. ⏳ Create component specifications
3. ⏳ Set up schedulezero-islands repo
4. ⏳ Build Vuetify islands
5. ⏳ Copy built assets to Python repo
6. ⏳ Update Tornado templates to use islands
