---
title: ConductorZero Architecture
tags:
  - exploration
  - architecture
  - orchestration
status: exploration
date: 2025-11-10
---

# ConductorZero - Simple Orchestration via ZMQ

**Date**: 2025-11-10  
**Status**: EXPLORATION - Simplified Architecture

## The Elegant Solution

### Core Insight: Don't Manage Processes - Coordinate Them

**Problem with previous analysis**: Trying to make governor control handler processes (start/stop/restart)
**Better approach**: Let handlers manage themselves, use ZMQ for coordination

## ConductorZero Architecture

### What It Is
A **lightweight orchestration handler** that runs like any other handler, using ZMQ to coordinate:
- Resource metrics collection
- Handler health monitoring  
- Coordination signals (optional)
- Load distribution (optional)

### What It's NOT
- ❌ NOT a process manager (systemd does that)
- ❌ NOT a gateway (handlers talk directly to server)
- ❌ NOT a supervisor (handlers are autonomous)
- ❌ Just another handler with orchestration methods

## Architecture

```
ScheduleZero Server (port 4244)
    ↓ ZMQ REQ/REP
    ├─→ Handler 1 (port 5001) ← Job execution
    ├─→ Handler 2 (port 5002) ← Job execution
    ├─→ Handler 3 (port 5003) ← Job execution
    └─→ ConductorZero (port 5999) ← Orchestration queries
            ↓ ZMQ REQ (client mode)
            ├─→ Handler 1 (port 5001) ← "report_metrics"
            ├─→ Handler 2 (port 5002) ← "report_metrics"
            └─→ Handler 3 (port 5003) ← "report_metrics"
```

**Key Points**:
- ConductorZero is **just another handler**
- It can **call other handlers** via ZMQ (as client)
- Handlers remain **autonomous** (manage own lifecycle)
- No process management needed!

## Handler Self-Management

### Handlers Can Sleep/Idle on Their Own

```python
class SmartHandler(ZMQHandlerBase):
    """Handler that self-manages resource consumption."""
    
    def __init__(self):
        super().__init__()
        self.idle_since = None
        self.sleep_mode = False
    
    async def _receive_loop(self):
        """Modified receive loop with idle detection."""
        while self.running:
            if await self.socket.poll(timeout=60000):  # 60 second timeout
                # Got message - handle it
                message = await self.socket.recv_json()
                self.idle_since = None
                self.sleep_mode = False
                
                # Process normally...
                result = await self._dispatch(message)
                await self.socket.send_json(result)
            
            else:
                # No message for 60 seconds - enter idle mode
                if not self.idle_since:
                    self.idle_since = datetime.now()
                    self.logger.info("Entering idle mode", idle_since=self.idle_since)
                
                # Sleep mode after 5 minutes idle
                idle_duration = (datetime.now() - self.idle_since).total_seconds()
                if idle_duration > 300 and not self.sleep_mode:
                    self.sleep_mode = True
                    self.logger.info("Entering sleep mode (releasing resources)", 
                                   idle_duration=idle_duration)
                    await self._release_resources()
    
    async def _release_resources(self):
        """Release expensive resources while idle."""
        # Close database connections
        if hasattr(self, 'db_pool'):
            await self.db_pool.close()
            self.db_pool = None
        
        # Clear caches
        if hasattr(self, 'cache'):
            self.cache.clear()
        
        # Garbage collect
        import gc
        gc.collect()
        
        self.logger.info("Resources released", mode="sleep")
    
    async def _ensure_resources(self):
        """Restore resources when needed."""
        if self.sleep_mode:
            self.logger.info("Waking from sleep mode")
            self.sleep_mode = False
            
            # Reconnect database
            if not self.db_pool:
                self.db_pool = await create_db_pool()
            
            # Warm up caches if needed
            await self._warm_cache()
```

**Benefits**:
- Handlers reduce RAM/CPU when idle **automatically**
- No external process manager needed
- Handlers wake instantly when job arrives
- Each handler controls its own resource strategy

## ConductorZero Implementation

### Simple Handler That Calls Other Handlers

