#!/usr/bin/env python3
"""
Interactive Handler REPL for ScheduleZero

A REPL-like environment for testing ZMQ handlers interactively.
Runs a handler in the background and provides commands to interact with it.

Usage:
    python scripts/interactive_handler.py              # Start interactive REPL
    python scripts/interactive_handler.py --tmux       # Run in tmux session
    
Commands in REPL:
    status                  - Show handler status
    methods                 - List available methods
    call <method> [args]    - Call a handler method
    buffer save <name>      - Save current output to buffer
    buffer load <name>      - Load buffer contents
    buffer list             - List saved buffers
    log [n]                 - Show last n log entries (default 10)
    clear                   - Clear screen
    help                    - Show this help
    quit / exit             - Stop handler and exit

Examples:
    >>> call write_file filename=test.txt content="Hello"
    >>> buffer save test1
    >>> log 5
"""
import sys
import os
import json
import threading
import time
import cmd
import shlex
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.zmq_handler_base import ZMQHandlerBase
import logging

# Configuration
HANDLER_ID = os.environ.get("SCHEDULEZERO_HANDLER_ID", "interactive-handler")
HANDLER_HOST = os.environ.get("SCHEDULEZERO_HANDLER_HOST", "127.0.0.1")
HANDLER_PORT = int(os.environ.get("SCHEDULEZERO_HANDLER_PORT", 4245))  # Different from test handler
SERVER_HOST = os.environ.get("SCHEDULEZERO_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SCHEDULEZERO_SERVER_PORT", 4242))

HANDLER_ADDRESS = f"tcp://{HANDLER_HOST}:{HANDLER_PORT}"
SERVER_ADDRESS = f"tcp://{SERVER_HOST}:{SERVER_PORT}"


class InteractiveHandler(ZMQHandlerBase):
    """Handler that can be controlled interactively."""
    
    def __init__(self, handler_id, handler_address, server_address):
        super().__init__(
            handler_id=handler_id,
            handler_address=handler_address,
            server_address=server_address,
            max_registration_retries=5
        )
        
        self.output_dir = Path("interactive_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.buffers = {}
        self.execution_history = []
        
    def write_file(self, params):
        """Write content to a file."""
        filename = params.get('filename', 'output.txt')
        content = params.get('content', '')
        
        filepath = self.output_dir / filename
        filepath.write_text(content)
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'method': 'write_file',
            'filename': filename,
            'length': len(content)
        }
        self.execution_history.append(entry)
        
        return {
            'status': 'success',
            'filepath': str(filepath),
            'bytes_written': len(content)
        }
    
    def read_file(self, params):
        """Read content from a file."""
        filename = params.get('filename', 'output.txt')
        filepath = self.output_dir / filename
        
        if not filepath.exists():
            return {
                'status': 'error',
                'message': f'File not found: {filename}'
            }
        
        content = filepath.read_text()
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'method': 'read_file',
            'filename': filename,
            'length': len(content)
        }
        self.execution_history.append(entry)
        
        return {
            'status': 'success',
            'content': content,
            'bytes_read': len(content)
        }
    
    def echo(self, params):
        """Echo back the parameters."""
        message = params.get('message', '')
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'method': 'echo',
            'message': message
        }
        self.execution_history.append(entry)
        
        return {
            'status': 'success',
            'echo': message,
            'received_at': datetime.now().isoformat()
        }
    
    def get_history(self, params):
        """Get execution history."""
        limit = params.get('limit', 10)
        return {
            'status': 'success',
            'history': self.execution_history[-limit:],
            'total_executions': len(self.execution_history)
        }


