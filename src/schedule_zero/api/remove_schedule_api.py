"""API endpoint to remove/delete scheduled jobs."""
from apscheduler import JobLookupError
from .tornado_base_handlers import BaseAPIHandler
from ..logging_config import get_logger

logger = get_logger(__name__, component="RemoveScheduleAPI")


class RemoveScheduleHandler(BaseAPIHandler):
    """API endpoint to remove a scheduled job."""
    
    async def delete(self, schedule_id):
        """Remove a schedule by ID."""
        scheduler = self.deps.get('scheduler')
        
        if not schedule_id:
            return self.send_error(400, reason="Missing schedule ID")
        
        try:
            await scheduler.remove_schedule(schedule_id)
            logger.info(f"Removed schedule via API: {schedule_id}")
            self.write_json({
                "status": "success",
                "message": f"Schedule '{schedule_id}' removed",
                "schedule_id": schedule_id
            })
            
        except JobLookupError:
            return self.send_error(404, reason=f"Schedule '{schedule_id}' not found")
        except Exception as e:
            logger.error(f"Failed to remove schedule: {e}", exc_info=True)
            return self.send_error(500, reason=f"Failed to remove schedule: {e}")
