# Security & Network Architecture for ScheduleZero

## 🔒 Authentication & Authorization Strategy

### Current State (Alpha)
- ❌ **No authentication** - Open API endpoints
- ❌ **No authorization** - All users have full access
- ⚠️ **Security Warning**: Current implementation is **NOT production-ready**

### Planned Implementation (Required for Demo/Production)

#### Phase 1: Basic Authentication (Essential for Demo)
```python
# JWT-based authentication for API
- POST /api/auth/login → Returns JWT token
- All other endpoints require valid JWT in Authorization header
- Token refresh mechanism
```

**Priority Features:**
1. **API Key Authentication** for handlers
   - Each handler gets unique API key on registration
   - Server validates handler identity via key
   - Revocable keys stored in database

2. **Web UI Authentication** 
   - Username/password login
   - Session management
   - Optional OAuth2 (GitHub, Google)

3. **Role-Based Access Control (RBAC)**
   - **Admin**: Full access (create/delete schedules, manage handlers)
   - **Operator**: View schedules, trigger jobs, view logs
   - **Viewer**: Read-only access to dashboard and logs

#### Phase 2: Authorization & Hardening
1. **Handler Authorization**
   - Handlers can only execute jobs assigned to them
   - Method-level permissions (which methods can be called)
   - Handler groups/namespaces for multi-tenancy

2. **Schedule Authorization**
   - Users can only modify their own schedules
   - Admins can manage all schedules
   - Audit log for all schedule changes

3. **API Rate Limiting**
   ```python
   # Per-user rate limits
   - 100 requests/minute for authenticated users
   - 10 requests/minute for unauthenticated (health checks only)
   ```

4. **Input Validation & Sanitization**
   - Validate all job parameters
   - Prevent code injection in schedule definitions
   - Limit job parameter size (prevent DOS)

#### Phase 3: Advanced Security (Production)
1. **TLS/SSL for all connections**
   - HTTPS for Tornado web server
   - ZMQ with CurveZMQ encryption
   
2. **Secrets Management**
   - Integration with HashiCorp Vault or AWS Secrets Manager
   - Never store credentials in job parameters
   - Secure credential injection at runtime

3. **Audit Logging**
   - Log all authentication attempts
   - Log all API calls with user/handler identity
   - Log all schedule modifications
   - Exportable to SIEM systems

4. **Security Headers**
   ```python
   # Tornado security headers
   Content-Security-Policy
   X-Frame-Options: DENY
   X-Content-Type-Options: nosniff
   Strict-Transport-Security
   ```

## 🌐 ZMQ Network Architecture & NAT Traversal

### Current Architecture
```
Server (ZMQ REP socket)
  ↑
  | Direct TCP connection
  | tcp://server:4242
  ↓
Handler (ZMQ REQ socket)
```

**Limitation**: Handlers must have direct network access to server
- ❌ Doesn't work across NAT boundaries
- ❌ Handlers can't connect from behind firewalls
- ❌ No built-in NAT traversal ("hole punching")

### ZMQ Routing Patterns for Distributed Deployments

#### Option 1: ROUTER/DEALER Pattern (Recommended for Multiple Handlers)
```python
# Server uses ROUTER socket
# Handlers use DEALER sockets
# Advantages:
# - Asynchronous bidirectional communication
# - Server can track handler identities
# - Handlers can reconnect with same identity
# - Better for unreliable networks

Server (ROUTER) ←→ Handler1 (DEALER)
                ←→ Handler2 (DEALER)
                ←→ Handler3 (DEALER)
```

**Implementation:**
```python
# server.py
import zmq

context = zmq.Context()
router = context.socket(zmq.ROUTER)
router.bind("tcp://*:4242")

while True:
    # Receive: [handler_id, empty, message]
    identity, empty, msg = router.recv_multipart()
    
    # Process message
    response = process_job(msg)
    
    # Send back to specific handler
    router.send_multipart([identity, b"", response])
```

```python
# handler.py
import zmq
import uuid

context = zmq.Context()
dealer = context.socket(zmq.DEALER)
dealer.setsockopt_string(zmq.IDENTITY, f"handler-{uuid.uuid4()}")
dealer.connect("tcp://server:4242")

# Send/receive messages
dealer.send(b"register")
response = dealer.recv()
```

