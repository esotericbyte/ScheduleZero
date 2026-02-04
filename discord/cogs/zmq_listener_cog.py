"""
ZeroMQ Listener Cog for Discord Bot

This cog runs a ZeroMQ subscriber that listens for events/messages from the
ScheduleZero server and can trigger Discord actions in response.

Architecture:
    - Runs a background thread with ZMQ SUB socket
    - Subscribes to topics from ScheduleZero server
    - Dispatches received messages to registered handlers
    - Can trigger Discord bot actions based on events

Use Cases:
    - Receive notifications when jobs are executed
    - Get alerts on job failures
    - Broadcast messages to Discord channels based on scheduled events
    - Real-time status updates from ScheduleZero

Usage:
    # In your bot main file:
    bot.load_extension("cogs.zmq_listener_cog")
    
    # Configure in config/zmq_listener.yaml:
    zmq_pub_address: "tcp://127.0.0.1:4243"  # ScheduleZero PUB socket
    topics:
      - "job.executed"
      - "job.failed"
      - "handler.status"
"""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import discord
from discord.ext import commands, tasks
import zmq
import yaml
import json

logger = logging.getLogger("ZMQListenerCog")


class ZMQListener:
    """
    Threaded ZeroMQ subscriber that listens for events from ScheduleZero.
    
    Runs in a separate thread and queues messages for the bot to process.
    """
    
    def __init__(
        self,
        bot: discord.Bot,
        zmq_pub_address: str,
        topics: List[str] = None
    ):
        self.bot = bot
        self.zmq_pub_address = zmq_pub_address
        self.topics = topics or ["job.", "handler.", "scheduler."]
        
        # Thread management
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False
        self._stop_event = threading.Event()
        
        # Message queue for bot to process
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Event handlers - map topic prefix to handler functions
        self.handlers: Dict[str, List[Callable]] = {}
        
        # ZMQ (created in thread)
        self.zmq_context = None
        self.subscriber_socket = None
        
        logger.info(f"ZMQListener initialized for {zmq_pub_address}")
        logger.info(f"Subscribed topics: {self.topics}")
    
    def register_handler(self, topic: str, handler: Callable):
        """
        Register a handler function for a specific topic.
        
        Args:
            topic: Topic prefix to match (e.g., "job.executed")
            handler: Async function that takes (bot, topic, data) and processes it
        """
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)
        logger.info(f"Registered handler for topic: {topic}")
    
    def unregister_handler(self, topic: str, handler: Callable):
        """Unregister a handler function."""
        if topic in self.handlers and handler in self.handlers[topic]:
            self.handlers[topic].remove(handler)
            logger.info(f"Unregistered handler for topic: {topic}")
    
    def start(self):
        """Start the listener thread."""
        if self.running:
            logger.warning("Listener already running")
            return
        
        self.running = True
        self._stop_event.clear()
        
        self.listener_thread = threading.Thread(
            target=self._run_listener,
            name="ZMQListener",
            daemon=True
        )
        self.listener_thread.start()
        
        logger.info(f"Listener thread started")
    
    def stop(self):
        """Stop the listener thread."""
        if not self.running:
            return
        
        logger.info("Stopping listener thread...")
        self.running = False
        self._stop_event.set()
        
        if self.listener_thread:
            self.listener_thread.join(timeout=5.0)
        
        logger.info("Listener stopped")
    
    def _run_listener(self):
        """Main listener loop (runs in separate thread)."""
        try:
            # Setup ZMQ
            self.zmq_context = zmq.Context()
            self.subscriber_socket = self.zmq_context.socket(zmq.SUB)
            self.subscriber_socket.connect(self.zmq_pub_address)
            
            # Subscribe to topics
            for topic in self.topics:
                self.subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, topic)
            
            logger.info(f"Listener connected to {self.zmq_pub_address}")
            
            # Main loop
            while self.running and not self._stop_event.is_set():
                try:
                    # Poll for messages with timeout
                    if self.subscriber_socket.poll(timeout=1000):
                        # Receive message: [topic, data]
                        message = self.subscriber_socket.recv_multipart()
                        
                        if len(message) >= 2:
                            topic = message[0].decode('utf-8')
                            data_raw = message[1].decode('utf-8')
                            
                            try:
                                data = json.loads(data_raw)
                            except json.JSONDecodeError:
                                data = {'raw': data_raw}
                            
                            # Queue message for bot to process
                            asyncio.run_coroutine_threadsafe(
                                self.message_queue.put((topic, data)),
                                self.bot.loop
                            )
                            
                            logger.debug(f"Received message on topic: {topic}")
                
                except zmq.ZMQError as e:
                    if e.errno == zmq.ETERM:
                        break
                    logger.error(f"ZMQ error in listener: {e}")
                    time.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Fatal error in listener thread: {e}", exc_info=True)
        
        finally:
            # Cleanup
            if self.subscriber_socket:
                self.subscriber_socket.close()
            if self.zmq_context:
                self.zmq_context.term()
            
            logger.info("Listener thread exited")
    
    async def dispatch_message(self, topic: str, data: Dict[str, Any]):
        """
        Dispatch a received message to registered handlers.
        
        Finds handlers that match the topic and calls them.
        """
        handlers_called = 0
        
        for handler_topic, handlers in self.handlers.items():
            if topic.startswith(handler_topic):
                for handler in handlers:
                    try:
                        await handler(self.bot, topic, data)
                        handlers_called += 1
                    except Exception as e:
                        logger.error(f"Error in handler for {topic}: {e}", exc_info=True)
        
        if handlers_called == 0:
            logger.debug(f"No handlers for topic: {topic}")


