"""
DingDongHandler - A fun handler that plays clock chimes!

Plays:
- Big clock BONG sound on the hour (number of bongs = hour in 24hr format)
- Short musical chimes at 15, 30, and 45 minutes past the hour

Perfect for long-term scheduling tests and making the day more fun!
"""
import os
import signal
from datetime import datetime
from pathlib import Path
import sys
import logging

# Add src to path so we can import schedule_zero modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from schedule_zero.zmq_handler_base import ZMQHandlerBase, setup_handler_logging

# --- Configuration ---
# Deployment mode uses different ports than test mode!
# Test mode: handler port 4244, handler-id "test-handler-001" (existing test handler)
# Deployment mode: handler port 4245, handler-id "ding-dong-handler" (production clock)

# Check if we're in deployment mode (default to test mode for safety)
DEPLOYMENT_MODE = os.environ.get("DING_DONG_DEPLOY", "false").lower() == "true"

if DEPLOYMENT_MODE:
    # DEPLOYMENT MODE - Long-term clock with real schedules
    # Connects to CLOCK deployment server (port 8889 web, 4243 ZMQ)
    DEFAULT_HANDLER_ID = "ding-dong-handler"
    DEFAULT_HANDLER_PORT = 4245
    DEFAULT_SERVER_PORT = 4243  # Clock deployment ZMQ port
    DEFAULT_LOG_DIR = "ding_dong_logs"
    logger_prefix = "🔔 [DEPLOY]"
else:
    # TEST MODE - Development/testing
    # Connects to DEFAULT deployment server (port 8888 web, 4242 ZMQ)
    DEFAULT_HANDLER_ID = "ding-dong-test"
    DEFAULT_HANDLER_PORT = 4246
    DEFAULT_SERVER_PORT = 4242  # Default deployment ZMQ port
    DEFAULT_LOG_DIR = "ding_dong_logs_test"
    logger_prefix = "🧪 [TEST]"

HANDLER_ID = os.environ.get("SCHEDULEZERO_DING_DONG_ID", DEFAULT_HANDLER_ID)
HANDLER_HOST = os.environ.get("SCHEDULEZERO_HANDLER_HOST", "127.0.0.1")
HANDLER_PORT = int(os.environ.get("SCHEDULEZERO_HANDLER_PORT", DEFAULT_HANDLER_PORT))
HANDLER_ADDRESS = f"tcp://{HANDLER_HOST}:{HANDLER_PORT}"

SERVER_HOST = os.environ.get("SCHEDULEZERO_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SCHEDULEZERO_SERVER_PORT", DEFAULT_SERVER_PORT))
SERVER_ADDRESS = f"tcp://{SERVER_HOST}:{SERVER_PORT}"

MAX_REGISTRATION_RETRIES = int(os.environ.get("SCHEDULEZERO_MAX_RETRIES", 5))

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(HANDLER_ID)


