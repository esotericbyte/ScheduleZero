"""
Simple integration tests for ScheduleZero.

Clean, straightforward tests with minimal complexity.
"""
import pytest
import requests
import time
from pathlib import Path


class TestBasics:
    """Basic integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self, server_process, handler_process, api_base_url, test_handler_id):
        """Setup test attributes."""
        self.api = api_base_url
        self.handler = test_handler_id
        self.output = Path(__file__).parent / "test_output"
        self.output.mkdir(exist_ok=True)
    
    def test_server_is_running(self):
        """Verify server responds to health check."""
        response = requests.get(f"{self.api}/")
        assert response.status_code == 200
    
    def test_handler_is_registered(self):
        """Verify test handler is registered."""
        response = requests.get(f"{self.api}/api/handlers")
        assert response.status_code == 200
        
        data = response.json()
        handler_ids = [h['id'] for h in data['handlers']]
        assert self.handler in handler_ids
    
    def test_run_job_immediately(self):
        """Run a job immediately and verify it executes."""
        job_data = {
            "handler_id": self.handler,
            "job_method": "write_file",
            "job_params": {
                "filename": "immediate_test.txt",
                "content": "Test content"
            }
        }
        
        response = requests.post(f"{self.api}/api/run_now", json=job_data)
        assert response.status_code == 200
        
        # Verify file was created
        output_file = self.output / "immediate_test.txt"
        assert output_file.exists()
        assert output_file.read_text() == "Test content"
    
    def test_schedule_job(self):
        """Schedule a job and verify it's created."""
        job_data = {
            "handler_id": self.handler,
            "job_method": "heartbeat",
            "job_params": {},
            "trigger": {
                "type": "interval",
                "minutes": 60
            },
            "job_id": "test_schedule_1"
        }
        
        response = requests.post(f"{self.api}/api/schedule", json=job_data)
        assert response.status_code == 201  # Created
        
        result = response.json()
        assert result["status"] == "success"
        assert result["job_id"] == "test_schedule_1"
    
    def test_list_schedules(self):
        """List all schedules."""
        response = requests.get(f"{self.api}/api/schedules")
        assert response.status_code == 200
        
        data = response.json()
        assert "schedules" in data
        assert isinstance(data["schedules"], list)
    
    def test_schedule_executes_on_interval(self):
        """Schedule a job with short interval and verify it executes."""
        # Schedule job to run every 5 seconds
        job_data = {
            "handler_id": self.handler,
            "job_method": "write_file",
            "job_params": {
                "filename": "interval_test.txt",
                "content": "Executed"
            },
            "trigger": {
                "type": "interval",
                "seconds": 5
            },
            "job_id": "test_interval_exec"
        }
        
        response = requests.post(f"{self.api}/api/schedule", json=job_data)
        assert response.status_code == 201  # Created
        
        # Wait for file to be created (first execution)
        output_file = self.output / "interval_test.txt"
        max_wait = 10  # Wait up to 10 seconds
        
        for _ in range(max_wait):
            if output_file.exists():
                break
            time.sleep(1)
        
        assert output_file.exists(), "Scheduled job did not execute within timeout"
        assert output_file.read_text() == "Executed"
