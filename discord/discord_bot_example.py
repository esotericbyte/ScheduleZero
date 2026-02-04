"""
Example Discord Bot with ScheduleZero Integration

This demonstrates how to integrate ScheduleZero with a Discord.py bot.
The handler runs as an asyncio task in the same event loop as the bot.
"""
import discord
import asyncio
import logging
from discord_handler import DiscordScheduleHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

# Handler instance (created after bot is ready)
schedule_handler: DiscordScheduleHandler = None


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    global schedule_handler
    
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    
    # Start the ScheduleZero handler
    schedule_handler = DiscordScheduleHandler(
        bot=bot,
        handler_id=f"discord-{bot.user.id}",
        config_file="discord_jobs.yaml",
        handler_port=5000,
        server_address="tcp://127.0.0.1:4242"  # Default ScheduleZero server
    )
    
    await schedule_handler.start()
    print(f'ScheduleZero handler started!')


@bot.slash_command(name="schedule", description="Schedule a message")
async def schedule_message(
    ctx: discord.ApplicationContext,
    message: str,
    minutes: int
):
    """
    Schedule a message to be sent after a delay.
    
    This demonstrates scheduling from Discord commands.
    """
    import requests
    from datetime import datetime, timedelta
    
    # Calculate execution time
    exec_time = datetime.utcnow() + timedelta(minutes=minutes)
    
    # Schedule via ScheduleZero API
    job_data = {
        "handler_id": f"discord-{bot.user.id}",
        "job_method": "send_message",
        "job_params": {
            "channel_id": ctx.channel.id,
            "content": message
        },
        "trigger": {
            "type": "date",
            "run_date": exec_time.timestamp()
        },
        "job_id": f"discord_msg_{ctx.interaction.id}"
    }
    
    try:
        response = requests.post("http://127.0.0.1:8888/api/schedule", json=job_data)
        if response.status_code == 201:
            await ctx.respond(
                f"✅ Message scheduled for {minutes} minutes from now!\n"
                f"Will be sent at: {exec_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        else:
            await ctx.respond(f"❌ Failed to schedule: {response.text}")
    except Exception as e:
        await ctx.respond(f"❌ Error: {e}")


@bot.slash_command(name="status", description="Update bot status on a schedule")
async def schedule_status(
    ctx: discord.ApplicationContext,
    status: str,
    minutes: int
):
    """Schedule a status update."""
    import requests
    from datetime import datetime, timedelta
    
    exec_time = datetime.utcnow() + timedelta(minutes=minutes)
    
    job_data = {
        "handler_id": f"discord-{bot.user.id}",
        "job_method": "update_status",
        "job_params": {
            "activity_type": "playing",
            "name": status
        },
        "trigger": {
            "type": "date",
            "run_date": exec_time.timestamp()
        }
    }
    
    try:
        response = requests.post("http://127.0.0.1:8888/api/schedule", json=job_data)
        if response.status_code == 201:
            await ctx.respond(f"✅ Status will update to '{status}' in {minutes} minutes!")
        else:
            await ctx.respond(f"❌ Failed: {response.text}")
    except Exception as e:
        await ctx.respond(f"❌ Error: {e}")


@bot.event
async def on_close():
    """Called when the bot is shutting down."""
    global schedule_handler
    
    if schedule_handler:
        await schedule_handler.stop()
        print("ScheduleZero handler stopped")


def main():
    """Main entry point."""
    # Get token from environment or config
    import os
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable not set!")
        print("Usage: export DISCORD_BOT_TOKEN='your-token-here'")
        return
    
    # Run the bot
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
