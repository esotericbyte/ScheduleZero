"""
Process-Based Governor Implementation

Manages server and handler as separate OS processes with PID tracking.
Suitable for production deployment with systemd.
"""
import subprocess
import sys
import time
import signal
import os
import atexit
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

from .logging_config import setup_logging, get_logger
from .deployment_config import get_deployment_config
from .governor_base import GovernorBase, HandlerConfig, ProcessInfo

logger = get_logger(__name__, component="ProcessGovernor")


class ProcessManager:
    """Manages a subprocess with logging, PID tracking, and health monitoring."""
    
    def __init__(self, name: str, command: list[str], log_file: Path, pid_dir: Path):
        self.name = name
        self.command = command
        self.log_file = log_file
        self.pid_file = pid_dir / f"{name}.pid"
        self.process = None
        self.log_handle = None
        self.start_time = None
        self.restart_count = 0
        self.last_error = None
        
        # Ensure PID directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
    def start(self):
        """Start the process (idempotent)."""
        if self.process and self.process.poll() is None:
            logger.info(f"{self.name} already running", method="start", pid=self.process.pid)
            return False
        
        # Clean up old process if exists
        if self.process:
            self.process = None
        
        # Open log file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = open(self.log_file, 'a', buffering=1)
        
        # Start process
        logger.info(f"Starting {self.name}", method="start", command=' '.join(self.command))
        
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=self.log_handle,
                stderr=subprocess.STDOUT,
                cwd=Path.cwd(),
                env=None,  # Inherit environment
                # On Windows, create new process group for better signal handling
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            self.start_time = datetime.now()
            
            # Write PID file
            self._write_pid_file()
            
            # Verify it started
            time.sleep(0.5)
            if self.process.poll() is None:
                logger.info(f"{self.name} started successfully", method="start", 
                           pid=self.process.pid, pid_file=str(self.pid_file))
                return True
            else:
                self.last_error = "Process exited immediately"
                logger.error(f"{self.name} failed to start (exited immediately)", method="start")
                self._cleanup_pid_file()
                return False
                
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to start {self.name}: {e}", method="start", exc_info=True)
            self._cleanup_pid_file()
            return False
    
    def stop(self, timeout=15):
        """Stop the process gracefully with proper signal handling."""
        if not self.process or self.process.poll() is not None:
            logger.info(f"{self.name} not running", method="stop")
            self._cleanup_pid_file()
            return
        
        pid = self.process.pid
        logger.info(f"Stopping {self.name}", method="stop", pid=pid)
        
        try:
            # Try graceful shutdown (SIGTERM)
            logger.info(f"Sending SIGTERM to {self.name}", method="stop", pid=pid)
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=timeout)
                logger.info(f"{self.name} stopped gracefully", method="stop", pid=pid)
            except subprocess.TimeoutExpired:
                # Force kill (SIGKILL)
                logger.warning(f"{self.name} did not stop gracefully, sending SIGKILL", 
                             method="stop", pid=pid)
                self.process.kill()
                
                try:
                    self.process.wait(timeout=5)
                    logger.info(f"{self.name} force killed", method="stop", pid=pid)
                except subprocess.TimeoutExpired:
                    logger.error(f"{self.name} could not be killed!", method="stop", pid=pid)
        
        except Exception as e:
            logger.error(f"Error stopping {self.name}: {e}", method="stop", exc_info=True)
        
        finally:
            if self.log_handle:
                self.log_handle.close()
                self.log_handle = None
            self._cleanup_pid_file()
    
    def _write_pid_file(self):
        """Write PID to file for external monitoring."""
        if self.process:
            self.pid_file.write_text(str(self.process.pid))
            logger.debug(f"Wrote PID file", method="_write_pid_file", 
                        pid_file=str(self.pid_file), pid=self.process.pid)
    
    def _cleanup_pid_file(self):
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
            logger.debug(f"Removed PID file", method="_cleanup_pid_file", 
                        pid_file=str(self.pid_file))
    
    def is_running(self) -> bool:
        """Check if process is currently running."""
        return self.process is not None and self.process.poll() is None
    
    def get_info(self) -> ProcessInfo:
        """Get current process information."""
        if self.is_running():
            status = "running"
        elif self.process and self.process.poll() is not None:
            status = "crashed"
        else:
            status = "stopped"
        
        return ProcessInfo(
            name=self.name,
            pid=self.process.pid if self.process else None,
            status=status,
            restart_count=self.restart_count,
            last_error=self.last_error
        )


