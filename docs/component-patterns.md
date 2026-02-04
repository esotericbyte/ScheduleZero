# Web Component Patterns for ScheduleZero

## Component Design Principles

All ScheduleZero Web Components follow these principles:

1. **Islands Architecture** - Components are self-contained islands in server-rendered HTML
2. **Progressive Enhancement** - Work without JavaScript (graceful degradation)
3. **HTMX Integration** - Cooperate with HTMX for server interactions
4. **Configuration-Driven** - Use HTML attributes for configuration
5. **Event-Based Communication** - Emit custom events for parent interaction

## Component Types

### Type 1: Vanilla JavaScript Components

**Use for:** Lightweight utilities, simple UI enhancements

**Example:** `copy-button.js`
```javascript
class CopyButton extends HTMLElement {
  connectedCallback() {
    this.addEventListener('click', this.handleCopy);
  }
  
  handleCopy() {
    const text = this.getAttribute('data-copy');
    navigator.clipboard.writeText(text);
    this.dispatchEvent(new CustomEvent('copied', { bubbles: true }));
  }
}

customElements.define('copy-button', CopyButton);
```

**Usage:**
```html
<copy-button data-copy="some text">Copy</copy-button>
```

### Type 2: TypeScript with Shadow DOM

**Use for:** Complex components needing encapsulation (like navigation)

**Example:** `sz-nav.ts`
```typescript
class SzNav extends HTMLElement {
  private shadow: ShadowRoot;
  private config?: PortalConfig;
  
  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
  }
  
  async connectedCallback() {
    const configUrl = this.getAttribute('config-url');
    await this.loadConfig(configUrl);
    this.render();
  }
  
  private async loadConfig(url: string) {
    const response = await fetch(url);
    this.config = await response.json();
  }
  
  private render() {
    this.shadow.innerHTML = `
      <style>
        nav { /* styles */ }
      </style>
      <nav>
        ${this.config.microsites.map(ms => `
          <a href="${ms.path}" 
             hx-get="${ms.path}"
             hx-target="#content"
             hx-push-url="true">
            ${ms.icon} ${ms.name}
          </a>
        `).join('')}
      </nav>
    `;
    
    // Make HTMX aware of new elements
    if (window.htmx) {
      window.htmx.process(this.shadow);
    }
  }
}

customElements.define('sz-nav', SzNav);
```

**Usage:**
```html
<sz-nav config-url="/api/portal/config" current-path="/dash"></sz-nav>
```

### Type 3: Vue + Vuetify Components

**Use for:** Data grids, forms, complex interactive UIs

**Example:** `schedule-grid.js`
```javascript
import { createApp, h } from 'vue';
import { createVuetify } from 'vuetify';

class ScheduleGrid extends HTMLElement {
  connectedCallback() {
    const app = createApp({
      data() {
        return {
          schedules: [],
          loading: true
        };
      },
      async mounted() {
        const endpoint = this.$el.getAttribute('api-endpoint');
        this.schedules = await this.fetchSchedules(endpoint);
        this.loading = false;
      },
      methods: {
        async fetchSchedules(endpoint) {
          const response = await fetch(endpoint);
          return response.json();
        },
        handleEdit(schedule) {
          this.$el.dispatchEvent(new CustomEvent('schedule:edit', {
            detail: { schedule_id: schedule.job_id },
            bubbles: true
          }));
        }
      },
      render() {
        return h('v-data-table', {
          items: this.schedules,
          loading: this.loading,
          headers: [
            { text: 'Job ID', value: 'job_id' },
            { text: 'Handler', value: 'handler' },
            { text: 'Status', value: 'status' }
          ],
          onRowClick: (item) => this.handleEdit(item)
        });
      }
    });
    
    app.use(createVuetify());
    app.mount(this);
  }
}

customElements.define('schedule-grid', ScheduleGrid);
```

**Usage:**
```html
<schedule-grid api-endpoint="/api/schedules"></schedule-grid>
<script>
  document.querySelector('schedule-grid').addEventListener('schedule:edit', (e) => {
    htmx.ajax('GET', `/schedules/edit/${e.detail.schedule_id}`, '#content');
  });
</script>
```

