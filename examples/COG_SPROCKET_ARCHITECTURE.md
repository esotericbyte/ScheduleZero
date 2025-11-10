# Discord Cog & Sprocket Architecture

## Overview

ScheduleZero integrates with Discord.py using a **cog + sprocket** pattern:

- **ScheduleZeroCog**: Main cog that manages the handler thread
- **Sprockets**: Pluggable cogs that register job methods dynamically

This architecture allows you to:
- ✅ Load/unload job handlers without restarting the bot
- ✅ Organize jobs into logical modules (announcements, moderation, etc.)
- ✅ Share sprockets across multiple bots
- ✅ Develop custom sprockets independently

---

## Architecture Diagram

```
Discord Bot Process
│
├─ Main Event Loop (discord.py)
│
├─ ScheduleZeroCog (Core)
│   ├─ Handler Thread (daemon)
│   │   └─ ZMQ listener (sync)
│   └─ Sprocket Registry
│       └─ {name: handler_function}
│
├─ Sprocket Cogs (Pluggable)
│   ├─ AnnouncementSprocket
│   │   └─ Registers: send_announcement, send_embed_announcement
│   ├─ ModerationSprocket
│   │   └─ Registers: cleanup_messages, lockdown_channel
│   └─ CustomSprocket
│       └─ Registers: your_custom_methods
│
└─ Communication Flow
    1. APScheduler (in ScheduleZero) triggers job at scheduled time
    2. ScheduleZero → ZMQ → Handler thread (sends job request)
    3. Handler thread → Sprocket registry → Find method
    4. Sprocket method → asyncio.run_coroutine_threadsafe → Bot event loop
    5. Bot event loop → Execute Discord operation → Returns result
    6. Result → Handler thread → ZMQ → ScheduleZero (for execution logging)
    
    Note: JobExecutor in ScheduleZero handles retry logic (3 attempts with 
    exponential backoff). The handler just executes and returns success/error.
```

---

## File Structure

```
your_bot/
├─ bot.py                           # Main bot file
├─ config/
│   └─ schedulezero.yaml           # ScheduleZero config
├─ cogs/
│   ├─ __init__.py
│   ├─ schedulezero_cog.py         # Core ScheduleZero cog
│   └─ sprockets/
│       ├─ __init__.py
│       ├─ announcement_sprocket.py  # Announcement jobs
│       ├─ moderation_sprocket.py    # Moderation jobs
│       └─ custom_sprocket.py        # Your custom jobs
```

---

## Quick Start

### 1. Setup Bot with ScheduleZeroCog

```python
# bot.py
import discord
from discord.ext import commands

bot = discord.Bot()

# CRITICAL: Load ScheduleZeroCog FIRST
bot.load_extension("cogs.schedulezero_cog")

# Load sprockets
bot.load_extension("cogs.sprockets.announcement_sprocket")
bot.load_extension("cogs.sprockets.moderation_sprocket")

bot.run(TOKEN)
```

### 2. Create Config File

```yaml
# config/schedulezero.yaml
handler_id: "my-discord-bot"
handler_port: 5000
server_address: "tcp://127.0.0.1:4242"
```

### 3. Run Everything

```bash
# Terminal 1: Start ScheduleZero server
poetry run python -m schedule_zero.tornado_app_server

# Terminal 2: Start Discord bot
python bot.py
```

---

## Creating a Custom Sprocket

### Sprocket Template

```python
# cogs/sprockets/custom_sprocket.py
import logging
import discord
from discord.ext import commands
from typing import Dict, Any

logger = logging.getLogger("CustomSprocket")

# =============================================================================
# Job Methods (called by ScheduleZero)
# =============================================================================

async def my_custom_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Your custom scheduled job.
    
    Params:
        channel_id: int
        custom_param: str
    
    Returns:
        Dict with results
    """
    channel_id = params.get("channel_id")
    custom_param = params.get("custom_param")
    
    # Access bot context
    channel = bot.get_channel(channel_id)
    
    # Do something with Discord API
    message = await channel.send(f"Custom job executed: {custom_param}")
    
    logger.info(f"Custom job executed")
    
    return {
        "message_id": message.id,
        "result": "success"
    }

# You can have multiple job methods
async def another_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """Another job."""
    # Your code here
    return {"status": "ok"}

# =============================================================================
# Sprocket Cog (registers methods)
# =============================================================================

class CustomSprocket(commands.Cog):
    """Your custom sprocket."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        logger.info("CustomSprocket initialized")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Register sprocket methods when bot is ready."""
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if not schedulezero_cog:
            logger.error("ScheduleZeroCog not found! Load it first.")
            return
        
        # Register your job methods
        schedulezero_cog.register_sprocket("my_custom_job", my_custom_job)
        schedulezero_cog.register_sprocket("another_job", another_job)
        
        logger.info("CustomSprocket methods registered (2 methods)")
    
    def cog_unload(self):
        """Unregister when cog is unloaded."""
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if schedulezero_cog:
            schedulezero_cog.unregister_sprocket("my_custom_job")
            schedulezero_cog.unregister_sprocket("another_job")
        
        logger.info("CustomSprocket methods unregistered")

def setup(bot: discord.Bot):
    """Setup function (called by bot.load_extension)."""
    bot.add_cog(CustomSprocket(bot))
    logger.info("CustomSprocket loaded")
```

