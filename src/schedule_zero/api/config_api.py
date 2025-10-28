"""Configuration API endpoint."""
import logging
from .tornado_base_handlers import BaseAPIHandler

logger = logging.getLogger(__name__)


class ConfigHandler(BaseAPIHandler):
    """API endpoint to get server configuration."""
    
    async def get(self):
        """Return server configuration."""
        config = self.deps.get('config', {})
        self.write_json(config)
