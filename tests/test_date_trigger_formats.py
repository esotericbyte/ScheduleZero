"""
Test that date triggers accept both ISO strings and Unix timestamps.
"""
import pytest
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta


class TestDateTriggerFormats:
    """Test different date trigger input formats."""
    
    @pytest.fixture(autouse=True)
    def setup(self, server_process, handler_process, api_base_url, test_handler_id):
        """Setup test attributes."""
        self.api = api_base_url
        self.handler = test_handler_id
        self.output = Path(__file__).parent / "test_output"
        self.output.mkdir(exist_ok=True)
    
    def test_date_trigger_with_iso_string(self):
        """Test scheduling with ISO format datetime string."""
        # Schedule job for 3 seconds from now using ISO format
        exec_time = datetime.now() + timedelta(seconds=3)
        iso_string = exec_time.isoformat()
        
        job_data = {
            "handler_id": self.handler,
            "job_method": "write_file",
            "job_params": {
                "filename": "iso_format_test.txt",
                "content": "ISO format worked!"
            },
            "trigger": {
                "type": "date",
                "run_date": iso_string  # ISO string
            },
            "job_id": "iso_format_job"
        }
        
        response = requests.post(f"{self.api}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to schedule: {response.text}"
        
        # Wait for job to execute
        time.sleep(5)
        
        # Verify file was created
        output_file = self.output / "iso_format_test.txt"
        assert output_file.exists(), "Job did not execute"
        assert output_file.read_text() == "ISO format worked!"
    
    def test_date_trigger_with_unix_timestamp(self):
        """Test scheduling with Unix timestamp (float)."""
        # Schedule job for 3 seconds from now using Unix timestamp
        exec_time = datetime.now() + timedelta(seconds=3)
        unix_timestamp = exec_time.timestamp()  # float
        
        job_data = {
            "handler_id": self.handler,
            "job_method": "write_file",
            "job_params": {
                "filename": "timestamp_format_test.txt",
                "content": "Timestamp format worked!"
            },
            "trigger": {
                "type": "date",
                "run_date": unix_timestamp  # Unix timestamp (float)
            },
            "job_id": "timestamp_format_job"
        }
        
        response = requests.post(f"{self.api}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to schedule: {response.text}"
        
        # Wait for job to execute
        time.sleep(5)
        
        # Verify file was created
        output_file = self.output / "timestamp_format_test.txt"
        assert output_file.exists(), "Job did not execute"
        assert output_file.read_text() == "Timestamp format worked!"
    
    def test_date_trigger_with_integer_timestamp(self):
        """Test scheduling with Unix timestamp (int)."""
        # Schedule job for 3 seconds from now using Unix timestamp as int
        exec_time = datetime.now() + timedelta(seconds=3)
        unix_timestamp = int(exec_time.timestamp())  # int
        
        job_data = {
            "handler_id": self.handler,
            "job_method": "write_file",
            "job_params": {
                "filename": "int_timestamp_test.txt",
                "content": "Int timestamp format worked!"
            },
            "trigger": {
                "type": "date",
                "run_date": unix_timestamp  # Unix timestamp (int)
            },
            "job_id": "int_timestamp_job"
        }
        
        response = requests.post(f"{self.api}/api/schedule", json=job_data)
        assert response.status_code == 201, f"Failed to schedule: {response.text}"
        
        # Wait for job to execute
        time.sleep(5)
        
        # Verify file was created
        output_file = self.output / "int_timestamp_test.txt"
        assert output_file.exists(), "Job did not execute"
        assert output_file.read_text() == "Int timestamp format worked!"