class ProcessGovernor(GovernorBase):
    """
    Process-based governor implementation.
    
    Manages server and handlers as separate OS processes with PID tracking,
    signal handling, and automatic restart capabilities.
    """
    
    def __init__(self, deployment: str, config_path: Optional[Path] = None):
        """Initialize process governor."""
        super().__init__(deployment, config_path)
        
        # Get deployment configuration
        self.deployment_config = get_deployment_config(deployment)
        
        # Setup directories
        self.base_dir = Path("deployments") / deployment
        self.log_dir = self.base_dir / "logs"
        self.pid_dir = self.base_dir / "pids"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        setup_logging(
            level="INFO",
            log_file=str(self.log_dir / "governor.log"),
            format_style="detailed"
        )
        
        # Process managers
        self.server_manager: Optional[ProcessManager] = None
        self.handler_managers: Dict[str, ProcessManager] = {}
        
        # Signal handling
        self._setup_signal_handlers()
        atexit.register(self._cleanup)
    
    def _setup_signal_handlers(self):
        """Setup OS signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name
            self.logger.info(f"Received {sig_name}, shutting down gracefully", 
                           method="signal_handler")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGQUIT'):
            signal.signal(signal.SIGQUIT, signal_handler)
    
    def start(self) -> bool:
        """Start the governor and all managed services."""
        if self._running:
            self.logger.warning("Governor already running", method="start")
            return True
        
        self.logger.info("Starting governor", method="start", deployment=self.deployment)
        
        # Start server
        if not self._start_server():
            self.logger.error("Failed to start server", method="start")
            return False
        
        # Start handlers from configuration
        # TODO: Load handler configs from file
        
        self._running = True
        self.logger.info("Governor started successfully", method="start")
        return True
    
    def _start_server(self) -> bool:
        """Start the ScheduleZero server process."""
        command = [
            "poetry", "run", "python", "-m",
            "src.schedule_zero.server",
            "--deployment", self.deployment
        ]
        
        self.server_manager = ProcessManager(
            name="server",
            command=command,
            log_file=self.log_dir / "server.log",
            pid_dir=self.pid_dir
        )
        
        return self.server_manager.start()
    
    def stop(self, timeout: float = 30.0) -> bool:
        """Stop all managed services gracefully."""
        if not self._running:
            self.logger.info("Governor not running", method="stop")
            return True
        
        self.logger.info("Stopping governor", method="stop", deployment=self.deployment)
        
        # Stop handlers first
        for handler_id, manager in list(self.handler_managers.items()):
            self.logger.info(f"Stopping handler: {handler_id}", method="stop")
            manager.stop(timeout=timeout)
        
        # Stop server
        if self.server_manager:
            self.logger.info("Stopping server", method="stop")
            self.server_manager.stop(timeout=timeout)
        
        self._running = False
        self.logger.info("Governor stopped", method="stop")
        return True
    
    def restart(self, timeout: float = 30.0) -> bool:
        """Restart all managed services."""
        self.logger.info("Restarting governor", method="restart")
        self.stop(timeout)
        time.sleep(2)  # Brief pause between stop and start
        return self.start()
    
    def status(self) -> Dict[str, ProcessInfo]:
        """Get status of all managed services."""
        status = {}
        
        if self.server_manager:
            status['server'] = self.server_manager.get_info()
        
        for handler_id, manager in self.handler_managers.items():
            status[handler_id] = manager.get_info()
        
        return status
    
    def add_handler(self, config: HandlerConfig) -> bool:
        """Dynamically add a new handler."""
        if config.handler_id in self.handler_managers:
            self.logger.warning(f"Handler already exists: {config.handler_id}", method="add_handler")
            return False
        
        command = [
            "poetry", "run", "python", "-m",
            "src.schedule_zero.zmq_handler_base",
            "--handler-id", config.handler_id,
            "--module", config.module_path,
            "--class", config.class_name,
            "--port", str(config.port)
        ]
        
        manager = ProcessManager(
            name=config.handler_id,
            command=command,
            log_file=self.log_dir / f"{config.handler_id}.log",
            pid_dir=self.pid_dir
        )
        
        if manager.start():
            self.handler_managers[config.handler_id] = manager
            self.logger.info(f"Handler added: {config.handler_id}", method="add_handler")
            return True
        else:
            self.logger.error(f"Failed to add handler: {config.handler_id}", method="add_handler")
            return False
    
    def remove_handler(self, handler_id: str, timeout: float = 10.0) -> bool:
        """Remove a handler and stop it gracefully."""
        manager = self.handler_managers.get(handler_id)
        if not manager:
            self.logger.warning(f"Handler not found: {handler_id}", method="remove_handler")
            return False
        
        manager.stop(timeout=timeout)
        del self.handler_managers[handler_id]
        self.logger.info(f"Handler removed: {handler_id}", method="remove_handler")
        return True
    
    def restart_handler(self, handler_id: str) -> bool:
        """Restart a specific handler."""
        manager = self.handler_managers.get(handler_id)
        if not manager:
            self.logger.warning(f"Handler not found: {handler_id}", method="restart_handler")
            return False
        
        self.logger.info(f"Restarting handler: {handler_id}", method="restart_handler")
        manager.stop(timeout=10.0)
        time.sleep(1)
        manager.restart_count += 1
        return manager.start()
    
    def get_handler_status(self, handler_id: str) -> Optional[ProcessInfo]:
        """Get status of a specific handler."""
        manager = self.handler_managers.get(handler_id)
        return manager.get_info() if manager else None
    
    def list_handlers(self) -> List[str]:
        """Get list of all handler IDs."""
        return list(self.handler_managers.keys())
    
    def _cleanup(self):
        """Cleanup on exit (called by atexit)."""
        if self._running:
            self.logger.info("Cleanup called, stopping governor", method="_cleanup")
            self.stop()
