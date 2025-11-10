# Discord.py Integration with ScheduleZero

## Architecture Overview

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│  Discord Bot Process (Single Event Loop)                │
│                                                          │
│  ┌────────────────────┐    ┌─────────────────────────┐ │
│  │  discord.py        │    │  ScheduleZero Handler   │ │
│  │  (Main Task)       │◄───┤  (Asyncio Task)         │ │
│  │                    │    │                          │ │
│  │  • Commands        │    │  • ZMQ Client (async)   │ │
│  │  • Events          │    │  • Job Execution        │ │
│  │  • Bot Context     │    │  • Same Event Loop!     │ │
│  └────────────────────┘    └──────────┬──────────────┘ │
│                                       │                 │
└───────────────────────────────────────┼─────────────────┘
                                        │ ZMQ (async)
                                        ▼
                         ┌──────────────────────────────┐
                         │  ScheduleZero Server         │
                         │  (Separate Process)          │
                         │                              │
                         │  • APScheduler               │
                         │  • Job Queue                 │
                         │  • Schedule Management       │
                         └──────────────────────────────┘
```

## Key Design Decisions

### 1. **Asyncio Task, NOT Thread**

**Why:** Discord.py uses asyncio and expects all operations to happen in its event loop.

✅ **Handler runs as `asyncio.Task`**
- Shares the same event loop as discord.py
- Can directly `await` Discord operations
- No thread-safety issues

❌ **NOT a separate thread**
- Threading with asyncio is complex
- Would need thread-safe queues
- Discord operations might fail across threads

### 2. **Handler Executes Jobs Directly**

**The bot's main loop DOES handle the actions!**

```python
# In DiscordScheduleHandler._execute_job()
async def _execute_job(self, request):
    method = self.send_message  # This is a coroutine
    result = await method(params)  # Executes in bot's event loop!
    return result
```

**Flow:**
1. ScheduleZero server sends job request → ZMQ
2. Handler receives request → Same event loop as bot
3. Handler calls job method → `await bot.send_message()`
4. Discord operation executes → Using bot's context
5. Result returned → Back to ScheduleZero

### 3. **Relationship Between Handler and Bot**

```python
class DiscordScheduleHandler:
    def __init__(self, bot: discord.Bot):
        self.bot = bot  # Direct reference!
    
    async def send_message(self, params):
        # Uses bot directly - same process, same memory!
        channel = self.bot.get_channel(params["channel_id"])
        await channel.send(params["content"])
```

**Relationship:**
- Handler has **direct reference** to bot object
- Handler runs **in same process**
- Handler uses **bot's event loop**
- Handler can access **all bot attributes** (guilds, users, channels)

## Setup Instructions

### 1. Install Dependencies

```powershell
pip install discord.py pyzmq pyyaml
```

### 2. Start ScheduleZero Server

```powershell
# Terminal 1: Start server
poetry run python -m schedule_zero.server
```

### 3. Create Discord Bot

```python
import discord
from discord_handler import DiscordScheduleHandler

bot = discord.Bot()

@bot.event
async def on_ready():
    # Handler starts as asyncio task
    handler = DiscordScheduleHandler(bot)
    await handler.start()  # Registers with ScheduleZero
    print("Bot and scheduler ready!")

bot.run(TOKEN)
```

### 4. Schedule Jobs

**Option A: Via Discord Commands**
```python
@bot.slash_command()
async def remind(ctx, message: str, minutes: int):
    # Schedule via API
    requests.post("http://127.0.0.1:8888/api/schedule", json={
        "handler_id": "discord-bot",
        "job_method": "send_message",
        "job_params": {"channel_id": ctx.channel.id, "content": message},
        "trigger": {"type": "date", "run_date": time + minutes}
    })
```

**Option B: Via ScheduleZero API**
```powershell
curl -X POST http://127.0.0.1:8888/api/schedule -H "Content-Type: application/json" -d '{
  "handler_id": "discord-bot",
  "job_method": "send_message",
  "job_params": {"channel_id": 123456, "content": "Scheduled message!"},
  "trigger": {"type": "interval", "hours": 1}
}'
```

## Available Job Methods

### `send_message`
Send a text message to a channel.
```yaml
params:
  channel_id: 123456789
  content: "Hello world!"
