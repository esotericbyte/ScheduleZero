"""
Example Discord Bot with ZeroMQ Listener

This example shows how to:
1. Set up a Discord bot with the ZMQ listener cog
2. Receive events from ScheduleZero server
3. Post notifications to Discord channels
4. Add custom event handlers

Prerequisites:
    - Discord bot token set in DISCORD_TOKEN environment variable
    - ScheduleZero server running with ZMQ publisher enabled
    - pyzmq, discord.py/py-cord, pyyaml installed

Usage:
    1. Set DISCORD_TOKEN environment variable
    2. Configure discord/config/zmq_listener.yaml
    3. Start ScheduleZero server
    4. Run: python discord_zmq_example.py
"""
import os
import discord
from discord.ext import commands
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.error("DISCORD_TOKEN environment variable must be set")
    sys.exit(1)

# Channel IDs for notifications (replace with your actual channel IDs)
NOTIFICATION_CHANNEL_ID = int(os.getenv("NOTIFICATION_CHANNEL_ID", "0"))
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))

# Create bot
bot = discord.Bot(
    intents=discord.Intents.default(),
    debug_guilds=None  # Set to list of guild IDs for testing
)


# =============================================================================
# Bot Events
# =============================================================================

@bot.event
async def on_ready():
    """Bot is ready - register custom handlers."""
    logger.info(f"🤖 Bot connected as {bot.user}")
    logger.info(f"📊 Guilds: {len(bot.guilds)}")
    
    # Get ZMQ listener cog
    zmq_cog = bot.get_cog("ZMQListenerCog")
    if zmq_cog and zmq_cog.listener:
        logger.info("✅ ZMQ Listener active")
        
        # Register custom handlers
        zmq_cog.listener.register_handler("job.executed", handle_job_success)
        zmq_cog.listener.register_handler("job.failed", handle_job_failure)
        zmq_cog.listener.register_handler("handler.registered", handle_handler_registered)
        
        logger.info("✅ Custom event handlers registered")
    else:
        logger.warning("⚠️ ZMQ Listener not loaded!")


@bot.event
async def on_application_command_error(ctx, error):
    """Handle command errors."""
    logger.error(f"Command error: {error}", exc_info=True)
    await ctx.respond(f"❌ Error: {error}", ephemeral=True)


# =============================================================================
# Custom Event Handlers
# =============================================================================

async def handle_job_success(bot: discord.Bot, topic: str, data: dict):
    """
    Handle successful job execution.
    
    Posts a notification to the notification channel.
    """
    job_name = data.get('job_name', 'Unknown')
    job_id = data.get('job_id', 'N/A')
    duration = data.get('duration', 0)
    
    logger.info(f"Job succeeded: {job_name} ({duration:.2f}s)")
    
    # Only post to channel if configured
    if NOTIFICATION_CHANNEL_ID:
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="✅ Job Completed",
                color=discord.Color.green(),
                description=f"**{job_name}**"
            )
            embed.add_field(name="Job ID", value=job_id, inline=True)
            embed.add_field(name="Duration", value=f"{duration:.2f}s", inline=True)
            embed.timestamp = discord.utils.utcnow()
            
            await channel.send(embed=embed)


async def handle_job_failure(bot: discord.Bot, topic: str, data: dict):
    """
    Handle job execution failure.
    
    Posts an alert to the alert channel with error details.
    """
    job_name = data.get('job_name', 'Unknown')
    job_id = data.get('job_id', 'N/A')
    error = data.get('error', 'Unknown error')
    retry_count = data.get('retry_count', 0)
    
    logger.error(f"Job failed: {job_name} - {error}")
    
    # Post to alert channel
    if ALERT_CHANNEL_ID:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="❌ Job Failure Alert",
                color=discord.Color.red(),
                description=f"**{job_name}**"
            )
            embed.add_field(name="Job ID", value=job_id, inline=True)
            embed.add_field(name="Retry", value=f"{retry_count}/3", inline=True)
            embed.add_field(name="Error", value=f"```{error}```", inline=False)
            embed.timestamp = discord.utils.utcnow()
            
            # Mention admins if max retries reached
            content = None
            if retry_count >= 3:
                content = "@here Maximum retries reached!"
            
            await channel.send(content=content, embed=embed)


