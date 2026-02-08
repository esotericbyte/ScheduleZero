"""
Handlers Registry Microsite Routes

Provides views for browsing and managing registered handlers.
"""

from ..base import MicrositeHandler


class HandlersListHandler(MicrositeHandler):
    """Display list of all registered handlers."""
    
    async def get(self):
        """Render handlers list page."""
        # TODO: Get handlers from registry when dependency injection is added
        handlers = []
        
        self.render_microsite(
            'microsites/sz_handlers/templates/handlers_list',
            handlers=handlers
        )


class HandlerDetailHandler(MicrositeHandler):
    """Display details for a specific handler."""
    
    def initialize(self, registry, registry_lock):
        """Initialize with handler registry."""
        self.registry = registry
        self.registry_lock = registry_lock
    
    async def get(self, handler_id):
        """Render handler detail page."""
        with self.registry_lock:
            handler = self.registry.get(handler_id)
        
        if not handler:
            self.set_status(404)
            self.write("<h1>Handler not found</h1>")
            return
        
        self.render_microsite(
            'microsites/sz_handlers/templates/handler_detail',
            handler=handler
        )


# Routes for this microsite
# Will be registered by tornado_app_server.py based on portal_config.yaml
routes = [
    (r"/", HandlersListHandler),
    (r"/([^/]+)", HandlerDetailHandler),
]
