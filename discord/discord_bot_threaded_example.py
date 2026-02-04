"""
Discord Bot Example - Threaded Handler

Demonstrates ScheduleZero integration with Discord.py using a separate thread.
This is the recommended approach for production bots.

Features:
- Threaded ZMQ handler for better isolation
- Slash commands to schedule messages and status updates
- Clean shutdown on bot close
- Robust error handling

Setup:
1. Install dependencies: pip install discord.py pyyaml pyzmq
2. Set DISCORD_TOKEN environment variable
3. Start ScheduleZero server: poetry run python -m schedule_zero.tornado_app_server
4. Run this bot: python discord_bot_threaded_example.py

Architecture:
    Bot Process
    ├─ Discord.py (main event loop)
    ├─ Handler Thread (daemon)
    │   └─ Synchronous ZMQ
    └─ Communication via run_coroutine_threadsafe()
"""
import os
import discord
from discord import ApplicationContext, Option
import logging
import asyncio
import requests
from discord_handler_threaded import DiscordScheduleHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable must be set")

SCHEDULEZERO_API = "http://localhost:8888"
HANDLER_PORT = 5000

# Create bot
bot = discord.Bot(intents=discord.Intents.default())

# Global handler reference
handler: DiscordScheduleHandler = None


@bot.event
async def on_ready():
    """Start the ScheduleZero handler when bot is ready."""
    global handler
    
    logger.info(f"Bot connected as {bot.user}")
    
    # Start handler thread
    handler = DiscordScheduleHandler(
        bot=bot,
        handler_id=f"discord-{bot.user.id}",
        handler_port=HANDLER_PORT,
        config_file="discord_jobs.yaml"
    )
    handler.start()  # Starts daemon thread
    
    logger.info(f"ScheduleZero handler started in thread: {handler.handler_thread.name}")
    logger.info(f"Handler listening on port {HANDLER_PORT}")
    
    # Wait a moment for registration
    await asyncio.sleep(1)
    
    # Verify handler is registered
    try:
        response = requests.get(f"{SCHEDULEZERO_API}/api/handlers")
        handlers = response.json()
        handler_ids = [h["handler_id"] for h in handlers]
        if handler.handler_id in handler_ids:
            logger.info("✅ Handler successfully registered with ScheduleZero")
        else:
            logger.warning("⚠️ Handler not found in registered handlers")
    except Exception as e:
        logger.error(f"Could not verify handler registration: {e}")


@bot.event
async def on_close():
    """Clean shutdown of handler thread."""
    global handler
    if handler:
        logger.info("Stopping ScheduleZero handler...")
        handler.stop()  # Stops thread cleanly
        logger.info("Handler stopped")


# ============================================================================
# Slash Commands
# ============================================================================

@bot.slash_command(name="schedule_message", description="Schedule a message for later")
async def schedule_message(
    ctx: ApplicationContext,
    seconds: Option(int, "Seconds from now", required=True),
    message: Option(str, "Message to send", required=True)
):
    """Schedule a message to be sent after a delay."""
    await ctx.defer()  # Defer response while we schedule
    
    channel_id = ctx.channel_id
    
    try:
        # Calculate run time (current time + seconds)
        import time
        run_time = int(time.time()) + seconds
        
        # Schedule via ScheduleZero API
        job_data = {
            "handler_id": handler.handler_id,
            "method": "send_message",
            "params": {
                "channel_id": channel_id,
                "content": message
            },
            "trigger": {
                "type": "date",
                "args": {
                    "run_date": run_time  # Unix timestamp
                }
            }
        }
        
        response = requests.post(f"{SCHEDULEZERO_API}/api/jobs", json=job_data)
        response.raise_for_status()
        result = response.json()
        
        job_id = result.get("job_id")
        await ctx.followup.send(
            f"✅ Message scheduled!\n"
            f"Job ID: `{job_id}`\n"
            f"Will send in {seconds} seconds"
        )
        
        logger.info(f"Scheduled message job: {job_id}")
    
    except Exception as e:
        await ctx.followup.send(f"❌ Error scheduling message: {e}")
        logger.error(f"Failed to schedule message: {e}")


