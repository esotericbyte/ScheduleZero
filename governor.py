"""
ScheduleZero Governor Process - Production-Ready Process Supervisor

Manages server and handler processes with proper PID tracking, signal handling,
and graceful shutdown. Suitable for systemd service deployment.

Features:
- PID file management for all supervised processes
- Proper OS signal handling (SIGTERM, SIGINT, SIGQUIT)
- Graceful shutdown with timeout and force-kill fallback
- Process health monitoring and automatic restart
- Idempotent operations (safe to run multiple times)
"""
import subprocess
import sys
import time
import signal
import argparse
import os
import atexit
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from src.schedule_zero.logging_config import setup_logging, get_logger
from src.schedule_zero.deployment_config import get_deployment_config

# Will be set when we know the deployment name
DEPLOYMENT = None
logger = None

def init_logging(deployment_name: str):
    """Initialize logging for the given deployment."""
    global DEPLOYMENT, logger
    DEPLOYMENT = get_deployment_config(deployment_name)
    
    # Setup governor logging
    log_dir = Path("deployments") / deployment_name / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(level="INFO", log_file=str(log_dir / "governor.log"), format_style="detailed")
    logger = get_logger(__name__, component="Governor", obj_id=deployment_name)


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
            time.sleep(0.5)  # Brief check
            if self.process.poll() is None:
                logger.info(f"{self.name} started successfully", method="start", 
                           pid=self.process.pid, pid_file=str(self.pid_file))
                return True
            else:
                logger.error(f"{self.name} failed to start (exited immediately)", method="start")
                self._cleanup_pid_file()
                return False
                
        except Exception as e:
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
            # Step 1: Try graceful shutdown (SIGTERM)
            logger.info(f"Sending SIGTERM to {self.name}", method="stop", pid=pid)
            self.process.terminate()
            
            # Step 2: Wait for graceful shutdown
            try:
                self.process.wait(timeout=timeout)
                logger.info(f"{self.name} stopped gracefully", method="stop", pid=pid)
            except subprocess.TimeoutExpired:
                # Step 3: Force kill (SIGKILL)
                logger.warning(f"{self.name} did not stop gracefully, sending SIGKILL", 
                             method="stop", pid=pid)
                self.process.kill()
                
                # Wait for force kill
                try:
                    self.process.wait(timeout=5)
                    logger.info(f"{self.name} force killed", method="stop", pid=pid)
                except subprocess.TimeoutExpired:
                    logger.error(f"{self.name} could not be killed!", method="stop", pid=pid)
        
        except Exception as e:
            logger.error(f"Error stopping {self.name}: {e}", method="stop", exc_info=True)
        
        finally:
            # Always cleanup
            if self.log_handle:
                self.log_handle.close()
                self.log_handle = None
            self._cleanup_pid_file()
    
    def _write_pid_file(self):
        """Write PID to file for external monitoring."""
        if self.process:
            try:
                with open(self.pid_file, 'w') as f:
                    f.write(str(self.process.pid))
                logger.debug(f"PID file written", method="_write_pid_file", 
                           pid_file=str(self.pid_file), pid=self.process.pid)
            except Exception as e:
                logger.warning(f"Failed to write PID file {self.pid_file}: {e}", 
                             method="_write_pid_file")
    
    def _cleanup_pid_file(self):
        """Remove PID file."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                logger.debug(f"PID file removed", method="_cleanup_pid_file", 
                           pid_file=str(self.pid_file))
            except Exception as e:
                logger.warning(f"Failed to remove PID file {self.pid_file}: {e}", 
                             method="_cleanup_pid_file")
    
    def get_pid_from_file(self) -> Optional[int]:
        """Get PID from file if it exists."""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, OSError) as e:
                logger.warning(f"Invalid PID file {self.pid_file}: {e}", 
                             method="get_pid_from_file")
                self._cleanup_pid_file()
        return None
    
    def is_running(self):
        """Check if process is running."""
        if self.process and self.process.poll() is None:
            return True
        
        # Also check PID file for orphaned processes
        pid = self.get_pid_from_file()
        if pid:
            try:
                # Check if process with this PID exists
                if os.name == 'nt':
                    # Windows: Try to open process handle
                    import ctypes
                    handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                        logger.warning(f"Found orphaned process {self.name} with PID {pid}", 
                                     method="is_running")
                        return True
                else:
                    # Unix: Send signal 0 (no-op but checks existence)
                    os.kill(pid, 0)
                    logger.warning(f"Found orphaned process {self.name} with PID {pid}", 
                                 method="is_running")
                    return True
            except (OSError, AttributeError):
                # Process doesn't exist, cleanup stale PID file
                self._cleanup_pid_file()
        
        return False
    
    def get_uptime(self):
        """Get process uptime in seconds."""
        if not self.start_time or not self.is_running():
            return 0
        return (datetime.now() - self.start_time).total_seconds()


class Governor:
    """Production-ready process supervisor for ScheduleZero components."""
    
    def __init__(self, deployment_name: str):
        self.deployment_name = deployment_name
        self.config = get_deployment_config(deployment_name)
        self.processes: Dict[str, ProcessManager] = {}
        self.running = False
        self.shutdown_requested = False
        
        # PID file management
        self.pid_dir = Path(f"deployments/{deployment_name}/pids")
        self.main_pid_file = self.pid_dir / "governor.pid"
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        
        # Write our own PID file
        self._write_main_pid()
        
        # Setup comprehensive signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        if hasattr(signal, 'SIGQUIT'):  # Unix only
            signal.signal(signal.SIGQUIT, self._handle_signal)
        
        # Cleanup on exit
        atexit.register(self._cleanup_on_exit)
    
    def _write_main_pid(self):
        """Write governor's PID to file."""
        try:
            with open(self.main_pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Governor PID written", method="_write_main_pid", 
                       pid=os.getpid(), pid_file=str(self.main_pid_file))
        except Exception as e:
            logger.warning(f"Failed to write governor PID file: {e}", method="_write_main_pid")
    
    def _cleanup_main_pid(self):
        """Remove governor's PID file."""
        if self.main_pid_file.exists():
            try:
                self.main_pid_file.unlink()
                logger.debug(f"Governor PID file removed", method="_cleanup_main_pid")
            except Exception as e:
                logger.warning(f"Failed to remove governor PID file: {e}", method="_cleanup_main_pid")
    
    def _cleanup_on_exit(self):
        """Cleanup function called on exit."""
        logger.info("Governor cleanup on exit", method="_cleanup_on_exit")
        self._cleanup_main_pid()
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals with proper daemon behavior."""
        if self.shutdown_requested:
            logger.warning(f"Signal {signum} received during shutdown, force exiting", 
                          method="_handle_signal")
            self._force_exit(2)  # Exit code 2 for forced shutdown
            return
        
        self.shutdown_requested = True
        signal_name = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM", 
            getattr(signal, 'SIGQUIT', -1): "SIGQUIT"
        }.get(signum, f"Signal {signum}")
        
        logger.info(f"Received {signal_name}, initiating graceful shutdown", 
                   method="_handle_signal", signal=signal_name, pid=os.getpid())
        
        try:
            # Graceful shutdown
            self.stop_all()
            self._cleanup_main_pid()
            logger.info("Graceful shutdown completed successfully", method="_handle_signal")
            sys.exit(0)  # Clean exit
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}", method="_handle_signal", exc_info=True)
            self._force_exit(1)  # Exit code 1 for errors
    
    def _force_exit(self, exit_code: int):
        """Force exit with cleanup."""
        logger.error(f"Force exiting with code {exit_code}", method="_force_exit")
        try:
            # Force stop all processes
            for process_mgr in self.processes.values():
                if process_mgr.process and process_mgr.process.poll() is None:
                    process_mgr.process.kill()
            self._cleanup_main_pid()
        except:
            pass  # Best effort cleanup
        os._exit(exit_code)
    
    def add_process(self, name: str, command: list[str], log_file: Path):
        """Add a process to be managed."""
        self.processes[name] = ProcessManager(name, command, log_file, self.pid_dir)
        logger.info(f"Added process '{name}' to governor", method="add_process")
    
    def start_all(self):
        """Start all managed processes (idempotent)."""
        logger.info(f"Starting all processes for {self.deployment_name}", method="start_all")
        self.running = True
        
        # Smart start: ensure server is up first, then handlers
        started_count = 0
        
        # 1. Start server first (if needed)
        if "server" in self.processes:
            if not self.processes["server"].is_running():
                logger.info("Starting server (required for handlers)", method="start_all")
                if self.processes["server"].start():
                    started_count += 1
                    time.sleep(3)  # Give server time to start
            else:
                logger.info("Server already running", method="start_all")
        
        # 2. Start handlers (if needed)
        for name, pm in self.processes.items():
            if name == "server":
                continue  # Already handled
                
            if not pm.is_running():
                logger.info(f"Starting {name}", method="start_all")
                if pm.start():
                    started_count += 1
                    time.sleep(1)  # Brief pause between handlers
            else:
                logger.info(f"{name} already running", method="start_all")
        
        logger.info(f"Start complete: {started_count} processes started", method="start_all")
    
    def stop_all(self):
        """Stop all managed processes (idempotent) with proper shutdown sequence."""
        logger.info("Stopping all processes", method="stop_all")
        self.running = False
        
        stopped_count = 0
        
        # Step 1: Stop handlers first, then server (reverse dependency order)
        for name in reversed(list(self.processes.keys())):
            pm = self.processes[name]
            if pm.is_running():
                logger.info(f"Stopping {name}", method="stop_all")
                pm.stop()
                stopped_count += 1
            else:
                logger.info(f"{name} already stopped", method="stop_all")
        
        # Step 2: Cleanup any orphaned processes
        self._cleanup_orphaned_processes()
        
        logger.info(f"Stop complete: {stopped_count} processes stopped", method="stop_all")
    
    def _cleanup_orphaned_processes(self):
        """Clean up any orphaned processes from previous runs."""
        logger.info("Checking for orphaned processes", method="_cleanup_orphaned_processes")
        
        if not self.pid_dir.exists():
            return
        
        cleaned_count = 0
        for pid_file in self.pid_dir.glob("*.pid"):
            if pid_file.name == "governor.pid":
                continue  # Skip our own PID file
                
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                process_name = pid_file.stem
                logger.debug(f"Checking process {process_name} with PID {pid}", 
                           method="_cleanup_orphaned_processes")
                
                # Check if process exists
                process_exists = False
                try:
                    if os.name == 'nt':
                        # Windows: Try to open process handle
                        import ctypes
                        handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                        if handle:
                            ctypes.windll.kernel32.CloseHandle(handle)
                            process_exists = True
                    else:
                        # Unix: Send signal 0
                        os.kill(pid, 0)
                        process_exists = True
                except (OSError, AttributeError):
                    process_exists = False
                
                if process_exists:
                    logger.warning(f"Found orphaned process {process_name} (PID {pid}), terminating", 
                                 method="_cleanup_orphaned_processes")
                    try:
                        # Try graceful termination first
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/PID', str(pid), '/T'], 
                                         capture_output=True, timeout=10)
                        else:
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(2)  # Give time for graceful shutdown
                            try:
                                os.kill(pid, 0)  # Check if still exists
                                os.kill(pid, signal.SIGKILL)  # Force kill if still running
                            except OSError:
                                pass  # Process already dead
                                
                        logger.info(f"Orphaned process {process_name} terminated", 
                                  method="_cleanup_orphaned_processes")
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Failed to terminate orphaned process {process_name}: {e}", 
                                   method="_cleanup_orphaned_processes")
                
                # Remove stale PID file
                pid_file.unlink()
                logger.debug(f"Removed stale PID file: {pid_file}", 
                           method="_cleanup_orphaned_processes")
                
            except (ValueError, OSError) as e:
                logger.warning(f"Invalid PID file {pid_file}: {e}", 
                             method="_cleanup_orphaned_processes")
                try:
                    pid_file.unlink()
                except:
                    pass
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} orphaned processes", 
                       method="_cleanup_orphaned_processes")
        else:
            logger.debug("No orphaned processes found", method="_cleanup_orphaned_processes")
    
    def monitor(self, check_interval=10):
        """Monitor processes and restart if they crash."""
        logger.info(f"Starting monitoring loop (interval={check_interval}s)", method="monitor")
        
        try:
            while self.running:
                time.sleep(check_interval)
                
                # Use intelligent health check
                self.ensure_running()
                
                # Show periodic status
                running_count = sum(1 for pm in self.processes.values() if pm.is_running())
                total_count = len(self.processes)
                logger.info(f"Health check: {running_count}/{total_count} processes running", 
                           method="monitor")
        
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", method="monitor", exc_info=True)
        
        finally:
            logger.info("Monitor loop ended", method="monitor")
    
    def start_process(self, name: str):
        """Start a specific process (idempotent)."""
        if name not in self.processes:
            logger.error(f"Process '{name}' not found", method="start_process")
            return False
        
        pm = self.processes[name]
        
        # For handlers, ensure server is running first
        if name != "server" and "server" in self.processes:
            server_pm = self.processes["server"]
            if not server_pm.is_running():
                logger.info(f"Starting server first (required for {name})", method="start_process")
                if not server_pm.start():
                    logger.error(f"Failed to start server, cannot start {name}", method="start_process")
                    return False
                time.sleep(2)  # Give server time to initialize
        
        return pm.start()
    
    def stop_process(self, name: str):
        """Stop a specific process."""
        if name not in self.processes:
            logger.error(f"Process '{name}' not found", method="stop_process")
            return False
        
        pm = self.processes[name]
        
        # If stopping server, warn about handlers
        if name == "server":
            running_handlers = [n for n, p in self.processes.items() 
                             if n != "server" and p.is_running()]
            if running_handlers:
                logger.warning(f"Stopping server while handlers are running: {running_handlers}",
                             method="stop_process")
        
        pm.stop()
        return True
    
    def restart_process(self, name: str):
        """Restart a specific process."""
        logger.info(f"Restarting {name}", method="restart_process")
        self.stop_process(name)
        time.sleep(1)
        return self.start_process(name)
    
    def ensure_running(self):
        """Ensure all processes are running (idempotent health check)."""
        logger.info("Ensuring all processes are running", method="ensure_running")
        
        issues_found = 0
        
        # Check server first
        if "server" in self.processes:
            server_pm = self.processes["server"]
            if not server_pm.is_running():
                logger.warning("Server not running, starting it", method="ensure_running")
                if server_pm.start():
                    issues_found += 1
                    time.sleep(3)  # Give time to start
                else:
                    logger.error("Failed to start server", method="ensure_running")
                    return False
        
        # Check handlers
        for name, pm in self.processes.items():
            if name == "server":
                continue
                
            if not pm.is_running():
                logger.warning(f"{name} not running, starting it", method="ensure_running")
                if pm.start():
                    issues_found += 1
                    time.sleep(1)
                else:
                    logger.error(f"Failed to start {name}", method="ensure_running")
        
        if issues_found > 0:
            logger.info(f"Fixed {issues_found} process issues", method="ensure_running")
        else:
            logger.info("All processes healthy", method="ensure_running")
            
        return True
    
    def status(self):
        """Print comprehensive status of all processes including PID management."""
        print(f"\n{'='*90}")
        print(f"Governor Status - {self.deployment_name} (Production Daemon Mode)")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Governor PID: {os.getpid()} | PID File: {self.main_pid_file}")
        print(f"{'='*90}\n")
        
        running_count = 0
        total_count = len(self.processes)
        
        for name, pm in self.processes.items():
            is_running = pm.is_running()
            if is_running:
                running_count += 1
                
            status = "🟢 RUNNING" if is_running else "🔴 STOPPED"
            uptime = int(pm.get_uptime()) if is_running else 0
            
            # Get PID from process or PID file
            pid = "N/A"
            pid_source = ""
            if pm.process and pm.process.poll() is None:
                pid = pm.process.pid
                pid_source = "(live)"
            else:
                file_pid = pm.get_pid_from_file()
                if file_pid:
                    pid = file_pid
                    pid_source = "(file)"
            
            print(f"  {name:20} [{status:12}] PID: {str(pid):8} {pid_source:6} Uptime: {uptime}s")
            print(f"  ├─ Log: {pm.log_file}")
            print(f"  └─ PID File: {pm.pid_file}")
            print()
        
        # Show PID directory summary
        pid_files = list(self.pid_dir.glob("*.pid"))
        print(f"PID Management:")
        print(f"  PID Directory: {self.pid_dir}")
        print(f"  Active PID Files: {len(pid_files)}")
        for pf in pid_files:
            try:
                with open(pf, 'r') as f:
                    file_pid = f.read().strip()
                print(f"    {pf.name}: {file_pid}")
            except:
                print(f"    {pf.name}: <invalid>")
        
        print(f"\nSummary: {running_count}/{total_count} processes running")
        
        if running_count < total_count:
            print(f"\n💡 To fix: poetry run python governor.py ensure")
        
        print()


def main():
    """Run the governor."""
    parser = argparse.ArgumentParser(description="ScheduleZero Governor Process")
    parser.add_argument("action", 
                       choices=["start", "stop", "status", "restart", "ensure", "start-server", "start-handlers"],
                       help="Action to perform")
    parser.add_argument("process", nargs="?", 
                       help="Specific process name (for start/stop/restart)")
    parser.add_argument("--deployment", default=None,
                       help="Deployment name (default: from env or 'default')")
    
    args = parser.parse_args()
    
    # Get deployment name
    deployment_name = args.deployment or os.environ.get('SCHEDULEZERO_DEPLOYMENT', 'default')
    
    # Initialize logging
    init_logging(deployment_name)
    
    # Create governor
    gov = Governor(deployment_name)
    
    # Define processes for this deployment
    log_base = Path("deployments") / deployment_name / "logs"
    
    # Server process
    gov.add_process(
        "server",
        ["poetry", "run", "python", "-m", "schedule_zero.tornado_app_server"],
        log_base / "server" / "server.log"
    )
    
    # Handler processes (add based on deployment)
    if deployment_name == "clock":
        import os
        os.environ["DING_DONG_DEPLOY"] = "true"
        gov.add_process(
            "handler-dingdong",
            ["poetry", "run", "python", "tests/ding_dong_handler.py"],
            log_base / "handlers" / "ding-dong-handler" / "process.log"
        )
    
    # Execute action
    if args.action == "start":
        if args.process:
            # Start specific process
            logger.info(f"Starting process {args.process}", method="main")
            print(f"🚀 Starting {args.process}...")
            if gov.start_process(args.process):
                print(f"✅ {args.process} started")
            else:
                print(f"❌ Failed to start {args.process}")
        else:
            # Start all processes
            logger.info("Governor starting all", method="main", action="start")
            print(f"🚀 Starting {deployment_name} deployment...")
            print(f"📁 Logs: deployments/{deployment_name}/logs/")
            print(f"🌐 Web UI: http://127.0.0.1:{DEPLOYMENT.tornado_port}")
            print(f"🔌 ZMQ Port: {DEPLOYMENT.zmq_port}")
            print()
            
            gov.start_all()
            print("✅ All processes started")
            print("📊 Monitoring processes (Ctrl+C to stop)...\n")
            
            # Monitor until interrupted
            try:
                gov.monitor()
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupt received, shutting down...")
                gov.stop_all()
                print("✅ Shutdown complete")
    
    elif args.action == "stop":
        if args.process:
            # Stop specific process
            logger.info(f"Stopping process {args.process}", method="main")
            print(f"⏹️  Stopping {args.process}...")
            gov.stop_process(args.process)
            print(f"✅ {args.process} stopped")
        else:
            # Stop all processes
            logger.info("Governor stopping all", method="main", action="stop")
            print(f"⏹️  Stopping {deployment_name} deployment...")
            gov.stop_all()
            print("✅ Stopped")
    
    elif args.action == "restart":
        if args.process:
            # Restart specific process
            logger.info(f"Restarting process {args.process}", method="main")
            print(f"🔄 Restarting {args.process}...")
            gov.restart_process(args.process)
            print(f"✅ {args.process} restarted")
        else:
            # Restart all processes
            logger.info("Governor restarting all", method="main", action="restart")
            print(f"🔄 Restarting {deployment_name} deployment...")
            gov.stop_all()
            time.sleep(2)
            gov.start_all()
            print("✅ Restarted")
    
    elif args.action == "status":
        gov.status()
    
    elif args.action == "ensure":
        # Idempotent health check and fix
        logger.info("Ensuring processes are healthy", method="main")
        print(f"🔍 Checking {deployment_name} deployment health...")
        if gov.ensure_running():
            print("✅ All processes healthy")
        else:
            print("❌ Some processes could not be started")
    
    elif args.action == "start-server":
        # Convenience command: just start server
        logger.info("Starting server only", method="main")
        print("🚀 Starting server...")
        if gov.start_process("server"):
            print("✅ Server started")
        else:
            print("❌ Failed to start server")
    
    elif args.action == "start-handlers":
        # Convenience command: start handlers (will start server if needed)
        logger.info("Starting handlers", method="main") 
        print("🚀 Starting handlers (will start server if needed)...")
        
        handlers_started = 0
        for name in gov.processes.keys():
            if name != "server":
                if gov.start_process(name):
                    handlers_started += 1
        
        print(f"✅ Started {handlers_started} handlers")


if __name__ == "__main__":
    main()