class InteractiveREPL(cmd.Cmd):
    """Interactive REPL for controlling the handler."""
    
    intro = """
╔═══════════════════════════════════════════════════════════╗
║  ScheduleZero Interactive Handler REPL                   ║
║  Type 'help' for commands, 'quit' to exit                ║
╚═══════════════════════════════════════════════════════════╝
    """
    prompt = '>>> '
    
    def __init__(self, handler):
        super().__init__()
        self.handler = handler
        self.handler_thread = None
        self.buffers = {}
        self.running = False
        
    def start_handler(self):
        """Start the handler in a background thread."""
        self.running = True
        self.handler_thread = threading.Thread(target=self._run_handler, daemon=True)
        self.handler_thread.start()
        
        # Wait a bit for registration
        time.sleep(2)
        print(f"✓ Handler '{self.handler.handler_id}' started on {HANDLER_ADDRESS}")
        print(f"✓ Registered with server at {SERVER_ADDRESS}")
        print()
    
    def _run_handler(self):
        """Run the handler loop in background thread."""
        try:
            self.handler.run()
        except Exception as e:
            print(f"\n✗ Handler error: {e}")
            self.running = False
    
    def stop_handler(self):
        """Stop the handler."""
        self.running = False
        if self.handler_thread:
            self.handler.stop()
            print("✓ Handler stopped")
    
    def do_status(self, arg):
        """Show handler status."""
        if self.running:
            print(f"✓ Handler running: {self.handler.handler_id}")
            print(f"  Address: {HANDLER_ADDRESS}")
            print(f"  Server: {SERVER_ADDRESS}")
            print(f"  Executions: {len(self.handler.execution_history)}")
        else:
            print("✗ Handler not running")
    
    def do_methods(self, arg):
        """List available handler methods."""
        methods = [
            'write_file - Write content to a file',
            'read_file - Read content from a file',
            'echo - Echo back parameters',
            'get_history - Get execution history'
        ]
        print("\nAvailable methods:")
        for method in methods:
            print(f"  • {method}")
        print()
    
    def do_call(self, arg):
        """
        Call a handler method directly (bypasses ScheduleZero server).
        Usage: call <method> key=value key2=value2
        """
        try:
            parts = shlex.split(arg)
            if not parts:
                print("Usage: call <method> [key=value ...]")
                return
            
            method_name = parts[0]
            params = {}
            
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key] = value
            
            # Call the method directly
            method = getattr(self.handler, method_name, None)
            if not method:
                print(f"✗ Method not found: {method_name}")
                return
            
            result = method(params)
            print(f"✓ Result: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def do_buffer(self, arg):
        """
        Buffer management commands.
        Usage: 
            buffer save <name>      - Save last output
            buffer load <name>      - Load buffer
            buffer list             - List buffers
        """
        parts = arg.split()
        if not parts:
            print("Usage: buffer <save|load|list> [name]")
            return
        
        cmd = parts[0]
        
        if cmd == 'save':
            if len(parts) < 2:
                print("Usage: buffer save <name>")
                return
            name = parts[1]
            # Save last execution result
            if self.handler.execution_history:
                self.buffers[name] = self.handler.execution_history[-1]
                print(f"✓ Saved to buffer: {name}")
            else:
                print("✗ No execution to save")
        
        elif cmd == 'load':
            if len(parts) < 2:
                print("Usage: buffer load <name>")
                return
            name = parts[1]
            if name in self.buffers:
                print(json.dumps(self.buffers[name], indent=2))
            else:
                print(f"✗ Buffer not found: {name}")
        
        elif cmd == 'list':
            if self.buffers:
                print("\nSaved buffers:")
                for name in self.buffers:
                    entry = self.buffers[name]
                    print(f"  • {name} - {entry.get('method')} at {entry.get('timestamp')}")
            else:
                print("No saved buffers")
        
        else:
            print(f"✗ Unknown buffer command: {cmd}")
    
    def do_log(self, arg):
        """Show execution log. Usage: log [n] (default 10)"""
        try:
            limit = int(arg) if arg else 10
            history = self.handler.execution_history[-limit:]
            
            if not history:
                print("No executions yet")
                return
            
            print(f"\nLast {len(history)} executions:")
            for entry in history:
                timestamp = entry.get('timestamp', '')
                method = entry.get('method', '')
                print(f"  {timestamp} - {method}")
                for key, value in entry.items():
                    if key not in ['timestamp', 'method']:
                        print(f"    {key}: {value}")
            print()
        except ValueError:
            print("Usage: log [n]")
    
    def do_clear(self, arg):
        """Clear the screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_quit(self, arg):
        """Stop handler and exit."""
        self.stop_handler()
        return True
    
    def do_exit(self, arg):
        """Stop handler and exit."""
        return self.do_quit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()
        return self.do_quit(arg)


def run_in_tmux():
    """Run the REPL in a tmux session."""
    import subprocess
    
    session_name = f"schedulezero-handler-{int(time.time())}"
    script_path = Path(__file__).absolute()
    
    # Create tmux session
    subprocess.run([
        'tmux', 'new-session', '-d', '-s', session_name,
        'python', str(script_path)
    ])
    
    # Attach to session
    subprocess.run(['tmux', 'attach-session', '-t', session_name])


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Interactive Handler REPL')
    parser.add_argument('--tmux', action='store_true', help='Run in tmux session')
    parser.add_argument('--handler-id', default=HANDLER_ID, help='Handler ID')
    parser.add_argument('--handler-port', type=int, default=HANDLER_PORT, help='Handler port')
    parser.add_argument('--server-port', type=int, default=SERVER_PORT, help='Server port')
    args = parser.parse_args()
    
    if args.tmux:
        run_in_tmux()
        return
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handler
    handler_address = f"tcp://{HANDLER_HOST}:{args.handler_port}"
    server_address = f"tcp://{SERVER_HOST}:{args.server_port}"
    
    handler = InteractiveHandler(
        handler_id=args.handler_id,
        handler_address=handler_address,
        server_address=server_address
    )
    
    # Create and start REPL
    repl = InteractiveREPL(handler)
    repl.start_handler()
    
    try:
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\n")
        repl.stop_handler()


if __name__ == '__main__':
    main()
