# APScheduler Fork Development Setup

**Instructions for setting up a separate ScheduleZero instance that uses your APScheduler fork for testing/development.**

## Overview

**Keep two separate ScheduleZero instances:**

1. **Main/Stable** (current `feature/fe-htmx-and-vuetify`)
   - Uses PyPI APScheduler release
   - Stable, working UI development
   - Don't break this

2. **APScheduler Dev** (new fork or branch)
   - Uses your APScheduler fork (master branch)
   - Test bed for bleeding edge features
   - Experimental, can break

## Setup Instructions

### Option 1: Separate Fork (Recommended)

**1. Fork ScheduleZero repo on GitHub:**
```
Original: esotericbyte/ScheduleZero
New fork: esotericbyte/ScheduleZero-APScheduler-Dev
```

**2. Clone the fork to separate directory:**
```powershell
cd C:\Users\johnl\windev\
git clone https://github.com/esotericbyte/ScheduleZero-APScheduler-Dev schedulezero-apscheduler-dev
cd schedulezero-apscheduler-dev
```

**3. Update `pyproject.toml` to use APScheduler fork:**
```toml
[tool.poetry.dependencies]
python = "^3.12"
# Use your APScheduler fork instead of PyPI release
apscheduler = {git = "https://github.com/YOUR_USERNAME/apscheduler.git", branch = "master"}
# Or if you have it locally:
# apscheduler = {path = "../apscheduler", develop = true}

tornado = "^6.4"
pyzmq = "^26.0.0"
# ... rest of dependencies
```

**4. Install dependencies:**
```powershell
poetry install
```

### Option 2: Separate Branch (Alternative)

**If you prefer single repo with branches:**

```powershell
# In current ScheduleZero repo
git checkout -b dev/apscheduler-fork

# Update pyproject.toml (same as above)
poetry lock --no-update
poetry install

# Switch back to stable when needed
git checkout feature/fe-htmx-and-vuetify
```

**Problem with this approach:**
- Poetry lock file conflicts between branches
- Need to reinstall dependencies when switching
- Easy to accidentally commit fork config to stable branch

**Recommendation: Use separate directory/fork**

## APScheduler Fork Setup

**1. Fork APScheduler on GitHub:**
```
Original: agronholm/apscheduler
Your fork: YOUR_USERNAME/apscheduler
```

**2. Clone locally:**
```powershell
cd C:\Users\johnl\windev\
git clone https://github.com/YOUR_USERNAME/apscheduler.git
cd apscheduler
```

**3. Add upstream remote:**
```powershell
git remote add upstream https://github.com/agronholm/apscheduler.git
git fetch upstream
```

**4. Keep fork synced with upstream:**
```powershell
git checkout master
git pull upstream master
git push origin master
```

## Using Local APScheduler Development

**If you want to modify APScheduler and test in ScheduleZero immediately:**

```toml
# pyproject.toml
[tool.poetry.dependencies]
# Point to local APScheduler checkout
apscheduler = {path = "../apscheduler", develop = true}
```

**Benefits:**
- Edit APScheduler code
- Changes immediately available in ScheduleZero
- No need to push/pull between repos

**Install:**
```powershell
cd C:\Users\johnl\windev\schedulezero-apscheduler-dev
poetry install
```

## Directory Structure

```
C:\Users\johnl\windev\
├── schedule-zero\               # Stable development
│   ├── pyproject.toml           # Uses PyPI APScheduler
│   └── ...
│
├── schedulezero-apscheduler-dev\  # Fork for APScheduler testing
│   ├── pyproject.toml           # Uses APScheduler fork/local
│   └── ...
│
└── apscheduler\                 # Your APScheduler fork
    ├── src\
    ├── tests\
    └── ...
```

## Workflow

### Working on Stable Features
```powershell
cd C:\Users\johnl\windev\schedule-zero
# Use PyPI APScheduler
# Safe, predictable
```

### Testing APScheduler Changes
```powershell
cd C:\Users\johnl\windev\schedulezero-apscheduler-dev
# Uses your APScheduler fork
# Test edge cases, new features
```

