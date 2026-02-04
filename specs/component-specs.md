# Component Specifications

## Vanilla JS Islands

### schedule-countdown.js ✅ Built

**Purpose:** Display live countdown to next schedule execution

**Attributes:**
- `next-run` (required) - ISO 8601 datetime string

**Example:**
```html
<schedule-countdown next-run="2025-11-12T10:00:00Z"></schedule-countdown>
```

**Behavior:**
- Updates every second
- Shows format: "2h 15m 30s"
- When countdown reaches 0: Shows "Running..." with `.running` class

---

### connection-status.js

**Purpose:** Live ZMQ connection status indicator

**Attributes:**
- `handler-name` (required) - Handler identifier
- `endpoint` (required) - WebSocket/SSE endpoint for status updates

**Example:**
```html
<connection-status 
    handler-name="discord_handler"
    endpoint="/api/handlers/discord_handler/status">
</connection-status>
```

**Behavior:**
- Displays colored dot: 🟢 connected, 🔴 disconnected, 🟡 connecting
- Polls endpoint every 5 seconds
- Shows tooltip with last ping time

---

### delete-button.js ✅ Built

**Purpose:** Delete confirmation button with HTMX

**Attributes:**
- `job-id` (required) - Item to delete
- `endpoint` (required) - DELETE endpoint

**Example:**
```html
<delete-button 
    job-id="chime"
    endpoint="/api/schedules/chime">
</delete-button>
```

**Behavior:**
- Renders button with HTMX `hx-delete` attribute
- Shows confirmation dialog
- Removes parent card on success

---

### copy-button.js

**Purpose:** Copy text to clipboard with feedback

**Attributes:**
- `text` (required) - Text to copy
- `label` (optional) - Button label (default: "Copy")

**Example:**
```html
<copy-button text="tcp://localhost:5555" label="Copy Address"></copy-button>
```

**Behavior:**
- Copies to clipboard on click
- Shows "✓ Copied!" for 2 seconds
- Falls back to text selection if clipboard API unavailable

---

### sz-flash.js

**Purpose:** Flash messages from HTMX response headers

**Usage:**
```python
# Python: Set HX-Trigger header
self.set_header('HX-Trigger', json.dumps({
    'showFlash': {'message': 'Schedule created!', 'type': 'success'}
}))
```

```html
<!-- Add to layout.html -->
<script src="/static/_container/js/components/sz-flash.js"></script>
```

**Behavior:**
- Listens for `showFlash` event from HTMX
- Shows message at top-right for 3 seconds
- Types: `success`, `error`, `info`, `warning`
- Auto-dismiss with slide-out animation

---

## Vuetify Islands

### schedule-grid.vue

**Purpose:** Sortable, filterable schedule table

**Props:**
```typescript
interface Props {
  schedules: Array<{
    job_id: string
    next_run: string        // ISO datetime
    status: 'active' | 'paused'
    trigger: string
  }>
}
```

**Emits:**
- `edit(jobId: string)` - User clicked edit
- `delete(jobId: string)` - User clicked delete
- `refresh()` - User clicked refresh

**Example:**
```html
<div id="schedule-grid"></div>

<script type="module">
import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import ScheduleGrid from './schedule-grid.js'

createApp(ScheduleGrid, {
  schedules: {{ schedules|tojson }}
}).use(createVuetify()).mount('#schedule-grid')
</script>
```

**Features:**
- Search across all columns
- Sort by any column
- Pagination (25/50/100 per page)
- Live countdown in "Next Run" column
- Action buttons: Edit, Delete
- Refresh button in toolbar

---

### schedule-form.vue

**Purpose:** Create/edit schedule form

**Props:**
```typescript
interface Props {
  schedule?: {              // Optional: for editing
    job_id: string
    trigger: object
  }
  handlers: string[]        // Available handler names
}
```

**Emits:**
- `submit(schedule: object)` - Form submitted
- `cancel()` - User canceled

**Example:**
```html
<div id="schedule-form"></div>

<script type="module">
import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import ScheduleForm from './schedule-form.js'

createApp(ScheduleForm, {
  handlers: {{ handler_names|tojson }}
}).use(createVuetify()).mount('#schedule-form')
</script>
```

**Features:**
- Job ID field with validation
- Handler dropdown (autocomplete)
- Trigger type selector (Cron, Interval, Date)
- Dynamic trigger fields based on type
- Cron expression builder
- Client-side validation
- Submit/Cancel buttons

---

### handler-grid.vue

**Purpose:** Handler registry table

**Props:**
```typescript
interface Props {
  handlers: Array<{
    name: string
    address: string
    methods: string[]
    status: 'connected' | 'disconnected'
  }>
}
```

**Emits:**
- `test(handlerName: string)` - Test connection
- `unregister(handlerName: string)` - Unregister handler

**Example:**
```html
<div id="handler-grid"></div>

<script type="module">
import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import HandlerGrid from './handler-grid.js'

createApp(HandlerGrid, {
  handlers: {{ handlers|tojson }}
}).use(createVuetify()).mount('#handler-grid')
</script>
```

**Features:**
- Search by name or address
- Status indicator column (colored chip)
- Expandable rows showing available methods
- Action buttons: Test, Unregister
- Copy address button
- Auto-refresh every 10 seconds

---

### execution-log-grid.vue

**Purpose:** Job execution history table

**Props:**
```typescript
interface Props {
  executions: Array<{
    timestamp: string       // ISO datetime
    job_id: string
    status: 'success' | 'error'
    duration_ms: number
    output?: string
    error?: string
  }>
  pageSize?: number         // Default: 25
}
```

**Emits:**
- `view-details(execution: object)` - View full execution details

**Example:**
```html
<div id="execution-log"></div>

<script type="module">
import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import ExecutionLogGrid from './execution-log-grid.js'

createApp(ExecutionLogGrid, {
  executions: {{ executions|tojson }},
  pageSize: 50
}).use(createVuetify()).mount('#execution-log')
</script>
```

**Features:**
- Relative time column ("2 minutes ago")
- Status chip (green/red)
- Duration column (formatted ms)
- Search across all fields
- Filter by status
- Date range picker
- Expandable rows for output/error
- Export to CSV button
- Pagination

---

## Vuetify Components Used (As-Is)

These Vuetify components are used directly without customization:

### Data Display
- `v-data-table` - Tables with sort/filter/pagination
- `v-chip` - Status badges
- `v-icon` - Material Design icons
- `v-tooltip` - Hover tooltips

### Forms
- `v-form` - Form validation
- `v-text-field` - Text inputs
- `v-select` - Dropdowns
- `v-autocomplete` - Searchable dropdowns
- `v-btn` - Buttons
- `v-checkbox` - Checkboxes

### Feedback
- `v-snackbar` - Toast notifications
- `v-progress-circular` - Loading spinners
- `v-alert` - Alert messages

### Layout
- `v-card` - Content cards
- `v-toolbar` - Toolbars
- `v-spacer` - Layout spacer

---

## Component Development Guidelines

### Vanilla JS Islands
- **Keep it tiny** - Target ~20 lines
- **No dependencies** - Pure Web Components
- **Single responsibility** - One job per component
- **Progressive enhancement** - Works without JS when possible

### Vuetify Islands
- **Composition API** - Use `<script setup>`
- **TypeScript** - Type props and emits
- **Emit events** - Don't make HTTP calls directly
- **Responsive** - Test mobile layouts

### Testing
- **Vanilla** - Test in browser console
- **Vuetify** - Vitest unit tests
- **E2E** - Playwright for critical flows
