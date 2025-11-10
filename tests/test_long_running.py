"""
Long-running tests to verify server stability over time.

Simple, straightforward tests as prescribed.
"""
import pytest
import requests
import time
from pathlib import Path
from datetime import datetime
import threading


class TestLongRunning:
    """Tests that run for extended periods."""
    
    @pytest.fixture(autouse=True)
    def setup(self, server_process, handler_process, api_base_url, test_handler_id):
        """Setup test attributes."""
        self.api = api_base_url
        self.handler = test_handler_id
        self.output = Path(__file__).parent / "test_output"
        self.output.mkdir(exist_ok=True)
        self.errors = []  # Track errors from threads
    
    def _print_worker(self):
        """Worker thread: print every 90 seconds for 5 minutes."""
        try:
            print("\n" + "="*60)
            print("TEST: Print every 90 seconds")
            print("="*60)
            
            # Run for 5 minutes (3-4 prints at 90-second intervals)
            end_time = time.time() + 300  # 5 minutes
            print_count = 0
            
            while time.time() < end_time:
                now = datetime.now()
                print_count += 1
                print(f"[Print #{print_count}] {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Check server is still alive
                response = requests.get(f"{self.api}/")
                if response.status_code != 200:
                    error = f"Server died at {now}"
                    print(f"ERROR: {error}")
                    self.errors.append(error)
                    return
                
                time.sleep(90)
            
            print("="*60)
            print("Print test completed successfully")
            print("="*60)
        except Exception as e:
            self.errors.append(f"Print worker error: {e}")
            print(f"ERROR in print worker: {e}")
    
    def _schedule_worker(self):
        """Worker thread: schedule 5-minute job and verify timing."""
        try:
            # Save start time
            start_time = datetime.now()
            print("\n" + "="*60)
            print(f"SCHEDULE TEST START TIME: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            
            # Calculate execution time (5 minutes from now) in ISO format
            from datetime import timedelta
            exec_datetime = start_time + timedelta(minutes=5)
            exec_datetime_iso = exec_datetime.isoformat()
            
            # Schedule job to write the ACTUAL execution timestamp (not passed as param)
            job_data = {
                "handler_id": self.handler,
                "job_method": "write_timestamp",
                "job_params": {
                    "filename": "five_minute_execution.txt"
                },
                "trigger": {
                    "type": "date",
                    "run_date": exec_datetime_iso  # ISO format string, not timestamp
                },
                "job_id": "five_minute_job"
            }
            
            print(f"Scheduling job for: {exec_datetime_iso}")
            response = requests.post(f"{self.api}/api/schedule", json=job_data)
            if response.status_code != 201:
                error = f"Failed to schedule job: {response.status_code} - {response.text}"
                print(f"ERROR: {error}")
                self.errors.append(error)
                return
            print(f"Job scheduled successfully")
            
            # Wait 5 minutes (+ 10 seconds buffer)
            print("Waiting 5 minutes...")
            time.sleep(310)
            
            # Check the execution time
            output_file = self.output / "five_minute_execution.txt"
            if not output_file.exists():
                error = "Job did not execute - file not found"
                print(f"ERROR: {error}")
                self.errors.append(error)
                return
            
            content = output_file.read_text()
            print(f"\nFile content: {content}")
            
            # Parse execution time from file
            exec_time_str = content.split("EXECUTION_TIME: ")[1]
            exec_time = datetime.strptime(exec_time_str, '%Y-%m-%d %H:%M:%S')
            
            # Calculate difference
            time_diff = (exec_time - start_time).total_seconds()
            
            print("="*60)
            print(f"START TIME:     {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"EXECUTION TIME: {exec_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"DIFFERENCE:     {time_diff:.2f} seconds")
            print(f"EXPECTED:       ~300 seconds (5 minutes)")
            print("="*60)
            
            # Verify difference is about 5 minutes (allow 10 second tolerance)
            if not (290 <= time_diff <= 310):
                error = f"Time difference {time_diff}s not close to 300s"
                print(f"ERROR: {error}")
                self.errors.append(error)
            else:
                print("\n✓ Time difference is within reason!")
        except Exception as e:
            self.errors.append(f"Schedule worker error: {e}")
            print(f"ERROR in schedule worker: {e}")
    
    def test_concurrent_long_running(self):
        """Run both tests concurrently to save time."""
        print("\n" + "="*80)
        print("STARTING CONCURRENT LONG-RUNNING TESTS")
        print("Both tests will run in parallel (5 minute duration)")
        print("="*80)
        
        # Start both workers
        print_thread = threading.Thread(target=self._print_worker, name="PrintWorker")
        schedule_thread = threading.Thread(target=self._schedule_worker, name="ScheduleWorker")
        
        print_thread.start()
        schedule_thread.start()
        
        # Wait for both to complete
        print("\nWaiting for both threads to complete...")
        print_thread.join()
        schedule_thread.join()
        
        print("\n" + "="*80)
        print("BOTH TESTS COMPLETED")
        print("="*80)
        
        # Check for errors
        if self.errors:
            error_msg = "\n".join(self.errors)
            pytest.fail(f"Test failures:\n{error_msg}")
        else:
            print("\n✓ ALL CHECKS PASSED!")