```python
# src/schedule_zero/handlers/conductor_zero.py

import zmq
import zmq.asyncio
import psutil
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from ..zmq_handler_base import ZMQHandlerBase


class ConductorZero(ZMQHandlerBase):
    """
    Lightweight orchestration handler for ScheduleZero.
    
    Collects metrics, monitors health, and coordinates handlers.
    Runs as a normal handler - no special privileges.
    """
    
    def __init__(self, handler_registry: Dict[str, int]):
        """
        Initialize ConductorZero.
        
        Args:
            handler_registry: Dict mapping handler_id -> port
                             e.g., {"discord": 5001, "backup": 5002}
        """
        super().__init__()
        self.handler_registry = handler_registry
        self.zmq_client_ctx = zmq.asyncio.Context()
    
    async def ping_handler(self, handler_id: str) -> Dict:
        """
        Ping a handler to check if it's alive.
        
        Called by server: schedule("conductor", "ping_handler", {"handler_id": "discord"})
        """
        port = self.handler_registry.get(handler_id)
        if not port:
            return {"alive": False, "error": f"Unknown handler: {handler_id}"}
        
        # Create ZMQ client to handler
        socket = self.zmq_client_ctx.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:{port}")
        
        try:
            # Send ping
            await socket.send_json({
                "method": "ping",
                "params": {},
                "request_id": f"conductor_ping_{handler_id}"
            })
            
            # Wait for response (with timeout)
            if await socket.poll(timeout=5000):  # 5 second timeout
                response = await socket.recv_json()
                return {
                    "alive": True,
                    "handler_id": handler_id,
                    "response_time_ms": response.get("duration_ms", 0)
                }
            else:
                return {"alive": False, "error": "Timeout"}
        
        except Exception as e:
            return {"alive": False, "error": str(e)}
        
        finally:
            socket.close()
    
    async def collect_metrics(self, handler_ids: Optional[List[str]] = None) -> Dict:
        """
        Collect resource metrics from handlers.
        
        Called by server: schedule("conductor", "collect_metrics", {})
        Returns: {"handlers": {...}, "summary": {...}}
        """
        if handler_ids is None:
            handler_ids = list(self.handler_registry.keys())
        
        metrics = {}
        
        for handler_id in handler_ids:
            port = self.handler_registry.get(handler_id)
            if not port:
                continue
            
            socket = self.zmq_client_ctx.socket(zmq.REQ)
            socket.connect(f"tcp://localhost:{port}")
            
            try:
                # Request metrics
                await socket.send_json({
                    "method": "get_metrics",
                    "params": {},
                    "request_id": f"conductor_metrics_{handler_id}"
                })
                
                if await socket.poll(timeout=5000):
                    response = await socket.recv_json()
                    metrics[handler_id] = response.get("result", {})
                else:
                    metrics[handler_id] = {"error": "Timeout"}
            
            except Exception as e:
                metrics[handler_id] = {"error": str(e)}
            
            finally:
                socket.close()
        
        # Calculate summary
        total_memory = sum(
            m.get("memory_mb", 0) 
            for m in metrics.values() 
            if "error" not in m
        )
        
        alive_count = sum(
            1 for m in metrics.values() 
            if "error" not in m
        )
        
        return {
            "handlers": metrics,
            "summary": {
                "total_handlers": len(handler_ids),
                "alive_handlers": alive_count,
                "total_memory_mb": total_memory,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def get_system_metrics(self) -> Dict:
        """
        Get system-wide resource metrics.
        
        Called by server: schedule("conductor", "get_system_metrics", {})
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_mb": memory.total / 1024 / 1024,
                "available_mb": memory.available / 1024 / 1024,
                "used_mb": memory.used / 1024 / 1024,
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / 1024 / 1024 / 1024,
                "free_gb": disk.free / 1024 / 1024 / 1024,
                "used_gb": disk.used / 1024 / 1024 / 1024,
                "percent": disk.percent
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict:
        """
        Comprehensive health check of all handlers.
        
        Called by server: schedule("conductor", "health_check", {})
        """
        handler_health = {}
        
        for handler_id, port in self.handler_registry.items():
            ping_result = await self.ping_handler(handler_id)
            handler_health[handler_id] = {
                "alive": ping_result.get("alive", False),
                "response_time_ms": ping_result.get("response_time_ms"),
                "error": ping_result.get("error")
            }
        
        healthy_count = sum(1 for h in handler_health.values() if h["alive"])
        
        return {
            "handlers": handler_health,
            "summary": {
                "healthy": healthy_count,
                "total": len(self.handler_registry),
                "health_percentage": (healthy_count / len(self.handler_registry) * 100) if self.handler_registry else 0
            },
            "timestamp": datetime.now().isoformat()
        }


# Standard handler methods required by ZMQHandlerBase
async def ping() -> Dict:
    """Health check endpoint."""
    return {"status": "ok", "handler": "conductor_zero"}


async def get_metrics() -> Dict:
    """Return conductor's own metrics."""
    process = psutil.Process()
    return {
        "cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "num_threads": process.num_threads(),
        "uptime_seconds": (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
    }
```

