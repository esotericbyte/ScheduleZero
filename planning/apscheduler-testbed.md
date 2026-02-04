# APScheduler Test Bed

**ScheduleZero as a comprehensive testing platform for APScheduler edge cases, stress tests, and complex scheduling patterns.**

## Purpose

Test APScheduler 4.x behavior under conditions beyond typical use cases:
- Self-modifying schedules (jobs that reschedule themselves)
- Conditional loops (job chains with branching logic)
- High-frequency scheduling (millisecond-scale intervals)
- Cascading triggers (jobs that spawn more jobs)
- Distributed feedback loops (across multiple nodes)
- Schedule storms (rapid creation/deletion)

## Test Categories

### 1. Temporal Resolution Tests

**Millisecond-scale scheduling:**
```python
# tests/apscheduler_testbed/test_temporal_resolution.py
import asyncio
from datetime import datetime, timedelta
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

async def test_millisecond_intervals():
    """Test APScheduler's minimum reliable interval"""
    execution_times = []
    
    async def record_execution():
        execution_times.append(datetime.now())
    
    async with AsyncScheduler() as scheduler:
        # Schedule at 10ms intervals
        await scheduler.add_schedule(
            record_execution,
            IntervalTrigger(milliseconds=10),
            id="ms_test"
        )
        
        await scheduler.start_in_background()
        await asyncio.sleep(1)  # Run for 1 second
    
    # Analyze jitter and missed executions
    intervals = [
        (execution_times[i+1] - execution_times[i]).total_seconds() * 1000
        for i in range(len(execution_times) - 1)
    ]
    
    print(f"Expected: 100 executions (10ms * 100 = 1s)")
    print(f"Actual: {len(execution_times)} executions")
    print(f"Mean interval: {sum(intervals) / len(intervals):.2f}ms")
    print(f"Min interval: {min(intervals):.2f}ms")
    print(f"Max interval: {max(intervals):.2f}ms")
    print(f"Jitter (stddev): {statistics.stdev(intervals):.2f}ms")


async def test_accelerated_time_simulation():
    """Run 24 hours of schedules in 1 minute (1440x speedup)"""
    # Simulate daily tasks at 60-second intervals instead of 86400
    SPEEDUP = 1440
    
    async def daily_task():
        print(f"Daily task at simulated time: {get_simulated_time()}")
    
    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(
            daily_task,
            IntervalTrigger(seconds=60),  # Represents 1 day at 1440x
            id="accelerated_daily"
        )
        
        await scheduler.start_in_background()
        await asyncio.sleep(60)  # Simulate 24 hours
    
    # Verify behavior matches expectations
```

### 2. Self-Modifying Schedules

**Jobs that reschedule themselves based on results:**
```python
# tests/apscheduler_testbed/test_self_modifying.py
class AdaptiveScheduler:
    """Job that adjusts its own schedule based on execution time"""
    
    def __init__(self, scheduler: AsyncScheduler):
        self.scheduler = scheduler
        self.execution_times = []
    
    async def adaptive_job(self):
        """Job that reschedules itself based on performance"""
        start = datetime.now()
        
        # Simulate variable workload
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        duration = (datetime.now() - start).total_seconds()
        self.execution_times.append(duration)
        
        # Calculate adaptive interval
        avg_duration = sum(self.execution_times[-10:]) / len(self.execution_times[-10:])
        
        # Keep interval 2x average execution time (prevent overlaps)
        new_interval = max(avg_duration * 2, 0.5)
        
        # Reschedule self with new interval
        await self.scheduler.remove_schedule("adaptive")
        await self.scheduler.add_schedule(
            self.adaptive_job,
            IntervalTrigger(seconds=new_interval),
            id="adaptive"
        )
        
        print(f"Execution took {duration:.2f}s, next run in {new_interval:.2f}s")


async def test_fibonacci_backoff():
    """Job that reschedules with Fibonacci backoff on failure"""
    fib_sequence = [1, 1]
    
    async def failing_job():
        try:
            # Simulate intermittent failure
            if random.random() < 0.7:
                raise Exception("Simulated failure")
            
            print("Success! Resetting backoff.")
            fib_sequence.clear()
            fib_sequence.extend([1, 1])
            next_run = 1
        except Exception as e:
            # Calculate next Fibonacci number
            next_fib = fib_sequence[-1] + fib_sequence[-2]
            fib_sequence.append(next_fib)
            next_run = min(next_fib, 3600)  # Cap at 1 hour
            
            print(f"Failed. Next retry in {next_run}s (Fibonacci backoff)")
        
        # Reschedule self
        await scheduler.remove_schedule("fibonacci_retry")
        await scheduler.add_schedule(
            failing_job,
            IntervalTrigger(seconds=next_run),
            id="fibonacci_retry"
        )
```

