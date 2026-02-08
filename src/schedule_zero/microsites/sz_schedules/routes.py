"""
Schedules Manager Microsite Routes

Provides views for managing scheduled jobs.
"""

from ..base import MicrositeHandler


class SchedulesListHandler(MicrositeHandler):
    """Display list of all scheduled jobs."""
    
    async def get(self):
        """Render schedules list page."""
        # TODO: Get schedules from scheduler when dependency injection is added
        schedules = []
        
        self.render_microsite(
            'microsites/sz_schedules/templates/schedules_list',
            schedules=schedules
        )


class ScheduleDetailHandler(MicrositeHandler):
    """Display details for a specific schedule."""
    
    def initialize(self, scheduler):
        """Initialize with scheduler."""
        self.scheduler = scheduler
    
    async def get(self, schedule_id):
        """Render schedule detail page."""
        try:
            schedule = await self.scheduler.get_schedule(schedule_id)
        except Exception:
            self.set_status(404)
            self.write("<h1>Schedule not found</h1>")
            return
        
        self.render_microsite(
            'microsites/sz_schedules/templates/schedule_detail',
            schedule=schedule
        )


class ScheduleCreateHandler(MicrositeHandler):
    """Create a new schedule."""
    
    def initialize(self, scheduler, registry, registry_lock):
        """Initialize with scheduler and registry."""
        self.scheduler = scheduler
        self.registry = registry
        self.registry_lock = registry_lock
    
    async def get(self):
        """Render schedule creation form."""
        with self.registry_lock:
            handlers = list(self.registry.values())
        
        self.render_microsite(
            'microsites/sz_schedules/templates/schedule_create',
            handlers=handlers
        )


# Routes for this microsite
# Will be registered by tornado_app_server.py based on portal_config.yaml
routes = [
    (r"/", SchedulesListHandler),
    (r"/create", ScheduleCreateHandler),
    (r"/([^/]+)", ScheduleDetailHandler),
]
