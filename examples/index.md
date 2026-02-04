# ScheduleZero Discord Integration Examples

This directory contains multiple approaches for integrating ScheduleZero with Discord.py bots.

## 📁 Directory Structure

```
examples/
├── README.md                                    # This file
├── config/
│   └── schedulezero.yaml                       # Configuration template
├── cogs/
│   ├── schedulezero_cog.py                     # Main ScheduleZero cog
│   └── sprockets/
│       ├── announcement_sprocket.py            # Announcement jobs
│       └── moderation_sprocket.py              # Moderation jobs
├── discord_handler.py                          # Asyncio task approach
├── discord_handler_threaded.py                 # Threaded approach
├── discord_bot_example.py                      # Simple bot (asyncio)
├── discord_bot_threaded_example.py             # Simple bot (threaded)
├── discord_bot_with_cogs.py                    # Bot with cog architecture
├── discord_jobs.yaml                           # Job configuration examples
├── DISCORD_INTEGRATION.md                      # Original asyncio docs
├── DISCORD_INTEGRATION_COMPARISON.md           # Asyncio vs Threaded
└── COG_SPROCKET_ARCHITECTURE.md                # Cog architecture guide
```

## 🏆 Recommended: Cog + Sprocket Architecture

**Best for most Discord bots** - Modular, dynamic, organized.

### Files
- `cogs/schedulezero_cog.py` - Main cog with handler thread
- `cogs/sprockets/announcement_sprocket.py` - Announcement jobs
- `cogs/sprockets/moderation_sprocket.py` - Moderation jobs
- `discord_bot_with_cogs.py` - Example bot
- `COG_SPROCKET_ARCHITECTURE.md` - Full documentation

### Quick Start

```python
# bot.py
import discord

bot = discord.Bot()

# Load ScheduleZero cog FIRST
bot.load_extension("cogs.schedulezero_cog")

# Load sprockets (can be loaded dynamically later)
bot.load_extension("cogs.sprockets.announcement_sprocket")
bot.load_extension("cogs.sprockets.moderation_sprocket")

bot.run(TOKEN)
```

### Why Use This?

✅ **Dynamic Loading** - Load/unload sprockets without bot restart  
✅ **Organized** - Jobs grouped by functionality  
✅ **Reusable** - Share sprockets across bots  
✅ **Native Pattern** - Uses Discord.py cog system  
✅ **Scalable** - Add new job types easily  

---

## 🔧 Alternative: Standalone Threaded Handler

**Best for simple bots** - Single handler file, thread isolation.

### Files
- `discord_handler_threaded.py` - Handler class
- `discord_bot_threaded_example.py` - Example bot
- `DISCORD_INTEGRATION_COMPARISON.md` - Comparison docs

### Quick Start

```python
# bot.py
import discord
from discord_handler_threaded import DiscordScheduleHandler

bot = discord.Bot()
handler = None

@bot.event
async def on_ready():
    global handler
    handler = DiscordScheduleHandler(bot)
    handler.start()  # Starts thread

bot.run(TOKEN)
```

### Why Use This?

✅ **Simple** - One file, easy to understand  
✅ **Isolated** - Thread won't block bot  
✅ **Robust** - Gemini-recommended approach  
✅ **Sync ZMQ** - Simpler than async  

---

## 🚀 Alternative: Asyncio Task Handler

**Best for personal bots** - Simplest code, direct awaits.

### Files
- `discord_handler.py` - Handler class
- `discord_bot_example.py` - Example bot
- `DISCORD_INTEGRATION.md` - Original docs

### Quick Start

```python
# bot.py
import discord
from discord_handler import DiscordScheduleHandler

bot = discord.Bot()

@bot.event
async def on_ready():
    handler = DiscordScheduleHandler(bot)
    await handler.start()  # Creates asyncio.Task

bot.run(TOKEN)
```

### Why Use This?

✅ **Simplest** - Direct awaits, no thread complexity  
✅ **Lightweight** - No thread overhead  
✅ **Fast** - No thread context switching  

---

## 📊 Comparison Table

| Feature | Cog + Sprocket | Threaded Handler | Asyncio Task |
|---------|----------------|------------------|--------------|
| **Modularity** | ✅ Excellent | ⚠️ Monolithic | ⚠️ Monolithic |
| **Dynamic Loading** | ✅ Yes | ❌ No | ❌ No |
| **Code Organization** | ✅ By functionality | ⚠️ Single file | ⚠️ Single file |
| **Isolation** | ✅ Thread | ✅ Thread | ⚠️ Same loop |
| **Complexity** | ⚠️ Medium | ✅ Simple | ✅ Simplest |
| **Reusability** | ✅ Share sprockets | ⚠️ Copy file | ⚠️ Copy file |
| **Best For** | Production bots | Simple bots | Personal bots |

---

## 🎯 Which Should I Use?

### Use **Cog + Sprocket** if:
- ✅ Building a production bot
- ✅ Want organized, modular code
- ✅ Need to add/remove job types dynamically
- ✅ Planning to share job modules
- ✅ Team development

### Use **Threaded Handler** if:
- ✅ Simple bot with fixed job types
- ✅ Want maximum stability (thread isolation)
- ✅ Prefer Gemini's recommendation
- ✅ Don't need dynamic loading

### Use **Asyncio Task** if:
- ✅ Personal/hobby bot
- ✅ Want simplest possible code
- ✅ Don't mind shared event loop
- ✅ Comfortable with async Python

