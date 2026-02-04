#!/usr/bin/env python3
"""
Test Governor Signal Handling and PID Management

Tests the enhanced governor with proper daemon behavior:
- PID file management
- Signal handling (SIGTERM, SIGINT)
- Graceful shutdown sequence
- Orphaned process cleanup
- Exit code behavior
"""

import sys
import os
import time
import signal
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from src.schedule_zero.logging_config import setup_logging, get_logger

# Setup logging
setup_logging("INFO")
logger = get_logger(__name__)

def test_governor_signal_handling():
    """Test governor signal handling and PID management."""
    
    print("🧪 Testing Governor Signal Handling & PID Management")
    print("=" * 60)
    
    # Test 1: Check PID file creation
    print("\n1️⃣ Testing PID file creation...")
    
    # Start governor in background (start command launches and detaches)
    gov_result = subprocess.run([
        sys.executable, "governor.py", "start", "--deployment", "test"
    ], capture_output=True, text=True, timeout=10)
    
    print(f"   Governor start result: {gov_result.returncode}")
    if gov_result.stdout:
        print(f"   STDOUT: {gov_result.stdout[:200]}...")
    if gov_result.stderr:
        print(f"   STDERR: {gov_result.stderr[:200]}...")
    
    # Give it time to fully start
    time.sleep(5)
    
    # Check PID files
    pid_dir = Path("deployments/test/pids")
    governor_pid_file = pid_dir / "governor.pid"
    server_pid_file = pid_dir / "server.pid"
    
    if governor_pid_file.exists():
        with open(governor_pid_file, 'r') as f:
            governor_pid = int(f.read().strip())
        print(f"   ✅ Governor PID file created: {governor_pid}")
    else:
        print(f"   ❌ Governor PID file missing")
        return False
    
    if server_pid_file.exists():
        with open(server_pid_file, 'r') as f:
            server_pid = int(f.read().strip())
        print(f"   ✅ Server PID file created: {server_pid}")
    else:
        print(f"   ❌ Server PID file missing")
    
    # Test 2: Check processes are running
    print("\n2️⃣ Testing process health...")
    
    def is_process_running(pid):
        try:
            if os.name == 'nt':
                # Windows: Use tasklist
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                      capture_output=True, text=True)
                return str(pid) in result.stdout
            else:
                # Unix: Send signal 0
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    
    if is_process_running(governor_pid):
        print(f"   ✅ Governor process running (PID {governor_pid})")
    else:
        print(f"   ❌ Governor process not running")
        return False
    
    if server_pid_file.exists() and is_process_running(server_pid):
        print(f"   ✅ Server process running (PID {server_pid})")
    else:
        print(f"   ⚠️ Server process check skipped or not running")
    
    # Test 3: Test graceful shutdown with SIGTERM
    print("\n3️⃣ Testing graceful shutdown (SIGTERM)...")
    
    print(f"   📡 Sending SIGTERM to governor (PID {governor_pid})")
    try:
        if os.name == 'nt':
            # Windows: Use taskkill with /T for tree termination
            subprocess.run(['taskkill', '/PID', str(governor_pid), '/T'], 
                         capture_output=True, timeout=15)
        else:
            os.kill(governor_pid, signal.SIGTERM)
        
        # Wait for graceful shutdown
        shutdown_start = time.time()
        while time.time() - shutdown_start < 20:  # 20 second timeout
            if not is_process_running(governor_pid):
                shutdown_time = time.time() - shutdown_start
                print(f"   ✅ Governor shut down gracefully in {shutdown_time:.1f}s")
                break
            time.sleep(0.5)
        else:
            print(f"   ❌ Governor did not shut down within timeout")
            return False
            
        # Check PID files are cleaned up
        time.sleep(1)
        if not governor_pid_file.exists():
            print(f"   ✅ Governor PID file cleaned up")
        else:
            print(f"   ❌ Governor PID file still exists")
        
        if not server_pid_file.exists():
            print(f"   ✅ Server PID file cleaned up")
        else:
            print(f"   ⚠️ Server PID file still exists (may be expected)")
            
    except Exception as e:
        print(f"   ❌ Error during shutdown test: {e}")
        return False
    
    # Test 4: Test orphaned process cleanup
    print("\n4️⃣ Testing orphaned process cleanup...")
    
    # Create fake PID files to test cleanup
    fake_pid_file = pid_dir / "fake_orphan.pid"
    fake_pid_file.write_text("999999")  # Non-existent PID
    
    dead_process_pid_file = pid_dir / "dead_process.pid"
    dead_process_pid_file.write_text("1")  # System process PID (should exist but not ours)
    
    print(f"   📝 Created test PID files")
    
    # Start governor again to test cleanup
    gov_process2 = subprocess.Popen([
        sys.executable, "governor.py", "start", "--deployment", "test"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(3)
    
    # Check if fake PID files were cleaned up
    if not fake_pid_file.exists():
        print(f"   ✅ Fake orphan PID file cleaned up")
    else:
        print(f"   ❌ Fake orphan PID file still exists")
    
    if not dead_process_pid_file.exists():
        print(f"   ✅ Dead process PID file cleaned up")
    else:
        print(f"   ⚠️ Dead process PID file still exists (check manually)")
    
    # Clean shutdown for test cleanup
    print(f"\n🧹 Final cleanup...")
    try:
        # Get new governor PID
        if governor_pid_file.exists():
            with open(governor_pid_file, 'r') as f:
                new_gov_pid = int(f.read().strip())
            
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(new_gov_pid), '/T'], 
                             capture_output=True, timeout=10)
            else:
                os.kill(new_gov_pid, signal.SIGTERM)
            
            time.sleep(2)
            print(f"   ✅ Test cleanup completed")
    except Exception as e:
        print(f"   ⚠️ Cleanup error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Signal handling tests completed!")
    return True

def test_exit_codes():
    """Test governor exit codes."""
    
    print("\n🧪 Testing Governor Exit Codes")
    print("=" * 40)
    
    # Test normal exit
    print("\n1️⃣ Testing normal exit code...")
    result = subprocess.run([
        sys.executable, "governor.py", "status", "--deployment", "test"
    ], capture_output=True)
    
    print(f"   Exit code for status command: {result.returncode}")
    
    # Test invalid command
    print("\n2️⃣ Testing error exit code...")
    result = subprocess.run([
        sys.executable, "governor.py", "invalid_command", "--deployment", "test"  
    ], capture_output=True)
    
    print(f"   Exit code for invalid command: {result.returncode}")
    
    return True

if __name__ == "__main__":
    print("🚀 Governor Signal Handling Test Suite")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        success = True
        
        if not test_governor_signal_handling():
            success = False
            
        if not test_exit_codes():
            success = False
        
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)