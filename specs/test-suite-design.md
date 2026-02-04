# ScheduleZero Test Suite Documentation

## Overview

Comprehensive test suite covering ZMQ socket recovery, governor architecture, and system integration with regression testing.

## Test Organization

### Test Files

```
tests/
├── test_zmq_socket_recovery.py  # ZMQ client and socket state tests
├── test_governor.py              # Governor ABC and ProcessGovernor tests
├── test_integration.py           # End-to-end integration tests
└── conftest.py                   # Pytest fixtures and configuration
```

### Test Categories

Tests are organized using pytest markers:

- **`unit`** - Fast, isolated unit tests
- **`integration`** - Tests requiring multiple components
- **`regression`** - Tests for previously fixed bugs
- **`zmq`** - Tests requiring ZMQ communication
- **`governor`** - Governor-specific tests
- **`slow`** - Tests taking >10 seconds

## Running Tests

### Quick Start

```powershell
# Run all tests
poetry run pytest

# Run quick tests only (exclude slow)
python run_tests.py quick

# Run specific test suite
python run_tests.py zmq
python run_tests.py governor
python run_tests.py integration

# Run with coverage
python run_tests.py all --coverage
```

### Using Test Runner

The `run_tests.py` script provides convenient test execution:

```powershell
# Show all available tests
python run_tests.py --list

# Run unit tests only
python run_tests.py unit

# Run regression tests
python run_tests.py regression

# Run specific file
python run_tests.py tests/test_zmq_socket_recovery.py

# Run with additional markers
python run_tests.py all -m "zmq and not slow"
```

### Direct pytest Usage

```powershell
# Run all tests verbosely
poetry run pytest -v

# Run specific test class
poetry run pytest tests/test_zmq_socket_recovery.py::TestZMQSocketRecovery

# Run specific test method
poetry run pytest tests/test_zmq_socket_recovery.py::TestZMQSocketRecovery::test_auto_reconnect_on_error

# Run with markers
poetry run pytest -m "unit and not slow"

# Generate HTML coverage report
poetry run pytest --cov=src/schedule_zero --cov-report=html
```

## Test Suite Details

### 1. ZMQ Socket Recovery Tests (`test_zmq_socket_recovery.py`)

**Purpose**: Verify ZMQ socket state management and error recovery.

**Test Classes**:
- `TestZMQSocketRecovery` - Socket recreation and reconnection
- `TestZMQErrorHandling` - Error conditions and timeouts
- `TestZMQRegressions` - Previously fixed bugs
- `TestZMQClientIntegration` - Real-world usage patterns

**Key Tests**:
```python
test_basic_connection()              # Basic connect and ping
test_socket_recreation_after_close() # Socket can be recreated
test_auto_reconnect_on_error()       # Auto-reconnect works
test_context_manager()               # Context manager cleanup
test_terminate_cleanup()             # Proper resource cleanup
test_multiple_reconnects()           # Multiple reconnection cycles
test_socket_state_machine_error()    # EFSM error recovery (regression)
test_context_leak_prevention()       # No context leaks (regression)
test_hanging_after_timeout()         # No hangs after timeout (regression)
```

**Fixtures**:
- `mock_handler` - Running mock ZMQ handler on port 5555
- `zmq_client` - Pre-configured ZMQ client

**What's Tested**:
- ✅ Socket creation and connection
- ✅ Automatic reconnection after errors
- ✅ ZMQ context termination
- ✅ Context manager support
- ✅ EFSM error recovery
- ✅ Resource leak prevention
- ✅ Concurrent client safety

### 2. Governor Tests (`test_governor.py`)

**Purpose**: Verify governor ABC, ProcessGovernor, and process management.

**Test Classes**:
- `TestHandlerConfig` - Handler configuration data class
- `TestProcessInfo` - Process information data class
- `TestGovernorBase` - Abstract base class validation
- `TestProcessManager` - Process management functionality
- `TestProcessGovernor` - Governor implementation
- `TestProcessGovernorIntegration` - Full lifecycle tests
- `TestGovernorRegressions` - Previously fixed bugs

