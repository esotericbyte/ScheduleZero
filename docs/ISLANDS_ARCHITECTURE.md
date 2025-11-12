# Islands of Interactivity Architecture

## Overview

ScheduleZero uses an **Islands Architecture** where most content is server-rendered static HTML, with small "islands" of interactivity provided by Web Components.

## Principles

1. **Server renders HTML** - Tornado templates generate most of the page
2. **Islands hydrate independently** - Only interactive parts load JavaScript
3. **Progressive enhancement** - Works without JavaScript, better with it
4. **Minimal client-side code** - Each island is ~50 lines or less

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│         Tornado Server (Python)              │
│  ┌─────────────────────────────────────┐   │
│  │   Template: dashboard.html           │   │
│  │  (Server-rendered HTML)              │   │
│  └─────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │ Sends HTML
                   ▼
┌─────────────────────────────────────────────┐
│           Browser (Client)                   │
│  ┌──────────────────────────────────────┐  │
│  │  Static HTML (rendered immediately)   │  │
│  │  ┌─────────────────────────────────┐ │  │
│  │  │ <schedule-countdown> ISLAND     │ │  │
│  │  │ (Loads countdown.js ~30 lines)  │ │  │
│  │  └─────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────┐ │  │
│  │  │ <delete-button> ISLAND          │ │  │
│  │  │ (Loads delete-button.js ~25 LOC)│ │  │
│  │  └─────────────────────────────────┘ │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Example: Dashboard Schedule Card

### Server Template (Tornado)

```html
<!-- dashboard.html - Server-rendered -->
<div class="schedule-card">
    <div class="card-header">
        <h3>{{ schedule.job_id }}</h3>
        <span class="status">{{ schedule.status }}</span>
    </div>
    <div class="card-body">
        <!-- ISLAND: Interactive countdown -->
        <schedule-countdown next-run="{{ schedule.next_run }}">
        </schedule-countdown>
    </div>
    <div class="card-actions">
        <!-- ISLAND: Delete button -->
        <delete-button job-id="{{ schedule.job_id }}">
        </delete-button>
    </div>
</div>
```

### Island Component (Client-side)

```javascript
// schedule-countdown.js - ~30 lines
class ScheduleCountdown extends HTMLElement {
    connectedCallback() {
        const nextRun = new Date(this.getAttribute('next-run'));
        setInterval(() => {
            const diff = nextRun - Date.now();
            this.textContent = formatDuration(diff);
        }, 1000);
    }
}
customElements.define('schedule-countdown', ScheduleCountdown);
```

## Benefits

✅ **Fast initial load** - HTML renders immediately, no JavaScript blocking  
✅ **SEO-friendly** - Real HTML content, not client-rendered  
✅ **Resilient** - Static content works even if JS fails  
✅ **Minimal payload** - Only load JS for interactive parts  
✅ **LLM-friendly** - Small, independent components with clear boundaries

## When to Create an Island

Create a new island Web Component when you need:

- **Real-time updates** (countdowns, live data polling)
- **User interactions** (forms, buttons with complex logic)
- **Client-side state** (toggles, filters, sorting)
- **Animations** (transitions, loading states)

DON'T create an island for:

- **Static content** (headings, paragraphs, labels)
- **Simple links** (navigation)
- **Server actions** (HTMX handles this without custom JS)

## File Structure

```
microsites/
  sz-dash/
    templates/
      dashboard.html          # Server-rendered HTML with island placeholders
    assets/
      css/
        dashboard.css         # Styles for static HTML
      js/
        components/
          schedule-countdown.js   # ~30 LOC island
          delete-button.js        # ~25 LOC island
```

## HTMX Integration

Islands work seamlessly with HTMX:

```html
<!-- Server renders this -->
<delete-button 
    job-id="chime"
    endpoint="/api/schedules/chime">
</delete-button>
```

```javascript
// Island adds HTMX attributes
class DeleteButton extends HTMLElement {
    connectedCallback() {
        const button = document.createElement('button');
        button.setAttribute('hx-delete', this.getAttribute('endpoint'));
        button.setAttribute('hx-confirm', `Delete '${this.getAttribute('job-id')}'?`);
        this.appendChild(button);
        htmx.process(button);  // Tell HTMX about new element
    }
}
```

## Performance Metrics

### Traditional SPA (React/Vue)
- **Initial load**: 300-500KB JavaScript
- **Time to interactive**: 2-4 seconds
- **Hydration**: Full page re-render

### Islands Architecture (ScheduleZero)
- **Initial load**: 14KB HTMX + ~2KB per island
- **Time to interactive**: <500ms
- **Hydration**: Only interactive components

## References

- [Islands Architecture (patterns.dev)](https://www.patterns.dev/posts/islands-architecture/)
- [Astro Islands](https://docs.astro.build/en/concepts/islands/)
- [HTMX + Web Components](https://htmx.org/essays/web-components/)
