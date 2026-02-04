"""
Moderation Sprocket

Handles scheduled moderation tasks: message cleanup, role management, 
channel lockdowns, etc.

Available Methods:
    - cleanup_messages: Delete old messages from channel
    - add_role_scheduled: Add role to user(s) at scheduled time
    - remove_role_scheduled: Remove role from user(s)
    - lockdown_channel: Lock channel (deny send messages)
    - unlock_channel: Unlock channel
    - send_dm: Send DM to user
"""
import logging
import discord
from discord.ext import commands
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger("ModerationSprocket")


# =============================================================================
# Sprocket Job Methods
# =============================================================================

async def cleanup_messages(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete messages from a channel.
    
    Params:
        channel_id: int
        limit: int (default 100) - Max messages to check
        age_days: int (optional) - Only delete messages older than this
        user_id: int (optional) - Only delete messages from this user
        contains: str (optional) - Only delete messages containing this text
    
    Returns:
        Dict with deleted_count
    """
    channel_id = params.get("channel_id")
    limit = params.get("limit", 100)
    age_days = params.get("age_days")
    user_id = params.get("user_id")
    contains_text = params.get("contains")
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return {"error": f"Channel {channel_id} not found"}
    
    deleted_count = 0
    cutoff_date = None
    
    if age_days:
        cutoff_date = datetime.utcnow() - timedelta(days=age_days)
    
    async for message in channel.history(limit=limit):
        should_delete = True
        
        # Check age filter
        if cutoff_date and message.created_at > cutoff_date:
            should_delete = False
        
        # Check user filter
        if user_id and message.author.id != user_id:
            should_delete = False
        
        # Check content filter
        if contains_text and contains_text not in message.content:
            should_delete = False
        
        if should_delete:
            await message.delete()
            deleted_count += 1
            await asyncio.sleep(0.5)  # Rate limit protection
    
    logger.info(f"Cleaned up {deleted_count} messages from #{channel.name}")
    
    return {
        "deleted_count": deleted_count,
        "channel_id": channel_id
    }


async def add_role_scheduled(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add role to user(s) at scheduled time.
    
    Params:
        guild_id: int
        user_ids: List[int] - Users to add role to
        role_id: int
    
    Returns:
        Dict with success_count, failed_users
    """
    guild_id = params.get("guild_id")
    user_ids = params.get("user_ids", [])
    role_id = params.get("role_id")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return {"error": f"Guild {guild_id} not found"}
    
    role = guild.get_role(role_id)
    if not role:
        return {"error": f"Role {role_id} not found"}
    
    success_count = 0
    failed_users = []
    
    for user_id in user_ids:
        try:
            member = guild.get_member(user_id)
            if not member:
                failed_users.append({"user_id": user_id, "error": "Member not found"})
                continue
            
            await member.add_roles(role)
            success_count += 1
            logger.info(f"Added role {role.name} to {member.name}")
        
        except Exception as e:
            failed_users.append({"user_id": user_id, "error": str(e)})
            logger.error(f"Failed to add role to {user_id}: {e}")
    
    return {
        "success_count": success_count,
        "total_users": len(user_ids),
        "failed_users": failed_users,
        "role_name": role.name
    }


async def remove_role_scheduled(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove role from user(s) at scheduled time.
    
    Params:
        guild_id: int
        user_ids: List[int]
        role_id: int
    
    Returns:
        Dict with success_count, failed_users
    """
    guild_id = params.get("guild_id")
    user_ids = params.get("user_ids", [])
    role_id = params.get("role_id")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return {"error": f"Guild {guild_id} not found"}
    
    role = guild.get_role(role_id)
    if not role:
        return {"error": f"Role {role_id} not found"}
    
    success_count = 0
    failed_users = []
    
    for user_id in user_ids:
        try:
            member = guild.get_member(user_id)
            if not member:
                failed_users.append({"user_id": user_id, "error": "Member not found"})
                continue
            
            await member.remove_roles(role)
            success_count += 1
            logger.info(f"Removed role {role.name} from {member.name}")
        
        except Exception as e:
            failed_users.append({"user_id": user_id, "error": str(e)})
            logger.error(f"Failed to remove role from {user_id}: {e}")
    
    return {
        "success_count": success_count,
        "total_users": len(user_ids),
        "failed_users": failed_users,
        "role_name": role.name
    }


async def lockdown_channel(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lock a channel (deny send messages for @everyone).
    
    Params:
        channel_id: int
        reason: str (optional)
    
    Returns:
        Dict with channel_id, locked status
    """
    channel_id = params.get("channel_id")
    reason = params.get("reason", "Scheduled lockdown")
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return {"error": f"Channel {channel_id} not found"}
    
    # Get @everyone role
    everyone_role = channel.guild.default_role
    
    # Deny send messages
    await channel.set_permissions(
        everyone_role,
        send_messages=False,
        reason=reason
    )
    
    logger.info(f"Locked channel #{channel.name}")
    
    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "locked": True,
        "reason": reason
    }


async def unlock_channel(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unlock a channel (allow send messages for @everyone).
    
    Params:
        channel_id: int
        reason: str (optional)
    
    Returns:
        Dict with channel_id, locked status
    """
    channel_id = params.get("channel_id")
    reason = params.get("reason", "Scheduled unlock")
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return {"error": f"Channel {channel_id} not found"}
    
    # Get @everyone role
    everyone_role = channel.guild.default_role
    
    # Allow send messages (or reset to None to use category settings)
    await channel.set_permissions(
        everyone_role,
        send_messages=None,  # None = inherit from category
        reason=reason
    )
    
    logger.info(f"Unlocked channel #{channel.name}")
    
    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "locked": False,
        "reason": reason
    }


async def send_dm(bot: discord.Bot, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send DM to a user at scheduled time.
    
    Params:
        user_id: int
        message: str
        embed: Dict (optional) - Embed params
    
    Returns:
        Dict with success status
    """
    user_id = params.get("user_id")
    message = params.get("message", "")
    embed_params = params.get("embed")
    
    user = bot.get_user(user_id)
    if not user:
        return {"error": f"User {user_id} not found"}
    
    try:
        if embed_params:
            embed = discord.Embed(
                title=embed_params.get("title", "Message"),
                description=embed_params.get("description", message),
                color=embed_params.get("color", 0x00ff00)
            )
            await user.send(embed=embed)
        else:
            await user.send(message)
        
        logger.info(f"Sent DM to {user.name}")
        
        return {
            "user_id": user_id,
            "username": str(user),
            "sent": True
        }
    
    except discord.Forbidden:
        return {"error": f"Cannot send DM to {user.name} (blocked or privacy settings)"}


# =============================================================================
# Sprocket Cog
# =============================================================================

class ModerationSprocket(commands.Cog):
    """Moderation sprocket for scheduled moderation tasks."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        logger.info("ModerationSprocket initialized")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Register sprocket methods."""
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if not schedulezero_cog:
            logger.error("ScheduleZeroCog not found!")
            return
        
        # Register methods
        schedulezero_cog.register_sprocket("cleanup_messages", cleanup_messages)
        schedulezero_cog.register_sprocket("add_role_scheduled", add_role_scheduled)
        schedulezero_cog.register_sprocket("remove_role_scheduled", remove_role_scheduled)
        schedulezero_cog.register_sprocket("lockdown_channel", lockdown_channel)
        schedulezero_cog.register_sprocket("unlock_channel", unlock_channel)
        schedulezero_cog.register_sprocket("send_dm", send_dm)
        
        logger.info("ModerationSprocket methods registered (6 methods)")
    
    def cog_unload(self):
        """Unregister sprocket methods."""
        schedulezero_cog = self.bot.get_cog("ScheduleZeroCog")
        
        if schedulezero_cog:
            schedulezero_cog.unregister_sprocket("cleanup_messages")
            schedulezero_cog.unregister_sprocket("add_role_scheduled")
            schedulezero_cog.unregister_sprocket("remove_role_scheduled")
            schedulezero_cog.unregister_sprocket("lockdown_channel")
            schedulezero_cog.unregister_sprocket("unlock_channel")
            schedulezero_cog.unregister_sprocket("send_dm")
        
        logger.info("ModerationSprocket methods unregistered")


def setup(bot: discord.Bot):
    """Setup function."""
    bot.add_cog(ModerationSprocket(bot))
    logger.info("ModerationSprocket loaded")