**Key Tests**:
```python
# HandlerConfig
test_basic_creation()                # Config creation
test_to_dict() / test_from_dict()   # Serialization

# ProcessManager
test_start_simple_command()          # Start processes
test_pid_file_creation()             # PID file tracking
test_stop_graceful()                 # Graceful shutdown
test_get_info()                      # Process info retrieval

# ProcessGovernor
test_start_creates_server()          # Server startup
test_stop_is_idempotent()           # Safe repeated stops
test_add_handler_config()            # Dynamic handler addition
test_full_lifecycle()                # Complete start/status/stop

# Regressions
test_process_cleanup_on_exit()       # Atexit cleanup (regression)
test_pid_file_cleanup()              # PID file removal (regression)
test_poetry_environment_usage()      # Poetry env usage (regression)
```

**Fixtures**:
- `temp_dirs` - Temporary log and PID directories
- `governor` - Test governor instance with cleanup

**What's Tested**:
- ✅ Governor ABC interface
- ✅ Handler configuration
- ✅ Process lifecycle management
- ✅ PID file tracking
- ✅ Signal handling
- ✅ Graceful shutdown
- ✅ Dynamic handler operations
- ✅ Process cleanup
- ✅ Poetry environment usage

### 3. Integration Tests (`test_integration.py`)

**Purpose**: End-to-end tests with running system.

**Test Classes**:
- `TestSystemIntegration` - Server health and metrics
- `TestHandlerIntegration` - Handler lifecycle
- `TestErrorRecovery` - Recovery scenarios
- `TestRegressionScenarios` - Real-world failure cases
- `TestSystemUnderLoad` - Performance and stability (slow)

**Key Tests**:
```python
# System Integration
test_server_health_check()           # Server responds to health checks
test_governor_status()               # Governor reports correct status
test_governor_metrics()              # Metrics collection

# Error Recovery
test_governor_restart()              # Governor can restart
test_stop_and_restart()             # Stop and restart cycles

# Regressions
test_rapid_start_stop_cycles()       # No PID conflicts (regression)
test_concurrent_stop_calls()         # No race conditions (regression)

# Load Tests (marked as slow)
test_long_running_server()           # Server stays up (30s)
test_multiple_handler_additions()    # Multiple handlers over time
```

**Fixtures**:
- `governor` - Module-scoped running governor

**What's Tested**:
- ✅ Server startup and health
- ✅ Governor status reporting
- ✅ Metrics collection
- ✅ Handler lifecycle
- ✅ System restart
- ✅ Rapid start/stop cycles
- ✅ Long-running stability

## Regression Tests

Regression tests ensure previously fixed bugs don't return:

### ZMQ Socket State Machine Error (EFSM)
**Bug**: After timeout, socket entered invalid state causing "Operation cannot be accomplished in current state" errors.

**Test**: `test_socket_state_machine_error()`

**Verification**: Socket automatically recovers after error.

### ZMQ Context Leaks
**Bug**: ZMQ contexts created but never terminated, causing resource leaks.

**Test**: `test_context_leak_prevention()`

**Verification**: All contexts properly terminated.

### Test Hanging After Timeout
**Bug**: After socket timeout, subsequent calls would hang forever.

**Test**: `test_hanging_after_timeout()`

**Verification**: Timeouts don't cause permanent hangs.

### Process Cleanup on Exit
**Bug**: Processes could be orphaned if governor exited without cleanup.

**Test**: `test_process_cleanup_on_exit()`

**Verification**: Atexit handler stops all processes.

### PID File Cleanup
**Bug**: PID files left behind after process stop.

**Test**: `test_pid_file_cleanup()`

**Verification**: PID files removed on process stop.

### Poetry Environment Usage
**Bug**: Governor used sys.executable (Windows Store Python) instead of Poetry environment.

**Test**: `test_poetry_environment_usage()`

**Verification**: Commands use "poetry run python".

### Rapid Start/Stop Cycles
**Bug**: Rapid start/stop could cause PID file conflicts.

**Test**: `test_rapid_start_stop_cycles()`

**Verification**: Multiple cycles complete cleanly.

