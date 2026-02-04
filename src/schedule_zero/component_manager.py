"""Component Manager for conditional startup/shutdown of ScheduleZero components.

Allows toggling components based on configuration:
- Tornado web server
- APScheduler
- ZMQ Event Broker
- Handler Registry (local/remote)
- ZMQ Registration Server
- ZMQ Client (for connecting to central server)
"""
from __future__ import annotations

import asyncio
import yaml
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.datastores.memory import MemoryDataStore

from .zmq_event_broker import ZMQEventBroker
from .local_handler_registry import LocalHandlerRegistry
from .handler_registry import RegistryManager
from .logging_config import get_logger

logger = get_logger(__name__, component="ComponentManager")


class ComponentManager:
    """Manages conditional startup/shutdown of ScheduleZero components."""
    
    def __init__(self, config: dict):
        """Initialize component manager with configuration.
        
        Args:
            config: Configuration dict with 'components' section
        """
        self.config = config
        self.components: dict[str, Any] = {}
        self._exit_stack = AsyncExitStack()
    
    async def start_scheduler(self) -> AsyncScheduler | None:
        """Start APScheduler if enabled.
        
        Returns:
            AsyncScheduler instance or None if disabled
        """
        sched_config = self.config.get('components', {}).get('scheduler', {})
        if not sched_config.get('enabled', True):
            logger.info("Scheduler disabled in config")
            return None
        
        # Configure datastore
        ds_config = sched_config.get('datastore', {})
        ds_type = ds_config.get('type', 'sqlite')
        
        if ds_type == 'memory':
            datastore = MemoryDataStore()
            logger.info("Using memory datastore")
        elif ds_type == 'sqlite':
            db_path = ds_config.get('path', 'schedulezero_jobs.db')
            datastore = SQLAlchemyDataStore(f"sqlite+aiosqlite:///{db_path}")
            logger.info("Using SQLite datastore", path=db_path)
        elif ds_type == 'postgresql':
            db_url = ds_config.get('url')
            if not db_url:
                raise ValueError("PostgreSQL datastore requires 'url' in config")
            datastore = SQLAlchemyDataStore(db_url)
            logger.info("Using PostgreSQL datastore")
        else:
            raise ValueError(f"Unknown datastore type: {ds_type}")
        
        # Configure event broker
        event_broker = await self.start_event_broker()
        
        # Create scheduler
        if event_broker:
            scheduler = AsyncScheduler(
                data_store=datastore,
                event_broker=event_broker
            )
        else:
            # Use default LocalEventBroker
            scheduler = AsyncScheduler(data_store=datastore)
        
        await self._exit_stack.enter_async_context(scheduler)
        
        # Start background processing for automatic schedule execution
        await scheduler.start_in_background()
        logger.info("Scheduler started with background execution enabled")
        
        return scheduler
    
    async def start_event_broker(self) -> ZMQEventBroker | None:
        """Start event broker if enabled.
        
        Returns:
            Event broker instance or None if disabled
        """
        broker_config = self.config.get('components', {}).get('event_broker', {})
        if not broker_config.get('enabled', False):
            logger.info("Event broker disabled (using local broker)")
            return None
        
        broker_type = broker_config.get('type', 'zmq')
        
        if broker_type == 'zmq':
            publish_addr = broker_config.get('publish_address', 'tcp://0.0.0.0:5555')
            subscribe_addrs = broker_config.get('subscribe_addresses', [])
            instance_id = broker_config.get('instance_id')
            heartbeat = broker_config.get('heartbeat_interval', 5)
            
            broker = ZMQEventBroker(
                publish_address=publish_addr,
                subscribe_addresses=subscribe_addrs,
                instance_id=instance_id,
                heartbeat_interval=heartbeat
            )
            
            logger.info(
                "ZMQ Event Broker configured",
                publish=publish_addr,
                subscribe_count=len(subscribe_addrs)
            )
            return broker
        
        elif broker_type == 'redis':
            # TODO: Implement Redis broker
            logger.warning("Redis event broker not yet implemented, using local")
            return None
        
        elif broker_type == 'mqtt':
            # TODO: Implement MQTT broker
            logger.warning("MQTT event broker not yet implemented, using local")
            return None
        
        else:
            raise ValueError(f"Unknown event broker type: {broker_type}")
    
    async def start_tornado(self):
        """Start Tornado web server if enabled.
        
        Returns:
            Tornado server instance or None if disabled
        """
        tornado_config = self.config.get('components', {}).get('tornado', {})
        if not tornado_config.get('enabled', True):
            logger.info("Tornado server disabled")
            return None
        
        # Import here to avoid circular dependency
        from .tornado_app_server import TornadoAppServer
        
        host = tornado_config.get('host', '0.0.0.0')
        port = tornado_config.get('port', 8888)
        
        # Tornado server needs scheduler reference
        scheduler = self.components.get('scheduler')
        
        server = TornadoAppServer(
            host=host,
            port=port,
            scheduler=scheduler
        )
        
        await server.start()
        logger.info("Tornado server started", host=host, port=port)
        
        return server
    
    async def start_local_handlers(self) -> LocalHandlerRegistry | None:
        """Start local handler registry if enabled.
        
        Returns:
            LocalHandlerRegistry instance or None if disabled
        """
        handlers_config = self.config.get('components', {}).get('handlers', {})
        local_config = handlers_config.get('local', {})
        
        if not local_config.get('enabled', True):
            logger.info("Local handlers disabled")
            return None
        
        registry = LocalHandlerRegistry()
        
        # Import modules with @register_local decorators
        modules = local_config.get('modules', [])
        for module_name in modules:
            try:
                __import__(module_name)
                logger.info("Imported handler module", module=module_name)
            except ImportError as e:
                logger.error(f"Failed to import handler module: {e}", module=module_name)
        
        return registry
    
    async def start_remote_handlers(self) -> RegistryManager | None:
        """Start remote handler registry if enabled.
        
        Returns:
            RegistryManager instance or None if disabled
        """
        handlers_config = self.config.get('components', {}).get('handlers', {})
        remote_config = handlers_config.get('remote', {})
        
        if not remote_config.get('enabled', True):
            logger.info("Remote handlers disabled")
            return None
        
        registry = RegistryManager()
        registry.load()
        
        # Start registration server if enabled
        reg_server_config = remote_config.get('registration_server', {})
        if reg_server_config.get('enabled', False):
            # TODO: Start ZMQ registration server
            logger.info("ZMQ registration server configured")
        
        return registry
    
    async def start_zmq_client(self):
        """Start ZMQ client for connecting to central server if enabled.
        
        Returns:
            ZMQClient instance or None if disabled
        """
        client_config = self.config.get('components', {}).get('zmq_client', {})
        if not client_config.get('enabled', False):
            logger.info("ZMQ client disabled")
            return None
        
        from .zmq_client import ZMQClient
        
        server_addr = client_config.get('server_address')
        if not server_addr:
            raise ValueError("ZMQ client requires 'server_address' in config")
        
        handler_id = client_config.get('handler_id', 'autonomous-handler')
        
        client = ZMQClient(server_addr)
        client.connect()
        
        logger.info(
            "ZMQ client connected",
            server=server_addr,
            handler_id=handler_id
        )
        
        return client
    
    async def start_all(self):
        """Start all enabled components in correct order.
        
        Returns:
            dict of component name -> instance
        """
        logger.info("Starting components", mode=self.config.get('deployment', {}).get('mode', 'full'))
        
        # Start in dependency order
        self.components['scheduler'] = await self.start_scheduler()
        self.components['local_handlers'] = await self.start_local_handlers()
        self.components['remote_handlers'] = await self.start_remote_handlers()
        self.components['zmq_client'] = await self.start_zmq_client()
        self.components['tornado'] = await self.start_tornado()
        
        # Count enabled components
        enabled_count = sum(1 for comp in self.components.values() if comp is not None)
        logger.info(f"Started {enabled_count} components")
        
        return self.components
    
    async def stop_all(self):
        """Stop all running components in reverse order."""
        logger.info("Stopping all components")
        
        # Stop Tornado first
        if self.components.get('tornado'):
            try:
                await self.components['tornado'].stop()
                logger.info("Tornado stopped")
            except Exception as e:
                logger.error(f"Error stopping Tornado: {e}")
        
        # Stop ZMQ client
        if self.components.get('zmq_client'):
            try:
                self.components['zmq_client'].close()
                logger.info("ZMQ client closed")
            except Exception as e:
                logger.error(f"Error closing ZMQ client: {e}")
        
        # Close remote handler connections
        if self.components.get('remote_handlers'):
            try:
                loop = asyncio.get_running_loop()
                await self.components['remote_handlers'].close_all_clients(loop)
                logger.info("Remote handlers closed")
            except Exception as e:
                logger.error(f"Error closing remote handlers: {e}")
        
        # Close exit stack (stops scheduler, event broker, etc.)
        try:
            await self._exit_stack.aclose()
            logger.info("Scheduler and event broker stopped")
        except Exception as e:
            logger.error(f"Error closing exit stack: {e}")
        
        self.components.clear()
        logger.info("All components stopped")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_all()


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override dict into base dict.
    
    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary
        
    Returns:
        Merged dictionary (modifies base in place and returns it)
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config_from_yaml(deployment: str = "default") -> dict | None:
    """Load configuration from YAML file for a deployment.
    
    Args:
        deployment: Deployment name (e.g., "default", "production", "edge")
        
    Returns:
        Configuration dict or None if file doesn't exist
    """
    config_path = Path(f"deployments/{deployment}/config.yaml")
    
    if not config_path.exists():
        logger.debug(f"No config file found at {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return None


def load_component_config(deployment: str = "default") -> dict:
    """Load component configuration for a deployment.
    
    Args:
        deployment: Deployment name (e.g., "default", "production", "edge")
        
    Returns:
        Configuration dict
    """
    from . import app_configuration as cfg
    
    # Load base config
    config = {
        'deployment': {
            'name': deployment,
            'mode': 'full'
        },
        'components': {
            'tornado': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8888
            },
            'scheduler': {
                'enabled': True,
                'datastore': {
                    'type': 'sqlite',
                    'path': f'deployments/{deployment}/schedulezero_jobs.db'
                }
            },
            'event_broker': {
                'enabled': False,
                'type': 'zmq'
            },
            'handlers': {
                'local': {
                    'enabled': True,
                    'modules': []
                },
                'remote': {
                    'enabled': True,
                    'registration_server': {
                        'enabled': False
                    }
                }
            },
            'zmq_client': {
                'enabled': False
            }
        }
    }
    
    # Load and merge deployment-specific config from YAML
    yaml_config = load_config_from_yaml(deployment)
    if yaml_config:
        _deep_merge(config, yaml_config)
        logger.info(f"Merged YAML config for deployment '{deployment}'")
    
    return config
