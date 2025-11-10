---
title: Job Execution Logging API
tags:
  - api
  - specification
  - user-docs
status: complete
---

# Job Execution Logging API

ScheduleZero now captures and exposes detailed execution history for all scheduled and immediate jobs through a REST API.

## Overview

The execution logging system:
- **Tracks every job execution** with timing, status, results, and errors
- **Stores up to 1000 recent executions** in a thread-safe circular buffer
- **Provides queryable APIs** for history, statistics, and error analysis
- **Works seamlessly** with both scheduled jobs and immediate executions

## Architecture

### Components

1. **JobExecutionLog** (`job_execution_log.py`)
   - In-memory circular buffer (deque with max_size=1000)
   - Thread-safe with locking for concurrent access
   - Automatically evicts oldest records when full

2. **JobExecutionRecord** (dataclass)
   - Captures: job_id, handler_id, method_name, timing, status, result, error, attempt_number
   - Status values: `"running"`, `"success"`, `"error"`, `"timeout"`

3. **API Handlers** (`api/job_execution_log_api.py`)
   - Four endpoints for querying execution data
   - Integrated with Tornado web server

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ APScheduler triggers job                                     │
│   ↓                                                           │
│ JobExecutor.__call__(job_id, handler_id, method, params)    │
│   ↓                                                           │
│ execution_log.record_start() → JobExecutionRecord           │
│   ↓                                                           │
│ Execute job via ZMQ                                          │
│   ↓                                                           │
│ Success? → execution_log.record_success()                   │
│ Error? → execution_log.record_error(is_final=...)          │
│   ↓                                                           │
│ Record stored in circular buffer                            │
│   ↓                                                           │
│ Queryable via /api/executions/* endpoints                   │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Query Execution History

**GET** `/api/executions`

Returns recent job executions with optional filtering.

**Query Parameters:**
- `limit` (int, default=100): Maximum number of records to return
- `handler_id` (string, optional): Filter by handler ID
- `job_id` (string, optional): Filter by job ID
- `status` (string, optional): Filter by status (`success`, `error`, `running`, `timeout`)

**Response:**
```json
{
  "count": 42,
  "limit": 100,
  "records": [
    {
      "job_id": "dingdong_1",
      "handler_id": "dingdong",
      "method_name": "ding",
      "started_at": "2024-01-15T10:30:00.123456Z",
      "completed_at": "2024-01-15T10:30:00.456789Z",
      "duration_ms": 333,
      "status": "success",
      "result": {"success": true, "message": "Ding!"},
      "error": null,
      "attempt_number": 1
    },
    ...
  ]
}
```

**Example:**
```bash
# Get last 50 executions for a specific handler
curl "http://localhost:8888/api/executions?handler_id=dingdong&limit=50"

# Get all errors
curl "http://localhost:8888/api/executions?status=error"

# Get executions for a specific job
curl "http://localhost:8888/api/executions?job_id=my_scheduled_task"
```

### 2. Get Execution Statistics

**GET** `/api/executions/stats`

Returns aggregated statistics about job executions.

**Response:**
```json
{
  "total_executions": 1523,
  "success_count": 1489,
  "error_count": 34,
  "success_rate": 97.77,
  "average_duration_ms": 245.3,
  "by_handler": {
    "dingdong": {
      "total": 823,
      "success": 823,
      "error": 0,
      "success_rate": 100.0,
      "avg_duration_ms": 123.4
    },
    "discord_bot": {
      "total": 700,
      "success": 666,
      "error": 34,
      "success_rate": 95.14,
      "avg_duration_ms": 387.9
    }
  },
  "buffer_utilization": 0.85
}
```

**Example:**
```bash
curl "http://localhost:8888/api/executions/stats"
```

### 3. Get Recent Errors

**GET** `/api/executions/errors`

Returns recent failed executions with error details.

**Query Parameters:**
- `limit` (int, default=50): Maximum number of errors to return

**Response:**
```json
{
  "count": 5,
  "limit": 50,
  "errors": [
    {
      "job_id": "problematic_task",
      "handler_id": "discord_bot",
      "method_name": "send_message",
      "started_at": "2024-01-15T10:45:23.123456Z",
      "completed_at": "2024-01-15T10:45:28.456789Z",
      "duration_ms": 5333,
      "status": "error",
      "error": "Connection timeout after 5000ms",
      "attempt_number": 3
    },
    ...
  ]
}
```

**Example:**
```bash
# Get last 20 errors
curl "http://localhost:8888/api/executions/errors?limit=20"
```

### 4. Clear Execution History

**POST** `/api/executions/clear`

Clears all execution history from the circular buffer.

⚠️ **Admin Operation**: This permanently removes all execution records.

**Response:**
```json
{
  "status": "success",
  "message": "Execution history cleared",
  "records_cleared": 1523
}
```

**Example:**
```bash
curl -X POST "http://localhost:8888/api/executions/clear"
```

## Configuration

### Circular Buffer Size

The default buffer size is **1000 records**. To change it, modify `tornado_app_server.py`:

```python
# Initialize execution log with custom size
execution_log = JobExecutionLog(max_size=5000)  # Store up to 5000 records
```

### Buffer Utilization

The `/api/executions/stats` endpoint includes `buffer_utilization` (0.0 to 1.0):
- **< 0.8**: Buffer has room for more records
- **≥ 0.8**: Buffer is filling up, oldest records being evicted
- **= 1.0**: Buffer is full (oldest records constantly evicted)

If you frequently see high utilization, consider increasing `max_size`.

## Retry Tracking

The system tracks retry attempts for failed jobs:

```json
{
  "job_id": "flaky_task",
  "status": "error",
  "attempt_number": 3,  // Final attempt (JobExecutor retries up to 3 times)
  "error": "Handler timeout after exponential backoff"
}
```

- **attempt_number**: Which retry attempt this record represents (1 = first try, 3 = final retry)
- Successful retries will have `status: "success"` with `attempt_number > 1`
- Final failures have `status: "error"` and `attempt_number = max_retries`

## Performance Notes

### Memory Usage

With default settings (1000 records), memory usage is approximately:
- **Per record**: ~500 bytes (depending on result/error size)
- **Total buffer**: ~500 KB to 1 MB

### Thread Safety

All operations are protected by `threading.Lock`, ensuring:
- ✅ Safe concurrent reads/writes from multiple handlers
- ✅ Safe access from Tornado request handlers
- ✅ No race conditions during record insertion

### Circular Buffer Behavior

When the buffer is full (1000 records):
- New records automatically evict the oldest record
- No manual cleanup needed
- FIFO (First In, First Out) eviction policy

## Use Cases

### 1. Monitor Job Health

```bash
# Check overall success rate
curl "http://localhost:8888/api/executions/stats" | jq .success_rate

# Find handlers with errors
curl "http://localhost:8888/api/executions/stats" | jq '.by_handler | to_entries | map(select(.value.error_count > 0))'
```

### 2. Debug Failing Jobs

```bash
# Get recent errors for a specific handler
curl "http://localhost:8888/api/executions/errors?limit=10" | jq '.errors[] | select(.handler_id == "discord_bot")'

# Find jobs that are timing out
curl "http://localhost:8888/api/executions?status=timeout"
```

### 3. Performance Analysis

```bash
# Find slow-running jobs
curl "http://localhost:8888/api/executions" | jq '.records | sort_by(.duration_ms) | reverse | .[0:10]'

# Average execution time per handler
curl "http://localhost:8888/api/executions/stats" | jq '.by_handler | to_entries | map({handler: .key, avg_ms: .value.avg_duration_ms})'
```

### 4. Audit Trail

```bash
# Get all executions for a specific scheduled job
curl "http://localhost:8888/api/executions?job_id=daily_report&limit=1000"

# Find jobs executed in the last hour (requires timestamp filtering in client)
curl "http://localhost:8888/api/executions" | jq --arg cutoff "$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
  '.records[] | select(.started_at > $cutoff)'
```

## Integration Examples

### Python Client

```python
import requests

class ScheduleZeroClient:
    def __init__(self, base_url="http://localhost:8888"):
        self.base_url = base_url
    
    def get_executions(self, handler_id=None, limit=100):
        """Get execution history."""
        params = {"limit": limit}
        if handler_id:
            params["handler_id"] = handler_id
        
        response = requests.get(f"{self.base_url}/api/executions", params=params)
        return response.json()
    
    def get_stats(self):
        """Get execution statistics."""
        response = requests.get(f"{self.base_url}/api/executions/stats")
        return response.json()
    
    def get_errors(self, limit=50):
        """Get recent errors."""
        response = requests.get(f"{self.base_url}/api/executions/errors", params={"limit": limit})
        return response.json()
    
    def clear_history(self):
        """Clear execution history (admin operation)."""
        response = requests.post(f"{self.base_url}/api/executions/clear")
        return response.json()

# Usage
client = ScheduleZeroClient()

# Get stats
stats = client.get_stats()
print(f"Success rate: {stats['success_rate']:.2f}%")

# Check for errors
errors = client.get_errors(limit=10)
if errors['count'] > 0:
    print(f"Warning: {errors['count']} recent errors!")
    for error in errors['errors']:
        print(f"  - {error['handler_id']}.{error['method_name']}: {error['error']}")
```

### Dashboard Integration

Build a monitoring dashboard by polling these endpoints:

```javascript
// Fetch execution stats every 30 seconds
setInterval(async () => {
  const stats = await fetch('/api/executions/stats').then(r => r.json());
  
  // Update dashboard metrics
  document.getElementById('success-rate').textContent = stats.success_rate.toFixed(2) + '%';
  document.getElementById('total-executions').textContent = stats.total_executions;
  document.getElementById('avg-duration').textContent = stats.average_duration_ms.toFixed(0) + 'ms';
  
  // Update per-handler charts
  updateHandlerChart(stats.by_handler);
}, 30000);

// Show recent errors in real-time
setInterval(async () => {
  const errors = await fetch('/api/executions/errors?limit=5').then(r => r.json());
  updateErrorList(errors.errors);
}, 10000);
```

## Future Enhancements

Potential additions to the execution logging system:

1. **Persistent Storage**: Write execution logs to SQLite/PostgreSQL for long-term analysis
2. **Webhook Notifications**: Trigger webhooks on job failures
3. **Prometheus Metrics**: Export execution stats as Prometheus metrics
4. **Web UI**: Built-in dashboard for visualizing execution history
5. **Time-based Queries**: Filter executions by timestamp ranges
6. **Export**: Download execution history as CSV/JSON

## See Also

- [API Documentation](./API.md)
- [Handler Development Guide](./HANDLERS.md)
- [Discord Cog Architecture](../examples/COG_SPROCKET_ARCHITECTURE.md)
