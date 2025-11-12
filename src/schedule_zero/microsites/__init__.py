"""
ScheduleZero Microsite Architecture

Provides a registry system for organizing the portal into independent microsites,
each with its own routes, templates, and static assets.
"""

from pathlib import Path
from typing import List, Tuple
import tornado.web


class Microsite:
    """
    Represents a microsite with its own routes, templates, and assets.
    
    Attributes:
        name: Human-readable name of the microsite
        url_prefix: URL prefix for this microsite (e.g., '/dash', '/schedules')
        routes: List of (pattern, handler) tuples for Tornado routing
        assets_path: Path to static assets (css, js, images) for this microsite
        templates_path: Path to Tornado templates for this microsite
    """
    
    def __init__(
        self,
        name: str,
        url_prefix: str,
        routes: List[Tuple[str, type]],
        assets_path: str | Path,
        templates_path: str | Path = None
    ):
        self.name = name
        self.url_prefix = url_prefix.rstrip('/')  # Normalize
        self.routes = routes
        self.assets_path = Path(assets_path)
        self.templates_path = Path(templates_path) if templates_path else self.assets_path.parent / 'templates'
    
    def get_route_handlers(self) -> List[Tuple[str, type]]:
        """
        Get Tornado route handlers with URL prefix applied.
        
        Returns:
            List of (url_pattern, handler_class) tuples
        """
        handlers = []
        for pattern, handler in self.routes:
            # Prefix the pattern with microsite's URL prefix
            if pattern == r"/":
                prefixed_pattern = self.url_prefix + "/"
            else:
                prefixed_pattern = self.url_prefix + pattern
            handlers.append((prefixed_pattern, handler))
        return handlers
    
    def get_static_handler(self) -> Tuple[str, type, dict]:
        """
        Get Tornado static file handler for this microsite's assets.
        
        Returns:
            Tuple of (url_pattern, StaticFileHandler, config_dict)
        """
        return (
            rf"{self.url_prefix}/static/(.*)",
            tornado.web.StaticFileHandler,
            {"path": str(self.assets_path)}
        )


class MicrositeRegistry:
    """
    Central registry for all microsites in the application.
    """
    
    def __init__(self):
        self.microsites: List[Microsite] = []
        self._container_path = Path(__file__).parent / '_container'
    
    def register(self, microsite: Microsite):
        """Register a microsite with the application."""
        self.microsites.append(microsite)
    
    def get_all_handlers(self) -> List[Tuple[str, type] | Tuple[str, type, dict]]:
        """
        Get all route handlers and static handlers from all registered microsites.
        
        Returns:
            List of Tornado route handler tuples
        """
        handlers = []
        
        # Add container static handler (shared assets)
        handlers.append((
            r"/static/_container/(.*)",
            tornado.web.StaticFileHandler,
            {"path": str(self._container_path / 'assets')}
        ))
        
        # Add each microsite's routes and static handlers
        for microsite in self.microsites:
            handlers.extend(microsite.get_route_handlers())
            handlers.append(microsite.get_static_handler())
        
        return handlers
    
    def get_template_paths(self) -> List[str]:
        """
        Get all template paths for Tornado template loader.
        
        Returns:
            List of template directory paths
        """
        paths = [str(self._container_path / 'templates')]
        
        for microsite in self.microsites:
            if microsite.templates_path.exists():
                paths.append(str(microsite.templates_path))
        
        return paths


# Global registry instance
registry = MicrositeRegistry()
