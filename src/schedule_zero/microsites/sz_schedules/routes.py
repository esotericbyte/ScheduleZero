"""
Schedules Manager Microsite Routes

Provides views for managing scheduled jobs.
"""

import tornado.web


class SchedulesListHandler(tornado.web.RequestHandler):
    """Display list of all scheduled jobs."""
    
    def initialize(self, scheduler):
        """Initialize with scheduler."""
        self.scheduler = scheduler
        
        # Set template path for this microsite
        import os
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates')
    
    async def get(self):
        """Render schedules list page."""
        # Get all schedules from APScheduler
        schedules = await self.scheduler.get_schedules()
        
        self.render('schedules_list.html', schedules=schedules)


class ScheduleDetailHandler(tornado.web.RequestHandler):
    """Display details for a specific schedule."""
    
    def initialize(self, scheduler):
        """Initialize with scheduler."""
        self.scheduler = scheduler
        
        # Set template path for this microsite
        import os
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates')
    
    async def get(self, schedule_id):
        """Render schedule detail page."""
        try:
            schedule = await self.scheduler.get_schedule(schedule_id)
        except Exception:
            self.set_status(404)
            self.render('schedule_not_found.html', schedule_id=schedule_id)
            return
        
        self.render('schedule_detail.html', schedule=schedule)


class ScheduleCreateHandler(tornado.web.RequestHandler):
    """Create a new schedule."""
    
    def initialize(self, scheduler, registry, registry_lock):
        """Initialize with scheduler and registry."""
        self.scheduler = scheduler
        self.registry = registry
        self.registry_lock = registry_lock
        
        # Set template path for this microsite
        import os
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates')
    
    async def get(self):
        """Render schedule creation form."""
        async with self.registry_lock:
            handlers = list(self.registry.list_handlers())
        
        self.render('schedule_create.html', handlers=handlers)


# Routes for this microsite
# Will be registered by tornado_app_server.py based on portal_config.yaml
routes = [
    (r"/", SchedulesListHandler),
    (r"/create", ScheduleCreateHandler),
    (r"/([^/]+)", ScheduleDetailHandler),
]
