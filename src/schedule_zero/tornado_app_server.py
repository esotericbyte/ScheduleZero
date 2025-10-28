"""
ScheduleZero Main Server

Simplified main server file that orchestrates all components.
"""
import asyncio
import logging
import os
import signal

import tornado.ioloop
import tornado.web

from apscheduler import AsyncScheduler, RunState
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore

from .app_configuration import (
    load_config,
    get_database_url,
    TORNADO_ADDRESS,
    TORNADO_PORT,
    README_FILE_PATH
)
from .handler_registry import RegistryManager
from .job_executor import JobExecutor
from .zmq_registration_server import ZMQRegistrationServer
from .api import (
    IndexHandler,
    ReadmeHandler,
    HealthCheckHandler,
    ListHandlersHandler,
    ScheduleJobHandler,
    RunNowHandler,
    ListSchedulesHandler,
    ConfigHandler,
    HandlersViewHandler,
    SchedulesViewHandler
)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def log_function(handler):
    """
    Custom log function that suppresses noisy polling endpoints.
    Only logs non-polling requests to reduce log spam from health checks
    and stats queries.
    """
    # Suppress logging for frequently polled endpoints
    if handler.request.uri in ['/api/health', '/api/handlers', '/api/schedules']:
        return
    
    # Log everything else normally
    if handler.get_status() < 400:
        log_method = logging.info
    elif handler.get_status() < 500:
        log_method = logging.warning
    else:
        log_method = logging.error
    
    request_time = 1000.0 * handler.request.request_time()
    log_method(
        "%d %s %s (%.2fms)",
        handler.get_status(),
        handler.request.method,
        handler.request.uri,
        request_time,
    )

# --- Global State ---
scheduler: AsyncScheduler | None = None
rpc_server: ZMQRegistrationServer | None = None
registry_manager: RegistryManager | None = None
job_executor: JobExecutor | None = None


def make_tornado_app(config, registry_manager, scheduler, job_executor):
    """
    Create and configure the Tornado application.
    
    Args:
        config: Application configuration dictionary
        registry_manager: RegistryManager instance
        scheduler: APScheduler AsyncScheduler instance
        job_executor: JobExecutor callable for running jobs
    
    Returns:
        Configured Tornado application
    """
    # Get portal path for templates and static files
    portal_path = os.path.join(os.path.dirname(__file__), 'portal')
    
    # Common dependencies for API handlers
    api_deps = {
        'config': config,
        'registry': registry_manager.registry,
        'registry_lock': registry_manager.lock,
        'scheduler': scheduler,
        'job_executor': job_executor
    }
    
    routes = [
        # Main UI
        (r"/", IndexHandler, {'config': config, 'template_path': portal_path}),
        (r"/readme", ReadmeHandler, {'readme_path': README_FILE_PATH}),
        
        # Web Views (HTML pages that consume JSON APIs)
        (r"/view/handlers", HandlersViewHandler),
        (r"/view/schedules", SchedulesViewHandler),
        
        # API endpoints (JSON only)
        (r"/api/health", HealthCheckHandler),
        (r"/api/handlers", ListHandlersHandler, api_deps),
        (r"/api/schedule", ScheduleJobHandler, api_deps),
        (r"/api/run_now", RunNowHandler, api_deps),
        (r"/api/schedules", ListSchedulesHandler, api_deps),
        (r"/api/config", ConfigHandler, api_deps),
    ]
    
    return tornado.web.Application(
        routes,
        template_path=portal_path,
        static_path=os.path.join(portal_path, 'static'),
        debug=False,  # Set to True for development
        serve_traceback=False,  # Set to True to see full tracebacks in API responses
        log_function=log_function  # Custom logging to suppress polling endpoint spam
    )


async def start_server():
    """Initialize and start all server components."""
    global scheduler, rpc_server, registry_manager, job_executor
    
    logger.info("Starting ScheduleZero Server...")
    
    # Load configuration
    config = load_config()
    
    # Initialize registry manager
    registry_manager = RegistryManager()
    registry_manager.load()
    
    # Initialize database and scheduler
    db_url = os.environ.get("SCHEDULEZERO_DATABASE_URL", get_database_url())
    logger.info(f"Using database URL: {db_url}")
    
    try:
        data_store = SQLAlchemyDataStore(db_url)
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy datastore for {db_url}: {e}", exc_info=True)
        return
    
    scheduler = AsyncScheduler(data_store=data_store)
    
    # Initialize job executor
    job_executor = JobExecutor(registry_manager)
    
    # Start ZMQ registration server
    rpc_server = ZMQRegistrationServer(
        address=f"tcp://{os.environ.get('SCHEDULEZERO_ZRPC_HOST', '127.0.0.1')}:"
                f"{os.environ.get('SCHEDULEZERO_ZRPC_PORT', '4242')}",
        registry=registry_manager.registry,
        registry_lock=registry_manager.lock,
        registry_path=registry_manager.registry_path,
        save_registry_callback=registry_manager.save
    )
    # Get the current event loop and start ZMQ server
    loop = asyncio.get_running_loop()
    rpc_server.start(loop)
    
    # Give ZMQ server a moment to start
    await asyncio.sleep(0.5)
    if not rpc_server.task or rpc_server.task.done():
        logger.critical("ZMQ server task failed to start. Check logs. Exiting.")
        return
    
    # Start APScheduler
    async with scheduler:
        logger.info("APScheduler started.")
        
        # Start Tornado web server
        try:
            app = make_tornado_app(config, registry_manager, scheduler, job_executor)
            app.listen(TORNADO_PORT, address=TORNADO_ADDRESS)
            logger.info(f"Tornado server listening on http://{TORNADO_ADDRESS}:{TORNADO_PORT}")
        except Exception as e:
            logger.critical(f"Failed to start Tornado server: {e}", exc_info=True)
            return
        
        # Keep running until interrupted
        await asyncio.Event().wait()


async def shutdown():
    """Gracefully shutdown all server components."""
    logger.info("Initiating shutdown...")
    
    # Stop ZMQ registration server
    if rpc_server:
        logger.info("Shutting down ZMQ server...")
        await rpc_server.stop()
    
    # Stop APScheduler
    if scheduler and scheduler.state == RunState.started:
        logger.info("Shutting down APScheduler...")
        try:
            await scheduler.stop()
            await scheduler.wait_until_stopped()
            logger.info("APScheduler stopped.")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)
    
    # Close handler clients
    if registry_manager:
        logger.info("Closing handler clients...")
        loop = asyncio.get_running_loop()
        await registry_manager.close_all_clients(loop)
    
    logger.info("Shutdown sequence complete.")


def handle_signal(sig, frame):
    """Handle interrupt signals."""
    logger.info(f"Received signal {sig}. Initiating graceful shutdown...")
    logger.info("Running shutdown sequence...")
    asyncio.create_task(shutdown())
    # Stop the event loop
    asyncio.get_event_loop().stop()


def main():
    """Main entry point for the server."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        logger.info("Running shutdown sequence...")
        asyncio.run(shutdown())
    finally:
        logger.info("Server stopped.")


if __name__ == "__main__":
    main()
