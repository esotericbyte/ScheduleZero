#!/usr/bin/env python3
"""
ScheduleZero Server Management

Cross-platform server start/stop with PID file management.
"""
import os
import sys
import signal
import subprocess
import time
from pathlib import Path
import argparse


def get_pid_file(deployment: str) -> Path:
    """Get path to PID file for deployment."""
    root = Path(__file__).parent.parent
    pid_dir = root / "deployments" / deployment / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir / "server.pid"


def is_process_running(pid: int) -> bool:
    """Check if process with PID is running (cross-platform)."""
    try:
        # Send signal 0 to check if process exists
        # Works on Unix and Windows (Python 3.2+)
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except PermissionError:
        # Process exists but we don't have permission (still running)
        return True


def read_pid(pid_file: Path) -> int | None:
    """Read PID from file, return None if invalid."""
    if not pid_file.exists():
        return None
    
    try:
        pid = int(pid_file.read_text().strip())
        return pid if pid > 0 else None
    except (ValueError, OSError):
        return None


def write_pid(pid_file: Path, pid: int):
    """Write PID to file."""
    pid_file.write_text(str(pid))


def start_server(deployment: str):
    """Start the ScheduleZero server."""
    pid_file = get_pid_file(deployment)
    
    # Check if already running
    existing_pid = read_pid(pid_file)
    if existing_pid and is_process_running(existing_pid):
        print(f"✓ Server already running (PID: {existing_pid})")
        print(f"  Web: http://127.0.0.1:8888")
        print(f"  ZMQ: tcp://127.0.0.1:4242")
        return 0
    
    # Clean up stale PID file
    if existing_pid:
        print(f"⚠ Cleaned up stale PID file (PID {existing_pid} not running)")
        pid_file.unlink(missing_ok=True)
    
    # Set deployment environment variable
    env = os.environ.copy()
    env['SCHEDULEZERO_DEPLOYMENT'] = deployment
    
    print(f"➜ Starting ScheduleZero Server (Deployment: {deployment})")
    
    # Start server as subprocess
    try:
        # Use subprocess.Popen for cross-platform daemon-like behavior
        process = subprocess.Popen(
            [sys.executable, "-m", "schedule_zero.tornado_app_server"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True if sys.platform != 'win32' else False,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if it's still running
        if process.poll() is None:
            # Write PID file
            write_pid(pid_file, process.pid)
            print(f"✓ Server started (PID: {process.pid})")
            print(f"  Web: http://127.0.0.1:8888")
            print(f"  ZMQ: tcp://127.0.0.1:4242")
            print(f"  PID file: {pid_file}")
            print(f"\nStop with: python scripts/server.py stop --deployment {deployment}")
            return 0
        else:
            print(f"✗ Server failed to start (exit code: {process.returncode})")
            return 1
            
    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return 1


def stop_server(deployment: str, force: bool = False):
    """Stop the ScheduleZero server."""
    pid_file = get_pid_file(deployment)
    
    # Read PID
    pid = read_pid(pid_file)
    if not pid:
        print("✓ Server not running (no PID file)")
        return 0
    
    # Check if process exists
    if not is_process_running(pid):
        print(f"✓ Process not running (cleaning up PID file)")
        pid_file.unlink(missing_ok=True)
        return 0
    
    print(f"➜ Stopping ScheduleZero Server (Deployment: {deployment}, PID: {pid})")
    
    # Ask for confirmation unless force
    if not force:
        response = input(f"Stop process {pid}? (y/N) ")
        if response.lower() != 'y':
            print("Cancelled")
            return 0
    
    try:
        # Try graceful shutdown first (SIGTERM on Unix, CTRL_BREAK on Windows)
        if sys.platform == 'win32':
            # On Windows, send CTRL_BREAK_EVENT
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            # On Unix, send SIGTERM
            os.kill(pid, signal.SIGTERM)
        
        # Wait up to 5 seconds for graceful shutdown
        for _ in range(10):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        
        # Force kill if still running
        if is_process_running(pid):
            print("⚠ Process still running, forcing shutdown...")
            os.kill(pid, signal.SIGKILL if sys.platform != 'win32' else signal.SIGTERM)
            time.sleep(1)
        
        print("✓ Server stopped")
        
    except Exception as e:
        print(f"⚠ Error stopping process: {e}")
    
    finally:
        # Always clean up PID file
        pid_file.unlink(missing_ok=True)
    
    return 0


def status_server(deployment: str):
    """Check server status."""
    pid_file = get_pid_file(deployment)
    
    pid = read_pid(pid_file)
    if not pid:
        print(f"Server: Not running (Deployment: {deployment})")
        return 1
    
    if is_process_running(pid):
        print(f"Server: Running (Deployment: {deployment})")
        print(f"  PID: {pid}")
        print(f"  Web: http://127.0.0.1:8888")
        print(f"  ZMQ: tcp://127.0.0.1:4242")
        return 0
    else:
        print(f"Server: Not running (stale PID: {pid})")
        return 1


def main():
    parser = argparse.ArgumentParser(description="ScheduleZero Server Management")
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--deployment",
        default="default",
        help="Deployment name (default: default)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operation without confirmation"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        return start_server(args.deployment)
    elif args.command == "stop":
        return stop_server(args.deployment, args.force)
    elif args.command == "restart":
        stop_server(args.deployment, force=True)
        time.sleep(1)
        return start_server(args.deployment)
    elif args.command == "status":
        return status_server(args.deployment)


if __name__ == "__main__":
    sys.exit(main())
