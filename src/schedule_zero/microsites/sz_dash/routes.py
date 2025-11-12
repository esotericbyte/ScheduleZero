"""
Dashboard Microsite Routes

Provides the main dashboard view with schedule overview.
"""

import tornado.web


class DashboardHandler(tornado.web.RequestHandler):
    """Main dashboard view showing schedule overview."""
    
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
            'sz_dash/templates/dashboard.html',
            active_site='dash',
            schedules=schedules
        )


# Microsite routes
routes = [
    (r"/", DashboardHandler),
]
