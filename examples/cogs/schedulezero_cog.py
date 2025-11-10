"""
ScheduleZero Cog for Discord.py

Load ScheduleZero handler as a Discord cog with dynamic sprocket management.

Architecture:
    Discord Bot
    ├─ Main Event Loop
    ├─ ScheduleZeroCog (loaded dynamically)
    │   ├─ Handler Thread (started by cog)
    │   ├─ Sprocket Registry (pluggable job modules)
    │   └─ Admin Commands (manage schedules)
    └─ Sprockets (loaded dynamically)
        ├─ AnnouncementSprocket
        ├─ ModerationSprocket
        ├─ ReminderSprocket
        └─ Custom sprockets...

Usage:
    # In your bot main file:
    bot = discord.Bot()
    bot.load_extension("cogs.schedulezero_cog")
    
    # Load sprockets:
    bot.load_extension("cogs.sprockets.announcement_sprocket")
    bot.load_extension("cogs.sprockets.moderation_sprocket")
"""
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import discord
from discord.ext import commands
import zmq
import yaml

logger = logging.getLogger("ScheduleZeroCog")


class ScheduleZeroHandler:
    """
    Threaded handler for ScheduleZero (lives inside cog).
    
    Manages ZMQ communication and job execution with sprocket support.
    """
    
    def __init__(
        self,
        bot: discord.Bot,
        handler_id: str = None,
        handler_port: int = 5000,
        server_address: str = "tcp://127.0.0.1:4242"
    ):
        self.bot = bot
        self.handler_id = handler_id or f"discord-{bot.user.id if bot.user else 'bot'}"
        self.handler_address = f"tcp://127.0.0.1:{handler_port}"
        self.server_address = server_address
        
        # Thread management
        self.handler_thread: Optional[threading.Thread] = None
        self.running = False
        self._stop_event = threading.Event()
        
        # Sprocket registry - pluggable job handlers
        self.sprockets: Dict[str, Callable] = {}
        
        # ZMQ (created in thread)
        self.zmq_context = None
        self.handler_socket = None
        self.server_socket = None
        
        logger.info(f"ScheduleZeroHandler initialized: {self.handler_id}")
    
    def register_sprocket(self, name: str, handler: Callable):
        """
        Register a sprocket (job handler function).
        
        Args:
            name: Sprocket name (used in job method field)
            handler: Function that takes (bot, params) and returns result
                     Can be sync or async
        """
        self.sprockets[name] = handler
        logger.info(f"Registered sprocket: {name}")
    
    def unregister_sprocket(self, name: str):
        """Unregister a sprocket."""
        if name in self.sprockets:
            del self.sprockets[name]
            logger.info(f"Unregistered sprocket: {name}")
    
    def list_sprockets(self) -> List[str]:
        """Get list of registered sprocket names."""
        return list(self.sprockets.keys())
    
    def start(self):
        """Start the handler thread."""
        if self.running:
            logger.warning("Handler already running")
            return
        
        self.running = True
        self._stop_event.clear()
        
        self.handler_thread = threading.Thread(
            target=self._run_handler,
            name="ScheduleZeroHandler",
            daemon=True
        )
        self.handler_thread.start()
        
        logger.info(f"Handler thread started: {self.handler_id}")
    
    def stop(self):
        """Stop the handler thread."""
        if not self.running:
            return
        
        logger.info("Stopping handler thread...")
        self.running = False
        self._stop_event.set()
        
        if self.handler_thread:
            self.handler_thread.join(timeout=5.0)
        
        logger.info("Handler stopped")
    
    def _run_handler(self):
        """Main handler loop (runs in separate thread)."""
        try:
            # Setup ZMQ
            self.zmq_context = zmq.Context()
            
            self.handler_socket = self.zmq_context.socket(zmq.REP)
            self.handler_socket.bind(self.handler_address)
            
            self.server_socket = self.zmq_context.socket(zmq.REQ)
            self.server_socket.connect(self.server_address)
            
            # Register with server
            self._register()
            
            logger.info(f"Handler listening on {self.handler_address}")
            
            # Main loop
            while self.running and not self._stop_event.is_set():
                if self.handler_socket.poll(timeout=1000):
                    request = self.handler_socket.recv_json()
                    response = self._execute_job(request)
                    self.handler_socket.send_json(response)
        
        except Exception as e:
            logger.error(f"Error in handler thread: {e}", exc_info=True)
        
        finally:
            if self.handler_socket:
                self.handler_socket.close()
            if self.server_socket:
                self.server_socket.close()
            if self.zmq_context:
                self.zmq_context.term()
            
            logger.info("Handler thread stopped")
    
    def _register(self):
        """Register with ScheduleZero server."""
        registration_data = {
            "action": "register",
            "handler_id": self.handler_id,
            "address": self.handler_address,
            "methods": self.list_sprockets()
        }
        
        self.server_socket.send_json(registration_data)
        response = self.server_socket.recv_json()
        
        if response.get("status") == "registered":
            logger.info(f"Registered with server - {len(self.sprockets)} sprockets")
        else:
            logger.error(f"Registration failed: {response}")
    
    def _execute_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a scheduled job via sprocket."""
        method_name = request.get("method")
        params = request.get("params", {})
        
        logger.info(f"Executing sprocket: {method_name}")
        
        if method_name not in self.sprockets:
            return {
                "status": "error",
                "error": f"Unknown sprocket: {method_name}"
            }
        
        sprocket = self.sprockets[method_name]
        
        try:
            # Check if sprocket is async or sync
            if asyncio.iscoroutinefunction(sprocket):
                # Async sprocket - run in bot's event loop
                result = self._run_coro_safe(sprocket(self.bot, params))
            else:
                # Sync sprocket - run directly
                result = sprocket(self.bot, params)
            
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"Sprocket execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _run_coro_safe(self, coro):
        """Run coroutine in bot's event loop from handler thread."""
        future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        return future.result(timeout=30.0)


