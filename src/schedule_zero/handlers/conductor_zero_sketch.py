"""
ConductorZero - Lightweight Orchestration Handler

A simple handler that coordinates other handlers via ZMQ.
NO PROCESS MANAGEMENT - just metrics collection and health monitoring.
"""

import zmq.asyncio
import psutil
import asyncio
from typing import Optional
from datetime import datetime

# Note: This would inherit from ZMQHandlerBase in real implementation
# Showing standalone for clarity


class ConductorZero:
    """
    Orchestration handler that calls other handlers for metrics/health.
    
    Usage:
        # In handler_registry.yaml
        handlers:
          - handler_id: conductor
            module_path: schedule_zero.handlers.conductor_zero
            class_name: ConductorZero
            port: 5999
            config:
              registry:
                discord: 5001
                backup: 5002
                webhook: 5003
    """
    
    def __init__(self, registry: Dict[str, int]):
        """
        Args:
            registry: Map of handler_id -> port
        """
        self.registry = registry
        self.ctx = zmq.asyncio.Context()
    
    async def _call_handler(self, handler_id: str, method: str, params: dict = None, timeout: int = 5000) -> dict:
        """Call a method on another handler via ZMQ."""
        port = self.registry.get(handler_id)
        if not port:
            return {"error": f"Unknown handler: {handler_id}"}
        
        socket = self.ctx.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:{port}")
        
        try:
            # Send request
            await socket.send_json({
                "method": method,
                "params": params or {},
                "request_id": f"conductor_{method}_{handler_id}"
            })
            
            # Wait for response
            if await socket.poll(timeout=timeout):
                return await socket.recv_json()
            else:
                return {"error": "Timeout"}
        
        except Exception as e:
            return {"error": str(e)}
        
        finally:
            socket.close()
    
    # ===== SCHEDULED METHODS (Called by ScheduleZero Server) =====
    
    async def collect_metrics(self, handler_ids: Optional[List[str]] = None) -> Dict:
        """
        Collect resource metrics from all handlers.
        
        Schedule this:
            POST /api/schedule
            {
                "handler_id": "conductor",
                "method_name": "collect_metrics",
                "trigger": {"type": "interval", "minutes": 5}
            }
        """
        if handler_ids is None:
            handler_ids = list(self.registry.keys())
        
        # Call all handlers in parallel
        tasks = [
            self._call_handler(hid, "get_metrics")
            for hid in handler_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build metrics dict
        metrics = {}
        for hid, result in zip(handler_ids, results):
            if isinstance(result, Exception):
                metrics[hid] = {"error": str(result)}
            else:
                metrics[hid] = result.get("result", result)
        
        # Summary stats
        total_memory = sum(
            m.get("memory_mb", 0)
            for m in metrics.values()
            if "error" not in m
        )
        
        alive = sum(1 for m in metrics.values() if "error" not in m)
        
        return {
            "handlers": metrics,
            "summary": {
                "total": len(handler_ids),
                "alive": alive,
                "total_memory_mb": round(total_memory, 2),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def health_check(self) -> Dict:
        """
        Ping all handlers to check they're responsive.
        
        Schedule this:
            POST /api/schedule
            {
                "handler_id": "conductor",
                "method_name": "health_check",
                "trigger": {"type": "interval", "minutes": 1}
            }
        """
        # Ping all handlers
        tasks = [
            self._call_handler(hid, "ping")
            for hid in self.registry.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build health status
        health = {}
        for hid, result in zip(self.registry.keys(), results):
            if isinstance(result, Exception):
                health[hid] = {"alive": False, "error": str(result)}
            else:
                health[hid] = {
                    "alive": "error" not in result,
                    "response_time_ms": result.get("duration_ms", 0)
                }
        
        healthy_count = sum(1 for h in health.values() if h["alive"])
        
        return {
            "handlers": health,
            "summary": {
                "healthy": healthy_count,
                "total": len(self.registry),
                "health_percentage": round(healthy_count / len(self.registry) * 100, 1) if self.registry else 0
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_system_metrics(self) -> Dict:
        """
        Get system-wide resource metrics.
        
        Schedule this:
            POST /api/schedule
            {
                "handler_id": "conductor",
                "method_name": "get_system_metrics",
                "trigger": {"type": "interval", "minutes": 10}
            }
        """
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu,
            "memory": {
                "total_mb": round(mem.total / 1024 / 1024, 2),
                "available_mb": round(mem.available / 1024 / 1024, 2),
                "used_mb": round(mem.used / 1024 / 1024, 2),
                "percent": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": disk.percent
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # ===== STANDARD HANDLER METHODS =====
    
    async def ping(self) -> Dict:
        """Health check endpoint."""
        return {"status": "ok", "handler": "conductor_zero"}
    
    async def get_metrics(self) -> Dict:
        """Conductor's own resource metrics."""
        process = psutil.Process()
        return {
            "handler_id": "conductor",
            "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "num_threads": process.num_threads(),
            "timestamp": datetime.now().isoformat()
        }


# ===== HANDLER SELF-MANAGEMENT EXAMPLE =====

class SleepyHandler:
    """
    Example handler that reduces resource consumption when idle.
    
    No external management needed - handler manages itself!
    """
    
    def __init__(self):
        self.idle_since = None
        self.sleep_mode = False
        self.db_pool = None
        self.cache = {}
    
    async def _receive_loop(self):
        """Modified receive loop with idle detection."""
        while self.running:
            # Poll with 60 second timeout
            if await self.socket.poll(timeout=60000):
                # Got message - wake up if sleeping
                if self.sleep_mode:
                    await self._wake_up()
                
                self.idle_since = None
                
                # Process message normally...
                message = await self.socket.recv_json()
                result = await self._dispatch(message)
                await self.socket.send_json(result)
            
            else:
                # No message for 60 seconds
                if not self.idle_since:
                    self.idle_since = datetime.now()
                
                # Enter sleep mode after 5 minutes idle
                idle_seconds = (datetime.now() - self.idle_since).total_seconds()
                if idle_seconds > 300 and not self.sleep_mode:
                    await self._sleep()
    
    async def _sleep(self):
        """Release resources while idle."""
        self.sleep_mode = True
        
        # Close database connections
        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None
        
        # Clear caches
        self.cache.clear()
        
        # Garbage collect
        import gc
        gc.collect()
        
        print(f"💤 Handler entering sleep mode (was idle 5+ minutes)")
    
    async def _wake_up(self):
        """Restore resources when needed."""
        print(f"⏰ Handler waking up from sleep mode")
        self.sleep_mode = False
        
        # Reconnect database if needed
        if not self.db_pool:
            self.db_pool = await self._create_db_pool()
    
    async def get_metrics(self) -> Dict:
        """Include sleep status in metrics."""
        process = psutil.Process()
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "status": "sleeping" if self.sleep_mode else "active",
            "idle_seconds": (datetime.now() - self.idle_since).total_seconds() if self.idle_since else 0
        }


# ===== SERVICE CATALOG EXAMPLE =====

class CloudProcessorHandler:
    """
    Example handler for service catalog deployment.
    
    Clients install this handler to process data and send to your SaaS.
    
    Benefits for client:
    - Data stays on-premise until ready to upload
    - Uses their compute resources
    - Scheduled on their terms
    - Built-in retry/logging via ScheduleZero
    
    Benefits for you (SaaS provider):
    - No polling client systems
    - Client handles orchestration
    - Distributed compute (their infrastructure)
    """
    
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
    
    async def process_and_upload(self, data_source: str, format: str = "json") -> Dict:
        """
        Client schedules this method on their terms.
        
        Client's schedule:
            POST http://localhost:8888/api/schedule
            {
                "handler_id": "cloud_processor",
                "method_name": "process_and_upload",
                "params": {
                    "data_source": "/data/exports/daily",
                    "format": "parquet"
                },
                "trigger": {
                    "type": "cron",
                    "hour": 2,
                    "minute": 0
                }
            }
        
        Runs at 2am daily on client's infrastructure.
        """
        import aiohttp
        
        # 1. Read client's data (their infrastructure)
        data = await self._read_local_data(data_source, format)
        
        # 2. Process locally (their compute)
        processed = await self._process_data(data)
        
        # 3. Upload to your SaaS
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/ingest",
                json=processed,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as resp:
                result = await resp.json()
        
        return {
            "status": "uploaded",
            "records": len(processed),
            "cloud_job_id": result.get("job_id"),
            "bytes_uploaded": result.get("bytes"),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_report(self) -> Dict:
        """
        Client schedules this to report health to your SaaS.
        
        You can monitor all clients without polling them!
        """
        import aiohttp
        
        metrics = await self.get_metrics()
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.endpoint}/health",
                json={
                    "client_id": self.api_key,
                    "metrics": metrics,
                    "timestamp": datetime.now().isoformat()
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        
        return {"status": "reported", "metrics": metrics}


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    """
    Example usage and scheduling patterns.
    """
    
    # Schedule metrics collection every 5 minutes
    schedule_metrics = {
        "handler_id": "conductor",
        "method_name": "collect_metrics",
        "trigger": {
            "type": "interval",
            "minutes": 5
        },
        "job_id": "metrics_collector"
    }
    
    # Schedule health check every minute
    schedule_health = {
        "handler_id": "conductor",
        "method_name": "health_check",
        "trigger": {
            "type": "interval",
            "minutes": 1
        },
        "job_id": "health_monitor"
    }
    
    # Query results via execution log API
    # GET http://localhost:8888/api/executions?handler_id=conductor&limit=1
    # Returns latest metrics in result field
    
    print("ConductorZero: Simple orchestration via ZMQ")
    print("\nKey features:")
    print("- Collects metrics from all handlers")
    print("- Health monitoring")
    print("- NO process management needed")
    print("- Handlers self-manage resources")
    print("- Service catalog ready")
    print("\nImplementation: 2-3 days")
