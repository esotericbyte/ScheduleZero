"""Handler-related API endpoints."""
import logging
from .tornado_base_handlers import BaseAPIHandler

logger = logging.getLogger(__name__)


class ListHandlersHandler(BaseAPIHandler):
    """API endpoint to list all registered handlers."""
    
    async def get(self):
        """Return list of all registered handlers with status."""
        registry_lock = self.deps.get('registry_lock')
        registry = self.deps.get('registry')
        
        with registry_lock:
            handlers_list = []
            for handler_id, info in registry.items():
                # Try to ping handler to check if it's alive
                status = "Disconnected"
                client = info.get('client')
                if client:
                    try:
                        client.ping(timeout=2)
                        status = "Connected"
                    except Exception:
                        status = "Disconnected"
                
                handlers_list.append({
                    "id": handler_id,
                    "address": info.get("address"),
                    "methods": info.get("methods", []),
                    "status": status
                })
        
        self.write_json({"handlers": handlers_list})
