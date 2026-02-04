"""
Handlers Registry Microsite Routes

Provides views for browsing and managing registered handlers.
"""

import tornado.web


class HandlersListHandler(tornado.web.RequestHandler):
    """Display list of all registered handlers."""
    
    def initialize(self, registry, registry_lock):
        """Initialize with handler registry."""
        self.registry = registry
        self.registry_lock = registry_lock
        
        # Set template path for this microsite
        import os
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates')
    
    async def get(self):
        """Render handlers list page."""
        async with self.registry_lock:
            handlers = list(self.registry.list_handlers())
        
        self.render('handlers_list.html', handlers=handlers)


class HandlerDetailHandler(tornado.web.RequestHandler):
    """Display details for a specific handler."""
    
    def initialize(self, registry, registry_lock):
        """Initialize with handler registry."""
        self.registry = registry
        self.registry_lock = registry_lock
        
        # Set template path for this microsite
        import os
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates')
    
    async def get(self, handler_id):
        """Render handler detail page."""
        async with self.registry_lock:
            handler = self.registry.get_handler(handler_id)
        
        if not handler:
            self.set_status(404)
            self.render('handler_not_found.html', handler_id=handler_id)
            return
        
        self.render('handler_detail.html', handler=handler)


# Routes for this microsite
# Will be registered by tornado_app_server.py based on portal_config.yaml
routes = [
    (r"/", HandlersListHandler),
    (r"/([^/]+)", HandlerDetailHandler),
]
