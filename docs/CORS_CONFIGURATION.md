# CORS Configuration for ScheduleZero Portal

## Critical Importance

**CORS (Cross-Origin Resource Sharing) is ABSOLUTELY ESSENTIAL for the portal framework to function.**

Without proper CORS headers, the entire HTMX + Web Components architecture will fail silently in browsers. This is especially critical because:

1. **Each protocol/port is a different origin**: `http://localhost:8888` vs `http://localhost:3000` are different origins
2. **HTMX requires specific headers**: Both request headers it sends AND response headers we return
3. **Web Components fetch configuration**: Custom elements need to access `/api/portal/config`
4. **Silent failures**: Browsers block CORS violations without obvious errors (check console)

## What is CORS?

When a web page from `origin A` makes a request to `origin B`, the browser enforces CORS:
- **Origin = Protocol + Domain + Port**: `https://example.com:443`
- **Same-Origin**: All three match
- **Cross-Origin**: Any one differs

Examples:
```
http://localhost:8888  →  http://localhost:8888/api/config    ✅ Same-origin
http://localhost:3000  →  http://localhost:8888/api/config    ❌ Cross-origin (different port)
https://example.com    →  http://example.com/api              ❌ Cross-origin (different protocol)
```

## CORS Flow

1. **Preflight Request** (for complex requests):
   - Browser sends `OPTIONS` request first
   - Server must respond with allowed methods/headers
   - Status: 204 No Content

2. **Actual Request**:
   - Browser sends real request with `Origin` header
   - Server responds with `Access-Control-Allow-Origin`
   - Browser checks if origin is allowed

3. **Response Header Access**:
   - Browser blocks access to response headers by default
   - Server must explicitly expose headers via `Access-Control-Expose-Headers`

## HTMX-Specific Requirements

### Headers HTMX Sends (Must Allow)
```
HX-Request: true                    // Indicates HTMX request
HX-Trigger: element-id              // Which element triggered request
HX-Target: target-id                // Target element for swap
HX-Current-URL: /current/path       // Current page URL
HX-Prompt: user-input               // User input from hx-prompt
```

### Headers We Send Back (Must Expose)
```
HX-Trigger: eventName               // Trigger client-side event
HX-Redirect: /new/url               // Client-side redirect
HX-Refresh: true                    // Force page reload
HX-Push-Url: /new/path              // Update browser URL
HX-Retarget: #new-target            // Change swap target
HX-Reswap: innerHTML                // Change swap method
```

## Implementation in ScheduleZero

### 1. BaseAPIHandler (JSON APIs)

**File**: `src/schedule_zero/api/tornado_base_handlers.py`

```python
def set_default_headers(self):
    """Set comprehensive CORS headers for API and HTMX support."""
    self.set_header("Content-Type", "application/json")
    
    # Allow all origins (adjust for production)
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
    
    # CRITICAL: Allow HTMX headers that client sends
    self.set_header("Access-Control-Allow-Headers", 
                   "Content-Type, HX-Request, HX-Trigger, HX-Target, HX-Current-URL, HX-Prompt")
    
    # CRITICAL: Expose HTMX headers that we send back
    self.set_header("Access-Control-Expose-Headers",
                   "HX-Trigger, HX-Redirect, HX-Refresh, HX-Push-Url, HX-Retarget, HX-Reswap")

def options(self, *args, **kwargs):
    """Handle CORS preflight requests."""
    self.set_status(204)
    self.finish()
```

**All API handlers extend this**: Automatic CORS support for all JSON endpoints.

### 2. PortalConfigHandler

**File**: `src/schedule_zero/api/portal_config_api.py`

```python
class PortalConfigHandler(BaseAPIHandler):
    """Extends BaseAPIHandler for proper CORS."""
```

This is **CRITICAL** - the `sz-nav` web component fetches `/api/portal/config` on load. Without CORS, navigation breaks.

### 3. MicrositeHandler (HTML Pages)