### Handler Base Class Extension

```python
# Add to ZMQHandlerBase to support metrics

class ZMQHandlerBase:
    # ... existing code ...
    
    async def get_metrics(self) -> Dict:
        """
        Get resource metrics for this handler.
        
        Override in subclass to add custom metrics.
        """
        try:
            process = psutil.Process()
            return {
                "handler_id": self.handler_id,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "num_threads": process.num_threads(),
                "connections": len(process.connections()),
                "uptime_seconds": self._get_uptime(),
                "status": "sleeping" if getattr(self, "sleep_mode", False) else "active",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_uptime(self) -> float:
        """Calculate handler uptime in seconds."""
        if hasattr(self, 'start_time'):
            return (datetime.now() - self.start_time).total_seconds()
        return 0
```

## Usage Examples

### Schedule Metrics Collection

```python
# Collect metrics every 5 minutes
response = requests.post("http://localhost:8888/api/schedule", json={
    "handler_id": "conductor",
    "method_name": "collect_metrics",
    "trigger": {
        "type": "interval",
        "minutes": 5
    },
    "job_id": "metrics_collection"
})

# Health check every minute
response = requests.post("http://localhost:8888/api/schedule", json={
    "handler_id": "conductor",
    "method_name": "health_check",
    "trigger": {
        "type": "interval",
        "minutes": 1
    },
    "job_id": "health_monitor"
})

# System metrics every 10 minutes
response = requests.post("http://localhost:8888/api/schedule", json={
    "handler_id": "conductor",
    "method_name": "get_system_metrics",
    "trigger": {
        "type": "interval",
        "minutes": 10
    },
    "job_id": "system_metrics"
})
```

### Query Results via Execution Log

```python
# Get latest metrics
response = requests.get("http://localhost:8888/api/executions", params={
    "handler_id": "conductor",
    "limit": 1
})

metrics = response.json()["records"][0]["result"]
print(f"Total memory: {metrics['summary']['total_memory_mb']} MB")
print(f"Alive handlers: {metrics['summary']['alive_handlers']}")
```

## Use Case: Service Catalog for Cloud Processors

### Scenario: Client-Hosted Endpoints for SaaS

**Architecture**:
```
Your SaaS Backend (Cloud)
    ↓ HTTPS API
Your Service Catalog
    ↓ Register endpoint
Client's ScheduleZero (On-Premise)
    ├─ Server (schedules jobs)
    ├─ CloudProcessor Handler (your service)
    ├─ ConductorZero (monitors health)
    └─ Client's custom handlers
```

### CloudProcessor Handler (Client Installs)

```python
# Your service catalog offering: "Data Processor Endpoint"

class CloudProcessorHandler(ZMQHandlerBase):
    """
    Client-installed handler that processes data and sends to your cloud.
    
    Client benefits:
    - Schedule processing on their terms (data residency, timing)
    - Use their compute resources (save your cloud costs)
    - ScheduleZero handles retry, monitoring, logging
    
    Your benefits:
    - Client does the scheduling/orchestration
    - You just receive processed data
    - No need to poll their systems
    """
    
    def __init__(self, api_key: str, endpoint: str):
        super().__init__()
        self.api_key = api_key
        self.endpoint = endpoint  # Your SaaS API
    
    async def process_and_upload(self, data_source: str, params: Dict) -> Dict:
        """
        Client schedules this method to run on their schedule.
        
        Client's schedule:
        POST http://localhost:8888/api/schedule
        {
            "handler_id": "cloud_processor",
            "method_name": "process_and_upload",
            "params": {
                "data_source": "/path/to/data",
                "params": {"format": "parquet"}
            },
            "trigger": {"type": "cron", "hour": 2, "minute": 0}  # 2am daily
        }
        """
        # 1. Read client's data (on their infrastructure)
        data = await self._read_data(data_source)
        
        # 2. Process locally (using their compute)
        processed = await self._process(data, params)
        
        # 3. Upload to your cloud
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                json=processed,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                result = await response.json()
        
        return {
            "status": "uploaded",
            "records": len(processed),
            "cloud_job_id": result.get("job_id"),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_report(self) -> Dict:
        """
        Client schedules this to send health status to your SaaS.
        
        You can monitor which clients are healthy without polling them.
        """
        metrics = await self.get_metrics()
        
        # Send to your monitoring endpoint
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
```

### Service Catalog Benefits

**For Clients**:
- ✅ Keep data on-premise (compliance, security)
- ✅ Use their compute (cost savings for them)
- ✅ Schedule on their terms (maintenance windows, rate limiting)
- ✅ Built-in retry, logging, monitoring (via ScheduleZero)
- ✅ Simple install: `pip install your-processor-handler`