### Load Your Sprocket

```python
# In bot.py
bot.load_extension("cogs.sprockets.custom_sprocket")

# Or dynamically via Discord command:
# /load_sprocket custom
```

---

## Sprocket Best Practices

### 1. Job Method Signature

All job methods must follow this signature:

```python
async def job_name(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job description.
    
    Params:
        param1: type - Description
        param2: type - Description
    
    Returns:
        Dict with result data
    """
    pass
```

### 2. Error Handling

Always handle errors and return useful information:

```python
async def safe_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        channel = bot.get_channel(params["channel_id"])
        if not channel:
            return {"error": "Channel not found"}
        
        # Do work
        result = await channel.send("Hello")
        
        return {"success": True, "message_id": result.id}
    
    except KeyError as e:
        return {"error": f"Missing parameter: {e}"}
    
    except discord.Forbidden:
        return {"error": "Bot lacks permissions"}
    
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        return {"error": str(e)}
```

### 3. Parameter Validation

Validate parameters at the start:

```python
async def validated_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    # Required parameters
    required = ["channel_id", "message"]
    missing = [p for p in required if p not in params]
    if missing:
        return {"error": f"Missing parameters: {missing}"}
    
    # Type validation
    if not isinstance(params["channel_id"], int):
        return {"error": "channel_id must be an integer"}
    
    # Proceed with job
    # ...
```

### 4. Rate Limiting

Respect Discord rate limits:

```python
import asyncio

async def bulk_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    channel_ids = params["channel_ids"]
    
    results = []
    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        await channel.send("Message")
        
        # Wait between operations
        await asyncio.sleep(1)  # 1 second delay
        
        results.append(channel_id)
    
    return {"sent_count": len(results)}
```

### 5. Logging

Use structured logging:

```python
logger.info(f"Job started: {params}")
logger.info(f"Sent message to #{channel.name} ({channel.id})")
logger.warning(f"Channel not found: {channel_id}")
logger.error(f"Failed to send message: {e}", exc_info=True)
```

---

## Scheduling Jobs from Discord

### Via ScheduleZero API (Recommended)

```python
import requests
import time

@bot.slash_command(name="schedule_announcement")
async def schedule_announcement(
    ctx: discord.ApplicationContext,
    channel: discord.TextChannel,
    message: str,
    minutes: int
):
    """Schedule an announcement."""
    await ctx.defer()
    
    # Calculate run time
    run_time = int(time.time()) + (minutes * 60)
    
    # Schedule via API
    job_data = {
        "handler_id": "my-discord-bot",
        "method": "send_announcement",  # Sprocket method name
        "params": {
            "channel_id": channel.id,
            "message": message
        },
        "trigger": {
            "type": "date",
            "args": {
                "run_date": run_time
            }
        }
    }
    
    response = requests.post("http://localhost:8888/api/jobs", json=job_data)
    result = response.json()
    
    await ctx.followup.send(f"✅ Scheduled! Job ID: {result['job_id']}")
```

---

## Dynamic Loading/Unloading

### Load Sprocket at Runtime

```python
# Via Discord command
@bot.slash_command(name="load_sprocket")
async def load_sprocket(ctx, sprocket_name: str):
    try:
        bot.load_extension(f"cogs.sprockets.{sprocket_name}_sprocket")
        
        # Re-register handler to update sprockets list
        schedulezero_cog = bot.get_cog("ScheduleZeroCog")
        schedulezero_cog.handler.stop()
        await asyncio.sleep(1)
        schedulezero_cog.handler.start()
        
        await ctx.respond(f"✅ Loaded: {sprocket_name}")
    except Exception as e:
        await ctx.respond(f"❌ Failed: {e}")
```

