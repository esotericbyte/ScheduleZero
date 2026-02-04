"""
ScheduleZero Discord Bot Handler

Integrates ScheduleZero with Discord.py as an asyncio task.
Runs in the same event loop as the Discord bot for seamless integration.

Architecture:
    Discord Bot Process
    ├─ discord.py (main event loop)
    ├─ ScheduleZero Handler Task (asyncio.Task)
    │   └─ ZMQ async client
    └─ Job methods execute directly using bot context

Usage:
    import discord
    from discord_handler import DiscordScheduleHandler
    
    bot = discord.Bot()
    
    @bot.event
    async def on_ready():
        # Start the scheduler handler
        handler = DiscordScheduleHandler(bot, config_file="discord_jobs.yaml")
        await handler.start()
        print(f"ScheduleZero handler started for {bot.user}")
    
    bot.run(TOKEN)
"""
import asyncio
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import zmq.asyncio
import discord

logger = logging.getLogger("DiscordScheduleHandler")


class DiscordScheduleHandler:
    """
    Async handler for ScheduleZero integration with Discord.py.
    
    Runs as an asyncio task alongside the Discord bot, using the same event loop.
    Receives scheduled job requests from ScheduleZero server via ZMQ and executes
    them in the bot's context.
    """
    
    def __init__(
        self,
        bot: discord.Bot,
        handler_id: str = None,
        config_file: str = "discord_jobs.yaml",
        handler_port: int = 5000,
        server_address: str = "tcp://127.0.0.1:4242"
    ):
        """
        Initialize Discord schedule handler.
        
        Args:
            bot: Discord bot instance
            handler_id: Unique handler ID (defaults to bot name)
            config_file: YAML config with job definitions
            handler_port: Port for this handler to listen on
            server_address: ScheduleZero server ZMQ address
        """
        self.bot = bot
        self.handler_id = handler_id or f"discord-{bot.user.id if bot.user else 'bot'}"
        self.config_file = Path(config_file)
        self.handler_address = f"tcp://127.0.0.1:{handler_port}"
        self.server_address = server_address
        
        # Async ZMQ context
        self.zmq_context = zmq.asyncio.Context()
        self.handler_socket = None
        self.server_socket = None
        
        # Task tracking
        self.handler_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Load job configuration
        self.job_config = self._load_config()
        
        logger.info(f"Initialized DiscordScheduleHandler: {self.handler_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load job configuration from YAML file."""
        if not self.config_file.exists():
            logger.warning(f"Config file not found: {self.config_file}")
            return {}
        
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded config from {self.config_file}")
        return config or {}
    
    async def start(self):
        """Start the handler task (runs in bot's event loop)."""
        if self.running:
            logger.warning("Handler already running")
            return
        
        self.running = True
        
        # Setup ZMQ sockets
        self.handler_socket = self.zmq_context.socket(zmq.REP)
        self.handler_socket.bind(self.handler_address)
        
        self.server_socket = self.zmq_context.socket(zmq.REQ)
        self.server_socket.connect(self.server_address)
        
        # Register with server
        await self._register()
        
        # Start handler task
        self.handler_task = asyncio.create_task(self._run_handler())
        
        logger.info(f"Handler started: {self.handler_id} on {self.handler_address}")
    
    async def stop(self):
        """Stop the handler task."""
        self.running = False
        
        if self.handler_task:
            self.handler_task.cancel()
            try:
                await self.handler_task
            except asyncio.CancelledError:
                pass
        
        # Close sockets
        if self.handler_socket:
            self.handler_socket.close()
        if self.server_socket:
            self.server_socket.close()
        
        self.zmq_context.term()
        
        logger.info(f"Handler stopped: {self.handler_id}")
    
    async def _register(self):
        """Register this handler with the ScheduleZero server."""
        registration_data = {
            "action": "register",
            "handler_id": self.handler_id,
            "address": self.handler_address,
            "methods": list(self._get_available_methods().keys())
        }
        
        await self.server_socket.send_json(registration_data)
        response = await self.server_socket.recv_json()
        
        if response.get("status") == "registered":
            logger.info(f"Successfully registered with server")
        else:
            logger.error(f"Registration failed: {response}")
    
    async def _run_handler(self):
        """Main handler loop - receives and executes jobs."""
        logger.info("Handler loop started")
        
        while self.running:
            try:
                # Wait for job request (with timeout to allow checking self.running)
                if await self.handler_socket.poll(timeout=1000):  # 1 second timeout
                    request = await self.handler_socket.recv_json()
                    
                    # Execute the job
                    response = await self._execute_job(request)
                    
                    # Send response
                    await self.handler_socket.send_json(response)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in handler loop: {e}", exc_info=True)
                # Send error response if we received a request
                try:
                    await self.handler_socket.send_json({
                        "status": "error",
                        "error": str(e)
                    })
                except:
                    pass
        
        logger.info("Handler loop stopped")
    
    async def _execute_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a scheduled job.
        
        Args:
            request: Job request with 'method' and 'params'
            
        Returns:
            Result dictionary
        """
        method_name = request.get("method")
        params = request.get("params", {})
        
        logger.info(f"Executing job: {method_name} with params {params}")
        
        # Get the method
        methods = self._get_available_methods()
        if method_name not in methods:
            return {
                "status": "error",
                "error": f"Unknown method: {method_name}"
            }
        
        method = methods[method_name]
        
        try:
            # Execute the method (it's a coroutine)
            result = await method(params)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"Job execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_available_methods(self) -> Dict[str, Any]:
        """Get all available job methods."""
        return {
            "send_message": self.send_message,
            "send_embed": self.send_embed,
            "update_status": self.update_status,
            "schedule_announcement": self.schedule_announcement,
            "cleanup_old_messages": self.cleanup_old_messages,
            "update_role": self.update_role,
        }
    
    # =========================================================================
    # Job Methods (executed by scheduler)
    # =========================================================================
    
    async def send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to a channel.
        
        Args:
            params: {
                "channel_id": int,
                "content": str
            }
        """
        channel_id = params.get("channel_id")
        content = params.get("content", "")
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return {"error": f"Channel {channel_id} not found"}
        
        message = await channel.send(content)
        
        return {
            "message_id": message.id,
            "channel_id": channel_id,
            "content": content
        }
    
    async def send_embed(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an embed to a channel.
        
        Args:
            params: {
                "channel_id": int,
                "title": str,
                "description": str,
                "color": int (optional)
            }
        """
        channel_id = params.get("channel_id")
        title = params.get("title", "")
        description = params.get("description", "")
        color = params.get("color", 0x00ff00)
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return {"error": f"Channel {channel_id} not found"}
        
        embed = discord.Embed(title=title, description=description, color=color)
        message = await channel.send(embed=embed)
        
        return {
            "message_id": message.id,
            "channel_id": channel_id
        }
    
    async def update_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update bot's status/presence.
        
        Args:
            params: {
                "activity_type": str ("playing", "watching", "listening"),
                "name": str
            }
        """
        activity_type = params.get("activity_type", "playing").lower()
        name = params.get("name", "")
        
        activity_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening
        }
        
        activity = discord.Activity(
            type=activity_map.get(activity_type, discord.ActivityType.playing),
            name=name
        )
        
        await self.bot.change_presence(activity=activity)
        
        return {
            "activity_type": activity_type,
            "name": name
        }
    
    async def schedule_announcement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a scheduled announcement with optional role mention.
        
        Args:
            params: {
                "channel_id": int,
                "message": str,
                "role_id": int (optional)
            }
        """
        channel_id = params.get("channel_id")
        message = params.get("message", "")
        role_id = params.get("role_id")
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return {"error": f"Channel {channel_id} not found"}
        
        content = message
        if role_id:
            content = f"<@&{role_id}> {message}"
        
        sent_message = await channel.send(content)
        
        return {
            "message_id": sent_message.id,
            "channel_id": channel_id,
            "mentioned_role": role_id
        }
    
    async def cleanup_old_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete old messages from a channel.
        
        Args:
            params: {
                "channel_id": int,
                "limit": int (number of messages to check),
                "age_days": int (delete messages older than this)
            }
        """
        from datetime import datetime, timedelta
        
        channel_id = params.get("channel_id")
        limit = params.get("limit", 100)
        age_days = params.get("age_days", 7)
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return {"error": f"Channel {channel_id} not found"}
        
        cutoff_date = datetime.utcnow() - timedelta(days=age_days)
        deleted_count = 0
        
        async for message in channel.history(limit=limit):
            if message.created_at < cutoff_date:
                await message.delete()
                deleted_count += 1
                await asyncio.sleep(1)  # Rate limit protection
        
        return {
            "channel_id": channel_id,
            "deleted_count": deleted_count
        }
    
    async def update_role(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add or remove a role from a user.
        
        Args:
            params: {
                "guild_id": int,
                "user_id": int,
                "role_id": int,
                "action": "add" or "remove"
            }
        """
        guild_id = params.get("guild_id")
        user_id = params.get("user_id")
        role_id = params.get("role_id")
        action = params.get("action", "add")
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return {"error": f"Guild {guild_id} not found"}
        
        member = guild.get_member(user_id)
        if not member:
            return {"error": f"Member {user_id} not found"}
        
        role = guild.get_role(role_id)
        if not role:
            return {"error": f"Role {role_id} not found"}
        
        if action == "add":
            await member.add_roles(role)
        elif action == "remove":
            await member.remove_roles(role)
        else:
            return {"error": f"Unknown action: {action}"}
        
        return {
            "user_id": user_id,
            "role_id": role_id,
            "action": action
        }
