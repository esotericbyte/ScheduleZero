"""Portal configuration management for ScheduleZero.

Loads and validates portal_config.yaml which defines:
- Portal root directory
- Microsite configurations
- Component library settings
- Static assets paths
- Template settings

If no portal_config.yaml exists, server gracefully degrades to:
- Minimal branded page
- Documentation microsite only
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .logging_config import get_logger

logger = get_logger(__name__, component="PortalConfig")


@dataclass
class MicrositeConfig:
    """Configuration for a single microsite."""
    name: str
    url_prefix: str
    routes_module: str
    templates_path: str
    assets_path: str
    enabled: bool = True
    
    def __post_init__(self):
        """Validate microsite configuration."""
        if not self.url_prefix.startswith('/'):
            raise ValueError(f"Microsite '{self.name}' url_prefix must start with '/' (got: {self.url_prefix})")
        if not self.routes_module:
            raise ValueError(f"Microsite '{self.name}' routes_module is required")


@dataclass
class PortalConfig:
    """Portal configuration loaded from portal_config.yaml."""
    portal_name: str
    portal_version: str
    description: str
    admin_contact: str
    portal_root: Path
    component_library: List[str]
    microsites: List[MicrositeConfig]
    static_path: str
    static_url_prefix: str
    template_cache: bool
    template_autoreload: bool
    
    def __post_init__(self):
        """Validate portal configuration."""
        # Ensure portal_root is absolute
        if not self.portal_root.is_absolute():
            # Make relative to config file directory
            config_dir = Path.cwd()
            self.portal_root = (config_dir / self.portal_root).resolve()
        
        # Validate static_url_prefix
        if not self.static_url_prefix.startswith('/'):
            self.static_url_prefix = '/' + self.static_url_prefix
        if not self.static_url_prefix.endswith('/'):
            self.static_url_prefix += '/'
    
    def get_static_path(self) -> Path:
        """Get absolute path to static assets."""
        return self.portal_root / self.static_path
    
    def get_microsite_templates_path(self, microsite: MicrositeConfig) -> Path:
        """Get absolute path to microsite templates."""
        templates_path = Path(microsite.templates_path)
        if templates_path.is_absolute():
            return templates_path
        return self.portal_root / templates_path
    
    def get_microsite_assets_path(self, microsite: MicrositeConfig) -> Path:
        """Get absolute path to microsite assets."""
        assets_path = Path(microsite.assets_path)
        if assets_path.is_absolute():
            return assets_path
        return self.portal_root / assets_path
    
    def get_enabled_microsites(self) -> List[MicrositeConfig]:
        """Get list of enabled microsites."""
        return [ms for ms in self.microsites if ms.enabled]


def get_portal_config_path() -> str:
    """Get the portal configuration file path.
    
    Checks environment variable SCHEDULEZERO_PORTAL_CONFIG first,
    then falls back to portal_config.yaml in current directory.
    """
    return os.environ.get("SCHEDULEZERO_PORTAL_CONFIG", "portal_config.yaml")


def load_portal_config() -> Optional[PortalConfig]:
    """Load portal configuration from YAML file.
    
    If portal_config.yaml is missing, returns None.
    Server will fall back to minimal branded page + docs microsite.
    
    Returns:
        PortalConfig object with validated configuration, or None if no config
        
    Raises:
        ValueError: If configuration exists but is invalid
        yaml.YAMLError: If YAML syntax is invalid
    """
    config_path = get_portal_config_path()
    
    # If no config file, return None (graceful degradation)
    if not os.path.exists(config_path):
        logger.warning(f"No portal configuration found at {config_path}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    # Load YAML
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML syntax in {config_path}: {e}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    if not data:
        logger.warning(f"Portal configuration is empty: {config_path}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    # Validate required fields
    required_fields = ['portal_name', 'portal_root', 'microsites']
    missing = [field for field in required_fields if field not in data]
    if missing:
        logger.error(f"Missing required fields in {config_path}: {', '.join(missing)}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    # Parse microsites
    microsites = []
    if not isinstance(data['microsites'], list):
        logger.error(f"'microsites' must be a list in {config_path}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    for ms_data in data['microsites']:
        try:
            microsite = MicrositeConfig(
                name=ms_data['name'],
                url_prefix=ms_data['url_prefix'],
                routes_module=ms_data['routes_module'],
                templates_path=ms_data['templates_path'],
                assets_path=ms_data['assets_path'],
                enabled=ms_data.get('enabled', True)
            )
            microsites.append(microsite)
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid microsite configuration: {e}")
            logger.warning("Skipping invalid microsite, continuing with others")
    
    # Build PortalConfig
    try:
        config = PortalConfig(
            portal_name=data['portal_name'],
            portal_version=data.get('portal_version', '1.0.0'),
            description=data.get('description', ''),
            admin_contact=data.get('admin_contact', ''),
            portal_root=Path(data['portal_root']),
            component_library=data.get('component_library', []),
            microsites=microsites,
            static_path=data.get('static_path', 'static'),
            static_url_prefix=data.get('static_url_prefix', '/static/'),
            template_cache=data.get('template_cache', True),
            template_autoreload=data.get('template_autoreload', False)
        )
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Portal configuration validation failed: {e}")
        logger.warning("Server will use minimal branded page + docs microsite only")
        return None
    
    # Log successful load
    logger.info(f"Loaded portal config: {config.portal_name} v{config.portal_version}")
    logger.info(f"Portal root: {config.portal_root}")
    logger.info(f"Component libraries: {', '.join(config.component_library) if config.component_library else 'none'}")
    logger.info(f"Enabled microsites: {len(config.get_enabled_microsites())}/{len(config.microsites)}")
    
    return config
