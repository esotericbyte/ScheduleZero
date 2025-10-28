#!/usr/bin/env python3
"""
Start all ScheduleZero components in order.

This script starts the ScheduleZero server and test handler, managing them as
subprocesses that can be monitored and stopped together.
"""
import sys
import time
import signal
import subprocess
import argparse
import requests
from pathlib import Path

processes = []

def stop_all():
    """Stop all running processes."""
    print("\nStopping all components...")
    for name, proc in processes:
        if proc.poll() is None:  # Still running
            print(f"  Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("All components stopped.")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    stop_all()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Start ScheduleZero components")
    parser.add_argument('--tests', action='store_true', help='Run tests after starting components')
    args = parser.parse_args()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("=== Starting ScheduleZero Components ===")
        print()
        
        # 1. Start the server
        print("1. Starting ScheduleZero Server...")
        server_proc = subprocess.Popen(
            ["poetry", "run", "python", "-m", "schedule_zero.server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Server", server_proc))
        print(f"   Server starting (PID: {server_proc.pid})")
        
        # Wait for server to be ready
        print("   Waiting for server to start...")
        max_wait = 30
        server_ready = False
        
        for waited in range(max_wait):
            time.sleep(1)
            
            try:
                response = requests.get("http://127.0.0.1:8888/", timeout=2)
                if response.status_code == 200:
                    server_ready = True
                    break
            except:
                pass
            
            # Check if process failed
            if server_proc.poll() is not None:
                print("   ✗ Server process failed to start!")
                output, _ = server_proc.communicate()
                print(output)
                raise Exception("Server failed to start")
        
        if not server_ready:
            print(f"   ✗ Server did not respond within {max_wait}s")
            raise Exception("Server startup timeout")
        
        print("   ✓ Server is ready!")
        print()
        
        # 2. Start the test handler
        print("2. Starting Test Handler...")
        handler_proc = subprocess.Popen(
            ["poetry", "run", "python", "tests/test_handler.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Test Handler", handler_proc))
        print(f"   Test handler starting (PID: {handler_proc.pid})")
        
        # Wait for handler to register
        print("   Waiting for handler to register...")
        max_wait = 20
        handler_registered = False
        
        for waited in range(max_wait):
            time.sleep(1)
            
            try:
                response = requests.get("http://127.0.0.1:8888/api/handlers", timeout=2)
                data = response.json()
                if any(h.get('id') == 'test-handler-001' for h in data.get('handlers', [])):
                    handler_registered = True
                    break
            except:
                pass
            
            # Check if process failed
            if handler_proc.poll() is not None:
                print("   ✗ Handler process failed!")
                output, _ = handler_proc.communicate()
                print(output)
                raise Exception("Handler failed to start")
        
        if not handler_registered:
            print(f"   ⚠ Handler did not register within {max_wait}s (may still be trying)")
        else:
            print("   ✓ Handler registered successfully!")
        print()
        
        # Show status
        print("=== Status ===")
        print("Server:       http://127.0.0.1:8888")
        print("zerorpc:      tcp://127.0.0.1:4242")
        print("Test Handler: tcp://127.0.0.1:4244")
        print()
        
        # Run tests if requested
        if args.tests:
            print("=== Running Tests ===")
            print()
            result = subprocess.run(
                ["poetry", "run", "pytest", "tests/test_scheduled_jobs.py", "-v"],
                cwd=Path(__file__).parent
            )
            print()
            
            if result.returncode == 0:
                print("✓ All tests passed!")
            else:
                print(f"✗ Some tests failed (exit code: {result.returncode})")
            print()
        
        # Keep running and monitor
        print("=== Components Running ===")
        print("Press Ctrl+C to stop all components")
        print()
        
        while True:
            time.sleep(5)
            
            # Check if any process failed
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n✗ {name} has stopped!")
                    output, _ = proc.communicate()
                    if output:
                        print(output)
                    raise Exception(f"{name} failed")
    
    except Exception as e:
        print(f"\nError: {e}")
        stop_all()
        sys.exit(1)

if __name__ == "__main__":
    main()