**For You (SaaS Provider)**:
- ✅ No polling client systems (they push to you)
- ✅ Client does orchestration (you just receive data)
- ✅ Cheaper compute (clients use their resources)
- ✅ Easier scaling (distributed to clients)
- ✅ Service catalog item: "Install our data processor handler"

### Installation Flow

**1. Client installs your handler**:
```bash
pip install your-company-processor-handler
```

**2. Client configures in handler_registry.yaml**:
```yaml
handlers:
  - handler_id: cloud_processor
    module_path: your_company.cloud_processor_handler
    class_name: CloudProcessorHandler
    port: 5555
    config:
      api_key: "client_api_key_here"
      endpoint: "https://api.yourcompany.com/v1/process"
```

**3. Client schedules jobs**:
```bash
# Via ScheduleZero API or portal
curl -X POST http://localhost:8888/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "handler_id": "cloud_processor",
    "method_name": "process_and_upload",
    "params": {"data_source": "/data/exports"},
    "trigger": {"type": "cron", "hour": 2, "minute": 0}
  }'
```

**4. Your SaaS receives processed data**:
- Client's ScheduleZero calls `process_and_upload` at 2am
- Handler processes on client's infrastructure
- Uploads to your API
- ScheduleZero handles retry, logging, monitoring

## Feature Breakdown (Realistic)

### Feature 1: ConductorZero Handler (Core)
**What**: Handler that calls other handlers for metrics/health  
**Effort**: 
- Base handler class: 2 hours (mostly done)
- Conductor methods: 4 hours
- Testing: 2 hours
**Total**: 1 day

### Feature 2: Handler Self-Management (Sleep Mode)
**What**: Handlers detect idle state and release resources  
**Effort**:
- Modify receive loop: 1 hour
- Resource release methods: 2 hours
- Testing: 2 hours
**Total**: 5 hours

### Feature 3: Metrics Integration
**What**: Add psutil metrics to all handlers  
**Effort**:
- Add psutil dependency: 5 minutes
- Implement get_metrics: 1 hour
- Update docs: 1 hour
**Total**: 2 hours

### Feature 4: Service Catalog Pattern
**What**: Document + example handler for client installation  
**Effort**:
- Example CloudProcessor handler: 3 hours
- Documentation: 2 hours
- Installation guide: 1 hour
**Total**: 6 hours

### Feature 5: Monitoring Dashboard (Optional)
**What**: Simple HTML dashboard showing conductor metrics  
**Effort**:
- HTML/JS frontend: 4 hours
- API integration: 2 hours
- Styling: 2 hours
**Total**: 1 day

**Grand Total**: 2-3 days for core features (1-5), 3-4 days with dashboard

## Advantages of This Approach

### vs. ProcessGovernor
| Aspect | ProcessGovernor | ConductorZero |
|--------|----------------|---------------|
| **Complexity** | High (process management) | Low (just another handler) |
| **Dependencies** | subprocess, signals, PIDs | psutil, ZMQ (already have) |
| **Process control** | Must start/stop handlers | Handlers are autonomous |
| **Resource savings** | Stop/start entire process | Handlers sleep in-place |
| **Implementation** | 4 weeks | 2-3 days |
| **Failure modes** | Zombie processes, orphans | Handler just doesn't respond |
| **Cross-platform** | Complex (signals differ) | Simple (ZMQ everywhere) |

### Benefits
1. **Simple**: ConductorZero is just another handler (no special powers)
2. **Fast**: 2-3 days vs 4 weeks
3. **Elegant**: Handlers self-manage resources (no external control)
4. **Scalable**: Works local or distributed (handlers anywhere)
5. **Service catalog ready**: Easy to package handlers for clients

### Limitations
- ⚠️ Can't force restart unresponsive handler (systemd still needed for that)
- ⚠️ Handlers must cooperate (implement get_metrics, sleep logic)
- ⚠️ No cold start (handlers always running, just sleeping)

## Recommendation

**Implement ConductorZero** as simple orchestration handler:

**Week 1** (3 days):
- Day 1: ConductorZero base implementation + metrics
- Day 2: Handler self-management (sleep mode) + testing
- Day 3: Documentation + service catalog example

**Week 2** (optional):
- Dashboard for metrics visualization
- Advanced coordination features if needed

**Result**: Lightweight, elegant solution that solves 80% of use cases in 20% of the time!

---

**Does this approach make more sense?** It's simpler, faster, and leverages ZMQ's strengths instead of fighting process management.
