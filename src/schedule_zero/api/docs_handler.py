"""
Documentation Handler for serving MkDocs site.
"""
import os
import tornado.web


class DocsHandler(tornado.web.StaticFileHandler):
    """
    Serve static documentation built by mkdocs.
    
    Usage:
        1. Build docs: mkdocs build
        2. Server runs at: http://localhost:8888/docs/
    """
    
    def initialize(self, docs_path):
        """Initialize with path to built docs."""
        self.root = docs_path
        super().initialize(path=docs_path, default_filename="index.html")
    
    @classmethod
    def get_absolute_path(cls, root, path):
        """Override to handle directory requests."""
        abspath = os.path.abspath(os.path.join(root, path))
        
        # If path is a directory, serve index.html
        if os.path.isdir(abspath):
            index_path = os.path.join(abspath, "index.html")
            if os.path.exists(index_path):
                return index_path
        
        return abspath
    
    def validate_absolute_path(self, root, absolute_path):
        """Override to allow serving from docs directory."""
        # Ensure path is within docs directory
        if not absolute_path.startswith(os.path.abspath(root)):
            raise tornado.web.HTTPError(403, "Access denied")
        
        if not os.path.exists(absolute_path):
            raise tornado.web.HTTPError(404, "Documentation not found")
        
        return absolute_path
    
    def set_extra_headers(self, path):
        """Set caching headers for static docs."""
        # Cache static assets for 1 hour
        if path.endswith(('.css', '.js', '.png', '.jpg', '.svg')):
            self.set_header("Cache-Control", "public, max-age=3600")
        else:
            # Don't cache HTML pages
            self.set_header("Cache-Control", "no-cache")


class DocsIndexHandler(tornado.web.RequestHandler):
    """
    Redirect /docs to /docs/ for proper static file serving.
    """
    
    def get(self):
        self.redirect("/docs/", permanent=True)
