"""
Base handler for microsites with HTMX support.

Provides utilities for rendering full pages vs. partial content
based on whether the request came from HTMX.
"""
import json
import tornado.web
from ..logging_config import get_logger

logger = get_logger(__name__, component="MicrositeBase")


class MicrositeHandler(tornado.web.RequestHandler):
    """
    Base handler for all microsite pages.
    
    Provides HTMX-aware rendering:
    - Full page loads: renders complete layout with navigation
    - HTMX requests: renders just the content fragment
    
    CORS Note: This handler serves HTML, not JSON. If serving from different
    origin/port than frontend, you may need to add CORS headers here too.
    For same-origin setups (typical), CORS is not required for HTML.
    
    Usage:
        class DashboardHandler(MicrositeHandler):
            async def get(self):
                data = await self.get_dashboard_data()
                self.render_microsite('dashboard', data=data)
    """
    
    def set_default_headers(self):
        """
        Set headers for HTML responses.
        
        Note: CORS typically not needed for same-origin HTML responses.
        If your frontend is on different origin (http://localhost:3000 vs :8888),
        uncomment these CORS headers.
        """
        # Uncomment if serving from different origin:
        # self.set_header("Access-Control-Allow-Origin", "*")
        # self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # self.set_header("Access-Control-Allow-Headers", "Content-Type, HX-Request, HX-Trigger, HX-Target, HX-Current-URL")
        pass
    
    def is_htmx_request(self):
        """
        Check if request came from HTMX.
        
        HTMX sets the HX-Request header to 'true' on all requests.
        
        Returns:
            bool: True if this is an HTMX request
        """
        return self.request.headers.get('HX-Request') == 'true'
    
    def get_current_path(self):
        """Get the current request path for navigation highlighting."""
        return self.request.path
    
    def render_microsite(self, template_name, **kwargs):
        """
        Render full page or partial based on HTMX request.
        
        For normal browser requests:
            - Renders {template_name}.html with full layout
        
        For HTMX requests:
            - Renders {template_name}_partial.html (just the content)
        
        Templates are resolved relative to src/schedule_zero/, so pass
        the full path from that root, e.g.:
            self.render_microsite('microsites/sz_dash/templates/dashboard', ...)
        
        Args:
            template_name: Template path (without .html, relative to src/schedule_zero/)
            **kwargs: Template variables
        """
        # Add current path for navigation
        kwargs['current_path'] = self.get_current_path()
        
        if self.is_htmx_request():
            # HTMX request: render just the content fragment
            template = f'{template_name}_partial.html'
            logger.debug(f"Rendering HTMX partial: {template}", path=self.request.path)
            self.render(template, **kwargs)
        else:
            # Normal request: render full page with layout
            template = f'{template_name}.html'
            logger.debug(f"Rendering full page: {template}", path=self.request.path)
            self.render(template, **kwargs)
    
    def trigger_client_event(self, event_name, data=None):
        """
        Trigger client-side event via HX-Trigger header.
        
        This allows the server to trigger JavaScript events on the client
        after an HTMX request completes.
        
        Args:
            event_name: Name of the event to trigger
            data: Optional data to pass with the event
        
        Example:
            # Trigger simple event
            self.trigger_client_event('refreshNav')
            
            # Trigger event with data
            self.trigger_client_event('showMessage', {
                'text': 'Schedule created!',
                'type': 'success'
            })
        """
        if data:
            self.set_header('HX-Trigger', json.dumps({event_name: data}))
        else:
            self.set_header('HX-Trigger', event_name)
        
        logger.debug(f"Triggered client event: {event_name}", data=data)
    
    def htmx_redirect(self, url):
        """
        Redirect the client via HX-Redirect header.
        
        This is a client-side redirect that works with HTMX.
        
        Args:
            url: URL to redirect to
        """
        self.set_header('HX-Redirect', url)
        logger.debug(f"HTMX redirect to: {url}")
    
    def htmx_refresh(self):
        """
        Tell the client to refresh the entire page.
        
        Sets HX-Refresh header to trigger a full page reload.
        """
        self.set_header('HX-Refresh', 'true')
        logger.debug("HTMX refresh triggered")
    
    def htmx_push_url(self, url):
        """
        Update browser URL without navigation.
        
        Args:
            url: URL to push to browser history
        """
        self.set_header('HX-Push-Url', url)
        logger.debug(f"HTMX push URL: {url}")
