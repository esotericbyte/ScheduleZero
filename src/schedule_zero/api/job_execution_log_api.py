"""
Job Execution Log API Handlers

Endpoints for querying job execution history, statistics, and errors.
"""
from typing import Optional
from .tornado_base_handlers import BaseAPIHandler


class JobExecutionHistoryHandler(BaseAPIHandler):
    """API endpoint to query job execution history."""
    
    def initialize(self, execution_log, **kwargs):
        """Initialize with execution log instance."""
        super().initialize(**kwargs)
        self.execution_log = execution_log
    
    def get(self):
        """
        Get job execution history.
        
        Query Parameters:
            limit: Maximum records to return (default: 100, max: 1000)
            handler_id: Filter by handler ID
            job_id: Filter by job ID
            status: Filter by status (success, error, running)
        """
        try:
            limit = int(self.get_argument("limit", "100"))
            limit = min(limit, 1000)  # Cap at 1000
            
            handler_id = self.get_argument("handler_id", None)
            job_id = self.get_argument("job_id", None)
            status_filter = self.get_argument("status", None)
            
            # Get filtered results
            if handler_id:
                records = self.execution_log.get_by_handler(handler_id, limit)
            elif job_id:
                records = self.execution_log.get_by_job(job_id, limit)
            else:
                records = self.execution_log.get_recent(limit)
            
            # Apply status filter if specified
            if status_filter:
                records = [r for r in records if r["status"] == status_filter]
            
            self.write_json({
                "count": len(records),
                "limit": limit,
                "records": records
            })
        
        except ValueError as e:
            self.send_error(400, reason=f"Invalid parameter: {e}")
        except Exception as e:
            self.logger.error(f"Error retrieving execution history: {e}", exc_info=True)
            self.send_error(500, reason=f"Failed to retrieve history: {e}")


class JobExecutionStatsHandler(BaseAPIHandler):
    """API endpoint for execution statistics."""
    
    def initialize(self, execution_log, **kwargs):
        """Initialize with execution log instance."""
        super().initialize(**kwargs)
        self.execution_log = execution_log
    
    def get(self):
        """
        Get execution statistics.
        
        Returns:
            - Total executions
            - Success/error counts and rates
            - Average duration
            - Per-handler statistics
        """
        try:
            stats = self.execution_log.get_stats()
            self.write_json(stats)
        
        except Exception as e:
            self.logger.error(f"Error retrieving execution stats: {e}", exc_info=True)
            self.send_error(500, reason=f"Failed to retrieve stats: {e}")


class JobExecutionErrorsHandler(BaseAPIHandler):
    """API endpoint for recent job execution errors."""
    
    def initialize(self, execution_log, **kwargs):
        """Initialize with execution log instance."""
        super().initialize(**kwargs)
        self.execution_log = execution_log
    
    def get(self):
        """
        Get recent job execution errors.
        
        Query Parameters:
            limit: Maximum errors to return (default: 50, max: 500)
        """
        try:
            limit = int(self.get_argument("limit", "50"))
            limit = min(limit, 500)
            
            errors = self.execution_log.get_errors(limit)
            
            self.write_json({
                "count": len(errors),
                "limit": limit,
                "errors": errors
            })
        
        except ValueError as e:
            self.send_error(400, reason=f"Invalid parameter: {e}")
        except Exception as e:
            self.logger.error(f"Error retrieving execution errors: {e}", exc_info=True)
            self.send_error(500, reason=f"Failed to retrieve errors: {e}")


class JobExecutionClearHandler(BaseAPIHandler):
    """API endpoint to clear execution history."""
    
    def initialize(self, execution_log, **kwargs):
        """Initialize with execution log instance."""
        super().initialize(**kwargs)
        self.execution_log = execution_log
    
    def post(self):
        """Clear execution history (admin endpoint)."""
        try:
            self.execution_log.clear()
            self.logger.info("Execution history cleared via API")
            
            self.write_json({
                "status": "success",
                "message": "Execution history cleared"
            })
        
        except Exception as e:
            self.logger.error(f"Error clearing execution history: {e}", exc_info=True)
            self.send_error(500, reason=f"Failed to clear history: {e}")