### 3. Conditional Loops & Branching

**Jobs that branch into different schedules based on conditions:**
```python
# tests/apscheduler_testbed/test_conditional_loops.py
class StateMachine:
    """Scheduling state machine with conditional branches"""
    
    def __init__(self, scheduler: AsyncScheduler):
        self.scheduler = scheduler
        self.state = "idle"
        self.data = {}
    
    async def state_idle(self):
        """Idle state: Check for work every 5 seconds"""
        print("[IDLE] Checking for work...")
        
        if self.should_start_work():
            self.state = "working"
            # Transition to working state (faster polling)
            await self.scheduler.remove_schedule("state_machine")
            await self.scheduler.add_schedule(
                self.state_working,
                IntervalTrigger(seconds=1),
                id="state_machine"
            )
    
    async def state_working(self):
        """Working state: Process tasks rapidly"""
        print("[WORKING] Processing task...")
        
        # Simulate work
        await asyncio.sleep(0.5)
        self.data["tasks_processed"] = self.data.get("tasks_processed", 0) + 1
        
        if self.data["tasks_processed"] >= 10:
            self.state = "cooldown"
            # Transition to cooldown
            await self.scheduler.remove_schedule("state_machine")
            await self.scheduler.add_schedule(
                self.state_cooldown,
                IntervalTrigger(seconds=2),
                id="state_machine"
            )
    
    async def state_cooldown(self):
        """Cooldown state: Slow down before returning to idle"""
        print("[COOLDOWN] Cooling down...")
        
        if self.should_return_to_idle():
            self.state = "idle"
            self.data["tasks_processed"] = 0
            # Return to idle
            await self.scheduler.remove_schedule("state_machine")
            await self.scheduler.add_schedule(
                self.state_idle,
                IntervalTrigger(seconds=5),
                id="state_machine"
            )


async def test_cascading_triggers():
    """Job that spawns multiple downstream jobs"""
    async def parent_job():
        print("Parent job triggered")
        
        # Spawn child jobs based on conditions
        if should_run_child_a():
            await scheduler.add_schedule(
                child_job_a,
                IntervalTrigger(seconds=1),
                id=f"child_a_{uuid.uuid4()}"
            )
        
        if should_run_child_b():
            await scheduler.add_schedule(
                child_job_b,
                IntervalTrigger(seconds=2),
                id=f"child_b_{uuid.uuid4()}"
            )
    
    async def child_job_a():
        print("Child A executing")
        # Child can spawn grandchildren
        if should_cascade():
            await scheduler.add_schedule(
                grandchild_job,
                IntervalTrigger(seconds=0.5),
                id=f"grandchild_{uuid.uuid4()}"
            )
    
    # This creates a tree of schedules
    # Test: Does APScheduler handle rapid schedule creation?
```

### 4. Schedule Storms

