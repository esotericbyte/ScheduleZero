# 🎵 DingAling Handler - Fast Development Testing

The **DingAling Handler** is a lightweight, rapid-feedback handler designed for fast development iteration and testing workflows.

## 🚀 Quick Start

### 1. Start the Clock Server (if not already running)
```powershell
poetry run python governor.py start clock
```

### 2. Start the DingAling Handler
```powershell
poetry run python tests/ding_aling_handler.py
```

### 3. Schedule Some Quick Tests
```powershell
poetry run python tests/schedule_aling_tests.py
```

### 4. Check Status
```powershell
poetry run python tests/check_aling_status.py
```

## 🎯 Features

### ⚡ Fast Feedback
- **Quick Alings**: Much faster than full chime sequences
- **Visual Indicators**: Console output with emojis and progress bars
- **Rapid Testing**: Tests scheduled every few seconds for immediate feedback

### 🔧 Development Methods
- `quick_aling()` - Single quick beep with counter
- `double_aling()` - Two quick beeps  
- `triple_aling()` - Three quick beeps
- `test_sequence()` - Full development test pattern
- `visual_ping()` - Console-only feedback (no sound)
- `counter_test()` - Simple counter increment with progress bar

### 📊 Test Patterns
1. **Quick Test** - 7 tests over 35 seconds (good for basic validation)
2. **Rapid Iteration** - 10 tests every 30 seconds (development workflow)
3. **Stress Test** - 20 tests every 3 seconds (performance testing)

## 🎵 Usage Examples

### Basic Testing
```bash
# Start handler
poetry run python tests/ding_aling_handler.py

# In another terminal, schedule quick tests
poetry run python tests/schedule_aling_tests.py
# Choose option 1 for quick test

# Check what's scheduled
poetry run python tests/check_aling_status.py
```

### Rapid Development Workflow
```bash
# Schedule tests every 30 seconds for continuous feedback
poetry run python tests/schedule_aling_tests.py
# Choose option 2 for rapid iteration

# Make code changes, tests will keep running automatically
# Check status anytime with:
poetry run python tests/check_aling_status.py
```

### API Usage
```python
import requests

# Schedule a quick aling
response = requests.post("http://127.0.0.1:8889/api/schedule", json={
    "handler_id": "ding-aling",
    "method": "quick_aling",
    "args": {"message": "API test"},
    "trigger_type": "date",
    "trigger_args": {"run_date": "2024-01-15T14:30:00"}
})
```

## 🔧 Configuration

- **Handler ID**: `ding-aling`
- **Port**: `4247` (unique port, won't conflict)
- **Server**: Connects to clock deployment (`127.0.0.1:4243`)
- **Logs**: Uses standard ScheduleZero logging with handler context

## 🎯 Perfect For

- ✅ **Rapid Prototyping** - Quick feedback on scheduling logic
- ✅ **API Testing** - Fast validation of REST endpoints  
- ✅ **Development Debugging** - Visual indicators help track execution
- ✅ **Integration Testing** - Lightweight tests that don't interfere with production
- ✅ **Demo Purposes** - Quick, visual demonstrations of ScheduleZero

## 🔄 Integration with Main Clock

The DingAling handler connects to the **same clock server** as the main DingDong handler, so:

- ✅ Shared scheduling infrastructure
- ✅ Same web UI shows both handlers  
- ✅ No conflicts (different ports)
- ✅ Can test scheduling logic without heavy chimes
- ✅ Perfect development companion to production clock

## 🎵 Sound Configuration

### Windows
Uses `winsound.Beep()` for quick, high-pitched beeps (500Hz, 100ms)

### Unix/Linux/Mac  
Uses terminal bell character (`\a`) with visual indicators

### Customization
Edit `_play_quick_sound()` method to:
- Play custom sound files
- Adjust beep frequency/duration
- Add different sound types
- Disable sound completely (visual-only mode)

## 📈 Performance

- **Startup**: < 1 second
- **Response Time**: ~10ms per aling
- **Memory Usage**: Minimal overhead
- **Sound Duration**: 100ms (vs 2-5 seconds for full chimes)

Perfect for rapid development where you need **fast feedback loops**! 🚀

## 🎯 Example Session

```bash
# Terminal 1: Start clock server
$ poetry run python governor.py start clock
✅ Clock server starting...

# Terminal 2: Start DingAling handler  
$ poetry run python tests/ding_aling_handler.py
🚀 DingAling Handler Starting!
🎵 DingAling handler is ready for rapid testing!

# Terminal 3: Schedule rapid tests
$ poetry run python tests/schedule_aling_tests.py
Select test pattern (1-4): 2
⚡ Scheduling rapid iteration tests...
✅ Test  1: quick_aling      at 14:30:05
✅ Test  2: double_aling     at 14:30:35
...

# Watch Terminal 2 for rapid feedback!
🔔 ALING! #1 [ding_aling_handler.py:67:quick_aling]
🎵 ALING-ALING! #2 [ding_aling_handler.py:89:double_aling]
```

**Happy rapid testing!** ⚡🎵