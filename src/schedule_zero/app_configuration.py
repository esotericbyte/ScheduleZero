"""Configuration management for ScheduleZero."""

import os
import logging
import yaml

logger = logging.getLogger(__name__)

# Default configuration paths
CONFIG_FILE_PATH = "config.yaml"
README_FILE_PATH = "README.md"
REGISTRY_FILE_PATH = "handler_registry.yaml"
DATABASE_URL = "sqlite+aiosqlite:///schedulezero_jobs.db"

# Network Configuration (Defaults to localhost)
TORNADO_ADDRESS = os.environ.get("SCHEDULEZERO_TORNADO_ADDR", "127.0.0.1")
TORNADO_PORT = int(os.environ.get("SCHEDULEZERO_TORNADO_PORT", 8888))
ZRPC_SERVER_HOST = os.environ.get("SCHEDULEZERO_ZRPC_HOST", "127.0.0.1")
ZRPC_SERVER_PORT = int(os.environ.get("SCHEDULEZERO_ZRPC_PORT", 4242))
ZRPC_SERVER_ADDRESS = f"tcp://{ZRPC_SERVER_HOST}:{ZRPC_SERVER_PORT}"

# RPC Client Configuration
HEARTBEAT_INTERVAL = 5
RPC_TIMEOUT = 10

# API Defaults
DEFAULT_PAGE_LIMIT = 50


def get_config_path() -> str:
    """Get the configuration file path from environment or default."""
    return os.environ.get("SCHEDULEZERO_CONFIG_PATH", CONFIG_FILE_PATH)


def get_registry_path() -> str:
    """Get the handler registry file path from environment or default."""
    return os.environ.get("SCHEDULEZERO_REGISTRY_PATH", REGISTRY_FILE_PATH)


def get_database_url() -> str:
    """Get the database URL from environment or default."""
    return os.environ.get("SCHEDULEZERO_DATABASE_URL", DATABASE_URL)


def load_config() -> dict:
    """Load configuration from YAML file.
    
    Returns:
        Dictionary containing configuration settings
    """
    config_path = get_config_path()
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        logger.info(f"Loaded config from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Config file '{config_path}' not found. Using defaults.")
        return {
            "instance_name": "ScheduleZero (Default)",
            "description": "Config file not found.",
            "admin_contact": "N/A",
            "version": "N/A"
        }
    except yaml.YAMLError as e:
        logger.error(f"Error parsing {config_path}: {e}")
        return {"error": f"Failed to load config: {e}"}
