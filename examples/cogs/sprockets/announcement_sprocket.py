"""
Announcement Sprocket

Handles scheduled announcements with role mentions, embeds, and channel management.

Sprocket Pattern:
    Each sprocket is a Discord cog that registers job methods with the 
    ScheduleZero handler. Methods can be async or sync.

Registration:
    bot.load_extension("cogs.sprockets.announcement_sprocket")
    
    The sprocket automatically registers with ScheduleZeroCog during setup.

Available Methods:
    - send_announcement: Send message with optional role mention
    - send_embed_announcement: Send rich embed announcement
    - send_to_multiple_channels: Broadcast to multiple channels
"""
import logging
import discord
from discord.ext import commands
from typing import Dict, Any, List

logger = logging.getLogger("AnnouncementSprocket")


# =============================================================================
# Sprocket Job Methods (called by ScheduleZero)
# =============================================================================

async def send_announcement(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a scheduled announcement.
    
    Params:
        channel_id: int - Channel to send to
        message: str - Message content
        role_id: int (optional) - Role to mention
        everyone: bool (optional) - Mention @everyone
    
    Returns:
        Dict with message_id, channel_id, mentions
    """
    channel_id = params.get("channel_id")
    message = params.get("message", "")
    role_id = params.get("role_id")
    mention_everyone = params.get("everyone", False)
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return {"error": f"Channel {channel_id} not found"}
    
    # Build content with mentions
    content = message
    mentions = []
    
    if mention_everyone:
        content = f"@everyone {content}"
        mentions.append("@everyone")
    elif role_id:
        content = f"<@&{role_id}> {content}"
        mentions.append(f"role:{role_id}")
    
    sent_message = await channel.send(content)
    
    logger.info(f"Sent announcement to #{channel.name}: {message[:50]}")
    
    return {
        "message_id": sent_message.id,
        "channel_id": channel_id,
        "mentions": mentions,
        "content": message
    }


async def send_embed_announcement(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a rich embed announcement.
    
    Params:
        channel_id: int
        title: str
        description: str
        color: int (optional) - Hex color (e.g., 0x00ff00)
        footer: str (optional)
        thumbnail_url: str (optional)
        image_url: str (optional)
        fields: List[Dict] (optional) - [{name, value, inline}, ...]
    
    Returns:
        Dict with message_id, channel_id
    """
    channel_id = params.get("channel_id")
    title = params.get("title", "Announcement")
    description = params.get("description", "")
    color = params.get("color", 0x00ff00)
    footer = params.get("footer")
    thumbnail_url = params.get("thumbnail_url")
    image_url = params.get("image_url")
    fields = params.get("fields", [])
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return {"error": f"Channel {channel_id} not found"}
    
    # Build embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    if image_url:
        embed.set_image(url=image_url)
    
    # Add fields
    for field in fields:
        embed.add_field(
            name=field.get("name", "Field"),
            value=field.get("value", ""),
            inline=field.get("inline", False)
        )
    
    sent_message = await channel.send(embed=embed)
    
    logger.info(f"Sent embed announcement to #{channel.name}: {title}")
    
    return {
        "message_id": sent_message.id,
        "channel_id": channel_id,
        "embed_title": title
    }


async def send_to_multiple_channels(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Broadcast announcement to multiple channels.
    
    Params:
        channel_ids: List[int] - List of channel IDs
        message: str - Message to send
        embed: Dict (optional) - Embed params (see send_embed_announcement)
    
    Returns:
        Dict with sent_count, failed_channels
    """
    channel_ids = params.get("channel_ids", [])
    message = params.get("message", "")
    embed_params = params.get("embed")
    
    sent_count = 0
    failed_channels = []
    
    for channel_id in channel_ids:
        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                failed_channels.append({"channel_id": channel_id, "error": "Not found"})
                continue
            
            if embed_params:
                # Send as embed
                embed = discord.Embed(
                    title=embed_params.get("title", "Announcement"),
                    description=embed_params.get("description", message),
                    color=embed_params.get("color", 0x00ff00)
                )
                await channel.send(embed=embed)
            else:
                # Send as plain message
                await channel.send(message)
            
            sent_count += 1
            logger.info(f"Broadcast sent to #{channel.name}")
        
        except Exception as e:
            failed_channels.append({"channel_id": channel_id, "error": str(e)})
            logger.error(f"Failed to send to channel {channel_id}: {e}")
    
    return {
        "sent_count": sent_count,
        "total_channels": len(channel_ids),
        "failed_channels": failed_channels
    }


# =============================================================================
# Sprocket Cog (registers methods with ScheduleZero)
# =============================================================================

class AnnouncementSprocket(commands.Cog):
    """
    Announcement sprocket for scheduled announcements.
    
    Registers announcement job methods with ScheduleZero handler.
    """
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        logger.info("AnnouncementSprocket initialized")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Register sprocket methods when bot is ready."""
        # Get ScheduleZero cog
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if not schedulezero_cog:
            logger.error("ScheduleZeroCog not found! Load it before sprockets.")
            return
        
        # Register our sprocket methods
        schedulezero_cog.register_sprocket("send_announcement", send_announcement)
        schedulezero_cog.register_sprocket("send_embed_announcement", send_embed_announcement)
        schedulezero_cog.register_sprocket("send_to_multiple_channels", send_to_multiple_channels)
        
        logger.info("AnnouncementSprocket methods registered (3 methods)")
    
    def cog_unload(self):
        """Unregister sprocket methods when cog is unloaded."""
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if schedulezero_cog:
            schedulezero_cog.unregister_sprocket("send_announcement")
            schedulezero_cog.unregister_sprocket("send_embed_announcement")
            schedulezero_cog.unregister_sprocket("send_to_multiple_channels")
        
        logger.info("AnnouncementSprocket methods unregistered")
    
    # =========================================================================
    # Admin Commands (for scheduling announcements)
    # =========================================================================
    
    announcement_group = discord.SlashCommandGroup(
        name="announcement",
        description="Schedule announcements",
        default_member_permissions=discord.Permissions(manage_messages=True)
    )
    
    @announcement_group.command(name="schedule", description="Schedule an announcement")
    async def schedule_announcement(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        message: str,
        minutes_from_now: int,
        role: discord.Role = None
    ):
        """Schedule a simple announcement."""
        await ctx.defer(ephemeral=True)
        
        # TODO: Make API call to ScheduleZero to schedule job
        # For now, just show what would be scheduled
        
        await ctx.followup.send(
            f"Would schedule announcement:\n"
            f"• Channel: {channel.mention}\n"
            f"• Message: {message[:50]}...\n"
            f"• In: {minutes_from_now} minutes\n"
            f"• Mention: {role.mention if role else 'None'}",
            ephemeral=True
        )


def setup(bot: discord.Bot):
    """Setup function called by bot.load_extension()."""
    bot.add_cog(AnnouncementSprocket(bot))
    logger.info("AnnouncementSprocket loaded")
