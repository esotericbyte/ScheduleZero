#!/usr/bin/env python3
"""
Test the enhanced idempotent governor functionality.

This script demonstrates the new governor commands and idempotent behavior.
"""
import subprocess
import time
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and show output."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"📝 Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print("📤 STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("📥 STDERR:")  
            print(result.stderr)
        
        print(f"🔢 Exit Code: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test governor idempotent behavior."""
    print("""
🚀 ScheduleZero Governor Idempotent Test
═══════════════════════════════════════

This script tests the enhanced governor with:
✅ Idempotent operations (safe to run multiple times)
✅ Smart dependency management (server before handlers)  
✅ Individual process control
✅ Health monitoring and auto-recovery
✅ Intelligent status reporting
""")
    
    # Test commands in sequence
    tests = [
        ("poetry run python governor.py status", "Check initial status"),
        ("poetry run python governor.py start-server", "Start server only"),
        ("poetry run python governor.py status", "Check server status"),
        ("poetry run python governor.py start-server", "Start server again (should be idempotent)"),
        ("poetry run python governor.py start-handlers", "Start handlers (server dependency check)"),
        ("poetry run python governor.py status", "Check all processes status"),
        ("poetry run python governor.py ensure", "Health check and ensure all running"),
        ("poetry run python governor.py stop server", "Stop just the server"),
        ("poetry run python governor.py status", "Check status after stopping server"),
        ("poetry run python governor.py ensure", "Auto-fix (should restart server)"),
        ("poetry run python governor.py status", "Final status check"),
        ("poetry run python governor.py stop", "Stop all processes")
    ]
    
    success_count = 0
    
    for cmd, description in tests:
        if run_command(cmd, description):
            success_count += 1
        else:
            print(f"❌ Test failed: {description}")
            
        # Brief pause between tests
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"🎯 Test Results: {success_count}/{len(tests)} tests successful")
    print(f"{'='*60}")
    
    if success_count == len(tests):
        print("🎉 All tests passed! Governor is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print("""
📋 Available Governor Commands:
  
  Basic Operations:
    poetry run python governor.py start          # Start all processes  
    poetry run python governor.py stop           # Stop all processes
    poetry run python governor.py restart        # Restart all processes
    poetry run python governor.py status         # Show process status
    
  Individual Process Control:
    poetry run python governor.py start server   # Start just server
    poetry run python governor.py stop server    # Stop just server  
    poetry run python governor.py restart server # Restart just server
    
  Smart Operations:
    poetry run python governor.py start-server   # Convenience: start server
    poetry run python governor.py start-handlers # Start handlers (auto-starts server if needed)
    poetry run python governor.py ensure         # Health check and auto-fix
    
  Monitoring:
    poetry run python governor.py start          # Starts with continuous monitoring
    
🎯 Key Features:
  ✅ All operations are idempotent (safe to run multiple times)
  ✅ Smart dependency management (server started before handlers)
  ✅ Auto-restart crashed processes during monitoring
  ✅ Individual process control with dependency checking
  ✅ Rich status reporting with process health
""")

if __name__ == "__main__":
    main()