"""
Integration tests for ScheduleZero scheduled jobs.

These tests verify that:
1. Jobs can be scheduled with various trigger types
2. Jobs execute as scheduled and produce expected output
3. Handler methods are called correctly with parameters
4. Execution can be verified through generated files and logs

Uses pytest fixtures from conftest.py for server/handler lifecycle management.
"""
import time
import json
import pytest
import requests
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta


class TestScheduledJobs:
    """Test suite for scheduled job execution."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, server_process, handler_process, api_base_url, test_handler_id, test_output_dir):
        """Set up and tear down for each test."""
        # Make fixtures available as instance attributes
        self.api_base_url = api_base_url
        self.handler_id = test_handler_id
        self.test_output_dir = test_output_dir
        self.db_path = Path("schedulezero_jobs.db")
        
        # Setup: Clear test output directory
        if self.test_output_dir.exists():
            for file in self.test_output_dir.iterdir():
                if file.is_file():
                    file.unlink()
        else:
            self.test_output_dir.mkdir(parents=True, exist_ok=True)
        
        yield
        
        # Teardown: Optionally clean up (commented out to preserve test artifacts)
        # if self.test_output_dir.exists():
        #     for file in self.test_output_dir.iterdir():
        #         if file.is_file():
        #             file.unlink()
    
    def query_db(self, query):
        """Execute a query on the APScheduler database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_tasks_from_db(self):
        """Get all tasks from the database."""
        return self.query_db("SELECT * FROM tasks")
    
    def get_schedules_from_db(self):
        """Get all schedules from the database."""
        return self.query_db("SELECT id, task_id, paused, next_fire_time FROM schedules")
    
    def get_jobs_from_db(self):
        """Get all jobs from the database."""
        return self.query_db("SELECT id, task_id, schedule_id, created_at FROM jobs")
    
    def wait_for_file(self, filename, timeout=30, check_interval=1):
        """
        Wait for a file to be created in the test output directory.
        
        Args:
            filename: Name of the file to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check in seconds
            
        Returns:
            Path to the file if found
            
        Raises:
            TimeoutError if file is not created within timeout
        """
        file_path = self.test_output_dir / filename
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if file_path.exists():
                return file_path
            time.sleep(check_interval)
        
        raise TimeoutError(f"File {filename} was not created within {timeout} seconds")
    
    def read_execution_log(self):
        """Read the test handler execution log."""
        log_file = self.test_output_dir / "execution_log.json"
        if not log_file.exists():
            return []
        
        with open(log_file, 'r') as f:
            return json.load(f)
    
    def test_server_health(self):
        """Test that the server is running and responding."""
        response = requests.get(f"{self.api_base_url}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ScheduleZero"
    
    def test_handler_registered(self):
        """Test that the test handler is registered with the server."""
        response = requests.get(f"{self.api_base_url}/api/handlers")
        assert response.status_code == 200
        
        data = response.json()
        handlers = data.get("handlers", [])
        
        # Find our test handler
        test_handler = next((h for h in handlers if h["id"] == self.handler_id), None)
        assert test_handler is not None, f"Test handler {self.handler_id} not found in registered handlers"
        
        # Verify methods are registered
        expected_methods = ["write_file", "append_to_file", "increment_counter", 
                          "generate_report", "heartbeat", "ping", "get_execution_count", "clear_output"]
        actual_methods = test_handler.get("methods", [])
        
        for method in expected_methods:
            assert method in actual_methods, f"Method {method} not found in registered methods"
    
    def test_database_task_registration(self):
        """DIAGNOSTIC: Verify that job_executor task is registered in APScheduler database."""
        tasks = self.get_tasks_from_db()
        print(f"\nTasks in database: {tasks}")
        
        assert len(tasks) > 0, "No tasks found in database - job_executor was not registered!"
        
        # Look for our job_executor task
        task_ids = [t['id'] for t in tasks]
        assert 'job_executor' in task_ids, f"job_executor not found in tasks. Found: {task_ids}"
        
        # Get the job_executor task details
        job_executor_task = next(t for t in tasks if t['id'] == 'job_executor')
        print(f"job_executor task: {job_executor_task}")
        assert job_executor_task['job_executor'] is not None
    
    def test_schedule_creates_database_entry(self):
        """DIAGNOSTIC: Verify that creating a schedule writes to the database."""
        # Get initial schedule count
        initial_schedules = self.get_schedules_from_db()
        initial_count = len(initial_schedules)
        print(f"\nInitial schedules in DB: {initial_count}")
        
        # Create a schedule
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "heartbeat",
            "job_params": {},
            "trigger": {
                "type": "interval",
                "minutes": 60
            },
            "job_id": f"diagnostic_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to create schedule: {response.text}"
        
        result = response.json()
        job_id = result.get("job_id")
        print(f"Created schedule with job_id: {job_id}")
        
        # Give it a moment to persist
        time.sleep(0.5)
        
        # Check database
        schedules = self.get_schedules_from_db()
        print(f"Schedules after creation: {schedules}")
        
        assert len(schedules) > initial_count, f"Schedule count did not increase! Was {initial_count}, still {len(schedules)}"
        
        # Find our schedule
        our_schedule = next((s for s in schedules if s['id'] == job_id), None)
        assert our_schedule is not None, f"Schedule {job_id} not found in database. Found: {[s['id'] for s in schedules]}"
        
        # Verify it references the job_executor task
        assert our_schedule['task_id'] == 'job_executor', f"Schedule task_id is '{our_schedule['task_id']}', expected 'job_executor'"
        assert our_schedule['next_fire_time'] is not None, "Schedule has no next_fire_time!"
        print(f"✓ Schedule verified in database with task_id='job_executor' and next_fire_time={our_schedule['next_fire_time']}")
    
    def test_schedule_api_vs_database(self):
        """DIAGNOSTIC: Compare /api/schedules endpoint with database contents."""
        # Create a schedule
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "heartbeat",
            "job_params": {},
            "trigger": {
                "type": "interval",
                "minutes": 30
            },
            "job_id": f"api_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        job_id = response.json().get("job_id")
        
        time.sleep(0.5)
        
        # Check database directly
        db_schedules = self.get_schedules_from_db()
        print(f"\nSchedules in database: {db_schedules}")
        
        # Check API endpoint
        response = requests.get(f"{self.api_base_url}/api/schedules")
        assert response.status_code == 200
        api_schedules = response.json().get("schedules", [])
        print(f"Schedules from API: {api_schedules}")
        
        # Compare
        assert len(db_schedules) > 0, "Database has no schedules!"
        
        if len(api_schedules) == 0:
            pytest.fail(f"API returned 0 schedules but database has {len(db_schedules)}! This is the bug.")
        
        assert len(api_schedules) == len(db_schedules), f"Mismatch: API has {len(api_schedules)}, DB has {len(db_schedules)}"
    
    def test_run_now_write_file(self):
        """Test immediate execution of write_file job."""
        # Schedule a job to run immediately
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": "test_immediate.txt",
                "content": "Hello from immediate execution!"
            }
        }

        response = requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["status"] == "success"
        
        # Wait for file to be created
        file_path = self.wait_for_file("test_immediate.txt", timeout=10)
        
        # Verify content
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert content == "Hello from immediate execution!"
    
    def test_run_now_increment_counter(self):
        """Test counter increment via immediate execution."""
        # Increment counter multiple times
        for i in range(5):
            job_data = {
                "handler_id": self.handler_id,
                "job_method": "increment_counter",
                "job_params": {
                    "counter_name": "test_counter"
                }
            }
            
            response = requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
            assert response.status_code == 200
        
        # Wait a moment for all jobs to complete
        time.sleep(3)
        
        # Verify counter file
        counter_file = self.test_output_dir / "counter_test_counter.txt"
        assert counter_file.exists(), "Counter file was not created"
        
        with open(counter_file, 'r') as f:
            value = int(f.read().strip())
        
        assert value == 5, f"Expected counter value 5, got {value}"
    
    def test_schedule_interval_api(self):
        """Test that interval jobs can be scheduled via API."""
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": f"interval_api_{int(time.time())}.txt",
                "content": "Interval test"
            },
            "trigger": {
                "type": "interval",
                "seconds": 30
            },
            "job_id": "interval_api_test"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to schedule interval job: {response.text}"
        
        result = response.json()
        assert result["status"] == "success"
        assert result.get("job_id") is not None
    
    def test_scheduled_interval_executes(self):
        """Test that scheduled interval jobs actually execute."""
        # Use append_to_file so we can see multiple executions in one file
        filename = f"interval_exec_{int(time.time())}.txt"
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "append_to_file",
            "job_params": {
                "filename": filename,
                "content": "Execution"
            },
            "trigger": {
                "type": "interval",
                "seconds": 30  # Execute every 30 seconds
            },
            "job_id": f"interval_exec_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        # Wait up to 75 seconds for at least 2 executions (at 0s, 30s, 60s)
        print(f"Waiting up to 75 seconds for interval executions...")
        start_time = time.time()
        file_path = self.test_output_dir / filename
        
        while time.time() - start_time < 75:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                if len(lines) >= 2:
                    print(f"Found {len(lines)} executions after {int(time.time() - start_time)} seconds")
                    assert len(lines) >= 2, f"Expected at least 2 executions, got {len(lines)}"
                    return
            time.sleep(5)
        
        # If we get here, check what we have
        if file_path.exists():
            with open(file_path, 'r') as f:
                lines = f.readlines()
            pytest.fail(f"Only got {len(lines)} execution(s) in 75 seconds, expected at least 2")
        else:
            pytest.fail("No executions found - file was never created")
    
    def test_schedule_date_api(self):
        """Test that date-based jobs can be scheduled via API."""
        run_time = datetime.now() + timedelta(seconds=30)
        
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": f"date_api_{int(time.time())}.txt",
                "content": "Date test"
            },
            "trigger": {
                "type": "date",
                "run_date": run_time.isoformat()
            },
            "job_id": "date_api_test"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to schedule date job: {response.text}"
        
        result = response.json()
        assert result["status"] == "success"
        assert result.get("job_id") is not None
    
    def test_scheduled_date_executes(self):
        """Test that date-scheduled jobs execute at the right time."""
        # Schedule a job to run 60 seconds from now
        run_time = datetime.now() + timedelta(seconds=60)
        filename = f"date_exec_{int(time.time())}.txt"
        
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": filename,
                "content": f"Executed at scheduled time: {run_time.isoformat()}"
            },
            "trigger": {
                "type": "date",
                "run_date": run_time.isoformat()
            },
            "job_id": f"date_exec_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["status"] == "success"
        
        # Record when we scheduled it
        schedule_time = time.time()
        
        # Wait for the job to execute (60 seconds + 20 second buffer)
        print(f"Waiting up to 80 seconds for date-scheduled job...")
        file_path = self.wait_for_file(filename, timeout=80)
        
        # Verify file was created
        assert file_path.exists(), "Date-scheduled job did not create file"
        
        # Verify file was created at approximately the right time (within 15 seconds)
        file_ctime = file_path.stat().st_ctime
        actual_delay = file_ctime - schedule_time
        assert 45 <= actual_delay <= 75, f"File created after {actual_delay}s, expected ~60s"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert "Executed at scheduled time" in content
    
    def test_generate_report(self):
        """Test report generation job."""
        # First, run some other jobs to populate execution log
        for i in range(3):
            job_data = {
                "handler_id": self.handler_id,
                "job_method": "heartbeat",
                "job_params": {}
            }
            requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
        
        time.sleep(2)
        
        # Now generate a report
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "generate_report",
            "job_params": {
                "report_name": "test_report"
            }
        }
        
        response = requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
        assert response.status_code == 200
        
        # Wait for report file to be created
        time.sleep(3)
        
        # Find report file (has timestamp in name)
        report_files = list(self.test_output_dir.glob("report_test_report_*.txt"))
        assert len(report_files) > 0, "Report file was not created"
        
        # Verify report content
        with open(report_files[0], 'r') as f:
            content = f.read()
        
        assert "test_report Report" in content
        assert self.handler_id in content
        assert "Total executions:" in content
    
    def test_execution_log_tracking(self):
        """Test that execution log properly tracks all method calls."""
        # Clear any existing log
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "clear_output",
            "job_params": {}
        }
        requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
        time.sleep(1)
        
        # Execute various methods
        methods_to_test = [
            ("write_file", {"filename": "log_test.txt", "content": "test"}),
            ("increment_counter", {"counter_name": "log_counter"}),
            ("heartbeat", {}),
        ]
        
        for method, params in methods_to_test:
            job_data = {
                "handler_id": self.handler_id,
                "job_method": method,
                "job_params": params
            }
            response = requests.post(f"{self.api_base_url}/api/run_now", json=job_data)
            assert response.status_code == 200
        
        # Wait for all jobs to complete
        time.sleep(3)
        
        # Verify execution log
        log = self.read_execution_log()
        assert len(log) >= len(methods_to_test), "Not all executions were logged"
        
        # Verify each method appears in log
        logged_methods = [entry.get("method") for entry in log]
        for method, _ in methods_to_test:
            assert method in logged_methods, f"Method {method} not found in execution log"
    
    def test_list_schedules_api(self):
        """Test that scheduled jobs appear in the schedules list API."""
        # Schedule a job with a reasonable interval
        filename = f"list_test_{int(time.time())}.txt"
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "heartbeat",
            "job_params": {},
            "trigger": {
                "type": "interval",
                "minutes": 60  # Long interval, won't execute during test
            },
            "job_id": f"list_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        result = response.json()
        job_id = result.get("job_id")
        
        # List schedules
        response = requests.get(f"{self.api_base_url}/api/schedules")
        assert response.status_code == 200
        
        data = response.json()
        schedules = data.get("schedules", [])
        assert len(schedules) > 0, "No schedules found in list"
        
        # Find our scheduled job - check by ID since field names might vary
        our_schedule = next((s for s in schedules if s.get("id") == job_id), None)
        assert our_schedule is not None, f"Scheduled job {job_id} not found in schedules list"
        
        # Verify schedule has trigger info
        assert "trigger" in our_schedule or "next_fire_time" in our_schedule
    
    def test_list_schedules_execution(self):
        """Test that schedules listed actually execute."""
        # Schedule a job with short interval that will execute during test
        filename = f"list_exec_{int(time.time())}.txt"
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": filename,
                "content": "List execution test"
            },
            "trigger": {
                "type": "interval",
                "seconds": 30
            },
            "job_id": f"list_exec_test_{int(time.time())}"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        result = response.json()
        job_id = result.get("job_id")
        
        # Verify it's in the list
        response = requests.get(f"{self.api_base_url}/api/schedules")
        assert response.status_code == 200
        schedules = response.json().get("schedules", [])
        our_schedule = next((s for s in schedules if s.get("id") == job_id), None)
        assert our_schedule is not None, "Job not found in schedules list"
        
        # Wait for first execution to verify schedule is actually running
        print(f"Waiting up to 45 seconds for first execution...")
        try:
            file_path = self.wait_for_file(filename, timeout=45)
            assert file_path.exists(), "Scheduled job from list test did not execute"
        except TimeoutError:
            pytest.fail("Scheduled job appeared in list but never executed")


if __name__ == "__main__":
    # Run pytest with verbose output
    pytest.main([__file__, "-v", "-s"])


