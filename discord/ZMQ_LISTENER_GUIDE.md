# Discord Bot Integration with ZeroMQ Listener

This guide explains how to integrate the ZeroMQ listener cog into your Discord bot to receive real-time events from the ScheduleZero server.

## Overview

The ZMQ Listener Cog enables your Discord bot to:
- Receive real-time notifications when jobs execute
- Get alerts on job failures
- Monitor handler registrations and status changes
- React to scheduler events
- Trigger Discord actions based on ScheduleZero events

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐
│  ScheduleZero       │  ZMQ    │  Discord Bot     │
│  Server             │────────>│  Process         │
│                     │  PUB    │                  │
│  - APScheduler      │         │  - ZMQ SUB       │
│  - Job Execution    │         │  - Event Handler │
│  - Handler Registry │         │  - Bot Commands  │
└─────────────────────┘         └──────────────────┘
```

The ScheduleZero server publishes events via ZeroMQ's PUB socket, and the Discord bot subscribes to these events via a SUB socket running in a background thread.

## Prerequisites

1. **ScheduleZero server** running with ZMQ publisher enabled
2. **Discord bot** using discord.py/py-cord
3. **Python packages**: `pyzmq`, `pyyaml`

Install dependencies:
```bash
pip install pyzmq pyyaml discord-py-interactions
# or
pip install pyzmq pyyaml py-cord
```

## Setup

### 1. Enable ZMQ Publisher in ScheduleZero

First, ensure ScheduleZero is configured to publish events. Add to your `deployment_config.py`:

```python
# ZMQ Publisher for broadcasting events
zmq_publisher_enabled: bool = True
zmq_publisher_port: int = 4243  # Default publisher port
```

### 2. Configure the Discord Bot

Create or update `discord/config/zmq_listener.yaml`:

```yaml
# ZMQ Listener Configuration
zmq_pub_address: "tcp://127.0.0.1:4243"

topics:
  - "job."        # All job events
  - "handler."    # All handler events
  - "scheduler."  # All scheduler events

# Optional: Configure Discord channels for notifications
notification_channels:
  job_failed: 123456789012345678  # Channel ID for failure alerts
  job_executed: null              # null = don't post to channel
  handler_status: null
```

### 3. Load the Cog in Your Bot

In your Discord bot's main file (e.g., `bot.py`):

```python
import discord
from discord.ext import commands

bot = discord.Bot()

# Load the ZMQ listener cog
bot.load_extension("cogs.zmq_listener_cog")

# Load other cogs
bot.load_extension("cogs.schedulezero_cog")  # If you're using the scheduler cog
bot.load_extension("cogs.sprockets.announcement_sprocket")

bot.run(TOKEN)
```

### 4. Verify Setup

Once your bot is running, use the `/zmq_status` command in Discord:

```
/zmq_status
```

This will show:
- ✅ Running status
- Message queue size
- Number of registered handlers
- Connected ZMQ address
- Subscribed topics

## Customizing Event Handlers

### Register Custom Handlers

You can register custom handlers for specific event types:

```python
# In your bot or another cog
from cogs.zmq_listener_cog import ZMQListenerCog

@bot.event
async def on_ready():
    zmq_cog = bot.get_cog("ZMQListenerCog")
    if zmq_cog and zmq_cog.listener:
        # Register custom handler for job completion
        zmq_cog.listener.register_handler(
            "job.executed",
            handle_job_completion
        )

async def handle_job_completion(bot, topic, data):
    """Send a message when a specific job completes."""
    job_id = data.get('job_id')
    job_name = data.get('job_name', 'unknown')
    
    # Post to specific channel
    channel = bot.get_channel(YOUR_CHANNEL_ID)
    if channel:
        await channel.send(f"✅ Job completed: {job_name}")
```

### Example: Alert on Job Failures

Create a custom handler in a separate cog:

```python
# cogs/alert_cog.py
import discord
from discord.ext import commands

class AlertCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel_id = 123456789012345678
    
    async def cog_load(self):
        # Register handler when cog loads
        zmq_cog = self.bot.get_cog("ZMQListenerCog")
        if zmq_cog and zmq_cog.listener:
            zmq_cog.listener.register_handler(
                "job.failed",
                self.alert_job_failure
            )
    
    async def alert_job_failure(self, bot, topic, data):
        """Send alert embed when job fails."""
        channel = bot.get_channel(self.alert_channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="❌ Job Failure Alert",
            color=discord.Color.red(),
            description=f"Job `{data.get('job_name', 'unknown')}` failed"
        )
        embed.add_field(name="Job ID", value=data.get('job_id', 'N/A'))
        embed.add_field(name="Error", value=data.get('error', 'Unknown error'))
        embed.add_field(name="Retry Count", value=data.get('retry_count', 0))
        embed.timestamp = discord.utils.utcnow()
        
        await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(AlertCog(bot))
