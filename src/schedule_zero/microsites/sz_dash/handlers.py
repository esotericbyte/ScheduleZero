"""
Dashboard microsite handlers.

Displays system overview with stats and recent activity.
"""
from ..base import MicrositeHandler
from ...logging_config import get_logger

logger = get_logger(__name__, component="Dashboard")


class DashboardHandler(MicrositeHandler):
    """
    Main dashboard page showing system overview.
    
    Displays:
    - System statistics (schedules, handlers, jobs)
    - Recent activity
    - Quick actions
    """
    
    def initialize(self, registry=None, registry_lock=None, scheduler=None):
        """Initialize with dependencies."""
        self.registry = registry
        self.registry_lock = registry_lock
        self.scheduler = scheduler
    
    async def get(self):
        """Render dashboard page."""
        # Get system statistics
        stats = await self.get_system_stats()
        
        # Get recent schedules
        recent_schedules = await self.get_recent_schedules()
        
        # Render full page or partial based on HTMX request
        self.render_microsite(
            'microsites/sz_dash/templates/dashboard',
            stats=stats,
            recent_schedules=recent_schedules
        )
    
    async def get_system_stats(self):
        """
        Get dashboard statistics.
        
        Returns:
            dict: System statistics
        """
        stats = {
            'total_handlers': 0,
            'active_handlers': 0,
            'total_schedules': 0,
            'active_schedules': 0,
            'jobs_today': 0
        }
        
        # Count handlers
        if self.registry and self.registry_lock:
            async with self.registry_lock.reader:
                stats['total_handlers'] = len(self.registry)
                stats['active_handlers'] = sum(
                    1 for h in self.registry.values() 
                    if h.get('status') == 'active'
                )
        
        # Count schedules
        if self.scheduler:
            try:
                schedules = await self.scheduler.get_schedules()
                stats['total_schedules'] = len(schedules)
                # TODO: Count active schedules (next_fire_time is set)
                stats['active_schedules'] = len([
                    s for s in schedules 
                    if s.next_fire_time is not None
                ])
            except Exception as e:
                logger.error(f"Error getting schedules: {e}", exc_info=True)
        
        return stats
    
    async def get_recent_schedules(self):
        """
        Get recently created or modified schedules.
        
        Returns:
            list: Recent schedule information
        """
        recent = []
        
        if self.scheduler:
            try:
                schedules = await self.scheduler.get_schedules()
                # Get up to 5 most recent schedules
                # TODO: Sort by created/modified time when available
                for schedule in schedules[:5]:
                    recent.append({
                        'id': schedule.id,
                        'task': schedule.task_id,
                        'next_run': schedule.next_fire_time.isoformat() if schedule.next_fire_time else 'Not scheduled',
                        'trigger': type(schedule.trigger).__name__
                    })
            except Exception as e:
                logger.error(f"Error getting recent schedules: {e}", exc_info=True)
        
        return recent


# Routes for this microsite
routes = [
    (r"/dash/?", DashboardHandler),
]