class ZMQListenerCog(commands.Cog):
    """
    Discord cog that manages ZeroMQ listener for receiving events.
    
    This cog:
    - Starts a ZMQ subscriber thread
    - Processes messages from the queue
    - Dispatches to registered handlers
    - Provides commands to manage the listener
    """
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.listener: Optional[ZMQListener] = None
        
        # Load config
        config_path = Path("config/zmq_listener.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            # Default config
            self.config = {
                'zmq_pub_address': 'tcp://127.0.0.1:4243',
                'topics': ['job.', 'handler.', 'scheduler.']
            }
            logger.warning(f"Config not found at {config_path}, using defaults")
        
        logger.info("ZMQListenerCog initialized")
    
    async def cog_load(self):
        """Called when cog is loaded."""
        # Create and start listener
        self.listener = ZMQListener(
            bot=self.bot,
            zmq_pub_address=self.config['zmq_pub_address'],
            topics=self.config['topics']
        )
        
        # Register default handlers
        self._register_default_handlers()
        
        # Start listener
        self.listener.start()
        
        # Start message processor
        self.message_processor.start()
        
        logger.info("✅ ZMQ Listener started")
    
    async def cog_unload(self):
        """Called when cog is unloaded."""
        # Stop message processor
        if self.message_processor.is_running():
            self.message_processor.stop()
        
        # Stop listener
        if self.listener:
            self.listener.stop()
        
        logger.info("ZMQ Listener stopped")
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        # Example: Log all job execution events
        self.listener.register_handler("job.executed", self._handle_job_executed)
        self.listener.register_handler("job.failed", self._handle_job_failed)
        self.listener.register_handler("handler.registered", self._handle_handler_registered)
    
    async def _handle_job_executed(self, bot: discord.Bot, topic: str, data: Dict[str, Any]):
        """Handle job execution events."""
        logger.info(f"Job executed: {data.get('job_id', 'unknown')}")
        # You can extend this to post to specific channels, etc.
    
    async def _handle_job_failed(self, bot: discord.Bot, topic: str, data: Dict[str, Any]):
        """Handle job failure events."""
        logger.warning(f"Job failed: {data.get('job_id', 'unknown')} - {data.get('error', 'unknown error')}")
        # You can extend this to alert admins in Discord
    
    async def _handle_handler_registered(self, bot: discord.Bot, topic: str, data: Dict[str, Any]):
        """Handle handler registration events."""
        logger.info(f"Handler registered: {data.get('handler_id', 'unknown')}")
    
    @tasks.loop(seconds=0.1)
    async def message_processor(self):
        """Process messages from the queue."""
        try:
            # Process up to 10 messages per iteration
            for _ in range(10):
                try:
                    topic, data = self.listener.message_queue.get_nowait()
                    await self.listener.dispatch_message(topic, data)
                except asyncio.QueueEmpty:
                    break
        except Exception as e:
            logger.error(f"Error in message processor: {e}", exc_info=True)
    
    @message_processor.before_loop
    async def before_message_processor(self):
        """Wait for bot to be ready before processing messages."""
        await self.bot.wait_until_ready()
    
    # --- Commands ---
    
    @commands.slash_command(
        name="zmq_status",
        description="Check ZMQ listener status"
    )
    async def zmq_status(self, ctx: discord.ApplicationContext):
        """Check listener status."""
        if not self.listener:
            await ctx.respond("❌ Listener not initialized", ephemeral=True)
            return
        
        status = "🟢 Running" if self.listener.running else "🔴 Stopped"
        queue_size = self.listener.message_queue.qsize()
        handler_count = sum(len(handlers) for handlers in self.listener.handlers.values())
        
        embed = discord.Embed(
            title="ZMQ Listener Status",
            color=discord.Color.green() if self.listener.running else discord.Color.red()
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Queue Size", value=str(queue_size), inline=True)
        embed.add_field(name="Handlers", value=str(handler_count), inline=True)
        embed.add_field(name="Address", value=self.config['zmq_pub_address'], inline=False)
        embed.add_field(name="Topics", value=", ".join(self.config['topics']), inline=False)
        
        await ctx.respond(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="zmq_restart",
        description="Restart ZMQ listener",
        default_member_permissions=discord.Permissions(administrator=True)
    )
    async def zmq_restart(self, ctx: discord.ApplicationContext):
        """Restart the listener."""
        await ctx.defer(ephemeral=True)
        
        if self.listener:
            self.listener.stop()
            await asyncio.sleep(1)
            self.listener.start()
            await ctx.followup.send("✅ ZMQ Listener restarted")
        else:
            await ctx.followup.send("❌ Listener not initialized")


def setup(bot: discord.Bot):
    """Setup function for cog loading."""
    bot.add_cog(ZMQListenerCog(bot))
