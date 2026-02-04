# ScheduleZero Tests

This directory contains integration tests for the ScheduleZero distributed task scheduler.

## Test Components

### Test Handler (`test_handler.py`)

A specialized handler implementation designed for testing. It provides methods that generate observable output:

- **`write_file(params)`** - Writes content to a file
- **`append_to_file(params)`** - Appends content to a file
- **`increment_counter(params)`** - Increments a counter and stores the value
- **`generate_report(params)`** - Creates a timestamped report
- **`heartbeat()`** - Simple ping for connectivity testing
- **`get_execution_count()`** - Returns execution statistics
- **`clear_output()`** - Cleans up test files and resets logs

All methods log their execution to `test_output/execution_log.json` for verification.

### Integration Tests (`test_scheduled_jobs.py`)

Comprehensive pytest suite that tests:

1. **Server Health** - Verifies API endpoints are responding
2. **Handler Registration** - Confirms test handler is properly registered
3. **Immediate Execution** - Tests `run_now` API for immediate job execution
4. **Interval Triggers** - Schedules jobs that repeat at intervals
5. **Date Triggers** - Schedules jobs for specific times
6. **Report Generation** - Tests complex job workflows
7. **Execution Tracking** - Verifies all executions are logged
8. **Schedule Listing** - Tests the schedules API

## Running the Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   poetry add --group dev pytest requests
   ```

2. **Start the ScheduleZero server:**
   ```bash
   poetry run python -m schedule_zero.tornado_app_server
   ```

3. **Start the test handler (in a separate terminal):**
   ```bash
   poetry run python tests/test_handler.py
   ```

### Run Tests

```bash
# Run all tests with verbose output
poetry run pytest tests/test_scheduled_jobs.py -v

# Run a specific test
poetry run pytest tests/test_scheduled_jobs.py::TestScheduledJobs::test_run_now_write_file -v

# Run with output displayed (helpful for debugging)
poetry run pytest tests/test_scheduled_jobs.py -v -s
```

## Test Output

Tests generate files in `tests/test_output/`:
- `execution_log.json` - Log of all handler method calls
- `test_immediate.txt` - Output from immediate execution tests
- `interval_test.txt` - Output from interval trigger tests
- `date_test.txt` - Output from date trigger tests
- `counter_*.txt` - Counter files
- `report_*.txt` - Generated report files

These files can be inspected after test runs to verify job execution.

## Test Architecture

```
┌─────────────────┐     HTTP API      ┌──────────────────┐
│  Test Suite     │ ───────────────> │  ScheduleZero    │
│  (pytest)       │                   │  Server          │
└─────────────────┘                   └──────────────────┘
        │                                     │
        │ Verifies files                     │ zerorpc
        │ created                            │
        ↓                                    ↓
┌─────────────────┐                   ┌──────────────────┐
│  test_output/   │ <───────────────  │  Test Handler    │
│  Files & Logs   │   Writes output   │  (test_handler)  │
└─────────────────┘                   └──────────────────┘
```

## Extending Tests

To add new tests:

1. Add a new method to `TestHandlerService` in `test_handler.py`
2. Create a test method in `test_scheduled_jobs.py`
3. Use `wait_for_file()` to wait for observable output
4. Verify the output matches expectations

Example:
```python
def test_my_new_feature(self):
    """Test description."""
    job_data = {
        "handler_id": HANDLER_ID,
        "method": "my_method",
        "params": {"key": "value"}
    }
    
    response = requests.post(f"{API_BASE_URL}/api/run_now", json=job_data)
    assert response.status_code == 200
    
    # Wait for and verify output
    file_path = self.wait_for_file("expected_output.txt", timeout=10)
    # ... verify content ...
```

## Troubleshooting

**Handler not registered:**
- Ensure test handler is running before running tests
- Check handler logs for connection errors

**Jobs not executing:**
- Verify server is running on port 8888
- Check server logs for execution errors
- Increase timeout values in tests if system is slow

**Files not created:**
- Check `test_output/execution_log.json` to see if method was called
- Verify handler methods are completing successfully
- Check handler logs for errors