```

### `send_embed`
Send a rich embed.
```yaml
params:
  channel_id: 123456789
  title: "Announcement"
  description: "Important update"
  color: 0x00ff00
```

### `update_status`
Change bot's presence/status.
```yaml
params:
  activity_type: "playing"  # or "watching", "listening"
  name: "with code"
```

### `schedule_announcement`
Send announcement with role mention.
```yaml
params:
  channel_id: 123456789
  message: "Event starting soon!"
  role_id: 987654321  # Optional
```

### `cleanup_old_messages`
Delete old messages from a channel.
```yaml
params:
  channel_id: 123456789
  limit: 100
  age_days: 7
```

### `update_role`
Add/remove role from user.
```yaml
params:
  guild_id: 123456789
  user_id: 987654321
  role_id: 111111111
  action: "add"  # or "remove"
```

## Adding Custom Job Methods

Just add async methods to the handler class:

```python
class DiscordScheduleHandler:
    # ... existing code ...
    
    async def my_custom_job(self, params: Dict[str, Any]):
        """Your custom job logic."""
        # Access bot directly
        guild = self.bot.get_guild(params["guild_id"])
        
        # Do async Discord operations
        await guild.create_text_channel("scheduled-channel")
        
        return {"status": "success"}
    
    def _get_available_methods(self):
        return {
            # ... existing methods ...
            "my_custom_job": self.my_custom_job,  # Register it!
        }
```

## Event Loop Architecture

### Why This Works

```python
# Discord.py starts the event loop
bot.run(TOKEN)  # Creates event loop, runs until done

# Inside on_ready (already in the loop):
@bot.event
async def on_ready():
    handler = DiscordScheduleHandler(bot)
    await handler.start()  # Creates asyncio.Task
    # Task runs concurrently with Discord.py!
```

**Both run in the same loop:**
- Discord.py processes Discord events
- Handler processes scheduled job requests
- They can call each other safely
- No race conditions or threading issues

### Execution Flow

1. **Discord.py receives Discord event** → Processes in event loop
2. **Handler receives job request** → Processes in SAME event loop
3. **Job calls Discord API** → `await bot.channel.send()` works!
4. **Result returns** → Back through ZMQ to ScheduleZero

## Benefits of This Architecture

✅ **Simple** - No threading complexity  
✅ **Safe** - No race conditions  
✅ **Direct** - Handler has full bot access  
✅ **Async** - Everything uses `await` properly  
✅ **Integrated** - Jobs run in bot's context  
✅ **Scalable** - ScheduleZero handles scheduling  

## Common Patterns

### Daily Announcements
```python
# Schedule via API or Discord command
{
    "trigger": {"type": "cron", "hour": 12, "minute": 0},
    "job_method": "send_message",
    "job_params": {"channel_id": 123, "content": "Daily update!"}
}
```

### Event Reminders
```python
# 5 minutes before event
{
    "trigger": {"type": "date", "run_date": event_time - timedelta(minutes=5)},
    "job_method": "schedule_announcement",
    "job_params": {"channel_id": 123, "message": "Event starts in 5 min!", "role_id": 456}
}
```

### Status Rotation
```python
# Change status every hour
{
    "trigger": {"type": "interval", "hours": 1},
    "job_method": "update_status",
    "job_params": {"activity_type": "playing", "name": f"Hour {hour}"}
}
```

## Troubleshooting

### Handler Won't Register
- Check ScheduleZero server is running
- Verify ZMQ ports aren't blocked
- Check `server_address` in handler config

### Jobs Don't Execute
- Check handler task is running: `handler.running == True`
- Verify job method name is correct
- Check handler logs for errors

### Discord API Errors
- Ensure bot has proper permissions
- Check channel/guild IDs are valid
- Verify bot is in the guild

## Summary

**Thread vs Task:** Handler is an **asyncio.Task**, not a thread  
**Relationship:** Handler has **direct reference** to bot, runs in **same process**  
**Execution:** Bot's **event loop handles everything** - Discord events AND scheduled jobs  
**Communication:** ZMQ (async) for receiving jobs from ScheduleZero  
**Result:** Clean, safe, integrated scheduling for Discord bots! 🤖📅