```

## Event Types

### Job Events

| Topic | Description | Data Fields |
|-------|-------------|-------------|
| `job.scheduled` | Job scheduled | `job_id`, `job_name`, `next_run_time` |
| `job.executed` | Job completed successfully | `job_id`, `job_name`, `duration`, `result` |
| `job.failed` | Job execution failed | `job_id`, `job_name`, `error`, `retry_count` |
| `job.removed` | Job removed from scheduler | `job_id`, `job_name` |

### Handler Events

| Topic | Description | Data Fields |
|-------|-------------|-------------|
| `handler.registered` | Handler registered with server | `handler_id`, `address`, `methods` |
| `handler.unregistered` | Handler unregistered | `handler_id` |
| `handler.ping` | Handler ping/heartbeat | `handler_id`, `status` |

### Scheduler Events

| Topic | Description | Data Fields |
|-------|-------------|-------------|
| `scheduler.started` | Scheduler started | `deployment`, `timestamp` |
| `scheduler.stopped` | Scheduler stopped | `deployment`, `timestamp` |

## Commands

The ZMQ Listener Cog provides these slash commands:

### `/zmq_status`
Shows the current status of the ZMQ listener.

**Output:**
```
Status: 🟢 Running
Queue Size: 3
Handlers: 5
Address: tcp://127.0.0.1:4243
Topics: job., handler., scheduler.
```

### `/zmq_restart` (Admin Only)
Restarts the ZMQ listener (requires administrator permissions).

## Troubleshooting

### Listener Not Connecting

**Problem:** Listener shows as stopped or can't connect to ZMQ server.

**Solutions:**
1. Verify ScheduleZero server is running and publishing events
2. Check ZMQ publisher port in both configs matches:
   - `deployments/{deployment}/config.yaml` (server side)
   - `discord/config/zmq_listener.yaml` (bot side)
3. Check firewall rules allow ZMQ port (default: 4243)
4. Verify network connectivity: `telnet 127.0.0.1 4243`

### No Events Received

**Problem:** Listener is running but no events are dispatched.

**Solutions:**
1. Check topic subscriptions match event topics
2. Verify ScheduleZero is actually triggering events (schedule a test job)
3. Enable debug logging in bot:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```
4. Check message queue size with `/zmq_status` - if growing, handlers may be slow

### High Message Queue

**Problem:** Message queue size keeps growing.

**Solutions:**
1. Handlers may be too slow - optimize async operations
2. Reduce message processing frequency (adjust loop in `message_processor`)
3. Filter out unnecessary events in topic subscriptions
4. Add more specific handlers instead of generic catch-all handlers

### Events Missing

**Problem:** Some events are not received.

**Solutions:**
1. ZMQ PUB/SUB is "fire and forget" - subscribers only receive messages sent AFTER they connect
2. Ensure bot starts before scheduling jobs
3. Consider using REQ/REP pattern for critical notifications (not implemented yet)

## Best Practices

### 1. Use Specific Topic Filters

Instead of subscribing to everything:
```yaml
topics:
  - "job."  # Everything
```

Be specific:
```yaml
topics:
  - "job.failed"      # Only failures
  - "job.executed"    # Only successes
  - "handler.registered"  # Only registrations
```

### 2. Async Handler Functions

Always make handlers async and avoid blocking operations:

```python
# ✅ Good - async, non-blocking
async def my_handler(bot, topic, data):
    await bot.get_channel(CHANNEL_ID).send("Event received")

# ❌ Bad - blocking
async def my_handler(bot, topic, data):
    time.sleep(5)  # Blocks the entire event loop!
```

### 3. Error Handling

Always wrap handler logic in try/except:

```python
async def my_handler(bot, topic, data):
    try:
        # Your logic here
        await process_event(data)
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        # Optionally notify admins
```

### 4. Rate Limiting

If posting to Discord channels, respect rate limits:

```python
from discord.ext import tasks

class EventPoster:
    def __init__(self):
        self.message_buffer = []
    
    @tasks.loop(seconds=2)
    async def post_buffered_messages(self):
        """Post at most 5 messages every 2 seconds."""
        channel = self.bot.get_channel(CHANNEL_ID)
        messages = self.message_buffer[:5]
        self.message_buffer = self.message_buffer[5:]
        
        for msg in messages:
            await channel.send(msg)
```

### 5. Persistent Storage

For critical events, consider logging to database:

```python
async def log_critical_event(bot, topic, data):
    """Log critical events to database for audit trail."""
    if topic == "job.failed":
        # Store in your database
        await db.events.insert_one({
            'topic': topic,
            'data': data,
            'timestamp': datetime.utcnow()
        })
```

## Advanced Usage

### Multiple Bot Instances

If running multiple bot instances, each can have its own listener:

```yaml
# Bot 1: discord/config/zmq_listener.yaml
zmq_pub_address: "tcp://127.0.0.1:4243"
topics:
  - "job."  # Monitor all jobs

# Bot 2: discord/config/zmq_listener_bot2.yaml  
zmq_pub_address: "tcp://127.0.0.1:4243"
topics:
  - "handler."  # Only monitor handlers
```

### Remote ZMQ Server

To connect to a remote ScheduleZero instance:

```yaml
# Use external IP or hostname
zmq_pub_address: "tcp://schedulezero.example.com:4243"
```

⚠️ **Security Warning:** ZMQ has no built-in authentication. For production:
1. Use VPN or SSH tunnel
2. Implement authentication layer
3. Restrict firewall rules

### Event Filtering

Filter events programmatically:

```python
async def filtered_handler(bot, topic, data):
    """Only handle specific job names."""
    job_name = data.get('job_name', '')
    
    if job_name not in ['important-job', 'critical-job']:
        return  # Ignore
    
    # Process important jobs only
    await notify_admins(job_name)
```

## See Also

- [Discord Bot with Cogs Documentation](COG_SPROCKET_ARCHITECTURE.md)
- [ScheduleZero Handler Architecture](../docs/autonomous-handler-architecture.md)
- [ZeroMQ Event Broker Design](../docs/zmq-event-broker-design.md)