**File**: `src/schedule_zero/microsites/base.py`

For **same-origin** setups (frontend and backend on same host/port), CORS is not required for HTML.

For **cross-origin** setups (Vite dev server on :3000, Python on :8888):

```python
def set_default_headers(self):
    # Uncomment if serving from different origin:
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.set_header("Access-Control-Allow-Headers", 
                   "Content-Type, HX-Request, HX-Trigger, HX-Target, HX-Current-URL")
```

## Production Security

**Development**: `Access-Control-Allow-Origin: *` is fine for testing.

**Production**: Restrict to specific origins:

```python
def set_default_headers(self):
    allowed_origins = [
        "https://schedulezero.example.com",
        "https://portal.example.com"
    ]
    origin = self.request.headers.get("Origin")
    if origin in allowed_origins:
        self.set_header("Access-Control-Allow-Origin", origin)
    
    # Rest of headers...
```

Or use environment variable:

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
```

## Debugging CORS Issues

### Browser Console Errors

**Symptom**: Red CORS errors in browser console:
```
Access to fetch at 'http://localhost:8888/api/portal/config' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
```

**Fix**: Ensure `BaseAPIHandler.set_default_headers()` is called.

### Silent Failures

**Symptom**: HTMX requests succeed but no content swaps.

**Cause**: Missing `Access-Control-Expose-Headers` - browser blocks access to `HX-Trigger` etc.

**Fix**: Add expose headers for HTMX response headers.

### Preflight Failures

**Symptom**: `OPTIONS` request fails with 405 Method Not Allowed.

**Cause**: Handler doesn't implement `options()` method.

**Fix**: Extend `BaseAPIHandler` which includes `options()`.

### Browser Developer Tools

1. **Network Tab**: 
   - Look for `OPTIONS` preflight requests
   - Check response headers include `Access-Control-Allow-*`
   
2. **Console Tab**:
   - Look for red CORS errors
   - Check for blocked header access warnings

3. **Application Tab** → **Storage**:
   - Ensure cookies/localStorage work cross-origin if needed

## Testing CORS

### 1. Same-Origin (Production Setup)
```bash
# Start server
poetry run python -m schedule_zero.server

# Visit http://localhost:8888
# Everything should work - no CORS needed
```

### 2. Cross-Origin (Development Setup)
```bash
# Terminal 1: Start Python backend
poetry run python -m schedule_zero.server
# → Listening on http://localhost:8888

# Terminal 2: Start Vite dev server
cd ../schedulezero-islands
npm run dev
# → Listening on http://localhost:3000

# Visit http://localhost:3000
# HTMX requests to :8888 require CORS
```

### 3. Manual Testing
```bash
# Test preflight
curl -X OPTIONS http://localhost:8888/api/portal/config \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: HX-Request" \
  -v

# Should return:
# HTTP/1.1 204 No Content
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
# Access-Control-Allow-Headers: Content-Type, HX-Request, ...

# Test actual request
curl http://localhost:8888/api/portal/config \
  -H "Origin: http://localhost:3000" \
  -H "HX-Request: true" \
  -v

# Should return:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: *
# Access-Control-Expose-Headers: HX-Trigger, HX-Redirect, ...
# Content-Type: application/json
```

## Summary

✅ **BaseAPIHandler**: Comprehensive CORS for all JSON APIs  
✅ **PortalConfigHandler**: Extends BaseAPIHandler (automatic CORS)  
✅ **HTMX Headers**: Both request and response headers configured  
✅ **Preflight**: `OPTIONS` method handled  
✅ **Expose Headers**: Response headers accessible to JavaScript  

**This CORS configuration is ESSENTIAL for portal framework functionality.**

Without it:
- ❌ sz-nav cannot fetch portal config
- ❌ HTMX navigation breaks
- ❌ Web components cannot communicate with backend
- ❌ API calls from frontend fail silently

**Include this CORS setup in any portal starter template or framework scaffolding.**
