# GitHub Copilot Instructions for ScheduleZero

## Critical Rules

### README.md
**WE ARE NOT ADDING DETAILS TO THE README!**
- ask for agreement before making changes
- Keep README.md concise
- Do not add verbose explanations
- Do not expand documentation in README
- README is a brief high-level overview

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
- Clean up test artifacts (database files, test outputs) between test runs

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

## Frontend Architecture
- **Architecture:** Islands of Interactivity (HTMX + Vanilla JS + Vuetify)
- **Decision tree:** Simple interactions → HTMX; Real-time updates → Vanilla JS; Complex tables/forms → Vuetify
- **Microsites:** `_container/` (shared chrome), `sz-dash/`, `sz-schedules/`, `sz-handlers/`, `mkdocs/`
- **Full details:** See `docs/frontend-architecture.md` when working on frontend code