### Concurrent Stop Calls
**Bug**: Concurrent stop calls could cause race conditions.

**Test**: `test_concurrent_stop_calls()`

**Verification**: Multiple stops are safe.

## Test Fixtures

### Mock Handler (`mock_handler`)
Provides a running mock ZMQ handler for testing:
- Listens on port 5555
- Responds to ping and call requests
- Runs in separate thread
- Auto-cleanup on fixture teardown

### ZMQ Client (`zmq_client`)
Pre-configured ZMQ client:
- Connected to tcp://127.0.0.1:5555
- 2 second timeout
- Auto-cleanup with terminate()

### Governor (`governor`)
Test governor instance:
- Deployment: "test"
- Auto-cleanup on teardown
- Function-scoped for isolation

### Temporary Directories (`temp_dirs`)
Provides clean log and PID directories:
- Temporary log directory
- Temporary PID directory
- Auto-cleanup by pytest

## Coverage Goals

Target coverage by module:

- **`zmq_client.py`**: 95%+ (critical path)
- **`handler_registry.py`**: 90%+ (client management)
- **`governor_base.py`**: 100% (ABC must be complete)
- **`process_governor.py`**: 85%+ (process management)

Generate coverage report:
```powershell
poetry run pytest --cov=src/schedule_zero --cov-report=html
# Open htmlcov/index.html
```

## Continuous Integration

### Required Checks
All tests must pass for PR merge:
```powershell
# Quick tests (fast feedback)
poetry run pytest -m "not slow" --tb=short

# Full test suite (before merge)
poetry run pytest tests/

# With coverage (weekly)
poetry run pytest --cov=src/schedule_zero --cov-fail-under=80
```

### Test Performance
- Quick tests: < 30 seconds
- Full suite (no slow): < 2 minutes
- Full suite (with slow): < 5 minutes

## Writing New Tests

### Test Naming Convention
```python
def test_<what>_<condition>_<expected>():
    """
    Test that <what> <expected result> when <condition>.
    
    <Additional context or regression info>
    """
```

### Example Test
```python
def test_socket_reconnects_after_timeout():
    """
    Test that socket automatically reconnects after timeout.
    
    Regression test for issue where timeouts caused permanent
    connection loss requiring manual restart.
    """
    client = ZMQClient("tcp://127.0.0.1:5555")
    client.connect()
    
    # Cause timeout by stopping handler
    handler.stop()
    
    with pytest.raises(zmq.Again):
        client.call("ping")
    
    # Restart handler
    handler.start()
    
    # Should auto-reconnect
    result = client.call("ping", auto_reconnect=True)
    assert result["success"]
```

### Adding Markers
```python
@pytest.mark.slow
@pytest.mark.integration
def test_long_running_scenario():
    """Test marked as slow and integration."""
    pass
```

## Troubleshooting Tests

### Tests Hang
- Check for missing timeouts on ZMQ sockets
- Verify mock handler is stopped in fixture cleanup
- Use `pytest-timeout` plugin: `pytest --timeout=60`

### Intermittent Failures
- Add stabilization delays after process start
- Check for race conditions in concurrent tests
- Verify proper cleanup in fixtures

### Resource Leaks
- Check that all fixtures have proper teardown
- Verify ZMQ contexts are terminated
- Use `terminate()` instead of `close()` for full cleanup

## Next Steps

1. ✅ **Core Test Suite** - Complete
2. 🔨 **Add pytest-cov** to pyproject.toml dependencies
3. 🔨 **Add pytest-timeout** for hanging test protection
4. 🔨 **Add pytest-xdist** for parallel test execution
5. 🔨 **Create CI/CD pipeline** configuration
6. 🔨 **Add performance benchmarks** with pytest-benchmark
7. 🔨 **Property-based testing** with hypothesis

## Resources

- pytest Documentation: https://docs.pytest.org/
- pytest Markers: https://docs.pytest.org/en/stable/mark.html
- pytest Fixtures: https://docs.pytest.org/en/stable/fixture.html
- Coverage.py: https://coverage.readthedocs.io/