### Reload After Changes

```python
# During development
bot.reload_extension("cogs.sprockets.custom_sprocket")
```

---

## Built-in Sprockets

### AnnouncementSprocket

**Methods:**
- `send_announcement`: Send message with role mentions
- `send_embed_announcement`: Send rich embed
- `send_to_multiple_channels`: Broadcast to multiple channels

**Example:**
```json
{
  "handler_id": "my-bot",
  "method": "send_embed_announcement",
  "params": {
    "channel_id": 123456789,
    "title": "Server Update",
    "description": "New features available!",
    "color": 3447003,
    "fields": [
      {"name": "Feature 1", "value": "Description", "inline": false}
    ]
  },
  "trigger": {
    "type": "cron",
    "args": {"hour": 12, "minute": 0}
  }
}
```

### ModerationSprocket

**Methods:**
- `cleanup_messages`: Delete old messages
- `add_role_scheduled`: Add role to users
- `remove_role_scheduled`: Remove role from users
- `lockdown_channel`: Lock channel
- `unlock_channel`: Unlock channel
- `send_dm`: Send DM to user

**Example:**
```json
{
  "handler_id": "my-bot",
  "method": "cleanup_messages",
  "params": {
    "channel_id": 123456789,
    "limit": 100,
    "age_days": 30
  },
  "trigger": {
    "type": "cron",
    "args": {"day": 1, "hour": 3}
  }
}
```

---

## FAQ

### Q: Can sprockets be loaded/unloaded without restarting the bot?

**A:** Yes! Use `bot.load_extension()` and `bot.unload_extension()`. After loading/unloading, reload the handler to update ScheduleZero server registration.

### Q: Can one sprocket call methods from another sprocket?

**A:** Yes, through the sprocket registry:

```python
schedulezero_cog = bot.get_cog("ScheduleZeroCog")
other_method = schedulezero_cog.handler.sprockets["other_method"]
result = await other_method(bot, params)
```

### Q: Can sprockets have slash commands?

**A:** Yes! Sprocket cogs are regular Discord cogs:

```python
class CustomSprocket(commands.Cog):
    @discord.slash_command(name="custom_command")
    async def custom_command(self, ctx):
        await ctx.respond("Custom command!")
```

### Q: Do sprockets need to be async?

**A:** No! Sprockets can be sync or async. The handler will detect and handle appropriately:

```python
# Async (preferred for Discord operations)
async def async_job(bot, params):
    channel = bot.get_channel(params["channel_id"])
    await channel.send("Hello")
    return {"status": "sent"}

# Sync (for non-Discord operations)
def sync_job(bot, params):
    result = some_calculation(params["value"])
    return {"result": result}
```

### Q: How do I test a sprocket locally?

**A:** Create a test script:

```python
import asyncio
from unittest.mock import Mock

# Mock bot
bot = Mock()
bot.get_channel = Mock(return_value=Mock())

# Test your sprocket method
from cogs.sprockets.custom_sprocket import my_custom_job

result = asyncio.run(my_custom_job(bot, {"channel_id": 123}))
print(result)
```

---

## Troubleshooting

### Sprocket not registered

**Problem:** Sprocket loaded but methods not available in ScheduleZero.

**Solution:**
1. Check logs for registration success
2. Verify `on_ready` was called
3. Use `/schedule reload` to re-register handler
4. Check sprocket name matches method name exactly

### Handler not starting

**Problem:** ScheduleZeroCog loaded but handler thread not starting.

**Solution:**
1. Check `config/schedulezero.yaml` exists
2. Verify ScheduleZero server is running
3. Check port conflicts (default 5000)
4. Look for errors in thread startup logs

### Job execution fails

**Problem:** Job scheduled but execution returns error.

**Solution:**
1. Check bot has required permissions
2. Verify channel/user/role IDs are correct
3. Check sprocket method error handling
4. Review ScheduleZero server logs for ZMQ errors

---

## Next Steps

1. ✅ Create your own custom sprocket
2. ✅ Add slash commands to schedule jobs from Discord
3. ✅ Build a library of reusable sprockets
4. ✅ Share sprockets with the community!

Happy scheduling! 🚀
