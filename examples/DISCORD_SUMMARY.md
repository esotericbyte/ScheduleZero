# ScheduleZero Discord Integration - Complete Summary

## 🎯 Three Approaches Available

### 1. 🏆 Cog + Sprocket Architecture (RECOMMENDED)

**The "Professional Bot" Approach**

```
Discord Bot
├─ ScheduleZeroCog
│   └─ Handler Thread
│       └─ Sprocket Registry
└─ Sprockets (load/unload dynamically)
    ├─ AnnouncementSprocket
    ├─ ModerationSprocket  
    └─ YourCustomSprocket
```

**Example:**
```python
bot = discord.Bot()
bot.load_extension("cogs.schedulezero_cog")
bot.load_extension("cogs.sprockets.announcement_sprocket")
bot.run(TOKEN)
```

**Best for:**
- ✅ Production bots
- ✅ Multiple job types
- ✅ Team development
- ✅ Modular organization

**Files:**
- `cogs/schedulezero_cog.py`
- `cogs/sprockets/*.py`
- `discord_bot_with_cogs.py`

---

### 2. 🔧 Standalone Threaded Handler

**The "Gemini Recommended" Approach**

```
Discord Bot
├─ Main Event Loop
└─ ScheduleZero Handler Thread
    └─ Sync ZMQ + asyncio.run_coroutine_threadsafe()
```

**Example:**
```python
handler = DiscordScheduleHandler(bot)
handler.start()  # Thread
```

**Best for:**
- ✅ Simple bots
- ✅ Single handler file
- ✅ Maximum stability
- ✅ Thread isolation

**Files:**
- `discord_handler_threaded.py`
- `discord_bot_threaded_example.py`

---

### 3. 🚀 Asyncio Task Handler

**The "Simplest" Approach**

```
Discord Bot (Single Event Loop)
├─ discord.py
└─ ScheduleZero Handler (asyncio.Task)
    └─ Async ZMQ
```

**Example:**
```python
handler = DiscordScheduleHandler(bot)
await handler.start()  # Task
```

**Best for:**
- ✅ Personal bots
- ✅ Learning
- ✅ Simplest code
- ✅ Direct awaits

**Files:**
- `discord_handler.py`
- `discord_bot_example.py`

---

## 📊 Feature Comparison

| Feature | Cog+Sprocket | Threaded | Asyncio |
|---------|--------------|----------|---------|
| **Modularity** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Dynamic Loading** | ✅ Yes | ❌ No | ❌ No |
| **Simplicity** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Isolation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Reusability** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Lines of Code** | ~400 | ~490 | ~400 |

---

## 🎬 Quick Start (Cog Architecture)

### Step 1: Install Dependencies

```bash
pip install discord.py pyyaml pyzmq
```

### Step 2: Start ScheduleZero

```bash
poetry run python -m schedule_zero.tornado_app_server
```

### Step 3: Create Bot

```python
# bot.py
import discord
import os

bot = discord.Bot()

# Load ScheduleZero cog FIRST
bot.load_extension("cogs.schedulezero_cog")

# Load sprockets
bot.load_extension("cogs.sprockets.announcement_sprocket")
bot.load_extension("cogs.sprockets.moderation_sprocket")

bot.run(os.getenv("DISCORD_TOKEN"))
```

### Step 4: Configure

```yaml
# config/schedulezero.yaml
handler_id: "my-bot"
handler_port: 5000
server_address: "tcp://127.0.0.1:4242"
```

### Step 5: Run Bot

```bash
export DISCORD_TOKEN="your-token"
python bot.py
```

### Step 6: Use Commands

```
/schedule status          # Check handler status
/schedule sprockets       # List loaded sprockets
/load_sprocket custom     # Load custom sprocket
```

---

## 🔨 Creating a Custom Sprocket

### Template

```python
# cogs/sprockets/custom_sprocket.py
import logging
import discord
from discord.ext import commands
from typing import Dict, Any

logger = logging.getLogger("CustomSprocket")

# Job method (called by ScheduleZero)
async def my_job(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Your job logic here.
    
    Params:
        channel_id: int
        message: str
    
    Returns:
        Dict with results
    """
    channel = bot.get_channel(params["channel_id"])
    await channel.send(params["message"])
    
    return {"status": "success"}

# Sprocket cog
class CustomSprocket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        cog = self.bot.get_cog("ScheduleZeroCog")
        if cog:
            cog.register_sprocket("my_job", my_job)
            logger.info("CustomSprocket registered")
    
    def cog_unload(self):
        cog = self.bot.get_cog("ScheduleZeroCog")
        if cog:
            cog.unregister_sprocket("my_job")

def setup(bot):
    bot.add_cog(CustomSprocket(bot))
```

