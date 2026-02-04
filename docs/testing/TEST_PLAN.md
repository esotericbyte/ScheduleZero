# ScheduleZero Comprehensive Test Plan

## Overview

This document outlines the testing strategy for ScheduleZero, including:
- Test categories and organization
- Test environment setup
- APScheduler 4.0.0a6 upgrade testing
- Component isolation and integration testing
- Discord bot testing
- Portal/API testing

## Current Test Status

### Existing Tests
- ✅ **Integration Tests**: `test_integration.py` - Governor, server lifecycle
- ✅ **Scheduled Jobs**: `test_scheduled_jobs.py` - Job execution, CRUD operations
- ✅ **Component Tests**: `test_component_manager.py`, `test_autonomous_handler.py`
- ✅ **ZMQ Tests**: `test_zmq_event_broker.py`, `test_zmq_recovery.py`
- ✅ **Governor Tests**: `test_governor.py`, `test_governor_abc.py`, `test_governor_signals.py`
- ⚠️ **Handler Tests**: `test_handler.py` - Needs APScheduler schema update
- ⚠️ **Date Trigger Tests**: `test_date_trigger_formats.py` - Schema issues

### Test Infrastructure
- ✅ **Fixtures**: `conftest.py` - Session fixtures for server/handler processes
- ✅ **Cleanup**: Database cleanup between test sessions
- ✅ **Output**: Test artifacts saved to `test_output/`
- ✅ **Logging**: Test logs saved to `test_logs/`

### Known Issues
- ❌ Database schema outdated (missing `metadata` column from APScheduler 4.0.0a6)
- ❌ Many tests failing due to schema mismatch
- ⚠️ No isolated component tests for portal/frontend
- ⚠️ No tests for Discord bot ZMQ listener cog

## Test Categories

### 1. Unit Tests (Component Isolation)
**Status**: Partially implemented, needs expansion

**Goal**: Test individual components in isolation without external dependencies

#### 1.1 Core Components
- [ ] `SQLAlchemyDataStore` initialization and methods
- [ ] `ZMQEventBroker` pub/sub functionality
- [ ] `JobExecutor` execution logic
- [ ] `RegistryManager` handler CRUD
- [ ] Trigger validation and parsing

#### 1.2 Portal Components (NEW - Missing)
- [ ] Tornado handlers (IndexHandler, ScheduleHandler, etc.)
- [ ] Template rendering
- [ ] Static asset serving
- [ ] Portal configuration loading
- [ ] Microsite routing

#### 1.3 Handler Components
- [ ] `ZMQHandlerBase` registration and lifecycle
- [ ] `AutonomousHandler` scheduling
- [ ] Method discovery and invocation
- [ ] Error handling and retries

### 2. Integration Tests
**Status**: Good coverage, needs schema update

**Goal**: Test component interactions and end-to-end workflows

#### 2.1 Server Integration
- [x] Server startup and shutdown
- [x] Handler registration
- [x] Job scheduling via API
- [ ] Job execution verification
- [ ] Schedule management (pause/resume/delete)

#### 2.2 ZMQ Communication
- [x] Handler-server communication
- [x] Event broker messaging
- [x] Connection recovery
- [ ] Multi-handler scenarios
- [ ] Load testing

#### 2.3 Scheduler Integration
- [ ] Job scheduling with various triggers
- [ ] Job execution and result tracking
- [ ] Schedule updates and deletions
- [ ] Concurrent job execution
- [ ] Job lease management (new in a6)

### 3. Functional Tests
**Status**: Needs expansion

**Goal**: Test complete user workflows from UI/API to execution

#### 3.1 API Workflows
- [ ] Schedule job via REST API
- [ ] Monitor job execution
- [ ] View execution history
- [ ] Handle job failures
- [ ] Update/delete schedules

#### 3.2 Portal Workflows (NEW - Missing)
- [ ] View dashboard
- [ ] Create schedule via UI
- [ ] View handlers list
- [ ] View schedules list
- [ ] View execution logs
- [ ] Navigate microsites

#### 3.3 Handler Workflows
- [ ] Handler registration
- [ ] Job execution with parameters
- [ ] Error handling and reporting
- [ ] Handler disconnection/reconnection

