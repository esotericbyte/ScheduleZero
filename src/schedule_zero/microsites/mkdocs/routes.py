"""
MkDocs Microsite Routes

Serves the built MkDocs documentation within the ScheduleZero container layout.
Uses iframe embedding to show MkDocs content while keeping SZ navigation visible.
"""

import tornado.web
from pathlib import Path


class DocsWrapperHandler(tornado.web.RequestHandler):
    """
    Render the docs page with MkDocs content embedded in an iframe.
    Shows ScheduleZero navigation with docs content.
    """
    
    async def get(self, path=""):
        """Render docs wrapper page."""
        # Default to index if no path specified
        iframe_path = path.strip('/') if path else "index.html"
        
        self.render(
            'mkdocs/templates/docs_wrapper.html',
            active_site='docs',
            iframe_path=iframe_path
        )


class DocsContentHandler(tornado.web.StaticFileHandler):
    """
    Serve raw MkDocs static files for iframe embedding.
    This is accessed at /docs-content/* to avoid route conflicts.
    """
    
    def initialize(self):
        """Initialize with path to built docs."""
        # Path to docs_site_build/ in project root
        docs_path = Path(__file__).parent.parent.parent.parent.parent / 'docs_site_build'
        super().initialize(path=str(docs_path), default_filename="index.html")
    
    @classmethod
    def get_absolute_path(cls, root, path):
        """Override to handle directory requests."""
        import os
        abspath = os.path.abspath(os.path.join(root, path))
        
        # If path is a directory, serve index.html
        if os.path.isdir(abspath):
            index_path = os.path.join(abspath, "index.html")
            if os.path.exists(index_path):
                return index_path
        
        return abspath
    
    def validate_absolute_path(self, root, absolute_path):
        """Override to allow serving from docs directory."""
        import os
        # Ensure path is within docs directory
        if not absolute_path.startswith(os.path.abspath(root)):
            raise tornado.web.HTTPError(403, "Access denied")
        
        if not os.path.exists(absolute_path):
            raise tornado.web.HTTPError(404, "Documentation not found. Run 'mkdocs build' first.")
        
        return absolute_path
    
    def set_extra_headers(self, path):
        """Set caching headers for static docs."""
        # Cache static assets for 1 hour
        if path.endswith(('.css', '.js', '.png', '.jpg', '.svg', '.woff', '.woff2')):
            self.set_header("Cache-Control", "public, max-age=3600")
        else:
            # Don't cache HTML pages (allows updates without hard refresh)
            self.set_header("Cache-Control", "no-cache")


# Microsite routes - wrapper page with HTMX navigation
routes = [
    (r"/(.*)", DocsWrapperHandler),  # Catch all paths, render wrapper
]
