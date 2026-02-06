#!/usr/bin/env bash
# Start ScheduleZero Server with PID Management

set -e

DEPLOYMENT="${1:-default}"

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/deployments/$DEPLOYMENT/pids"
SERVER_PID_FILE="$PID_DIR/server.pid"

# Ensure PID directory exists
mkdir -p "$PID_DIR"

# Check if server is already running
if [ -f "$SERVER_PID_FILE" ]; then
    OLD_PID=$(cat "$SERVER_PID_FILE" | tr -d '[:space:]')
    
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✓ Server already running (PID: $OLD_PID)"
        echo "  Web: http://127.0.0.1:8888"
        echo "  ZMQ: tcp://127.0.0.1:4242"
        exit 0
    else
        # Process not running, clean up stale PID file
        rm -f "$SERVER_PID_FILE"
        echo "⚠ Cleaned up stale PID file"
    fi
fi

# Set deployment environment variable
export SCHEDULEZERO_DEPLOYMENT="$DEPLOYMENT"

echo "➜ Starting ScheduleZero Server (Deployment: $DEPLOYMENT)"

# Start server in background
cd "$ROOT_DIR"
nohup poetry run python -m schedule_zero.tornado_app_server > "deployments/$DEPLOYMENT/server.log" 2>&1 &
SERVER_PID=$!

# Save PID
echo "$SERVER_PID" > "$SERVER_PID_FILE"

# Wait a moment and verify it started
sleep 2
if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "✓ Server started (PID: $SERVER_PID)"
    echo "  Web: http://127.0.0.1:8888"
    echo "  ZMQ: tcp://127.0.0.1:4242"
    echo "  Log: deployments/$DEPLOYMENT/server.log"
    echo "  PID: deployments/$DEPLOYMENT/pids/server.pid"
else
    echo "✗ Server failed to start"
    rm -f "$SERVER_PID_FILE"
    exit 1
fi
