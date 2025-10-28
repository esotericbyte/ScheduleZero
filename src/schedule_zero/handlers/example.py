"""Example handler implementation for ScheduleZero.

This handler demonstrates how to create a custom handler by inheriting from BaseHandler.
Users can copy and modify this file to create their own handlers.
"""

import logging
import random
import time
from datetime import datetime

from .base import BaseHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ExampleHandler(BaseHandler):
    """Example handler demonstrating job methods.
    
    This handler provides two example job methods that can be scheduled:
    - do_work: Simulates processing with random failure chance
    - another_task: Simple quick task
    """
    
    def do_work(self, params: dict):
        """Example job method that receives parameters as a dictionary.
        
        Args:
            params: Dictionary with 'data' and 'number' keys
            
        Returns:
            Dictionary with status, result, and timestamp
            
        Raises:
            ValueError: Randomly (10% chance) to simulate errors
        """
        data = params.get("data", "No data")
        number = params.get("number", 0)
        self._logger.info(
            f"Received job 'do_work': data='{data}', number={number}. Simulating work..."
        )
        
        # Simulate work that might fail sometimes
        if random.random() < 0.1:  # 10% chance of failure
            self._logger.error("'do_work' encountered a simulated error!")
            raise ValueError("Simulated processing error in do_work")
        
        time.sleep(random.uniform(1, 3))  # Simulate work duration
        self._logger.info("'do_work' finished successfully.")
        
        return {
            "status": "completed",
            "result": f"Processed '{data}' with number {number}",
            "timestamp": datetime.utcnow().isoformat()
        }

    def another_task(self, params: dict):
        """Another example task.
        
        Args:
            params: Dictionary with 'task_id' key
            
        Returns:
            Dictionary with status and task_id
        """
        task_id = params.get("task_id", "unknown")
        self._logger.info(f"Received job 'another_task': task_id='{task_id}'. Simulating short work...")
        time.sleep(0.5)
        self._logger.info("'another_task' finished.")
        return {"status": "ok", "task_id": task_id}


def main():
    """Entry point for running the example handler."""
    handler = ExampleHandler()
    handler.run()


if __name__ == "__main__":
    main()
