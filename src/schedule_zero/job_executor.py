"""Job execution and remote handler invocation for ScheduleZero."""

import asyncio
import random
from .logging_config import get_logger

logger = get_logger(__name__, component="JobExecutor")


class JobExecutor:
    """Executes jobs on remote handlers with retry logic and error handling."""
    
    def __init__(self, registry_manager, max_retries=3, base_delay=1.0):
        """
        Initialize the job executor.
        
        Args:
            registry_manager: RegistryManager instance for accessing handlers
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        self.registry_manager = registry_manager
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = 2.0
        self.jitter_factor = 0.5
    
    async def __call__(self, handler_id: str, method_name: str, job_params: dict):
        """
        Execute a job on a remote handler with retry logic.
        
        This method is called by APScheduler when a job is triggered.
        
        Args:
            handler_id: The unique identifier of the handler
            method_name: The name of the method to call on the handler
            job_params: Dictionary of parameters to pass to the method
            
        Returns:
            Result from the remote method call
            
        Raises:
            Exception: If all retry attempts fail
        """
        logger.info(
            f"Job triggered: {handler_id}.{method_name}",
            method="__call__",
            handler=handler_id,
            method_name=method_name
        )
        logger.debug(f"Job params: {job_params}", method="__call__")
        
        retries = 0
        current_delay = self.base_delay
        loop = asyncio.get_running_loop()
        
        while retries < self.max_retries:
            try:
                logger.debug(f"Getting client for handler '{handler_id}'", method="__call__", attempt=retries+1)
                client = self.registry_manager.get_client(handler_id)
                if not client:
                    raise ConnectionError(f"Handler '{handler_id}' not available or connection failed")
                
                logger.debug(f"Calling {method_name} on handler", method="__call__", handler=handler_id)
                # Execute RPC call in thread pool (ZMQ is synchronous)
                result = await loop.run_in_executor(
                    None,
                    lambda: client.call(method_name, job_params)
                )
                
                logger.debug(f"Received result: {result}", method="__call__")
                
                # Check if response indicates success
                if isinstance(result, dict) and result.get("success") is False:
                    error_msg = result.get("error", "Unknown error")
                    raise Exception(f"Handler returned error: {error_msg}")
                
                logger.info(
                    f"Job completed successfully",
                    method="__call__",
                    handler=handler_id,
                    method_name=method_name,
                    result_type=type(result).__name__
                )
                return result
                
            except (TimeoutError, ConnectionError, Exception) as e:
                retries += 1
                logger.warning(
                    f"Job execution failed (attempt {retries}/{self.max_retries}): {e}",
                    method="__call__",
                    handler=handler_id,
                    method_name=method_name,
                    error=str(e)
                )
                
                if retries < self.max_retries:
                    # Calculate backoff with jitter
                    jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * current_delay
                    sleep_time = max(0.1, current_delay + jitter)
                    logger.info(f"Retrying in {sleep_time:.2f}s", method="__call__", attempt=retries+1)
                    await asyncio.sleep(sleep_time)
                    current_delay *= self.backoff_factor
                else:
                    logger.error(
                        f"Job failed after {self.max_retries} attempts",
                        method="__call__",
                        handler=handler_id,
                        method_name=method_name,
                        exc_info=True
                    )
                    raise