### 4. Discord Bot Tests (NEW - Missing)
**Status**: No tests exist

**Goal**: Test Discord bot integration with ZMQ listener

#### 4.1 ZMQ Listener Cog
- [ ] Cog loading and initialization
- [ ] ZMQ connection establishment
- [ ] Topic subscription
- [ ] Message reception and queueing
- [ ] Handler registration and dispatch
- [ ] Commands: `/zmq_status`, `/zmq_restart`

#### 4.2 Event Handling
- [ ] Job execution events
- [ ] Job failure events
- [ ] Handler registration events
- [ ] Scheduler events
- [ ] Custom event handlers

#### 4.3 Discord Integration
- [ ] Post notifications to channels
- [ ] Embed formatting
- [ ] Rate limiting handling
- [ ] Error recovery

### 5. Performance Tests
**Status**: Minimal coverage

**Goal**: Ensure system can handle expected load

#### 5.1 Load Tests
- [ ] Multiple concurrent jobs
- [ ] High-frequency scheduling
- [ ] Large parameter payloads
- [ ] Multiple handlers
- [ ] Database growth over time

#### 5.2 Stress Tests
- [ ] Handler disconnection scenarios
- [ ] Database failures
- [ ] Network interruptions
- [ ] Memory leaks
- [ ] Long-running processes

### 6. Upgrade Tests (APScheduler 4.0.0a6)
**Status**: Planned

**Goal**: Verify compatibility with new APScheduler version

#### 6.1 Schema Migration
- [ ] Database schema updates
- [ ] Existing data migration
- [ ] Backward compatibility

#### 6.2 API Changes
- [ ] `add_schedule()` parameter changes
- [ ] Task/Schedule attribute read-only enforcement
- [ ] New datastore methods (`extend_acquired_job_leases`, etc.)
- [ ] `task_defaults` parameter usage

#### 6.3 Regression Testing
- [ ] All existing tests pass
- [ ] No performance degradation
- [ ] Job execution reliability

## Test Organization

### Directory Structure
```
tests/
├── unit/                      # NEW - Unit tests
│   ├── test_datastore.py
│   ├── test_event_broker.py
│   ├── test_job_executor.py
│   ├── test_portal_handlers.py
│   └── test_triggers.py
├── integration/               # Existing integration tests (rename/move)
│   ├── test_integration.py
│   ├── test_scheduled_jobs.py
│   └── test_zmq_recovery.py
├── functional/                # NEW - End-to-end workflows
│   ├── test_api_workflows.py
│   ├── test_portal_workflows.py
│   └── test_handler_workflows.py
├── discord/                   # NEW - Discord bot tests
│   ├── test_zmq_listener_cog.py
│   ├── test_event_handlers.py
│   └── test_discord_integration.py
├── performance/               # NEW - Load/stress tests
│   ├── test_load.py
│   └── test_stress.py
├── fixtures/                  # Shared fixtures
│   ├── __init__.py
│   ├── server_fixtures.py
│   ├── handler_fixtures.py
│   └── discord_fixtures.py
├── conftest.py                # Pytest configuration
└── test_output/               # Test artifacts
```

## Branch Strategy for APScheduler Upgrade

### Recommendation: Create Feature Branch

```bash
# Create feature branch for upgrade
git checkout -b feature/apscheduler-4.0.0a6

# Track changes
git add pyproject.toml poetry.lock
git commit -m "Upgrade APScheduler to 4.0.0a6"

# Clean up old database
rm schedulezero_jobs.db
rm deployments/*/schedulezero_jobs.db

# Run tests
poetry run pytest tests/

# Commit fixes
git add -A
git commit -m "Fix tests for APScheduler 4.0.0a6"
```

### Merge Strategy
1. All tests pass on feature branch
2. Create PR for review
3. Merge to main after approval

## Test Execution Plan

### Phase 1: Project Cleanup (Week 1)
1. **Clean up repository**
   - [ ] Move archived files to `archive/`
   - [ ] Organize documentation in `docs/`
   - [ ] Remove obsolete files
   - [ ] Update `.gitignore`

2. **Create feature branch**
   - [ ] `git checkout -b feature/apscheduler-4.0.0a6`
   - [ ] Delete old databases
   - [ ] Commit clean slate