class ScheduleZeroCog(commands.Cog):
    """
    Discord cog for ScheduleZero integration.
    
    Manages the handler thread and provides admin commands.
    """
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.handler: Optional[ScheduleZeroHandler] = None
        self.config = self._load_config()
        
        logger.info("ScheduleZeroCog initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML."""
        config_file = Path("config/schedulezero.yaml")
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start handler when bot is ready."""
        if self.handler is None:
            # Create and start handler
            self.handler = ScheduleZeroHandler(
                bot=self.bot,
                handler_id=self.config.get("handler_id"),
                handler_port=self.config.get("handler_port", 5000),
                server_address=self.config.get("server_address", "tcp://127.0.0.1:4242")
            )
            
            # Handler starts in separate thread
            self.handler.start()
            
            logger.info(f"ScheduleZero handler started for {self.bot.user}")
    
    def cog_unload(self):
        """Clean shutdown when cog is unloaded."""
        if self.handler:
            self.handler.stop()
            logger.info("Handler stopped (cog unload)")
    
    def register_sprocket(self, name: str, handler: Callable):
        """
        Register a sprocket with the handler.
        
        Called by sprocket cogs during their setup.
        """
        if self.handler:
            self.handler.register_sprocket(name, handler)
        else:
            logger.warning(f"Cannot register sprocket {name} - handler not initialized")
    
    def unregister_sprocket(self, name: str):
        """Unregister a sprocket."""
        if self.handler:
            self.handler.unregister_sprocket(name)
    
    # ========================================================================
    # Admin Commands
    # ========================================================================
    
    schedule_group = discord.SlashCommandGroup(
        name="schedule",
        description="Manage ScheduleZero jobs",
        default_member_permissions=discord.Permissions(administrator=True)
    )
    
    @schedule_group.command(name="status", description="Check handler status")
    async def status(self, ctx: discord.ApplicationContext):
        """Check handler and sprocket status."""
        if not self.handler:
            await ctx.respond("❌ Handler not initialized", ephemeral=True)
            return
        
        sprockets = self.handler.list_sprockets()
        sprocket_list = "\n".join([f"• `{s}`" for s in sprockets])
        
        embed = discord.Embed(
            title="ScheduleZero Status",
            color=discord.Color.green() if self.handler.running else discord.Color.red()
        )
        embed.add_field(name="Handler ID", value=f"`{self.handler.handler_id}`", inline=False)
        embed.add_field(name="Thread Status", value="✅ Running" if self.handler.running else "❌ Stopped", inline=True)
        embed.add_field(name="Thread Name", value=f"`{self.handler.handler_thread.name}`", inline=True)
        embed.add_field(name="Sprockets", value=sprocket_list or "None loaded", inline=False)
        
        await ctx.respond(embed=embed, ephemeral=True)
    
    @schedule_group.command(name="reload", description="Reload handler registration")
    async def reload_handler(self, ctx: discord.ApplicationContext):
        """Re-register handler with server (picks up new sprockets)."""
        await ctx.defer(ephemeral=True)
        
        if not self.handler or not self.handler.running:
            await ctx.followup.send("❌ Handler not running", ephemeral=True)
            return
        
        # Stop and restart to re-register
        self.handler.stop()
        await asyncio.sleep(1)
        self.handler.start()
        await asyncio.sleep(1)
        
        await ctx.followup.send(
            f"✅ Handler reloaded\n"
            f"Sprockets: {len(self.handler.list_sprockets())}",
            ephemeral=True
        )
    
    @schedule_group.command(name="sprockets", description="List loaded sprockets")
    async def list_sprockets(self, ctx: discord.ApplicationContext):
        """List all loaded sprockets."""
        if not self.handler:
            await ctx.respond("❌ Handler not initialized", ephemeral=True)
            return
        
        sprockets = self.handler.list_sprockets()
        
        if not sprockets:
            await ctx.respond("No sprockets loaded", ephemeral=True)
            return
        
        sprocket_list = "\n".join([f"{i+1}. `{s}`" for i, s in enumerate(sprockets)])
        
        embed = discord.Embed(
            title=f"Loaded Sprockets ({len(sprockets)})",
            description=sprocket_list,
            color=discord.Color.blue()
        )
        
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    """Setup function called by bot.load_extension()."""
    bot.add_cog(ScheduleZeroCog(bot))
    logger.info("ScheduleZeroCog loaded")