---

## 🚦 Setup Instructions

### 1. Prerequisites

```bash
# Install dependencies
pip install discord.py pyyaml pyzmq requests

# Or with poetry (in ScheduleZero project)
poetry install
```

### 2. Configure

Copy and edit the config file:

```bash
cp examples/config/schedulezero.yaml config/schedulezero.yaml
```

Edit values:
- `handler_id`: Unique bot identifier
- `handler_port`: Unique port (5000, 5001, etc.)
- `server_address`: ScheduleZero server ZMQ address

### 3. Start ScheduleZero Server

```bash
# In ScheduleZero project directory
poetry run python -m schedule_zero.tornado_app_server

# Or with specific deployment
export SCHEDULEZERO_DEPLOYMENT=production
poetry run python -m schedule_zero.tornado_app_server
```

### 4. Start Your Bot

```bash
# Set Discord token
export DISCORD_TOKEN="your-bot-token"

# Run bot
python discord_bot_with_cogs.py          # Cog architecture
# OR
python discord_bot_threaded_example.py   # Threaded handler
# OR
python discord_bot_example.py            # Asyncio task
```

---

## 📝 Creating Custom Sprockets

### 1. Create Sprocket File

```python
# cogs/sprockets/custom_sprocket.py
import discord
from discord.ext import commands
from typing import Dict, Any

async def my_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """Your custom job."""
    channel_id = params["channel_id"]
    channel = bot.get_channel(channel_id)
    await channel.send("Custom job!")
    return {"status": "success"}

class CustomSprocket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        cog = self.bot.get_cog("ScheduleZeroCog")
        cog.register_sprocket("my_job", my_job)

def setup(bot):
    bot.add_cog(CustomSprocket(bot))
```

### 2. Load Sprocket

```python
# In bot
bot.load_extension("cogs.sprockets.custom_sprocket")

# Or dynamically via Discord
# /load_sprocket custom
```

### 3. Schedule Job

```python
# Via ScheduleZero API
import requests

job = {
    "handler_id": "my-bot",
    "method": "my_job",
    "params": {"channel_id": 123456789},
    "trigger": {"type": "cron", "args": {"hour": 12}}
}

requests.post("http://localhost:8888/api/jobs", json=job)
```

---

## 🐛 Troubleshooting

### Handler not registering

**Problem:** Bot starts but handler not registered with ScheduleZero.

**Solutions:**
1. Check ScheduleZero server is running
2. Verify `server_address` in config
3. Check port conflicts
4. Look for errors in bot logs

### Sprockets not loading

**Problem:** Sprocket cog loaded but methods not registered.

**Solutions:**
1. Load `ScheduleZeroCog` BEFORE sprockets
2. Check `on_ready` was called
3. Use `/schedule reload` to re-register
4. Verify method names match exactly

### Jobs not executing

**Problem:** Job scheduled but not executing.

**Solutions:**
1. Check handler registration: `/schedule status`
2. Verify sprocket method exists
3. Check bot permissions (channel access, etc.)
4. Review ScheduleZero server logs
5. Test method manually

### Thread issues

**Problem:** Handler thread crashes or hangs.

**Solutions:**
1. Check for unhandled exceptions in sprocket methods
2. Add timeout to `_run_coro_safe()` calls
3. Verify ZMQ context is valid
4. Restart bot to recreate thread

---

## 📚 Documentation

- **[COG_SPROCKET_ARCHITECTURE.md](COG_SPROCKET_ARCHITECTURE.md)** - Complete cog/sprocket guide
- **[DISCORD_INTEGRATION_COMPARISON.md](DISCORD_INTEGRATION_COMPARISON.md)** - Compare threaded vs asyncio
- **[DISCORD_INTEGRATION.md](DISCORD_INTEGRATION.md)** - Original asyncio documentation

---

## 🤝 Contributing

Have a useful sprocket? Share it!

1. Create your sprocket following the template
2. Add documentation in docstrings
3. Test thoroughly
4. Submit PR to ScheduleZero examples

---

## 💡 Example Use Cases

### Daily Server Announcements
```python
# AnnouncementSprocket
# Schedule daily announcement at 9 AM
job = {
    "method": "send_announcement",
    "params": {
        "channel_id": 123456789,
        "message": "Good morning! Daily quest has reset.",
        "role_id": 987654321
    },
    "trigger": {"type": "cron", "args": {"hour": 9}}
}
```

### Weekly Channel Cleanup
```python
# ModerationSprocket
# Clean old messages every Sunday at 3 AM
job = {
    "method": "cleanup_messages",
    "params": {
        "channel_id": 123456789,
        "limit": 1000,
        "age_days": 30
    },
    "trigger": {"type": "cron", "args": {"day_of_week": 0, "hour": 3}}
}
```

### Timed Role Assignment
```python
# ModerationSprocket
# Add "Event Participant" role during event
job = {
    "method": "add_role_scheduled",
    "params": {
        "guild_id": 123456789,
        "user_ids": [111, 222, 333],
        "role_id": 999888777
    },
    "trigger": {"type": "date", "args": {"run_date": 1730200000}}
}
```

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/esotericbyte/ScheduleZero/issues)
- **Docs:** See markdown files in this directory
- **Examples:** All example files in this directory are runnable

---

**Happy Scheduling!** 🚀
