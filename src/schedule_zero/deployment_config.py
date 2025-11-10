"""
ScheduleZero Deployment Configuration

Supports running multiple ScheduleZero instances simultaneously:
- Different ports for web server and ZMQ
- Separate databases
- Separate log files
- Different handler registries

Usage:
    # Default (development) instance
    python -m schedule_zero.server
    
    # Production deployment
    SCHEDULEZERO_DEPLOYMENT=production python -m schedule_zero.server
    
    # Clock deployment (for DingDong handler)
    SCHEDULEZERO_DEPLOYMENT=clock python -m schedule_zero.server
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeploymentConfig:
    """Configuration for a ScheduleZero deployment."""
    
    # Deployment name
    name: str
    
    # Web server
    tornado_host: str
    tornado_port: int
    
    # ZMQ registration server
    zmq_host: str
    zmq_port: int
    
    # Database
    database_path: str
    
    # Logging
    log_file: Optional[str]
    log_level: str
    
    # Handler registry
    registry_file: str
    
    def __post_init__(self):
        """Ensure directories exist."""
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.registry_file).parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def zmq_address(self) -> str:
        """Full ZMQ server address."""
        return f"tcp://{self.zmq_host}:{self.zmq_port}"
    
    @property
    def database_url(self) -> str:
        """SQLAlchemy database URL."""
        return f"sqlite+aiosqlite:///{self.database_path}"


# Predefined deployment configurations
DEPLOYMENTS = {
    "default": DeploymentConfig(
        name="default",
        tornado_host="127.0.0.1",
        tornado_port=8888,
        zmq_host="127.0.0.1",
        zmq_port=4242,
        database_path="schedulezero_jobs.db",
        log_file=None,  # Console only for development
        log_level="INFO",
        registry_file="handler_registry.yaml"
    ),
    
    "production": DeploymentConfig(
        name="production",
        tornado_host="0.0.0.0",  # Listen on all interfaces
        tornado_port=8888,
        zmq_host="0.0.0.0",
        zmq_port=4242,
        database_path="deployments/production/schedulezero_jobs.db",
        log_file="deployments/production/logs/server.log",
        log_level="INFO",
        registry_file="deployments/production/handler_registry.yaml"
    ),
    
    "clock": DeploymentConfig(
        name="clock",
        tornado_host="127.0.0.1",
        tornado_port=8889,  # Different port!
        zmq_host="127.0.0.1",
        zmq_port=4243,  # Different port!
        database_path="deployments/clock/schedulezero_jobs.db",
        log_file="deployments/clock/logs/server.log",
        log_level="INFO",
        registry_file="deployments/clock/handler_registry.yaml"
    ),
    
    "test": DeploymentConfig(
        name="test",
        tornado_host="127.0.0.1",
        tornado_port=8890,
        zmq_host="127.0.0.1",
        zmq_port=4244,
        database_path="deployments/test/schedulezero_jobs.db",
        log_file="deployments/test/logs/server.log",
        log_level="DEBUG",
        registry_file="deployments/test/handler_registry.yaml"
    )
}


def get_deployment_config(deployment_name: Optional[str] = None) -> DeploymentConfig:
    """
    Get deployment configuration.
    
    Args:
        deployment_name: Name of deployment, or None to read from environment
        
    Returns:
        DeploymentConfig instance
        
    Raises:
        ValueError: If deployment name is unknown
    """
    if deployment_name is None:
        deployment_name = os.environ.get("SCHEDULEZERO_DEPLOYMENT", "default")
    
    if deployment_name not in DEPLOYMENTS:
        raise ValueError(
            f"Unknown deployment: {deployment_name}. "
            f"Available: {list(DEPLOYMENTS.keys())}"
        )
    
    config = DEPLOYMENTS[deployment_name]
    
    # Allow environment variable overrides
    config.tornado_host = os.environ.get("SCHEDULEZERO_HOST", config.tornado_host)
    config.tornado_port = int(os.environ.get("SCHEDULEZERO_PORT", config.tornado_port))
    config.zmq_host = os.environ.get("SCHEDULEZERO_ZMQ_HOST", config.zmq_host)
    config.zmq_port = int(os.environ.get("SCHEDULEZERO_ZMQ_PORT", config.zmq_port))
    config.log_level = os.environ.get("LOG_LEVEL", config.log_level)
    
    if os.environ.get("SCHEDULEZERO_LOG_FILE"):
        config.log_file = os.environ.get("SCHEDULEZERO_LOG_FILE")
    
    if os.environ.get("SCHEDULEZERO_DATABASE"):
        config.database_path = os.environ.get("SCHEDULEZERO_DATABASE")
    
    if os.environ.get("SCHEDULEZERO_REGISTRY"):
        config.registry_file = os.environ.get("SCHEDULEZERO_REGISTRY")
    
    return config


def print_deployment_info(config: DeploymentConfig):
    """Print deployment configuration info."""
    print()
    print("=" * 80)
    print(f"  ScheduleZero Deployment: {config.name.upper()}")
    print("=" * 80)
    print(f"Web Server:       http://{config.tornado_host}:{config.tornado_port}")
    print(f"ZMQ Server:       {config.zmq_address}")
    print(f"Database:         {config.database_path}")
    print(f"Registry:         {config.registry_file}")
    print(f"Log Level:        {config.log_level}")
    if config.log_file:
        print(f"Log File:         {config.log_file}")
    else:
        print(f"Log File:         Console only")
    print("=" * 80)
    print()
