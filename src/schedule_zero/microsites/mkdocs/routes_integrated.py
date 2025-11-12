"""
Alternative: Integrated MkDocs Routes (with iframe wrapper)

This provides true integration by wrapping MkDocs content in the container layout.
Use this if you want docs to appear as a native microsite with SZ navigation visible.
"""

import tornado.web
from pathlib import Path


class IntegratedDocsHandler(tornado.web.RequestHandler):
    """
    Serve MkDocs within the ScheduleZero container using an iframe.
    
    This approach:
    - Shows SZ navigation sidebar
    - Embeds MkDocs content in an iframe
    - Keeps MkDocs theme/navigation intact
    - Allows switching back to Dashboard without new tab
    """
    
    async def get(self, path=""):
        """Render docs page with iframe."""
        # Build iframe src path
        docs_path = path if path else "index.html"
        iframe_src = f"/docs-content/{docs_path}"
        
        self.render(
            'mkdocs/templates/docs_wrapper.html',
            active_site='docs',
            iframe_src=iframe_src
        )


class DocsContentHandler(tornado.web.StaticFileHandler):
    """
    Serve raw MkDocs content for iframe embedding.
    Separate from main /docs route to avoid conflicts.
    """
    
    def initialize(self):
        """Initialize with path to built docs."""
        docs_path = Path(__file__).parent.parent.parent.parent.parent / 'docs_site_build'
        super().initialize(path=str(docs_path), default_filename="index.html")
    
    @classmethod
    def get_absolute_path(cls, root, path):
        """Override to handle directory requests."""
        import os
        abspath = os.path.abspath(os.path.join(root, path))
        
        if os.path.isdir(abspath):
            index_path = os.path.join(abspath, "index.html")
            if os.path.exists(index_path):
                return index_path
        
        return abspath
    
    def validate_absolute_path(self, root, absolute_path):
        """Override to allow serving from docs directory."""
        import os
        if not absolute_path.startswith(os.path.abspath(root)):
            raise tornado.web.HTTPError(403, "Access denied")
        
        if not os.path.exists(absolute_path):
            raise tornado.web.HTTPError(404, "Documentation not found")
        
        return absolute_path


# INTEGRATED ROUTES (use these for iframe approach)
integrated_routes = [
    (r"/(.*)", IntegratedDocsHandler),  # Main docs page with iframe
]

# CONTENT ROUTES (these serve the actual MkDocs files for iframe)
# Register these in tornado_app_server.py as:
# (r"/docs-content/(.*)", DocsContentHandler)
