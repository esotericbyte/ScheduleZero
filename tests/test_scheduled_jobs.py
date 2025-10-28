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
    
    def test_scheduled_interval_job(self):
        """Test job scheduled with interval trigger."""
        # Schedule a job to run every 3 seconds for a short duration
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "append_to_file",
            "job_params": {
                "filename": "interval_test.txt",
                "content": "Interval execution"
            },
            "trigger": {
                "type": "interval",
                "seconds": 3
            },
            "job_id": "interval_test_job"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["status"] == "success"
        job_id = result.get("job_id")
        assert job_id is not None
        
        # Wait for the file to be created and written to multiple times
        time.sleep(10)  # Allow ~3 executions
        
        # Verify file exists and has multiple lines
        file_path = self.test_output_dir / "interval_test.txt"
        assert file_path.exists(), "Interval job did not create file"
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Should have at least 2 executions in 10 seconds (3 second interval)
        assert len(lines) >= 2, f"Expected at least 2 executions, got {len(lines)}"
        
        # Verify content
        for line in lines:
            assert "Interval execution" in line
    
    def test_scheduled_date_job(self):
        """Test job scheduled for a specific date/time."""
        # Schedule a job to run 5 seconds from now
        run_time = datetime.now() + timedelta(seconds=5)
        
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "write_file",
            "job_params": {
                "filename": "date_test.txt",
                "content": f"Executed at scheduled time: {run_time.isoformat()}"
            },
            "trigger": {
                "type": "date",
                "run_date": run_time.isoformat()
            },
            "job_id": "date_test_job"
        }
        
        response = requests.post(f"{self.api_base_url}/api/schedule", json=job_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["status"] == "success"
        
        # Wait for the job to execute
        file_path = self.wait_for_file("date_test.txt", timeout=15)
        
        # Verify file was created after schedule time
        assert file_path.exists()
        
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
    
    def test_list_schedules(self):
        """Test that scheduled jobs appear in the schedules list."""
        # Schedule a job
        job_data = {
            "handler_id": self.handler_id,
            "job_method": "heartbeat",
            "job_params": {},
            "trigger": {
                "type": "interval",
                "seconds": 60  # Long interval so it doesn't execute during test
            },
            "job_id": "list_schedules_test"
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
        
        # Find our scheduled job
        our_schedule = next((s for s in schedules if s.get("task_id") == "list_schedules_test"), None)
        assert our_schedule is not None, "Scheduled job not found in schedules list"
        
        # Verify schedule details
        assert our_schedule.get("id") == job_id
        assert "interval" in our_schedule.get("trigger", "").lower()


if __name__ == "__main__":
    # Run pytest with verbose output
    pytest.main([__file__, "-v", "-s"])