**Stress test rapid schedule creation/deletion:**
```python
# tests/apscheduler_testbed/test_schedule_storms.py
async def test_schedule_creation_storm():
    """Create and delete schedules rapidly"""
    async with AsyncScheduler() as scheduler:
        await scheduler.start_in_background()
        
        # Create 1000 schedules as fast as possible
        start_time = datetime.now()
        
        for i in range(1000):
            await scheduler.add_schedule(
                lambda: None,
                IntervalTrigger(seconds=10),
                id=f"storm_{i}"
            )
        
        creation_time = (datetime.now() - start_time).total_seconds()
        print(f"Created 1000 schedules in {creation_time:.2f}s")
        print(f"Rate: {1000 / creation_time:.0f} schedules/sec")
        
        # Delete all schedules
        start_time = datetime.now()
        
        for i in range(1000):
            await scheduler.remove_schedule(f"storm_{i}")
        
        deletion_time = (datetime.now() - start_time).total_seconds()
        print(f"Deleted 1000 schedules in {deletion_time:.2f}s")
        print(f"Rate: {1000 / deletion_time:.0f} schedules/sec")


async def test_schedule_churn():
    """Continuously create and delete schedules (churn test)"""
    async with AsyncScheduler() as scheduler:
        await scheduler.start_in_background()
        
        churn_rate = 100  # schedules/sec
        duration = 60  # seconds
        
        async def churner():
            for _ in range(duration * churn_rate):
                schedule_id = f"churn_{uuid.uuid4()}"
                
                # Create
                await scheduler.add_schedule(
                    lambda: None,
                    IntervalTrigger(seconds=random.uniform(1, 10)),
                    id=schedule_id
                )
                
                # Wait random time
                await asyncio.sleep(random.uniform(0.001, 0.1))
                
                # Delete
                try:
                    await scheduler.remove_schedule(schedule_id)
                except:
                    pass  # May have been auto-deleted
        
        await churner()
        
        # Check scheduler health
        schedules = await scheduler.get_schedules()
        print(f"Schedules remaining after churn: {len(schedules)}")
```

### 5. Distributed Feedback Loops

**Cross-node scheduling patterns:**
```python
# tests/apscheduler_testbed/test_distributed_loops.py
class DistributedLoop:
    """Test feedback loops across multiple ScheduleZero nodes"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.counter = 0
    
    async def node_a_job(self):
        """Node A increments counter, triggers Node B"""
        self.counter += 1
        print(f"[Node A] Counter: {self.counter}")
        
        # Send message to Node B via ZMQ
        await self.send_to_node_b({"action": "increment", "value": self.counter})
    
    async def node_b_job(self):
        """Node B processes, triggers Node C"""
        print(f"[Node B] Processing value: {self.counter}")
        
        # Transform and send to Node C
        transformed = self.counter * 2
        await self.send_to_node_c({"action": "check", "value": transformed})
    
    async def node_c_job(self):
        """Node C validates, may trigger Node A (loop)"""
        print(f"[Node C] Validating...")
        
        if self.should_loop():
            # Complete the loop back to Node A
            await self.send_to_node_a({"action": "continue"})
        else:
            print("[Node C] Loop terminated")


async def test_distributed_rate_limiting():
    """Test coordinated rate limiting across nodes"""
    # Multiple nodes share a rate limit via ZMQ coordination
    # If Node A exhausts quota, Node B should back off
    pass


async def test_distributed_leader_election():
    """Test scheduling behavior during leader failover"""
    # Master node fails, replica promotes
    # Verify schedules continue without duplication
    pass
```

### 6. Orchestration Patterns

**Workflow-style scheduling (DAGs, dependencies):**
```python
# tests/apscheduler_testbed/test_orchestration.py
class WorkflowScheduler:
    """Schedule jobs with dependencies (DAG-style)"""
    
    def __init__(self, scheduler: AsyncScheduler):
        self.scheduler = scheduler
        self.completed = set()
    
    async def schedule_workflow(self, workflow: dict):
        """
        workflow = {
            "task_a": {"depends_on": [], "job": task_a_func},
            "task_b": {"depends_on": ["task_a"], "job": task_b_func},
            "task_c": {"depends_on": ["task_a"], "job": task_c_func},
            "task_d": {"depends_on": ["task_b", "task_c"], "job": task_d_func},
        }
        """
        
        # Start root tasks (no dependencies)
        for task_id, config in workflow.items():
            if not config["depends_on"]:
                await self.schedule_task(task_id, config["job"], workflow)
    
    async def schedule_task(self, task_id: str, job_func, workflow: dict):
        """Schedule a task and its downstream dependencies"""
        
        async def wrapped_job():
            # Execute the job
            result = await job_func()
            
            # Mark complete
            self.completed.add(task_id)
            print(f"Completed: {task_id}")
            
            # Schedule downstream tasks if dependencies met
            for downstream_id, config in workflow.items():
                if task_id in config["depends_on"]:
                    # Check if all dependencies complete
                    if all(dep in self.completed for dep in config["depends_on"]):
                        await self.schedule_task(
                            downstream_id,
                            config["job"],
                            workflow
                        )
        
        await self.scheduler.add_schedule(
            wrapped_job,
            IntervalTrigger(seconds=0),  # Run immediately
            id=task_id
        )


async def test_map_reduce_pattern():
    """Schedule map phase, wait for all, then reduce"""
    
    async def map_task(partition: int):
        # Process partition
        await asyncio.sleep(random.uniform(0.1, 0.5))
        return f"result_{partition}"
    
    async def reduce_task(results: list):
        # Aggregate results
        print(f"Reduce: {len(results)} results")
    
    # Schedule map phase (parallel)
    partitions = 10
    results = []
    
    for i in range(partitions):
        result = await map_task(i)
        results.append(result)
    
    # Schedule reduce phase (after all maps complete)
    await reduce_task(results)
```