### Contributing to APScheduler
```powershell
cd C:\Users\johnl\windev\apscheduler

# Make changes
git checkout -b feature/zmq-replication
# ... edit code ...

# Test in ScheduleZero
cd ../schedulezero-apscheduler-dev
poetry install  # Picks up APScheduler changes
poetry run python -m schedule_zero.tornado_app_server

# If tests pass, push to your fork
cd ../apscheduler
git push origin feature/zmq-replication

# Open PR to upstream (agronholm/apscheduler)
```

## pyproject.toml Examples

### Stable (PyPI Release)
```toml
[tool.poetry.dependencies]
python = "^3.12"
apscheduler = "^4.0.0"  # From PyPI
tornado = "^6.4"
pyzmq = "^26.0.0"
```

### Fork Development (Git)
```toml
[tool.poetry.dependencies]
python = "^3.12"
apscheduler = {git = "https://github.com/YOUR_USERNAME/apscheduler.git", branch = "master"}
tornado = "^6.4"
pyzmq = "^26.0.0"
```

### Local Development (Path)
```toml
[tool.poetry.dependencies]
python = "^3.12"
apscheduler = {path = "../apscheduler", develop = true}
tornado = "^6.4"
pyzmq = "^26.0.0"
```

### Mixed (Stable + Optional Fork)
```toml
[tool.poetry.dependencies]
python = "^3.12"
apscheduler = "^4.0.0"  # Default: PyPI
tornado = "^6.4"
pyzmq = "^26.0.0"

[tool.poetry.group.dev.dependencies]
# Override APScheduler for dev testing
apscheduler = {git = "https://github.com/YOUR_USERNAME/apscheduler.git", branch = "master"}
```

## Testing Workflow

**1. Run APScheduler test bed against fork:**
```powershell
cd C:\Users\johnl\windev\schedulezero-apscheduler-dev

# Run temporal resolution tests
poetry run pytest tests/apscheduler_testbed/test_temporal_resolution.py

# Run schedule storm tests
poetry run pytest tests/apscheduler_testbed/test_schedule_storms.py

# Run all test bed scenarios
poetry run python tests/apscheduler_testbed/runner.py
```

**2. Compare results with stable:**
```powershell
cd C:\Users\johnl\windev\schedule-zero

# Run same tests against PyPI APScheduler
poetry run pytest tests/apscheduler_testbed/
```

**3. Document findings:**
- Performance differences
- Bug discoveries
- New features validated
- Edge case behavior

## Safety Checklist

Before setting up fork development:

- [ ] Current stable branch is committed and pushed
- [ ] No uncommitted changes in working directory
- [ ] Tests pass on stable branch
- [ ] Backup database files (if any)
- [ ] Separate directory for fork work
- [ ] Clear documentation of which instance is which
- [ ] Different ports for each instance (8888 vs 8889)

## Port Configuration

**Run both instances simultaneously:**

```yaml
# schedule-zero/config.yaml (stable)
server:
  port: 8888

# schedulezero-apscheduler-dev/config.yaml (fork)
server:
  port: 8889
```

**Access:**
- Stable: http://localhost:8888/
- Fork dev: http://localhost:8889/

## When to Use Each

**Use stable (`schedule-zero`):**
- Dashboard development
- UI/UX work
- ZMQ bug fixes
- Documentation
- Production testing

**Use fork dev (`schedulezero-apscheduler-dev`):**
- APScheduler edge case testing
- Performance benchmarks
- New APScheduler features
- Replication experiments
- Upstream contributions

## Summary

**DO:**
- ✅ Keep stable and fork dev completely separate
- ✅ Use different directories
- ✅ Use different ports
- ✅ Document which APScheduler version each uses
- ✅ Test in fork dev before merging to stable

**DON'T:**
- ❌ Switch APScheduler dependency on stable branch
- ❌ Mix fork and PyPI in same instance
- ❌ Forget which instance you're in
- ❌ Commit fork-specific config to stable branch

## Next Steps

When you're ready to set up fork development:

1. Decide: separate fork or local branch?
2. Fork APScheduler repo (if not already done)
3. Clone to new directory
4. Update pyproject.toml
5. Run `poetry install`
6. Verify separate instances work
7. Start testing APScheduler edge cases