@bot.slash_command(name="schedule_status", description="Schedule a status update")
async def schedule_status(
    ctx: ApplicationContext,
    seconds: Option(int, "Seconds from now", required=True),
    activity_type: Option(str, "Activity type", choices=["playing", "watching", "listening"], required=True),
    status_text: Option(str, "Status text", required=True)
):
    """Schedule a bot status update."""
    await ctx.defer()
    
    try:
        import time
        run_time = int(time.time()) + seconds
        
        job_data = {
            "handler_id": handler.handler_id,
            "method": "update_status",
            "params": {
                "activity_type": activity_type,
                "name": status_text
            },
            "trigger": {
                "type": "date",
                "args": {
                    "run_date": run_time
                }
            }
        }
        
        response = requests.post(f"{SCHEDULEZERO_API}/api/jobs", json=job_data)
        response.raise_for_status()
        result = response.json()
        
        job_id = result.get("job_id")
        await ctx.followup.send(
            f"✅ Status update scheduled!\n"
            f"Job ID: `{job_id}`\n"
            f"Will update in {seconds} seconds to: {activity_type} {status_text}"
        )
        
        logger.info(f"Scheduled status job: {job_id}")
    
    except Exception as e:
        await ctx.followup.send(f"❌ Error scheduling status: {e}")
        logger.error(f"Failed to schedule status: {e}")


@bot.slash_command(name="handler_status", description="Check handler status")
async def handler_status(ctx: ApplicationContext):
    """Check if handler is registered and working."""
    await ctx.defer()
    
    try:
        # Check handler registration
        response = requests.get(f"{SCHEDULEZERO_API}/api/handlers")
        handlers = response.json()
        
        handler_info = next(
            (h for h in handlers if h["handler_id"] == handler.handler_id),
            None
        )
        
        if handler_info:
            methods = ", ".join(handler_info["methods"][:5])  # First 5 methods
            await ctx.followup.send(
                f"✅ Handler is registered!\n"
                f"**ID:** `{handler.handler_id}`\n"
                f"**Address:** `{handler.handler_address}`\n"
                f"**Thread:** `{handler.handler_thread.name}` (alive: {handler.handler_thread.is_alive()})\n"
                f"**Methods:** {methods}, ..."
            )
        else:
            await ctx.followup.send(
                f"⚠️ Handler not found in registry\n"
                f"**ID:** `{handler.handler_id}`\n"
                f"**Thread:** `{handler.handler_thread.name}` (alive: {handler.handler_thread.is_alive()})"
            )
    
    except Exception as e:
        await ctx.followup.send(f"❌ Error checking status: {e}")
        logger.error(f"Failed to check handler status: {e}")


@bot.slash_command(name="list_jobs", description="List scheduled jobs")
async def list_jobs(ctx: ApplicationContext):
    """List all scheduled jobs for this handler."""
    await ctx.defer()
    
    try:
        # Get all jobs
        response = requests.get(f"{SCHEDULEZERO_API}/api/jobs")
        all_jobs = response.json()
        
        # Filter to our handler
        our_jobs = [j for j in all_jobs if j.get("handler_id") == handler.handler_id]
        
        if not our_jobs:
            await ctx.followup.send("No scheduled jobs found for this handler")
            return
        
        # Format job list
        job_lines = []
        for job in our_jobs[:10]:  # Limit to 10
            job_id = job.get("job_id", "unknown")
            method = job.get("method", "unknown")
            next_run = job.get("next_run_time", "unknown")
            job_lines.append(f"• `{job_id}`: {method} - next run: {next_run}")
        
        jobs_text = "\n".join(job_lines)
        await ctx.followup.send(
            f"**Scheduled Jobs ({len(our_jobs)} total):**\n{jobs_text}"
        )
    
    except Exception as e:
        await ctx.followup.send(f"❌ Error listing jobs: {e}")
        logger.error(f"Failed to list jobs: {e}")


# ============================================================================
# Run Bot
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Discord bot with threaded ScheduleZero handler...")
    logger.info(f"Handler will use port: {HANDLER_PORT}")
    logger.info(f"ScheduleZero API: {SCHEDULEZERO_API}")
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        if handler:
            handler.stop()
        logger.info("Cleanup complete")
