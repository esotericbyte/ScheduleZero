# Handler Port 0 Binding (OS-Assigned Ports)

## What Changed

Handlers now use **port 0 binding**, letting the OS automatically assign available ports instead of hardcoding them.

## Before (Port Conflicts)

```python
# Handler configuration
handler_address = "tcp://127.0.0.1:5000"

# Binding
socket.bind("tcp://127.0.0.1:5000")  # FAIL if port taken!

# Multiple handlers
Handler A: 5000 ✓
Handler B: 5000 ✗ CRASH (address in use)
```

**Problems:**
- ❌ Handlers crash if port already used
- ❌ Must manually coordinate ports
- ❌ Can't start multiple handlers simultaneously
- ❌ Brittle during development/testing

## After (OS-Assigned Ports)

```python
# Handler configuration (hint only)
handler_address = "tcp://127.0.0.1:5000"  # Port ignored

# Binding
socket.bind("tcp://127.0.0.1:0")  # OS assigns available port
actual_address = socket.getsockopt_string(zmq.LAST_ENDPOINT)
# → "tcp://127.0.0.1:54321"

# Multiple handlers
Handler A: 54321 ✓
Handler B: 54322 ✓
Handler C: 54323 ✓
Handler D: 54324 ✓
```

**Benefits:**
- ✅ Zero port conflicts
- ✅ Zero configuration needed
- ✅ Parallel handler startup works
- ✅ Robust in all environments

## Implementation Details

### ZMQHandlerBase Changes

**File:** `src/schedule_zero/zmq_handler_base.py`

1. **Constructor:**
   - `handler_address` parameter is now a "hint" (for host extraction)
   - `self.handler_address` is set to `None` initially
   - Actual address determined after binding

2. **Server Binding:**
   ```python
   # Extract host from hint
   host = self.handler_address_hint.split("://")[1].split(":")[0]
   
   # Bind to port 0 (OS chooses)
   socket.bind(f"tcp://{host}:0")
   
   # Get actual bound address
   self.handler_address = socket.getsockopt_string(zmq.LAST_ENDPOINT)
   ```

3. **Registration:**
   - Registration thread waits for `self.handler_address` to be set
   - Registers with the actual OS-assigned address
   - ScheduleZero learns real address from registration

## Compatibility

### Backward Compatible ✅

Existing handler code continues to work:

```python
# Old code (still works)
handler = MyHandler(
    handler_id="my_handler",
    handler_address="tcp://127.0.0.1:5000",  # Port ignored now
    server_address="tcp://127.0.0.1:4242"
)
```

The port in `handler_address` is now ignored (except for host extraction). The OS assigns the actual port.

### Config Files

**Before:**
```yaml
handler_id: my-handler
handler_port: 5000  # Must be unique per handler
server_address: tcp://127.0.0.1:4242
```

**After:**
```yaml
handler_id: my-handler
handler_host: 127.0.0.1  # Only host matters
server_address: tcp://127.0.0.1:4242
# Port is auto-assigned by OS
```

You can still specify a port in config for compatibility, but it will be ignored.

## Testing

### Test: Multiple Handlers No Conflicts

**File:** `tests/test_port_zero_binding.py`

```bash
poetry run python tests/test_port_zero_binding.py
```

**Result:**
```
✓ All 5 handlers bound successfully
✓ All handlers got unique ports: 51438, 51445, 51452, 51459, 51466
✓ All ports in valid ephemeral range (>1024)
```

## Debugging

### Finding Handler Ports

**Option 1: Check Registry**
```bash
curl http://localhost:8888/api/handlers
```

```json
{
  "handlers": [
    {
      "handler_id": "my-handler",
      "address": "tcp://127.0.0.1:54321",
      "methods": ["do_work", "send_message"]
    }
  ]
}
```

**Option 2: Check Logs**
```
Handler server listening - address=tcp://127.0.0.1:54321 note=OS-assigned port
```

**Option 3: Registry File**
```yaml
# deployments/default/handler_registry.yaml
my-handler:
  address: tcp://127.0.0.1:54321
  methods:
    - do_work
    - send_message
```

## Security Note

This change doesn't add security, but it enables future security improvements:

**Current:** Handlers bind to predictable ports (5000, 5001, etc.)
- Anyone can predict and connect to handler ports
- Port scanning finds handlers easily

**With Port 0:** Handlers bind to random high ports (50000-60000 range)
- Harder to guess handler ports
- Still need authentication (future work)

## Migration Guide

### For Handler Developers

**No changes required!** Your existing handler code works as-is.

If you're explicitly binding to ports in custom code, update to:

```python
# Before
socket.bind("tcp://127.0.0.1:5000")

# After
socket.bind("tcp://127.0.0.1:0")
actual_address = socket.getsockopt_string(zmq.LAST_ENDPOINT)
# Use actual_address for registration
```

### For Handler Users

**No changes required!** Just start handlers as before. They'll automatically get unique ports.

### For Tests

Tests that hardcode handler ports should be updated:

```python
# Before
TEST_HANDLER_PORT = 4244

# After - Don't hardcode, let OS assign
# Query the handler's actual address from registry after startup
```

## Performance

**No performance impact:**
- Port assignment is instantaneous (< 1ms)
- Registration happens once at startup
- No retry/scanning logic needed

## Limitations

### Port Ranges

OS assigns ports from the ephemeral port range:
- **Linux:** 32768-60999 (default)
- **Windows:** 49152-65535 (default)
- **macOS:** 49152-65535 (default)

If you need handlers on specific ports (e.g., firewall rules), you'll need to:
1. Configure firewall for ephemeral range, OR
2. Manually bind handlers to specific ports (not recommended)

### Predictability

You can no longer predict which port a handler will use. This is usually fine, but if you need predictable ports:

**Workaround:** Query the registry after handler starts to learn its port.

## Future Enhancements

1. **Port Range Configuration:** Allow limiting ephemeral range
2. **Port Reservation:** ScheduleZero assigns ports from a pool
3. **Named Handlers:** Connect by handler_id instead of address
4. **Health Monitoring:** Track which handlers are on which ports

## Related Issues

This change solves:
- ✅ Port conflicts during handler startup
- ✅ Test flakiness from port reuse
- ✅ Manual port coordination
- ✅ Multi-deployment port isolation

## See Also

- [ZMQHandlerBase Documentation](../src/schedule_zero/zmq_handler_base.py)
- [Port 0 Binding Test](../tests/test_port_zero_binding.py)
- [Handler Registry API](./HANDLER_REGISTRY.md)