class DingDongHandler(ZMQHandlerBase):
    """Handler that plays clock chimes and musical notes."""
    
    def __init__(self, handler_id, handler_address, server_address, log_dir_name=DEFAULT_LOG_DIR):
        """Initialize the DingDongHandler."""
        super().__init__(
            handler_id=handler_id,
            handler_address=handler_address,
            server_address=server_address,
            max_registration_retries=MAX_REGISTRATION_RETRIES
        )
        
        # Setup log directory (different for test vs deploy)
        self.log_dir = Path(__file__).parent / log_dir_name
        self.log_dir.mkdir(exist_ok=True)
        self.chime_log = self.log_dir / "chime_log.txt"
        self.mode = "DEPLOY" if DEPLOYMENT_MODE else "TEST"
        
        # Try to import audio library
        try:
            import winsound
            self.winsound = winsound
            self.has_audio = True
            logger.info(f"{logger_prefix} Audio support enabled (winsound)")
        except ImportError:
            self.winsound = None
            self.has_audio = False
            logger.warning(f"{logger_prefix} No audio support (winsound not available)")
        
        # Try to import text-to-speech
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            # Set voice properties (optional - adjust rate/volume)
            self.tts_engine.setProperty('rate', 150)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            self.has_tts = True
            logger.info(f"{logger_prefix} Text-to-speech enabled (pyttsx3)")
        except Exception as e:
            self.tts_engine = None
            self.has_tts = False
            logger.warning(f"{logger_prefix} No TTS support: {e}")
    
    def _log_chime(self, chime_type, count=None):
        """Log a chime event to file."""
        now = datetime.utcnow()
        log_entry = f"[{self.mode}] {now.isoformat()} UTC - {chime_type}"
        if count:
            log_entry += f" (x{count})"
        log_entry += f" - Local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        with open(self.chime_log, 'a') as f:
            f.write(log_entry)
        
        logger.info(f"{logger_prefix} {log_entry.strip()}")
    
    def play_hour_bongs(self, params):
        """
        Play BONG sounds for the hour (24-hour clock).
        
        Args:
            params: dict with optional 'hour' (default: current UTC hour)
            
        Returns:
            dict with status and bong count
        """
        hour = params.get("hour")
        if hour is None:
            hour = datetime.utcnow().hour
        
        # Ensure hour is in 0-23 range
        hour = hour % 24
        
        # If it's midnight (0), play 24 bongs!
        bong_count = 24 if hour == 0 else hour
        
        self._log_chime(f"HOUR BONG", bong_count)
        
        # Play the bongs!
        if self.has_audio:
            for i in range(bong_count):
                # Big Ben style: Lower frequency for hour chimes
                # E4 (330 Hz) - a nice deep bong
                self.winsound.Beep(330, 800)  # 800ms per bong
                if i < bong_count - 1:
                    # Brief pause between bongs
                    import time
                    time.sleep(0.5)
        
        return {
            "status": "success",
            "type": "hour_bong",
            "bong_count": bong_count,
            "hour": hour,
            "utc_time": datetime.utcnow().isoformat(),
            "local_time": datetime.now().isoformat(),
            "audio_played": self.has_audio
        }
    
    def play_quarter_chime(self, params):
        """
        Play musical chimes for quarter hours (15, 30, 45 minutes).
        
        Args:
            params: dict with optional 'quarter' (1=:15, 2=:30, 3=:45)
            
        Returns:
            dict with status and chime details
        """
        quarter = params.get("quarter", 1)
        minute = quarter * 15
        
        self._log_chime(f"QUARTER CHIME at :{minute:02d}")
        
        # Play Westminster Quarters melody (simplified)
        # More notes for later quarters
        if self.has_audio:
            if quarter == 1:
                # First quarter: Short melody
                self._play_melody([523, 440, 392, 330], [200, 200, 200, 400])  # C-A-G-E
            elif quarter == 2:
                # Half hour: Longer melody
                self._play_melody([523, 440, 392, 330, 392, 440, 523, 330], 
                                [200, 200, 200, 400, 200, 200, 200, 400])
            elif quarter == 3:
                # Three quarters: Even longer
                self._play_melody([523, 440, 392, 330, 392, 440, 523, 330, 523, 440, 392, 330], 
                                [200, 200, 200, 400, 200, 200, 200, 400, 200, 200, 200, 400])
        
        return {
            "status": "success",
            "type": "quarter_chime",
            "quarter": quarter,
            "minute": minute,
            "utc_time": datetime.utcnow().isoformat(),
            "local_time": datetime.now().isoformat(),
            "audio_played": self.has_audio
        }
    
    def _play_melody(self, frequencies, durations):
        """Play a sequence of notes."""
        import time
        for freq, duration in zip(frequencies, durations):
            self.winsound.Beep(freq, duration)
            time.sleep(0.05)  # Tiny pause between notes
    
    def announce_time(self, params=None):
        """
        Announce the current UTC time and date via text-to-speech.
        
        Args:
            params: dict (optional, currently unused)
            
        Returns:
            dict with status and announcement text
        """
        now_utc = datetime.utcnow()
        
        # Format the announcement
        # Example: "The time is 3:00 PM UTC, Wednesday, October 29th, 2025"
        time_str = now_utc.strftime("%I:%M %p")  # 03:00 PM
        date_str = now_utc.strftime("%A, %B %d, %Y")  # Wednesday, October 29, 2025
        
        # Add ordinal suffix to day (1st, 2nd, 3rd, 4th, etc.)
        day = now_utc.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]
        
        date_str_ordinal = now_utc.strftime(f"%A, %B {day}{suffix}, %Y")
        
        announcement = f"The time is {time_str} UTC, {date_str_ordinal}"
        
        self._log_chime(f"TIME ANNOUNCEMENT: {announcement}")
        
        # Speak it!
        if self.has_tts:
            try:
                self.tts_engine.say(announcement)
                self.tts_engine.runAndWait()
                spoken = True
            except Exception as e:
                logger.error(f"TTS error: {e}")
                spoken = False
        else:
            spoken = False
        
        return {
            "status": "success",
            "type": "time_announcement",
            "announcement": announcement,
            "utc_time": now_utc.isoformat(),
            "local_time": datetime.now().isoformat(),
            "spoken": spoken,
            "tts_available": self.has_tts
        }
    
    def get_chime_log(self, params=None):
        """
        Get the chime log contents.
        
        Returns:
            dict with log contents
        """
        if not self.chime_log.exists():
            return {
                "status": "success",
                "entries": 0,
                "log": ""
            }
        
        with open(self.chime_log, 'r') as f:
            log_content = f.read()
        
        entry_count = log_content.count('\n')
        
        return {
            "status": "success",
            "entries": entry_count,
            "log": log_content,
            "log_file": str(self.chime_log)
        }
    
    def clear_log(self, params=None):
        """Clear the chime log."""
        if self.chime_log.exists():
            self.chime_log.unlink()
        
        return {
            "status": "success",
            "message": "Chime log cleared"
        }


def main():
    """Run the DingDongHandler as a standalone process."""
    # Setup logging first
    log_file = setup_handler_logging(HANDLER_ID, log_level="INFO")
    print(f"📝 Logging to: {log_file}")
    
    # Create handler instance
    handler = DingDongHandler(
        handler_id=HANDLER_ID,
        handler_address=HANDLER_ADDRESS,
        server_address=SERVER_ADDRESS,
        log_dir_name=DEFAULT_LOG_DIR
    )
    
    # Set up signal handlers
    def handle_signal(signum, frame):
        handler.logger.info(f"Received signal {signum}. Shutting down...", method="main")
        handler.stop()
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Run handler (blocks until stopped)
    mode_name = "DEPLOYMENT" if DEPLOYMENT_MODE else "TEST"
    handler.logger.info(f"Starting in {mode_name} mode", method="main")
    handler.logger.info(f"Handler address: {HANDLER_ADDRESS}", method="main")
    handler.logger.info(f"Server address: {SERVER_ADDRESS}", method="main")
    handler.logger.info(f"Log directory: {DEFAULT_LOG_DIR}/", method="main")
    handler.logger.info("Ready to BONG on the hour and chime on the quarters!", method="main")
    handler.run()
    
    handler.logger.info("DingDongHandler shut down", method="main")


if __name__ == "__main__":
    main()