## Test Execution Framework

```python
# tests/apscheduler_testbed/runner.py
class TestBedRunner:
    """Execute test suites with metrics collection"""
    
    def __init__(self):
        self.metrics = {
            "total_executions": 0,
            "failed_executions": 0,
            "avg_latency": 0,
            "max_latency": 0,
            "schedules_created": 0,
            "schedules_deleted": 0,
            "memory_peak_mb": 0,
        }
    
    async def run_test_suite(self, tests: list):
        """Run multiple tests with instrumentation"""
        for test in tests:
            print(f"\n{'='*60}")
            print(f"Running: {test.__name__}")
            print(f"{'='*60}\n")
            
            # Collect metrics
            start_mem = self.get_memory_usage()
            start_time = datetime.now()
            
            try:
                await test()
            except Exception as e:
                print(f"❌ Test failed: {e}")
                self.metrics["failed_executions"] += 1
            
            duration = (datetime.now() - start_time).total_seconds()
            end_mem = self.get_memory_usage()
            
            print(f"\n{'='*60}")
            print(f"Duration: {duration:.2f}s")
            print(f"Memory delta: {end_mem - start_mem:.2f}MB")
            print(f"{'='*60}\n")
    
    def report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST BED REPORT")
        print("="*60)
        for key, value in self.metrics.items():
            print(f"{key}: {value}")


# Run all tests
if __name__ == "__main__":
    runner = TestBedRunner()
    
    tests = [
        test_millisecond_intervals,
        test_self_modifying,
        test_fibonacci_backoff,
        test_schedule_creation_storm,
        test_schedule_churn,
        test_cascading_triggers,
        test_distributed_feedback_loops,
        test_map_reduce_pattern,
    ]
    
    asyncio.run(runner.run_test_suite(tests))
```

## Test Configuration

```yaml
# tests/apscheduler_testbed/config.yaml
testbed:
  mode: accelerated  # or realtime
  speedup: 1440  # 1 day = 1 minute
  
  tests:
    temporal_resolution:
      enabled: true
      min_interval_ms: 10
      duration_seconds: 60
    
    self_modifying:
      enabled: true
      max_reschedules: 100
    
    schedule_storms:
      enabled: true
      schedules_per_burst: 1000
      bursts: 10
    
    distributed_loops:
      enabled: true
      nodes: 3
      loop_depth: 5
  
  limits:
    max_schedules: 10000
    max_execution_time_seconds: 3600
    memory_limit_mb: 1024
  
  reporting:
    output_dir: test_output/apscheduler_testbed
    metrics_format: json
    generate_graphs: true
```

## Expected Insights

**What we'll learn about APScheduler:**

1. **Temporal limits**: What's the minimum reliable interval?
2. **Schedule churn**: How does it handle rapid create/delete cycles?
3. **Self-modification**: Does rescheduling from within a job cause issues?
4. **Memory behavior**: Does it leak under stress?
5. **Concurrency**: How many concurrent jobs before degradation?
6. **Edge cases**: What breaks under unusual patterns?

**Benefits for APScheduler project:**

- Identify bugs in edge cases
- Performance regression testing
- Real-world usage patterns (Discord bots, gaming)
- Validation of replication designs
- Documentation of limits and best practices

## Next Steps

1. Implement basic test framework
2. Run temporal resolution tests first (baseline)
3. Add instrumentation (metrics, profiling)
4. Document findings in separate report
5. Share results with APScheduler maintainer (respectfully)

## Notes

- Keep tests isolated (don't assume implementation details)
- Focus on observable behavior, not internals
- Document any unexpected results
- Provide reproducible test cases
- Offer to contribute fixes if bugs found
