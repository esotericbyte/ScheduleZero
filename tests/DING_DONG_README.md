# 🔔 DingDong Handler - Clock Chimes for ScheduleZero

A fun and practical handler that plays clock chimes on a schedule!

## What It Does

- **Hour Bongs**: Plays deep "BONG" sounds on the hour (24-hour format)
  - Midnight (00:00) = 24 bongs! 🎉
  - 1:00 AM/PM = 1 bong
  - 13:00 (1 PM) = 13 bongs
  - etc.

- **Quarter Chimes**: Plays musical Westminster-style chimes at:
  - :15 minutes (1 quarter)
  - :30 minutes (2 quarters)
  - :45 minutes (3 quarters)

## Modes

The handler supports **two modes** so you can run both simultaneously!

### TEST Mode (Default)
- Handler ID: `ding-dong-test`
- Port: 4246
- Log dir: `ding_dong_logs_test/`
- Use: Development and testing
- Start: `poetry run python tests/ding_dong_handler.py`

### DEPLOYMENT Mode
- Handler ID: `ding-dong-handler`
- Port: 4245
- Log dir: `ding_dong_logs/`
- Use: Long-term production clock
- Start: `$env:DING_DONG_DEPLOY='true'; poetry run python tests/ding_dong_handler.py`

**You can run BOTH at the same time!** They use different ports and handler IDs.

## Why This Is Awesome

1. **Long-term testing**: Schedules 2 full days of events (192 total!)
2. **UTC time handling**: All schedules are in UTC (tests timezone handling)
3. **Audio feedback**: Actually hear when jobs execute!
4. **Comprehensive logging**: Every chime is logged with UTC and local times
5. **Fun**: Your computer becomes a clock tower! 🏰

## Quick Start

### 1. Make sure the server is running:
```powershell
poetry run python -m schedule_zero.server
```

### 2. Start the DingDongHandler (choose mode):

**TEST MODE (development):**
```powershell
poetry run python tests/ding_dong_handler.py
```

**DEPLOYMENT MODE (long-term clock):**
```powershell
$env:DING_DONG_DEPLOY='true'
poetry run python tests/ding_dong_handler.py
```

### 3. Schedule 2 days of chimes (match the mode):

**TEST MODE:**
```powershell
poetry run python tests/schedule_ding_dongs.py
```

**DEPLOYMENT MODE:**
```powershell
$env:DING_DONG_DEPLOY='true'
poetry run python tests/schedule_ding_dongs.py
```

### 4. Check status anytime:

**TEST MODE:**
```powershell
poetry run python tests/check_ding_dongs.py
```

**DEPLOYMENT MODE:**
```powershell
$env:DING_DONG_DEPLOY='true'
poetry run python tests/check_ding_dongs.py
```

## Checking Status

### Quick status check:
```powershell
poetry run python tests/check_ding_dongs.py
```

Shows:
- Handler registration status
- Number of schedules (total and by type)
- Next 3 upcoming chimes
- Chime log summary (how many bongs/chimes have played)
- Last 5 chime events

### View the chime log directly:
```powershell
# Test mode:
cat tests/ding_dong_logs_test/chime_log.txt

# Deploy mode:
cat tests/ding_dong_logs/chime_log.txt
```

### View scheduled jobs via API:
```powershell
curl http://127.0.0.1:8888/api/schedules
```

### Count schedules:
```powershell
(curl http://127.0.0.1:8888/api/schedules | ConvertFrom-Json).schedules.Count
```

## Handler Methods

### `play_hour_bongs`
- Params: `{"hour": 13}` (optional, defaults to current UTC hour)
- Plays N bongs where N = hour (or 24 for midnight)

### `play_quarter_chime`
- Params: `{"quarter": 1}` (1=:15, 2=:30, 3=:45)
- Plays Westminster Quarters melody

### `get_chime_log`
- Returns the full chime log with timestamps

### `clear_log`
- Clears the chime log

## Technical Details

- Uses `winsound` on Windows for audio (falls back to silent logging if unavailable)
- All schedules use Unix timestamps for precise UTC timing
- Each event has a unique `job_id` like `bong_20251028_1300` or `chime_20251028_1315_q1`
- Demonstrates APScheduler's date trigger with hundreds of scheduled events

## What You'll Learn

This handler demonstrates:
- ✅ Long-term job scheduling (2 days)
- ✅ High-volume scheduling (192 events)
- ✅ UTC timestamp handling
- ✅ Date trigger usage
- ✅ Handler method parameters
- ✅ Logging and monitoring
- ✅ Real-time feedback (audio!)

## Have Fun! 🎵

Enjoy your clock chimes and know that ScheduleZero is working perfectly! 🔔