3. **Reorganize tests**
   - [ ] Create `tests/unit/`, `tests/integration/`, etc.
   - [ ] Move existing tests to appropriate directories
   - [ ] Update import paths

### Phase 2: Unit Tests (Week 2)
1. **Portal component tests**
   - [ ] Create `test_portal_handlers.py`
   - [ ] Test each Tornado handler
   - [ ] Mock scheduler/registry dependencies
   - [ ] Verify responses and error handling

2. **Core component tests**
   - [ ] Test datastore operations
   - [ ] Test event broker pub/sub
   - [ ] Test job executor logic
   - [ ] Test trigger parsing

### Phase 3: Integration Tests (Week 3)
1. **Fix existing tests**
   - [ ] Run integration tests
   - [ ] Fix schema-related failures
   - [ ] Update for APScheduler a6 changes
   - [ ] Verify all pass

2. **Expand coverage**
   - [ ] Add multi-handler tests
   - [ ] Add concurrent execution tests
   - [ ] Add schedule update/delete tests

### Phase 4: Discord Bot Tests (Week 4)
1. **Create Discord test fixtures**
   - [ ] Mock Discord bot
   - [ ] Mock ZMQ publisher
   - [ ] Test environment setup

2. **ZMQ listener tests**
   - [ ] Test cog loading
   - [ ] Test event reception
   - [ ] Test handler dispatch
   - [ ] Test commands

3. **Integration tests**
   - [ ] Test with live ScheduleZero server
   - [ ] Test event flow end-to-end

### Phase 5: Functional Tests (Week 5)
1. **API workflow tests**
   - [ ] Complete job lifecycle via API
   - [ ] Error scenarios
   - [ ] Edge cases

2. **Portal workflow tests**
   - [ ] UI navigation
   - [ ] Form submissions
   - [ ] Data display

### Phase 6: Performance Tests (Week 6)
1. **Load tests**
   - [ ] Concurrent job execution
   - [ ] High-frequency scheduling
   - [ ] Multiple handlers

2. **Stress tests**
   - [ ] Failure scenarios
   - [ ] Resource exhaustion
   - [ ] Recovery testing

## Test Data Management

### Fixtures
- **Server fixtures**: Start/stop server for tests
- **Handler fixtures**: Test handler with observable methods
- **Database fixtures**: Clean database state
- **Discord fixtures**: Mock Discord bot and channels

### Test Databases
- Use `test` deployment for testing
- Separate database: `deployments/test/schedulezero_jobs.db`
- Clean between test sessions
- Snapshot/restore for specific test scenarios

### Test Output
- Save to `tests/test_output/`
- Include in `.gitignore`
- Preserve for debugging failures
- Clean up successful runs

## Success Criteria

### Phase 1-2: Component Testing
- [ ] All unit tests pass
- [ ] 80%+ code coverage for core components
- [ ] Portal handlers fully tested

### Phase 3: Integration Testing
- [ ] All integration tests pass
- [ ] No schema errors
- [ ] Job execution verified

### Phase 4: Discord Bot Testing
- [ ] ZMQ listener cog tests pass
- [ ] Event handling verified
- [ ] Integration with server confirmed

### Phase 5-6: Functional & Performance
- [ ] All functional workflows tested
- [ ] Performance benchmarks met
- [ ] No memory leaks or resource issues

### Final: Merge to Main
- [ ] All tests passing
- [ ] Documentation updated
- [ ] PR reviewed and approved
- [ ] APScheduler a6 upgrade complete

## Continuous Integration

### GitHub Actions (Future)
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: poetry run pytest tests/ -v --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Documentation Updates

### Test Documentation
- [ ] Update `tests/index.md` with new structure
- [ ] Create test writing guide
- [ ] Document fixture usage
- [ ] Add troubleshooting guide

### API Documentation
- [ ] Document test endpoints
- [ ] Add example requests/responses
- [ ] Update for APScheduler a6

## Notes

- Focus on **component isolation** before integration
- **Clean database** between test runs
- Use **feature branch** for APScheduler upgrade
- **Document failures** for investigation
- **Incremental approach** - don't try to fix everything at once

## References

- [Testing Status](../testing-status.md)
- [Test Index](../../tests/index.md)
- [APScheduler 4.x Documentation](https://apscheduler.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