#### Option 2: NAT Traversal with ZMQ Proxy Pattern
```
Internet Handlers
        ↓
    [NAT/Firewall]
        ↓
   ZMQ Proxy (DMZ)
        ↓
  Internal Server
```

**Implementation:**
```python
# proxy.py (runs in DMZ or cloud)
import zmq

context = zmq.Context()

# Frontend: Handlers connect here
frontend = context.socket(zmq.ROUTER)
frontend.bind("tcp://*:5555")

# Backend: Server connects here
backend = context.socket(zmq.DEALER)
backend.bind("tcp://*:5556")

# Proxy messages bidirectionally
zmq.proxy(frontend, backend)
```

#### Option 3: WebSocket + ZMQ Bridge (NAT-Friendly)
```
Handlers (behind NAT)
    ↓ (WebSocket outbound)
WebSocket Server
    ↓ (ZMQ internal)
ScheduleZero Server
```

**Advantages:**
- WebSocket works through most firewalls
- Handlers initiate connection (no inbound ports needed)
- Compatible with corporate networks
- Can add authentication at WebSocket layer

**Implementation:**
```python
# ws_bridge.py
import asyncio
import zmq.asyncio
from tornado import web, websocket

class HandlerWebSocket(websocket.WebSocketHandler):
    def initialize(self, zmq_socket):
        self.zmq = zmq_socket
        
    async def on_message(self, message):
        # Forward to ZMQ
        await self.zmq.send(message)
        response = await self.zmq.recv()
        # Send back via WebSocket
        await self.write_message(response)
```

#### Option 4: Reverse Tunnel Pattern (Advanced)
```
Server exposes public endpoint
    ↓
Handler creates reverse tunnel
    ↓
Server sends jobs through tunnel
```

**Use Case**: Handlers behind strict firewalls
- Handler establishes long-lived connection to server
- Server sends jobs over this connection
- Similar to SSH reverse tunnel

### Recommended Deployment Patterns

#### Pattern 1: Simple (Same Network)
- **Use**: Development, single datacenter
- **Pattern**: REQ/REP or ROUTER/DEALER
- **Security**: Private network, API keys
```
[Server:4242] ←→ [Handler1, Handler2, Handler3]
```

#### Pattern 2: Cloud with VPN (Recommended)
- **Use**: Distributed handlers, production
- **Pattern**: ROUTER/DEALER with VPN mesh
- **Security**: VPN + TLS + API keys
```
[Server in Cloud] ←→ [VPN Gateway] ←→ [Handlers in offices]
```

#### Pattern 3: Public Internet (Highest Security)
- **Use**: Handlers from anywhere
- **Pattern**: WebSocket bridge or ZMQ with CurveZMQ
- **Security**: TLS + CurveZMQ encryption + JWT authentication
```
[Server + WS Bridge] ←← [Handlers connect outbound through NAT]
```

## 🎯 Implementation Roadmap

### Phase 1: Essential for Demo (2-3 weeks)
- [ ] JWT authentication for API endpoints
- [ ] Handler API key system
- [ ] Basic RBAC (admin/operator/viewer)
- [ ] Rate limiting on API endpoints
- [ ] Input validation for job parameters
- [ ] Security headers in Tornado responses

### Phase 2: Production-Ready (4-6 weeks)
- [ ] HTTPS support with Let's Encrypt
- [ ] ZMQ CurveZMQ encryption
- [ ] Audit logging system
- [ ] Secrets management integration
- [ ] ROUTER/DEALER pattern for handlers
- [ ] WebSocket bridge option

### Phase 3: Enterprise Features (8+ weeks)
- [ ] OAuth2/OIDC integration
- [ ] Multi-tenancy support
- [ ] Advanced audit logging (export to SIEM)
- [ ] Fine-grained permissions system
- [ ] Network policy enforcement
- [ ] VPN/reverse tunnel options

## 📚 Resources

### ZMQ Patterns
- [ZMQ Guide - Advanced Request-Reply](http://zguide.zeromq.org/page:all#advanced-request-reply)
- [ZMQ Guide - Security](http://zguide.zeromq.org/page:all#Security)
- [CurveZMQ Authentication](https://rfc.zeromq.org/spec/26/)

### Authentication Libraries
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT for Python
- [Tornado authentication](https://www.tornadoweb.org/en/stable/auth.html)
- [python-social-auth](https://python-social-auth.readthedocs.io/) - OAuth

### Security Best Practices
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)
