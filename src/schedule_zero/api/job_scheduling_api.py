"""Job scheduling API endpoints."""
import dateutil.parser
from apscheduler import ConflictingIdError, TaskLookupError
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from .tornado_base_handlers import BaseAPIHandler
from ..logging_config import get_logger

logger = get_logger(__name__, component="JobSchedulingAPI")


class ScheduleJobHandler(BaseAPIHandler):
    """API endpoint to schedule a new job."""
    
    async def post(self):
        """Schedule a job with specified trigger."""
        # Get required fields
        trigger = self.json_args.get("trigger")
        if not trigger:
            return self.send_error(400, reason="Missing required field: 'trigger'")
        
        result = self.get_required_fields("handler_id", "job_method", "job_params")
        if result is None:
            return  # Error already sent
        
        handler_id, job_method, job_params = result
        job_id = self.json_args.get("job_id")  # Optional
        
        # Get dependencies
        registry_lock = self.deps.get('registry_lock')
        registry = self.deps.get('registry')
        scheduler = self.deps.get('scheduler')
        # No longer need job_executor - use task_id instead
        
        # Validate handler and method
        with registry_lock:
            handler_info = registry.get(handler_id)
        
        if not handler_info:
            return self.send_error(404, reason=f"Handler '{handler_id}' not registered.")
        
        if job_method not in handler_info["methods"]:
            return self.send_error(
                400,
                reason=f"Method '{job_method}' not exposed by handler '{handler_id}'."
            )
        
        if not self.validate_dict(job_params, "job_params"):
            return
        
        # Parse trigger
        try:
            trigger_obj = self._parse_trigger(trigger)
        except ValueError as e:
            return self.send_error(400, reason=f"Invalid trigger configuration: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing trigger: {e}", method="post", 
                        exc_info=True)
            return self.send_error(500, reason=f"Internal error parsing trigger: {e}")
        
        # Add schedule to APScheduler
        try:
            schedule_options = {
                "id": job_id,
                "args": [handler_id, job_method, job_params]
            }
            
            if job_id is None:
                del schedule_options["id"]
            
            # Use the task_id instead of passing the callable directly
            schedule_id = await scheduler.add_schedule("job_executor", trigger=trigger_obj, **schedule_options)
            logger.info(f"Scheduled job via API: ID={schedule_id}, Handler={handler_id}, Method={job_method}")
            self.write_json({
                "status": "success",
                "job_id": schedule_id
            }, 201)
            
        except ConflictingIdError:
            return self.send_error(409, reason=f"Job ID '{job_id}' already exists.")
        except TaskLookupError:
            logger.error("TaskLookupError: Job executor function not found", exc_info=True)
            return self.send_error(500, reason="Internal error: Target task function not found.")
        except Exception as e:
            logger.error(f"API schedule add failed: {e}", exc_info=True)
            return self.send_error(500, reason=f"Internal error adding schedule: {e}")
    
    def _parse_trigger(self, trigger_config):
        """Parse trigger configuration and return appropriate trigger object."""
        trigger_type = trigger_config.get("type", "").lower()
        trigger_args = {k: v for k, v in trigger_config.items() if k != "type"}
        
        if trigger_type == "date":
            run_date_str = trigger_args.get("run_date")
            if not run_date_str:
                raise ValueError("'run_date' is required for date trigger")
            run_date = dateutil.parser.isoparse(run_date_str)
            return DateTrigger(run_time=run_date)
        
        elif trigger_type == "interval":
            # Convert interval units to floats
            for key in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
                if key in trigger_args:
                    trigger_args[key] = float(trigger_args[key])
            return IntervalTrigger(**trigger_args)
        
        elif trigger_type == "cron":
            return CronTrigger(**trigger_args)
        
        else:
            raise ValueError(
                f"Unsupported trigger type: '{trigger_type}'. Use 'date', 'interval', or 'cron'."
            )


class RunNowHandler(BaseAPIHandler):
    """API endpoint to execute a job immediately."""
    
    async def post(self):
        """Execute a job immediately without scheduling."""
        # Get required fields
        result = self.get_required_fields("handler_id", "job_method", "job_params")
        if result is None:
            return
        
        handler_id, job_method, job_params = result
        
        # Get dependencies
        registry_lock = self.deps.get('registry_lock')
        registry = self.deps.get('registry')
        job_executor = self.deps.get('job_executor')
        
        # Validate handler and method
        with registry_lock:
            handler_info = registry.get(handler_id)
        
        if not handler_info:
            return self.send_error(404, reason=f"Handler '{handler_id}' not registered.")
        
        if job_method not in handler_info["methods"]:
            return self.send_error(
                400,
                reason=f"Method '{job_method}' not exposed by handler '{handler_id}'."
            )
        
        if not self.validate_dict(job_params, "job_params"):
            return
        
        # Execute immediately
        try:
            result = await job_executor(handler_id, job_method, job_params)
            logger.info(f"Executed job immediately via API: Handler={handler_id}, Method={job_method}")
            self.write_json({
                "status": "success",
                "result": result,
                "message": f"Job executed on handler '{handler_id}'"
            })
        except Exception as e:
            logger.error(f"Failed to execute job immediately: {e}", exc_info=True)
            return self.send_error(500, reason=f"Failed to execute job: {e}")


class ListSchedulesHandler(BaseAPIHandler):
    """API endpoint to list all scheduled jobs."""
    
    async def get(self):
        """Return list of all scheduled jobs."""
        scheduler = self.deps.get('scheduler')
        
        try:
            schedules = await scheduler.get_schedules()
            schedules_list = []
            
            for schedule in schedules:
                schedules_list.append({
                    "id": schedule.id,
                    "next_fire_time": schedule.next_fire_time.isoformat() if schedule.next_fire_time else None,
                    "trigger": str(schedule.trigger),
                    "args": schedule.args if hasattr(schedule, 'args') else None
                })
            
            self.write_json({"schedules": schedules_list, "count": len(schedules_list)})
            
        except Exception as e:
            logger.error(f"Failed to list schedules: {e}", exc_info=True)
            return self.send_error(500, reason=f"Failed to list schedules: {e}")
