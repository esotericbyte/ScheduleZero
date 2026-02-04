"""
Portal Configuration API

Provides portal configuration to frontend components (sz-nav, etc.)
"""
import tornado.web
from .tornado_base_handlers import BaseAPIHandler
from ..logging_config import get_logger

logger = get_logger(__name__, component="PortalConfigAPI")


class PortalConfigHandler(BaseAPIHandler):
    """
    Serves portal configuration to frontend components.
    
    Extends BaseAPIHandler for proper CORS support with HTMX headers.
    
    GET /api/portal/config returns:
    {
        "portal": {
            "name": "ScheduleZero",
            "version": "1.0.0"
        },
        "microsites": [
            {
                "id": "sz_dash",
                "name": "Dashboard",
                "icon": "📊",
                "path": "/dash",
                "type": "htmx",
                "description": "..."
            }
        ],
        "theme": {
            "css_variables": {...},
            "stylesheet": "/static/css/theme.css"
        }
    }
    """
    
    def initialize(self, portal_config=None, **kwargs):
        """Initialize with portal configuration."""
        super().initialize(**kwargs)
        self.portal_config = portal_config
    
    def get(self):
        """Return portal configuration as JSON."""
        if not self.portal_config:
            # Fallback: minimal configuration
            logger.debug("No portal config - returning minimal fallback")
            self.write_json({
                'portal': {
                    'name': 'ScheduleZero',
                    'version': '1.0.0'
                },
                'microsites': [
                    {
                        'id': 'docs',
                        'name': 'Documentation',
                        'icon': '📚',
                        'path': '/docs',
                        'type': 'mkdocs',
                        'description': 'API Documentation'
                    }
                ],
                'theme': {
                    'css_variables': {
                        'primary_color': '#1976D2',
                        'secondary_color': '#424242'
                    },
                    'stylesheet': '/static/css/theme.css'
                }
            })
            return
        
        try:
            # Get enabled microsites from config
            enabled_microsites = self.portal_config.get_enabled_microsites()
            
            # Transform for frontend
            microsites_data = []
            for ms_config in enabled_microsites:
                microsites_data.append({
                    'id': ms_config.id,
                    'name': ms_config.name,
                    'icon': ms_config.icon,
                    'path': ms_config.url_prefix,
                    'type': ms_config.microsite_type,
                    'description': ms_config.description
                })
            
            # Build response
            response = {
                'portal': {
                    'name': self.portal_config.portal_name,
                    'version': self.portal_config.portal_version
                },
                'microsites': microsites_data,
                'theme': {
                    'css_variables': self.portal_config.theme_css_variables,
                    'stylesheet': self.portal_config.theme_stylesheet,
                    'component_styles': self.portal_config.theme_component_styles
                }
            }
            
            logger.debug(f"Returning portal config with {len(microsites_data)} microsites")
            self.write_json(response)
            
        except Exception as e:
            logger.error(f"Error building portal config response: {e}", exc_info=True)
            self.write_json({'error': str(e)}, status_code=500)
