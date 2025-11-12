"""
Base Tornado handlers and utilities for the ScheduleZero API.

Provides common functionality for JSON APIs, error handling, and response formatting.
"""
import logging
import json
import tornado.web

logger = logging.getLogger(__name__)


class BaseAPIHandler(tornado.web.RequestHandler):
    """Base handler for JSON API endpoints with common functionality."""
    
    def initialize(self, **kwargs):
        """Store any dependencies passed during route setup."""
        self.deps = kwargs
        self.json_args = None
    
    def prepare(self):
        """Parse JSON body for POST/PUT requests."""
        if self.request.method in ["POST", "PUT", "PATCH"]:
            content_type = self.request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    self.json_args = json.loads(self.request.body.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Failed to parse JSON body: {e}")
                    self.json_args = None
    
    def set_default_headers(self):
        """Set CORS and content-type headers."""
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
    
    def options(self, *args, **kwargs):
        """Handle CORS preflight requests."""
        self.set_status(204)
        self.finish()
    
    def write_json(self, data, status_code=200):
        """Write JSON response with proper status code."""
        self.set_status(status_code)
        self.write(json.dumps(data, indent=2, default=str))
        self.finish()
    
    def write_error(self, status_code, **kwargs):
        """Custom error response in JSON format."""
        error_data = {
            "error": {
                "code": status_code,
                "message": self._reason or "Unknown error"
            }
        }
        
        # Include exception details in debug mode
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            import traceback
            error_data["error"]["traceback"] = "".join(
                traceback.format_exception(*kwargs["exc_info"])
            )
        
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(error_data, indent=2))
        self.finish()
    
    def send_error(self, status_code=500, **kwargs):
        """Override to use custom error format."""
        reason = kwargs.get('reason')
        if reason:
            self._reason = reason
        super().send_error(status_code, **kwargs)
    
    def get_required_fields(self, *fields):
        """
        Extract required fields from JSON body.
        
        Returns tuple of field values or sends error if missing.
        Returns None if any field is missing (error already sent).
        """
        if not self.json_args:
            self.send_error(400, reason="JSON body required.")
            return None
        
        missing = [f for f in fields if f not in self.json_args]
        if missing:
            self.send_error(400, reason=f"Missing required fields: {missing}")
            return None
        
        return tuple(self.json_args[f] for f in fields)
    
    def validate_dict(self, value, field_name):
        """Validate that a field is a dictionary."""
        if not isinstance(value, dict):
            self.send_error(400, reason=f"'{field_name}' must be a dictionary/object.")
            return False
        return True


class HealthCheckHandler(BaseAPIHandler):
    """Simple health check endpoint."""
    
    async def get(self):
        """Return health status."""
        self.write_json({
            "status": "ok",
            "service": "ScheduleZero"
        })


class IndexHandler(tornado.web.RequestHandler):
    """Serve the main HTML interface with enhanced UI."""
    
    def initialize(self, config, template_path):
        """Store config and template path for rendering."""
        self.config = config
        self.template_path = template_path
    
    def get(self):
        """Render the enhanced main HTML page."""
        instance_name = self.config.get('instance_name', 'Distributed Task Scheduler')
        description = self.config.get('description', 'N/A')
        version = self.config.get('version', 'N/A')
        admin_contact = self.config.get('admin_contact', 'N/A')
        title = self.config.get('title', 'ScheduleZero')
        
        self.render(
            "index.html",
            title=title,
            instance_name=instance_name,
            description=description,
            version=version,
            admin_contact=admin_contact
        )


class ReadmeHandler(tornado.web.RequestHandler):
    """Serve README content."""
    
    def initialize(self, readme_path):
        """Store README path."""
        self.readme_path = readme_path
    
    def get(self):
        """Return README as plain text."""
        try:
            with open(self.readme_path, 'r') as f:
                readme_content = f.read()
            self.set_header("Content-Type", "text/plain")
            self.write(readme_content)
        except FileNotFoundError:
            self.send_error(404, reason="README not found")
        except Exception as e:
            logger.error(f"Error reading README: {e}")
            self.send_error(500, reason=f"Error reading README: {e}")