## HTMX Integration Patterns

### Pattern 1: Component Emits Event, HTMX Handles Request

**Component:**
```javascript
this.dispatchEvent(new CustomEvent('action:needed', {
  detail: { id: 123 },
  bubbles: true
}));
```

**Template:**
```html
<schedule-grid id="grid"></schedule-grid>
<script>
  document.getElementById('grid').addEventListener('action:needed', (e) => {
    htmx.ajax('POST', '/api/action', {
      target: '#result',
      values: { id: e.detail.id }
    });
  });
</script>
```

### Pattern 2: Component Contains HTMX Elements

**Component creates elements with HTMX attributes:**
```javascript
const button = document.createElement('button');
button.textContent = 'Load More';
button.setAttribute('hx-get', '/api/more');
button.setAttribute('hx-target', '#results');
this.appendChild(button);

// Tell HTMX about new element
if (window.htmx) {
  window.htmx.process(button);
}
```

### Pattern 3: Component Responds to HTMX Events

**Listen for HTMX lifecycle events:**
```javascript
document.body.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target.id === 'content') {
    // Content was swapped, maybe update component state
    this.refresh();
  }
});
```

## Configuration API Pattern

For complex components that need server configuration:

**1. Define configuration structure:**
```typescript
interface ComponentConfig {
  endpoint: string;
  columns: string[];
  pageSize: number;
}
```

**2. Component fetches config:**
```typescript
async connectedCallback() {
  const configUrl = this.getAttribute('config-url') || '/api/component/config';
  const response = await fetch(configUrl);
  this.config = await response.json();
  this.render();
}
```

**3. Server provides config:**
```python
class ComponentConfigHandler(RequestHandler):
    def get(self):
        self.write({
            'endpoint': '/api/data',
            'columns': ['id', 'name', 'status'],
            'pageSize': 25
        })
```

**4. Usage:**
```html
<my-component config-url="/api/my-component/config"></my-component>
```

## Best Practices

### DO ✅

- Use Shadow DOM for encapsulation (especially navigation/chrome)
- Emit custom events for parent communication
- Use TypeScript for complex components
- Make components work with HTMX
- Provide sensible defaults (don't require all attributes)
- Use `htmx.process()` after creating HTMX elements dynamically

### DON'T ❌

- Don't use Shadow DOM for data components (breaks HTMX)
- Don't directly manipulate other components
- Don't make assumptions about page structure
- Don't bundle large dependencies (Vue/Vuetify) multiple times
- Don't forget to clean up event listeners in `disconnectedCallback()`

## Testing Components

### Unit Test Pattern
```javascript
describe('CopyButton', () => {
  let element;
  
  beforeEach(() => {
    element = document.createElement('copy-button');
    element.setAttribute('data-copy', 'test text');
    document.body.appendChild(element);
  });
  
  afterEach(() => {
    element.remove();
  });
  
  it('copies text to clipboard', async () => {
    const spy = jest.spyOn(navigator.clipboard, 'writeText');
    element.click();
    expect(spy).toHaveBeenCalledWith('test text');
  });
});
```

### Integration Test Pattern
```python
def test_component_with_backend():
    response = fetch('/dash')
    assert '<schedule-grid' in response.body
    
    # Simulate component API call
    api_response = fetch('/api/schedules')
    data = json.loads(api_response.body)
    assert 'schedules' in data
```

## Component Lifecycle

```
Constructor → connectedCallback → render → user interaction → events → disconnectedCallback
     ↓              ↓                 ↓           ↓              ↓            ↓
 Create shadow   Fetch config   Update DOM   Handle events  Notify parent  Cleanup
```

## TypeScript Definitions

Always provide TypeScript definitions:

```typescript
// src/types/components.d.ts
interface ScheduleGridElement extends HTMLElement {
  'api-endpoint'?: string;
  refresh(): void;
  addEventListener(
    type: 'schedule:edit',
    listener: (event: CustomEvent<{ schedule_id: string }>) => void
  ): void;
}

declare global {
  interface HTMLElementTagNameMap {
    'schedule-grid': ScheduleGridElement;
  }
}
```

This enables autocomplete and type checking when using components.
