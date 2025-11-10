"""
Discord Bot with ScheduleZero Cog Architecture

Demonstrates using ScheduleZero as a cog with dynamic sprocket loading.

Architecture:
    1. Load ScheduleZeroCog first (manages handler thread)
    2. Load sprocket cogs (register job methods)
    3. Sprockets auto-register when bot is ready
    4. Handler thread starts and registers all sprockets with server

Usage:
    1. Set DISCORD_TOKEN environment variable
    2. Start ScheduleZero server
    3. Run: python discord_bot_with_cogs.py
    4. Use /schedule commands to manage jobs
    5. Dynamically load/unload sprockets as needed

Sprockets:
    - AnnouncementSprocket: Scheduled announcements
    - ModerationSprocket: Cleanup, roles, lockdowns
    - Custom sprockets: Create your own!
"""
import os
import discord
from discord.ext import commands
import logging
import sys
from pathlib import Path

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

SCHEDULEZERO_API = os.getenv("SCHEDULEZERO_API", "http://localhost:8888")

# Create bot
bot = discord.Bot(
    intents=discord.Intents.default(),
    debug_guilds=None  # Set to list of guild IDs for testing
)


@bot.event
async def on_ready():
    """Bot is ready."""
    logger.info(f"🤖 Bot connected as {bot.user}")
    logger.info(f"📊 Guilds: {len(bot.guilds)}")
    logger.info(f"🔧 Cogs loaded: {', '.join(bot.cogs.keys())}")
    
    # Check ScheduleZero cog
    schedulezero_cog = bot.get_cog("ScheduleZeroCog")
    if schedulezero_cog:
        logger.info(f"✅ ScheduleZeroCog active")
        logger.info(f"🔌 Sprockets: {len(schedulezero_cog.handler.list_sprockets() if schedulezero_cog.handler else 0)}")
    else:
        logger.warning("⚠️ ScheduleZeroCog not loaded!")


@bot.event
async def on_application_command_error(ctx, error):
    """Handle command errors."""
    logger.error(f"Command error: {error}", exc_info=True)
    await ctx.respond(f"❌ Error: {error}", ephemeral=True)


# =============================================================================
# Extension Management Commands
# =============================================================================

@bot.slash_command(
    name="load_sprocket",
    description="Load a sprocket cog",
    default_member_permissions=discord.Permissions(administrator=True)
)
async def load_sprocket(
    ctx: discord.ApplicationContext,
    sprocket: discord.Option(
        str,
        description="Sprocket to load",
        choices=["announcement", "moderation"]
    )
):
    """Dynamically load a sprocket."""
    await ctx.defer(ephemeral=True)
    
    sprocket_path = f"cogs.sprockets.{sprocket}_sprocket"
    
    try:
        bot.load_extension(sprocket_path)
        await ctx.followup.send(
            f"✅ Loaded sprocket: {sprocket}\n"
            f"Use `/schedule reload` to re-register with server",
            ephemeral=True
        )
        logger.info(f"Loaded sprocket: {sprocket}")
    
    except Exception as e:
        await ctx.followup.send(
            f"❌ Failed to load sprocket: {e}",
            ephemeral=True
        )
        logger.error(f"Failed to load sprocket {sprocket}: {e}")


@bot.slash_command(
    name="unload_sprocket",
    description="Unload a sprocket cog",
    default_member_permissions=discord.Permissions(administrator=True)
)
async def unload_sprocket(
    ctx: discord.ApplicationContext,
    sprocket: discord.Option(
        str,
        description="Sprocket to unload",
        choices=["announcement", "moderation"]
    )
):
    """Dynamically unload a sprocket."""
    await ctx.defer(ephemeral=True)
    
    sprocket_path = f"cogs.sprockets.{sprocket}_sprocket"
    
    try:
        bot.unload_extension(sprocket_path)
        await ctx.followup.send(
            f"✅ Unloaded sprocket: {sprocket}\n"
            f"Use `/schedule reload` to update server registration",
            ephemeral=True
        )
        logger.info(f"Unloaded sprocket: {sprocket}")
    
    except Exception as e:
        await ctx.followup.send(
            f"❌ Failed to unload sprocket: {e}",
            ephemeral=True
        )
        logger.error(f"Failed to unload sprocket {sprocket}: {e}")


@bot.slash_command(
    name="reload_sprocket",
    description="Reload a sprocket cog",
    default_member_permissions=discord.Permissions(administrator=True)
)
async def reload_sprocket(
    ctx: discord.ApplicationContext,
    sprocket: discord.Option(
        str,
        description="Sprocket to reload",
        choices=["announcement", "moderation"]
    )
):
    """Dynamically reload a sprocket (unload + load)."""
    await ctx.defer(ephemeral=True)
    
    sprocket_path = f"cogs.sprockets.{sprocket}_sprocket"
    
    try:
        # Unload if already loaded
        try:
            bot.unload_extension(sprocket_path)
        except:
            pass
        
        # Load
        bot.load_extension(sprocket_path)
        
        await ctx.followup.send(
            f"✅ Reloaded sprocket: {sprocket}\n"
            f"Use `/schedule reload` to update server registration",
            ephemeral=True
        )
        logger.info(f"Reloaded sprocket: {sprocket}")
    
    except Exception as e:
        await ctx.followup.send(
            f"❌ Failed to reload sprocket: {e}",
            ephemeral=True
        )
        logger.error(f"Failed to reload sprocket {sprocket}: {e}")


# =============================================================================
# Startup
# =============================================================================

def load_extensions():
    """Load all extensions/cogs."""
    # CRITICAL: Load ScheduleZeroCog FIRST
    try:
        bot.load_extension("cogs.schedulezero_cog")
        logger.info("✅ Loaded ScheduleZeroCog")
    except Exception as e:
        logger.error(f"❌ Failed to load ScheduleZeroCog: {e}")
        logger.error("Cannot continue without ScheduleZeroCog!")
        sys.exit(1)
    
    # Load sprockets (optional - can be loaded dynamically)
    sprockets = [
        "cogs.sprockets.announcement_sprocket",
        "cogs.sprockets.moderation_sprocket",
    ]
    
    for sprocket in sprockets:
        try:
            bot.load_extension(sprocket)
            logger.info(f"✅ Loaded {sprocket}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load {sprocket}: {e}")
            logger.warning("Sprocket can be loaded later with /load_sprocket")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Discord Bot with ScheduleZero Cog Architecture")
    logger.info("=" * 60)
    logger.info(f"ScheduleZero API: {SCHEDULEZERO_API}")
    logger.info("")
    
    # Load extensions
    load_extensions()
    
    logger.info("")
    logger.info("Starting bot...")
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
    finally:
        logger.info("Shutdown complete")
