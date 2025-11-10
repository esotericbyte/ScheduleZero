"""
Test handler that generates content and performs scheduled tasks.

This handler is used for testing the ScheduleZero system by:
1. Exposing methods that can be called remotely
2. Writing results to files that tests can verify
3. Tracking execution history

Uses ZeroMQ for clean, asyncio-compatible communication.
"""
import os
import json
import signal
from datetime import datetime
from pathlib import Path
import sys

# Add src to path so we can import schedule_zero modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.zmq_handler_base import ZMQHandlerBase
import logging

# --- Configuration ---
HANDLER_ID = os.environ.get("SCHEDULEZERO_TEST_HANDLER_ID", "test-handler-001")
HANDLER_HOST = os.environ.get("SCHEDULEZERO_HANDLER_HOST", "127.0.0.1")
HANDLER_PORT = int(os.environ.get("SCHEDULEZERO_HANDLER_PORT", 4244))
HANDLER_ADDRESS = f"tcp://{HANDLER_HOST}:{HANDLER_PORT}"

SERVER_HOST = os.environ.get("SCHEDULEZERO_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SCHEDULEZERO_SERVER_PORT", 4242))
SERVER_ADDRESS = f"tcp://{SERVER_HOST}:{SERVER_PORT}"

MAX_REGISTRATION_RETRIES = int(os.environ.get("SCHEDULEZERO_MAX_RETRIES", 5))

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(HANDLER_ID)