### Load It

```python
# In bot
bot.load_extension("cogs.sprockets.custom_sprocket")
```

### Schedule It

```bash
curl -X POST http://localhost:8888/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "handler_id": "my-bot",
    "method": "my_job",
    "params": {"channel_id": 123456789, "message": "Hello!"},
    "trigger": {"type": "cron", "args": {"hour": 12}}
  }'
```

---

## 🎯 Built-in Sprockets

### AnnouncementSprocket

**Methods:**
- `send_announcement` - Send message with mentions
- `send_embed_announcement` - Send rich embed
- `send_to_multiple_channels` - Broadcast

**Example:**
```json
{
  "method": "send_embed_announcement",
  "params": {
    "channel_id": 123456789,
    "title": "Update",
    "description": "New features!",
    "color": 3447003
  }
}
```

### ModerationSprocket

**Methods:**
- `cleanup_messages` - Delete old messages
- `add_role_scheduled` - Add role to users
- `remove_role_scheduled` - Remove role
- `lockdown_channel` - Lock channel
- `unlock_channel` - Unlock channel
- `send_dm` - Send DM

**Example:**
```json
{
  "method": "cleanup_messages",
  "params": {
    "channel_id": 123456789,
    "limit": 100,
    "age_days": 30
  }
}
```

---

## 📁 File Structure

```
your_bot/
├─ bot.py                          # Main bot
├─ config/
│   └─ schedulezero.yaml           # Config
├─ cogs/
│   ├─ schedulezero_cog.py        # Core cog
│   └─ sprockets/
│       ├─ announcement_sprocket.py
│       ├─ moderation_sprocket.py
│       └─ custom_sprocket.py     # Your sprockets
```

---

## 🐛 Common Issues

### Handler Not Registering

**Check:**
1. ScheduleZero server running?
2. Correct port in config?
3. Bot has `on_ready` fired?

**Fix:**
```python
# Check logs
# Use /schedule status
```

### Sprocket Not Found

**Check:**
1. Sprocket loaded?
2. `on_ready` called?
3. Method name matches?

**Fix:**
```python
# Reload handler
await ctx.invoke(bot.get_command("schedule reload"))
```

### Job Fails

**Check:**
1. Bot permissions
2. Channel/role/user exists
3. Sprocket method has error handling

**Fix:**
```python
# Add try/except in sprocket method
try:
    # job code
    return {"status": "success"}
except Exception as e:
    logger.error(f"Failed: {e}")
    return {"error": str(e)}
```

---

## 📚 Documentation Files

- **[README.md](README.md)** - Overview & quick start
- **[COG_SPROCKET_ARCHITECTURE.md](COG_SPROCKET_ARCHITECTURE.md)** - Complete guide
- **[DISCORD_INTEGRATION_COMPARISON.md](DISCORD_INTEGRATION_COMPARISON.md)** - Compare approaches
- **[DISCORD_INTEGRATION.md](DISCORD_INTEGRATION.md)** - Asyncio details

---

## 💡 Real-World Examples

### Daily Reset Announcement

```python
# 9 AM every day
{
  "method": "send_announcement",
  "params": {
    "channel_id": 123456789,
    "message": "Daily quests have reset!",
    "role_id": 987654321
  },
  "trigger": {"type": "cron", "args": {"hour": 9}}
}
```

### Weekly Cleanup

```python
# Sunday 3 AM
{
  "method": "cleanup_messages",
  "params": {
    "channel_id": 123456789,
    "age_days": 30
  },
  "trigger": {"type": "cron", "args": {"day_of_week": 0, "hour": 3}}
}
```

### Event Role Management

```python
# Add role at event start
{
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

## ✅ Decision Matrix

**Choose Cog + Sprocket if:**
- [ ] Building a production bot
- [ ] Need multiple job types
- [ ] Want dynamic loading
- [ ] Team development
- [ ] Plan to add features over time

**Choose Threaded Handler if:**
- [ ] Simple bot with fixed jobs
- [ ] Want maximum stability
- [ ] Prefer single handler file
- [ ] Don't need dynamic loading

**Choose Asyncio Task if:**
- [ ] Personal/hobby bot
- [ ] Want simplest code
- [ ] Learning Discord bots
- [ ] Don't mind shared event loop

---

**Ready to build? Start with the Cog + Sprocket architecture!** 🚀

See [COG_SPROCKET_ARCHITECTURE.md](COG_SPROCKET_ARCHITECTURE.md) for complete tutorial.