async def handle_handler_registered(bot: discord.Bot, topic: str, data: dict):
    """
    Handle handler registration event.
    
    Logs when a new handler connects to ScheduleZero.
    """
    handler_id = data.get('handler_id', 'Unknown')
    address = data.get('address', 'N/A')
    methods = data.get('methods', [])
    
    logger.info(f"Handler registered: {handler_id} at {address}")
    
    # Optionally post to notification channel
    if NOTIFICATION_CHANNEL_ID:
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🔌 Handler Connected",
                color=discord.Color.blue(),
                description=f"**{handler_id}**"
            )
            embed.add_field(name="Address", value=address, inline=False)
            embed.add_field(
                name="Methods", 
                value=", ".join(methods) if methods else "None", 
                inline=False
            )
            embed.timestamp = discord.utils.utcnow()
            
            await channel.send(embed=embed)


# =============================================================================
# Custom Commands
# =============================================================================

@bot.slash_command(
    name="schedulezero",
    description="Get ScheduleZero status"
)
async def schedulezero_status(ctx: discord.ApplicationContext):
    """Display ScheduleZero server status."""
    await ctx.defer()
    
    zmq_cog = bot.get_cog("ZMQListenerCog")
    if not zmq_cog:
        await ctx.followup.send("❌ ZMQ Listener not loaded")
        return
    
    listener = zmq_cog.listener
    
    embed = discord.Embed(
        title="ScheduleZero Status",
        color=discord.Color.blue()
    )
    
    # Listener status
    status = "🟢 Connected" if listener.running else "🔴 Disconnected"
    embed.add_field(name="Listener", value=status, inline=True)
    
    # Queue size
    queue_size = listener.message_queue.qsize()
    embed.add_field(name="Queue Size", value=str(queue_size), inline=True)
    
    # Handler count
    handler_count = sum(len(handlers) for handlers in listener.handlers.values())
    embed.add_field(name="Handlers", value=str(handler_count), inline=True)
    
    # Address
    embed.add_field(name="Address", value=zmq_cog.config['zmq_pub_address'], inline=False)
    
    # Topics
    topics = ", ".join(zmq_cog.config['topics'])
    embed.add_field(name="Subscribed Topics", value=topics, inline=False)
    
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.followup.send(embed=embed)


@bot.slash_command(
    name="test_notification",
    description="Send a test notification (admin only)",
    default_member_permissions=discord.Permissions(administrator=True)
)
async def test_notification(ctx: discord.ApplicationContext):
    """Send a test notification to verify channels are configured."""
    await ctx.defer(ephemeral=True)
    
    if NOTIFICATION_CHANNEL_ID:
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if channel:
            await channel.send("🔔 Test notification from ScheduleZero bot")
            await ctx.followup.send(f"✅ Sent to <#{NOTIFICATION_CHANNEL_ID}>")
        else:
            await ctx.followup.send(f"❌ Channel {NOTIFICATION_CHANNEL_ID} not found")
    else:
        await ctx.followup.send("❌ NOTIFICATION_CHANNEL_ID not configured")


# =============================================================================
# Load Cogs
# =============================================================================

# Load ZMQ listener cog (REQUIRED)
try:
    bot.load_extension("cogs.zmq_listener_cog")
    logger.info("✅ Loaded ZMQ Listener Cog")
except Exception as e:
    logger.error(f"❌ Failed to load ZMQ Listener Cog: {e}")
    sys.exit(1)

# Load ScheduleZero management cog (OPTIONAL)
# Uncomment if you want to schedule jobs from Discord
# try:
#     bot.load_extension("cogs.schedulezero_cog")
#     logger.info("✅ Loaded ScheduleZero Cog")
# except Exception as e:
#     logger.warning(f"⚠️ Failed to load ScheduleZero Cog: {e}")

# Load sprocket cogs (OPTIONAL)
# Uncomment to add job handlers
# try:
#     bot.load_extension("cogs.sprockets.announcement_sprocket")
#     logger.info("✅ Loaded Announcement Sprocket")
# except Exception as e:
#     logger.warning(f"⚠️ Failed to load Announcement Sprocket: {e}")


# =============================================================================
# Run Bot
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Discord bot with ZMQ listener...")
    logger.info(f"Notification Channel: {NOTIFICATION_CHANNEL_ID or 'Not configured'}")
    logger.info(f"Alert Channel: {ALERT_CHANNEL_ID or 'Not configured'}")
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)
