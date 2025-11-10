"""
DingAlingHandler - Fast lightweight handler for rapid development feedback!

Features:
- Quick "aling" sounds (shorter than full ding-dong chimes)  
- Connects to clock server for shared schedule testing
- Minimal overhead for rapid iteration
- Visual feedback via console logs
- Perfect for development and testing workflows

Usage:
    # Start handler (connects to clock deployment)
    poetry run python tests/ding_aling_handler.py
    
    # Schedule some quick test alings
    poetry run python tests/schedule_aling_tests.py
"""
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.zmq_handler_base import ZMQHandlerBase, setup_handler_logging

# Configuration - Always connects to CLOCK deployment for shared testing
HANDLER_ID = "ding-aling"
HANDLER_HOST = "127.0.0.1" 
HANDLER_PORT = 4247  # Unique port for aling handler
SERVER_PORT = 4243   # Clock deployment ZMQ port
HANDLER_ADDRESS = f"tcp://{HANDLER_HOST}:{HANDLER_PORT}"
SERVER_ADDRESS = f"tcp://127.0.0.1:{SERVER_PORT}"


class DingAlingHandler(ZMQHandlerBase):
    """
    Fast, lightweight handler for development testing.
    
    Provides quick audio/visual feedback without the overhead
    of full chime sequences. Perfect for rapid iteration.
    """
    
    def __init__(self, handler_id: str, handler_address: str, server_address: str):
        super().__init__(handler_id, handler_address, server_address)
        self.test_counter = 0
        
        # Visual indicators for console output
        self.indicators = ["🔔", "🎵", "⭐", "🎯", "⚡", "🚀", "💫", "✨"]
        
    def get_supported_methods(self) -> list[str]:
        """Return list of methods this handler supports."""
        return [
            "quick_aling",        # Fast single beep
            "double_aling",       # Two quick beeps  
            "triple_aling",       # Three quick beeps
            "test_sequence",      # Development test sequence
            "visual_ping",        # Console-only feedback
            "counter_test"        # Incrementing counter test
        ]
    
    def quick_aling(self, message: str = "Quick aling!") -> Dict[str, Any]:
        """Play a quick aling sound - faster than full chimes."""
        self.test_counter += 1
        indicator = self.indicators[self.test_counter % len(self.indicators)]
        
        self.logger.info(
            f"{indicator} ALING! #{self.test_counter}", 
            method="quick_aling",
            message=message,
            counter=self.test_counter
        )
        
        # Simulate quick beep (much faster than full chime)
        self._play_quick_sound("aling")
        
        return {
            "status": "success",
            "sound": "aling",
            "counter": self.test_counter,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def double_aling(self, message: str = "Double aling!") -> Dict[str, Any]:
        """Play two quick alings."""
        self.test_counter += 1
        indicator = self.indicators[self.test_counter % len(self.indicators)]
        
        self.logger.info(
            f"{indicator} ALING-ALING! #{self.test_counter}", 
            method="double_aling",
            message=message
        )
        
        self._play_quick_sound("aling")
        time.sleep(0.1)  # Brief pause
        self._play_quick_sound("aling")
        
        return {
            "status": "success", 
            "sound": "double_aling",
            "counter": self.test_counter,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def triple_aling(self, message: str = "Triple aling!") -> Dict[str, Any]:
        """Play three quick alings."""
        self.test_counter += 1
        indicator = self.indicators[self.test_counter % len(self.indicators)]
        
        self.logger.info(
            f"{indicator} ALING-ALING-ALING! #{self.test_counter}", 
            method="triple_aling",
            message=message
        )
        
        for i in range(3):
            self._play_quick_sound("aling")
            if i < 2:  # Don't pause after last aling
                time.sleep(0.1)
        
        return {
            "status": "success",
            "sound": "triple_aling", 
            "counter": self.test_counter,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def test_sequence(self, sequence_name: str = "dev_test") -> Dict[str, Any]:
        """Run a quick test sequence for development."""
        self.test_counter += 1
        
        self.logger.info(
            f"🧪 Running test sequence: {sequence_name}",
            method="test_sequence",
            sequence=sequence_name,
            counter=self.test_counter
        )
        
        # Quick sequence: single, pause, double, pause, triple
        self._play_quick_sound("aling")
        time.sleep(0.2)
        
        self._play_quick_sound("aling") 
        time.sleep(0.1)
        self._play_quick_sound("aling")
        time.sleep(0.2)
        
        for i in range(3):
            self._play_quick_sound("aling")
            if i < 2:
                time.sleep(0.1)
        
        self.logger.info(
            f"✅ Test sequence completed: {sequence_name}",
            method="test_sequence",
            counter=self.test_counter
        )
        
        return {
            "status": "success",
            "sequence": sequence_name,
            "counter": self.test_counter,
            "timestamp": datetime.now().isoformat()
        }
    
    def visual_ping(self, message: str = "Visual ping!") -> Dict[str, Any]:
        """Console-only feedback - no sound, just visual indicators."""
        self.test_counter += 1
        indicator = self.indicators[self.test_counter % len(self.indicators)]
        
        # Create visual pattern
        pattern = f"{indicator} {'═' * (self.test_counter % 20 + 5)} {indicator}"
        
        self.logger.info(
            pattern,
            method="visual_ping",
            message=message,
            counter=self.test_counter
        )
        
        return {
            "status": "success",
            "type": "visual_only",
            "pattern": pattern,
            "counter": self.test_counter,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def counter_test(self, increment: int = 1) -> Dict[str, Any]:
        """Simple counter increment test."""
        self.test_counter += increment
        
        # Visual counter display
        bar_length = min(self.test_counter % 50, 30)
        progress_bar = "█" * bar_length + "░" * (30 - bar_length)
        
        self.logger.info(
            f"📊 Counter: {self.test_counter:4d} [{progress_bar}]",
            method="counter_test",
            counter=self.test_counter,
            increment=increment
        )
        
        return {
            "status": "success",
            "counter": self.test_counter,
            "increment": increment,
            "timestamp": datetime.now().isoformat()
        }
    
    def _play_quick_sound(self, sound_type: str):
        """
        Play a quick sound. Much faster than full chimes.
        
        For development, we'll use console beep or visual indicator.
        In production, could trigger actual sound files.
        """
        if os.name == 'nt':  # Windows
            try:
                import winsound
                # Quick high-pitched beep (500Hz, 100ms)
                winsound.Beep(500, 100)
            except ImportError:
                # Fallback to print if winsound not available
                print(f"\a🔔 {sound_type.upper()}", end='', flush=True)
        else:  # Unix/Linux/Mac
            # Terminal bell character
            print(f"\a🔔 {sound_type.upper()}", end='', flush=True)


def main():
    """Main entry point for the DingAling handler."""
    print(f"""
🚀 DingAling Handler Starting!
═══════════════════════════════

Handler ID: {HANDLER_ID}
Address: {HANDLER_ADDRESS}  
Server: {SERVER_ADDRESS}
Mode: FAST DEVELOPMENT

Supported methods:
  • quick_aling    - Single quick beep
  • double_aling   - Two quick beeps  
  • triple_aling   - Three quick beeps
  • test_sequence  - Development test pattern
  • visual_ping    - Console-only feedback
  • counter_test   - Simple counter increment

Perfect for rapid iteration! 🎯
""")
    
    # Setup logging for this handler
    setup_handler_logging(HANDLER_ID)
    
    # Create and start the handler
    handler = DingAlingHandler(HANDLER_ID, HANDLER_ADDRESS, SERVER_ADDRESS)
    
    def signal_handler(signum, frame):
        print("\n🛑 DingAling handler shutting down...")
        handler.stop()
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🎵 DingAling handler is ready for rapid testing!")
        handler.run()
    except KeyboardInterrupt:
        print("\n🛑 DingAling handler stopped by user")
    except Exception as e:
        print(f"\n❌ DingAling handler error: {e}")
        raise
    finally:
        handler.stop()


if __name__ == "__main__":
    main()