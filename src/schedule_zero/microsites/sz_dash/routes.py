"""
Dashboard Microsite Routes

Provides the main dashboard view with schedule overview.
"""

import os
import tornado.web


class DashboardHandler(tornado.web.RequestHandler):
    """Main dashboard view showing schedule overview."""
    
    def initialize(self):
        """Set template path for this microsite."""
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.template_path = template_dir
    
    async def get(self):
        # TODO: Fetch actual schedule data from APScheduler
        schedules = [
            {
                'job_id': 'chime',
                'next_run': '2025-11-12T10:00:00Z',
                'status': 'active',
                'trigger': 'interval: 15 minutes'
            },
            {
                'job_id': 'ding_dong',
                'next_run': '2025-11-12T11:30:00Z',
                'status': 'active',
                'trigger': 'cron: */30 * * * *'
            }
        ]
        
        self.render(
            'dashboard.html',
            active_site='dash',
            schedules=schedules
        )


class ComponentTestHandler(tornado.web.RequestHandler):
    """Test page for verifying synced components."""
    
    def initialize(self):
        """Set template path for this microsite."""
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.template_path = template_dir
    
    async def get(self):
        self.render(
            'component_test.html',
            active_site='dash'
        )


# Microsite routes
routes = [
    (r"/", DashboardHandler),
    (r"/test/components", ComponentTestHandler),
]
