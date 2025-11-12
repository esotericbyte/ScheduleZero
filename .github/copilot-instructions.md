# GitHub Copilot Instructions for ScheduleZero

## Critical Rules

### Process Management - ABSOLUTE RULES
**NEVER EVER use `Stop-Process -Name python` or kill all Python processes!**
- This is EXTREMELY DANGEROUS and will kill ALL Python processes on the system
- This can destroy the user's other work, Jupyter notebooks, other projects, etc.
- This is a TRUST violation - the user will stop trusting you if you do this

**Proper Process Management:**
- Use PID files: Store process IDs in `deployments/{deployment}/pids/` directory
- PID file format: `{service}.pid` (e.g., `server.pid`, `handler.pid`)
- Only kill processes whose PIDs are in OUR pid files
- Always check if process is actually ours before killing
- ALWAYS ask user before killing ANY process
- Use `Get-Process -Id $pid` to check specific process, not all processes

### Testing
- Tests in this project can be flaky due to timing and ZMQ socket state issues
- If tests fail intermittently, it may not indicate a code problem
- Clean up test artifacts (database files, test outputs) between test runs
- **90-second crash was test artifact** - system proven stable for 19+ hours in production

### APScheduler 4.x
- MUST use `async with scheduler:` context manager
- Cannot call scheduler methods without the context manager
- Database URL must be `sqlite+aiosqlite:///` for async support
- Requires `AsyncJobExecutor()` configured
- Must call `await scheduler.start_in_background()` to actually process schedules

## Project Structure
- Python project using Poetry for dependency management
- ZeroMQ for handler communication
- Tornado for web server
- APScheduler 4.x for job scheduling
- Structured logging with custom logger
- Multi-deployment support (default, production, clock, test)

## Discord Integration

### Architecture Options

**1. Cog + Sprocket Architecture (RECOMMENDED for most bots)** 🏆
- Handler loads as Discord cog with dynamic sprocket system
- Sprockets are pluggable cogs that register job methods
- Can load/unload job handlers without restarting bot
- Best for: Organized, modular Discord bots
- Files: `examples/cogs/schedulezero_cog.py`, `examples/cogs/sprockets/*.py`
- Docs: `examples/COG_SPROCKET_ARCHITECTURE.md`

**2. Standalone Threaded Handler (Recommended by Gemini)**
- Separate thread with sync ZMQ, uses `asyncio.run_coroutine_threadsafe()`
- Better isolation, can't block Discord event loop
- Best for: Simple bots, single-purpose handlers
- File: `examples/discord_handler_threaded.py`

**3. Asyncio Task Handler**
- Handler runs in same event loop as bot
- Simpler code, direct awaits
- Best for: Small/personal bots
- File: `examples/discord_handler.py`

See `examples/DISCORD_INTEGRATION_COMPARISON.md` for standalone handler comparison.

### Cog Architecture Benefits
- ✅ Dynamic loading/unloading of job modules (sprockets)
- ✅ Organized by functionality (announcements, moderation, custom)
- ✅ Handler thread managed by cog lifecycle
- ✅ Native Discord cog pattern that Discord devs understand
- ✅ Sprockets can include slash commands for scheduling
- ✅ Easy to share and reuse sprockets across bots

## Frontend Architecture

### Islands of Interactivity + HTMX + Vuetify

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

### Component Development

**Separate JS Project:** `schedulezero-islands`
- Vanilla JS components in `src/vanilla/`
- Vuetify components in `src/vuetify/`
- Built with Vite, output to `dist/`
- Copied to Python repo's `microsites/*/assets/js/`

**Python Repo:** Treats components as opaque assets
- No JS build tooling in Python repo
- Components pre-built and vendored
- LLM only sees Python context, no JS

### Decision Tree

```
Need interactivity?
├─ Simple form/button/link? → HTMX attributes
├─ Real-time updates? → Vanilla JS Island
├─ Complex table? → Vuetify Island (v-data-table)
└─ Complex form? → Vuetify Island (v-form)
```

### Microsite Structure

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

See `docs/FRONTEND_ARCHITECTURE.md` and `docs/COMPONENT_SPECS.md` for details.
