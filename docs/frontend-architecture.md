# Frontend Architecture

## Islands of Interactivity + HTMX + Vuetify

**Layer 1: Server-Rendered HTML (Tornado)**
- Primary content delivery
- SEO-friendly, fast initial load
- Templates in `microsites/*/templates/`

**Layer 2: HTMX (Declarative Interactivity)**
- Forms, buttons, navigation without page reloads
- 14KB library, no build step
- Use for: Simple interactions, form submissions, content updates

**Layer 3: Vanilla JS Islands (Minimal Client State)**
- Small Web Components (~20 LOC each)
- No framework, pure vanilla JS
- Use for: Countdowns, live status, copy buttons
- Examples: `schedule-countdown.js`, `connection-status.js`

**Layer 4: Vuetify Islands (Complex UI)**
- Vue 3 + Vuetify Material Design components
- Use for: Data grids (sort/filter/page), rich forms
- Built in separate `schedulezero-islands` repo
- Copied to Python repo as opaque `.min.js` assets

## Component Development

**Separate JS Project:** `schedulezero-islands`
- Vanilla JS components in `src/vanilla/`
- Vuetify components in `src/vuetify/`
- Built with Vite, output to `dist/`
- Copied to Python repo's `microsites/*/assets/js/`

**Python Repo:** Treats components as opaque assets
- No JS build tooling in Python repo
- Components pre-built and vendored
- LLM only sees Python context, no JS

## Decision Tree

```
Need interactivity?
├─ Simple form/button/link? → HTMX attributes
├─ Real-time updates? → Vanilla JS Island
├─ Complex table? → Vuetify Island (v-data-table)
└─ Complex form? → Vuetify Island (v-form)
```

## Microsite Structure

```
microsites/
  _container/          # Shared chrome (nav, layout)
  sz-dash/            # Dashboard microsite
  sz-schedules/       # Schedule management
  sz-handlers/        # Handler registry
  mkdocs/             # Documentation
```

Each microsite:
- Independent routes, templates, assets
- Registered in `microsites/__init__.py`
- Loaded by `tornado_app_server.py`

See `docs/FRONTEND_ARCHITECTURE.md` and `docs/COMPONENT_SPECS.md` for full details.
