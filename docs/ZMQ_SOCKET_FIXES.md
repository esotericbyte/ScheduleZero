# ZMQ Socket State Management Fixes

## Problem Summary
ZeroMQ REQ/REP sockets have strict state machine requirements. After a timeout or error, the socket enters an invalid state and cannot send/receive until properly recovered.

## Issues Fixed

### 1. Socket Not Reconnecting After Errors
**Problem**: After `zmq.EAGAIN` (timeout) or other errors, code only called `close()` but never reconnected.

**Root Cause**: REQ sockets require full close + reconnect to reset state machine.

**Fix**: Added `_recreate_socket()` method that:
- Closes socket with `linger=0` to discard pending messages
- Sets `_connected = False`
- Calls `connect()` to create new socket and reconnect
- Logs the recreation for debugging

### 2. Improved Error Handling in `call()` Method
**Changes**:
- Added `auto_reconnect` parameter (default: `True`)
- Catch `zmq.ZMQError` and check for `EFSM` (Finite State Machine error)
- Call `_recreate_socket()` instead of just `close()` after all errors
- Retry once after socket recreation for EFSM errors
- Better logging of error conditions

### 3. Context Termination
**Problem**: ZMQ contexts were created per-client but never properly terminated, causing resource leaks.

**Fix**: Added `terminate()` method and context manager support:
```python
def terminate(self):
    """Close socket and terminate ZMQ context."""
    self.close()
    if self.context:
        self.context.term()

# Context manager support
with ZMQClient(address) as client:
    client.ping()
# Automatically terminates on exit
```

### 4. Registry Manager Updates
**Changes**:
- Updated `get_client()` to call `terminate()` instead of `close()` when removing invalid clients
- Updated `_safe_close_client()` to use `terminate()` for full cleanup
- Ensures contexts are properly cleaned up when clients are recreated

## Testing
Run `test_zmq_recovery.py` to verify socket recovery works:
```powershell
poetry run python test_zmq_recovery.py
```

This test:
1. Connects to a handler
2. Makes successful ping
3. Forcibly closes socket (simulating error)
4. Attempts another call (should auto-recover)
5. Verifies recovery worked

## Impact
- **Reliability**: Socket errors automatically recovered without manual intervention
- **Performance**: No more hanging on socket state errors
- **Resource Management**: Proper ZMQ context cleanup prevents leaks
- **Testing**: Tests should no longer hang due to socket state issues

## Next Steps
1. Test with DingAling handler to verify fixes work in practice
2. Consider sharing ZMQ context across multiple clients (optimization)
3. Add metrics for socket recreation events (monitoring)
