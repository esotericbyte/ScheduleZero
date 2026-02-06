#!/usr/bin/env bash
# Stop ScheduleZero Server using PID file

set -e

DEPLOYMENT="${1:-default}"
FORCE="${2:-}"

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/deployments/$DEPLOYMENT/pids"
SERVER_PID_FILE="$PID_DIR/server.pid"

# Check if PID file exists
if [ ! -f "$SERVER_PID_FILE" ]; then
    echo "✓ Server not running (no PID file)"
    exit 0
fi

# Read PID
PID=$(cat "$SERVER_PID_FILE" | tr -d '[:space:]')

echo "➜ Stopping ScheduleZero Server (Deployment: $DEPLOYMENT, PID: $PID)"

# Check if process exists
if ! kill -0 "$PID" 2>/dev/null; then
    echo "✓ Process not running (cleaning up stale PID file)"
    rm -f "$SERVER_PID_FILE"
    exit 0
fi

# Get process name
if command -v ps >/dev/null 2>&1; then
    PROC_NAME=$(ps -p "$PID" -o comm= 2>/dev/null || echo "unknown")
    echo "Process: $PROC_NAME (PID: $PID)"
fi

# Ask for confirmation unless --force
if [ "$FORCE" != "--force" ]; then
    read -p "Stop this process? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# Try graceful shutdown first (SIGTERM)
echo "Sending SIGTERM..."
kill "$PID" 2>/dev/null || true

# Wait for process to stop (max 10 seconds)
for i in {1..10}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "✓ Server stopped gracefully"
        rm -f "$SERVER_PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "⚠ Graceful shutdown timeout, forcing..."
kill -9 "$PID" 2>/dev/null || true
sleep 1

if ! kill -0 "$PID" 2>/dev/null; then
    echo "✓ Server stopped (forced)"
    rm -f "$SERVER_PID_FILE"
    exit 0
else
    echo "✗ Failed to stop server"
    exit 1
fi
