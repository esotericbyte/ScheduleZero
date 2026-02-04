# 🚀 Multiple Deployment Support

ScheduleZero now supports running multiple simultaneous deployments with completely separate configurations!

## Available Deployments

### 1. **default** (Development)
- Web: `http://127.0.0.1:8888`
- ZMQ: `tcp://127.0.0.1:4242`
- Database: `schedulezero_jobs.db`
- Logs: Console only
- Registry: `handler_registry.yaml`

### 2. **clock** (DingDong Clock)
- Web: `http://127.0.0.1:8889`
- ZMQ: `tcp://127.0.0.1:4243`
- Database: `deployments/clock/schedulezero_jobs.db`
- Logs: `deployments/clock/logs/server.log`
- Registry: `deployments/clock/handler_registry.yaml`

### 3. **production** (Production Ready)
- Web: `http://0.0.0.0:8888` (all interfaces)
- ZMQ: `tcp://0.0.0.0:4242`
- Database: `deployments/production/schedulezero_jobs.db`
- Logs: `deployments/production/logs/server.log`
- Registry: `deployments/production/handler_registry.yaml`

### 4. **test** (Testing)
- Web: `http://127.0.0.1:8890`
- ZMQ: `tcp://127.0.0.1:4244`
- Database: `deployments/test/schedulezero_jobs.db`
- Logs: `deployments/test/logs/server.log`
- Registry: `deployments/test/handler_registry.yaml`

## Starting Deployments

### Using Governor (Recommended)

The governor process supervises both the server and handlers, automatically restarting them on crashes:

```powershell
# Start a deployment with its handlers
poetry run python governor.py start clock

# Check status
poetry run python governor.py status clock

# Stop everything
poetry run python governor.py stop clock

# Restart everything
poetry run python governor.py restart clock
```

### Manual Start (Development Only)

For development debugging, you can start components individually:

```powershell
# Start server only
$env:SCHEDULEZERO_DEPLOYMENT='clock'
poetry run python -m schedule_zero.server

# In another terminal, start handler manually
$env:DING_DONG_DEPLOY='true'
poetry run python tests/ding_dong_handler.py
```

## Running Multiple Deployments Simultaneously

**YES!** You can run all of them at the same time because they use different ports!

**Example: Run both default AND clock deployments:**

```powershell
# Terminal 1 - Start clock deployment
poetry run python governor.py start clock

# Terminal 2 - Start default deployment  
poetry run python governor.py start default
```

Now you have:
- Default server on port 8888
- Clock server on port 8889
- They can't interfere with each other!

## Handler Management

Handlers are automatically started and managed by the governor based on the `handler_registry.yaml` file for each deployment.

### Scheduling Jobs

Once the governor is running, you can schedule jobs for any registered handler:

```powershell
# Schedule DingDong chimes (connects to clock deployment)
$env:DING_DONG_DEPLOY='true'
poetry run python tests/schedule_ding_dongs.py

# Check status
$env:DING_DONG_DEPLOY='true'
poetry run python tests/check_ding_dongs.py
```

### Manual Handler Start (Development Only)

For debugging, you can start handlers manually:

```powershell
# Start handler in TEST mode (connects to default deployment)
poetry run python tests/ding_dong_handler.py

# Start handler in DEPLOY mode (connects to clock deployment)
$env:DING_DONG_DEPLOY='true'
poetry run python tests/ding_dong_handler.py
```

## Environment Variable Overrides

You can override any config value:

```powershell
$env:SCHEDULEZERO_DEPLOYMENT='clock'
$env:SCHEDULEZERO_PORT='9999'           # Override web port
$env:SCHEDULEZERO_ZMQ_PORT='5555'       # Override ZMQ port
$env:SCHEDULEZERO_LOG_FILE='custom.log' # Custom log file
$env:LOG_LEVEL='DEBUG'                   # Change log level

poetry run python -m schedule_zero.server
```

## Benefits

### Isolation
- Each deployment has its own database
- Each deployment has its own logs
- Each deployment has its own handler registry
- No cross-contamination!

### Flexibility
- Run production and development simultaneously
- Test new features without affecting production
- Run dedicated servers for specific handlers (like DingDong clock)

### Safety
- Crash in test deployment? Production keeps running
- Development experiments won't affect your running clock
- Clear separation of concerns

## Log Files

Each deployment writes structured logs with full context (file:line:function):

```powershell
# View clock server logs
cat deployments/clock/logs/server/server.log

# View handler logs
cat deployments/clock/logs/handlers/ding-dong/handler.log

# Tail logs in real-time
Get-Content deployments/clock/logs/server/server.log -Wait

# View production logs
cat deployments/production/logs/server/server.log
```

### Log Format

All logs include full execution context:
```
2024-01-15 14:30:25.123 [INFO] Server [server.py:45:start] Starting ScheduleZero server
2024-01-15 14:30:26.456 [INFO] Handler [ding_dong_handler.py:78:play_chime] Playing chime sound
```

## Databases

Each deployment has its own SQLite database:

```powershell
# Check clock database
sqlite3 deployments/clock/schedulezero_jobs.db "SELECT * FROM schedules"

# Check production database
sqlite3 deployments/production/schedulezero_jobs.db "SELECT * FROM schedules"
```

## Complete Example: 2-Day Clock Test

1. **Start clock deployment (server + handlers supervised):**
```powershell
poetry run python governor.py start clock
```

2. **Schedule 2 days of chimes:**
```powershell
$env:DING_DONG_DEPLOY='true'
poetry run python tests/schedule_ding_dongs.py
```

3. **Check status anytime:**
```powershell
# Check processes
poetry run python governor.py status clock

# Check scheduled jobs
$env:DING_DONG_DEPLOY='true'
poetry run python tests/check_ding_dongs.py

# View web UI
# Open http://127.0.0.1:8889
```

4. **Monitor logs:**
```powershell
Get-Content deployments/clock/logs/handlers/ding-dong/handler.log -Wait
```

5. **Meanwhile, you can start other deployments too!**
```powershell
poetry run python governor.py start default
```

## Troubleshooting

### Check Process Status
```powershell
poetry run python governor.py status clock
```

### View Process IDs
```powershell
cat deployments/clock/pids/server.pid
cat deployments/clock/pids/ding-dong.pid
```

### Manual Cleanup (if governor fails)
```powershell
# Stop all processes
poetry run python governor.py stop clock

# If that fails, check PIDs and stop manually
$serverPid = Get-Content deployments/clock/pids/server.pid
Stop-Process -Id $serverPid

$handlerPid = Get-Content deployments/clock/pids/ding-dong.pid
Stop-Process -Id $handlerPid
```

### Check Port Availability
```powershell
# Check if ports are in use
netstat -an | Select-String "8889|4243"
```

### ZMQ Socket Issues
If you see "Operation cannot be accomplished in current state" errors:
1. Stop the deployment: `poetry run python governor.py stop clock`
2. Wait 5 seconds for sockets to close
3. Restart: `poetry run python governor.py start clock`

## Summary

✅ Governor supervises both server and handlers  
✅ Automatic crash recovery and restart  
✅ Multiple deployments run simultaneously  
✅ Each has separate ports, databases, logs  
✅ No conflicts or cross-contamination  
✅ Full logging context (file:line:function)  
✅ Clean single-command management  

**Happy multi-deployment scheduling!** 🎉
