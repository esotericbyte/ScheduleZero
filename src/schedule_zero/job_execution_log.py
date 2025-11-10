"""
Job Execution Log

Captures job execution history for monitoring and analytics.
Provides in-memory circular buffer with optional database persistence.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass, asdict
import threading


@dataclass
class JobExecutionRecord:
    """Record of a job execution attempt."""
    
    # Execution identifiers
    job_id: str
    handler_id: str
    method_name: str
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Result
    status: str = "running"  # running, success, error, timeout
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Metadata
    attempt_number: int = 1
    max_attempts: int = 1
    params_summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO timestamps."""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class JobExecutionLog:
    """
    In-memory circular buffer for job execution history.
    
    Thread-safe storage of recent job executions with queryable interface.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize execution log.
        
        Args:
            max_size: Maximum number of records to keep in memory
        """
        self.max_size = max_size
        self._records = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._record_count = 0
    
    def record_start(
        self,
        job_id: str,
        handler_id: str,
        method_name: str,
        attempt_number: int = 1,
        max_attempts: int = 1,
        params: Optional[Dict] = None
    ) -> JobExecutionRecord:
        """
        Record the start of a job execution.
        
        Args:
            job_id: APScheduler job ID
            handler_id: Handler identifier
            method_name: Method being called
            attempt_number: Current attempt (for retries)
            max_attempts: Maximum attempts configured
            params: Job parameters (will be summarized)
        
        Returns:
            JobExecutionRecord that can be updated
        """
        # Create params summary (truncate large values)
        params_summary = None
        if params:
            # Handle both dict and non-dict params
            if isinstance(params, dict):
                summary_parts = []
                for key, value in list(params.items())[:5]:  # First 5 params
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    summary_parts.append(f"{key}={value_str}")
                params_summary = ", ".join(summary_parts)
                if len(params) > 5:
                    params_summary += f" (+{len(params) - 5} more)"
            else:
                # Non-dict params - just convert to string
                params_summary = str(params)[:100]
        
        record = JobExecutionRecord(
            job_id=job_id,
            handler_id=handler_id,
            method_name=method_name,
            started_at=datetime.now(timezone.utc),
            attempt_number=attempt_number,
            max_attempts=max_attempts,
            params_summary=params_summary
        )
        
        with self._lock:
            self._records.append(record)
            self._record_count += 1
        
        return record
    
    def record_success(
        self,
        record: JobExecutionRecord,
        result: Optional[Dict] = None
    ):
        """
        Mark a job execution as successful.
        
        Args:
            record: The execution record to update
            result: Result dict from handler
        """
        record.completed_at = datetime.now(timezone.utc)
        record.duration_ms = (
            (record.completed_at - record.started_at).total_seconds() * 1000
        )
        record.status = "success"
        record.result = result
    
    def record_error(
        self,
        record: JobExecutionRecord,
        error: str,
        is_final: bool = True
    ):
        """
        Mark a job execution as failed.
        
        Args:
            record: The execution record to update
            error: Error message
            is_final: Whether this was the final attempt
        """
        record.completed_at = datetime.now(timezone.utc)
        record.duration_ms = (
            (record.completed_at - record.started_at).total_seconds() * 1000
        )
        record.status = "error" if is_final else "retry"
        record.error = error
    
    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent job execution records.
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of execution records as dicts (newest first)
        """
        with self._lock:
            records = list(self._records)
        
        # Reverse to get newest first
        records.reverse()
        
        return [record.to_dict() for record in records[:limit]]
    
    def get_by_handler(
        self,
        handler_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get executions for a specific handler.
        
        Args:
            handler_id: Handler identifier
            limit: Maximum records to return
        
        Returns:
            List of execution records (newest first)
        """
        with self._lock:
            records = [r for r in self._records if r.handler_id == handler_id]
        
        records.reverse()
        return [record.to_dict() for record in records[:limit]]
    
    def get_by_job(
        self,
        job_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get executions for a specific job.
        
        Args:
            job_id: APScheduler job ID
            limit: Maximum records to return
        
        Returns:
            List of execution records (newest first)
        """
        with self._lock:
            records = [r for r in self._records if r.job_id == job_id]
        
        records.reverse()
        return [record.to_dict() for record in records[:limit]]
    
    def get_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent failed executions.
        
        Args:
            limit: Maximum records to return
        
        Returns:
            List of error records (newest first)
        """
        with self._lock:
            records = [r for r in self._records if r.status == "error"]
        
        records.reverse()
        return [record.to_dict() for record in records[:limit]]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dict with success rates, error counts, etc.
        """
        with self._lock:
            records = list(self._records)
        
        total = len(records)
        if total == 0:
            return {
                "total_executions": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0
            }
        
        success_count = sum(1 for r in records if r.status == "success")
        error_count = sum(1 for r in records if r.status == "error")
        
        # Calculate average duration for completed jobs
        completed = [r for r in records if r.duration_ms is not None]
        avg_duration = (
            sum(r.duration_ms for r in completed) / len(completed)
            if completed else 0.0
        )
        
        # Handler stats
        handler_stats = {}
        for record in records:
            if record.handler_id not in handler_stats:
                handler_stats[record.handler_id] = {
                    "total": 0,
                    "success": 0,
                    "error": 0
                }
            
            handler_stats[record.handler_id]["total"] += 1
            if record.status == "success":
                handler_stats[record.handler_id]["success"] += 1
            elif record.status == "error":
                handler_stats[record.handler_id]["error"] += 1
        
        return {
            "total_executions": total,
            "lifetime_executions": self._record_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / total) * 100 if total > 0 else 0.0,
            "avg_duration_ms": avg_duration,
            "by_handler": handler_stats,
            "buffer_size": self.max_size,
            "buffer_utilization": (total / self.max_size) * 100
        }
    
    def clear(self):
        """Clear all execution records."""
        with self._lock:
            self._records.clear()