class TestHandler(ZMQHandlerBase):
    """Handler service for testing scheduled job execution."""
    
    def __init__(self, handler_id, handler_address, server_address, output_dir=None):
        """
        Initialize test handler with an output directory for results.
        
        Args:
            handler_id: Unique identifier for this handler
            handler_address: TCP address where handler listens
            server_address: TCP address of ScheduleZero server
            output_dir: Directory where test results will be written
        """
        super().__init__(
            handler_id=handler_id,
            handler_address=handler_address,
            server_address=server_address,
            max_registration_retries=MAX_REGISTRATION_RETRIES
        )
        
        # Set up output directory
        if output_dir is None:
            output_dir = Path(__file__).parent / "test_output"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Track execution history
        self.execution_log = self.output_dir / "execution_log.json"
        self._init_log()
    
    def _init_log(self):
        """Initialize or load execution log."""
        if not self.execution_log.exists():
            self._write_log([])
    
    def _write_log(self, entries):
        """Write execution log to disk."""
        with open(self.execution_log, 'w') as f:
            json.dump(entries, f, indent=2)
    
    def _append_log(self, entry):
        """Append an entry to the execution log."""
        entries = self._read_log()
        entries.append(entry)
        self._write_log(entries)
    
    def _read_log(self):
        """Read execution log from disk."""
        if not self.execution_log.exists():
            return []
        with open(self.execution_log, 'r') as f:
            return json.load(f)
    
    def write_file(self, params):
        """
        Write content to a file in the output directory.
        
        Args:
            params: dict with 'filename' and 'content'
            
        Returns:
            dict with status and file path
        """
        filename = params.get("filename", "default.txt")
        content = params.get("content", "")
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Log the execution
        self._append_log({
            "method": "write_file",
            "filename": filename,
            "content_length": len(content),
            "timestamp": datetime.now().isoformat(),
            "success": True
        })
        
        logger.info(f"Wrote {len(content)} bytes to {filename}")
        
        return {
            "status": "success",
            "file": str(file_path),
            "size": len(content)
        }
    
    def write_timestamp(self, params):
        """
        Write current execution timestamp to a file.
        This captures the ACTUAL execution time, not a parameter.
        
        Args:
            params: dict with 'filename'
            
        Returns:
            dict with status and timestamp
        """
        filename = params.get("filename", "timestamp.txt")
        
        # Capture the ACTUAL execution time right now
        execution_time = datetime.now()
        content = f"EXECUTION_TIME: {execution_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Log the execution
        self._append_log({
            "method": "write_timestamp",
            "filename": filename,
            "timestamp": execution_time.isoformat(),
            "success": True
        })
        
        logger.info(f"Wrote execution timestamp to {filename}: {execution_time}")
        
        return {
            "status": "success",
            "file": str(file_path),
            "timestamp": execution_time.isoformat()
        }
    
    def append_to_file(self, params):
        """
        Append content to a file (creates if doesn't exist).
        
        Args:
            params: dict with 'filename' and 'content'
            
        Returns:
            dict with status and line count
        """
        filename = params.get("filename", "default.txt")
        content = params.get("content", "")
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'a') as f:
            f.write(content + '\n')
        
        # Count lines
        with open(file_path, 'r') as f:
            line_count = len(f.readlines())
        
        # Log the execution
        self._append_log({
            "method": "append_to_file",
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "line_count": line_count,
            "success": True
        })
        
        logger.info(f"Appended to {filename}, now {line_count} lines")
        
        return {
            "status": "success",
            "file": str(file_path),
            "lines": line_count
        }
    
    def increment_counter(self, params):
        """
        Increment a named counter and return the new value.
        
        Args:
            params: dict with 'counter_name' (optional)
            
        Returns:
            dict with the new counter value
        """
        counter_name = params.get("counter_name", "default")
        counter_file = self.output_dir / f"counter_{counter_name}.txt"
        
        # Read current value
        if counter_file.exists():
            with open(counter_file, 'r') as f:
                current = int(f.read().strip())
        else:
            current = 0
        
        # Increment
        new_value = current + 1
        
        # Write new value
        with open(counter_file, 'w') as f:
            f.write(str(new_value))
        
        # Log the execution
        self._append_log({
            "method": "increment_counter",
            "counter_name": counter_name,
            "previous_value": current,
            "new_value": new_value,
            "timestamp": datetime.now().isoformat(),
            "success": True
        })
        
        logger.info(f"Counter '{counter_name}' incremented to {new_value}")
        
        return {
            "status": "success",
            "counter": counter_name,
            "value": new_value
        }
    
    def generate_report(self, params):
        """
        Generate a timestamped report file.
        
        Args:
            params: dict with 'report_name'
            
        Returns:
            dict with report details
        """
        import time
        report_name = params.get("report_name", "default")
        timestamp = datetime.now().isoformat()
        report_file = self.output_dir / f"report_{report_name}_{int(time.time())}.txt"
        
        report_content = f"""
=== {report_name} Report ===
Generated: {timestamp}
Handler: {self.handler_id}

Execution Log Summary:
Total executions: {len(self._read_log())}

Report completed successfully.
"""
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        # Log the execution
        self._append_log({
            "method": "generate_report",
            "report_name": report_name,
            "timestamp": timestamp,
            "report_file": str(report_file),
            "success": True
        })
        
        logger.info(f"Generated report: {report_file}")
        
        return {
            "status": "success",
            "report": report_name,
            "file": str(report_file),
            "timestamp": timestamp
        }
    
    def heartbeat(self, params=None):
        """
        Simple heartbeat method for testing connectivity.
        
        Returns:
            dict with timestamp and handler info
        """
        timestamp = datetime.now().isoformat()
        
        # Log the execution
        self._append_log({
            "method": "heartbeat",
            "timestamp": timestamp,
            "success": True
        })
        
        return {
            "status": "alive",
            "handler_id": self.handler_id,
            "timestamp": timestamp
        }
    
    def get_execution_count(self, params=None):
        """
        Get the total number of method executions.
        
        Returns:
            dict with execution statistics
        """
        log = self._read_log()
        
        # Count by method
        method_counts = {}
        for entry in log:
            method = entry.get("method", "unknown")
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            "total_executions": len(log),
            "by_method": method_counts,
            "handler_id": self.handler_id
        }
    
    def clear_output(self, params=None):
        """
        Clear all output files and reset execution log.
        
        Returns:
            dict with cleanup status
        """
        # Remove all files in output directory except execution log
        removed_count = 0
        for file in self.output_dir.iterdir():
            if file.is_file() and file != self.execution_log:
                file.unlink()
                removed_count += 1
        
        # Reset execution log
        self._write_log([])
        
        return {
            "status": "success",
            "files_removed": removed_count,
            "log_reset": True
        }


def main():
    """Run the test handler as a standalone process."""
    # Create handler instance
    handler = TestHandler(
        handler_id=HANDLER_ID,
        handler_address=HANDLER_ADDRESS,
        server_address=SERVER_ADDRESS
    )
    
    # Set up signal handlers
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}. Shutting down...")
        handler.stop()
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Run handler (blocks until stopped)
    logger.info(f"Starting test handler '{HANDLER_ID}'...")
    handler.run()
    
    logger.info(f"Test handler '{HANDLER_ID}' shut down.")


if __name__ == "__main__":
    main()
