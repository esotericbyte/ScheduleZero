# WAF Setup for ScheduleZero

## Why You Need a WAF

**EVERY internet-facing API needs a Web Application Firewall.**

A WAF protects against:
- SQL injection
- Cross-site scripting (XSS)
- Path traversal
- Command injection
- OWASP Top 10 vulnerabilities
- DDoS attacks (basic rate limiting)
- Malformed requests
- Scanner/bot traffic

## Recommended Stack

### Development (localhost only)
```
Tornado on localhost:8888 (no WAF needed)
```

### Production (internet-facing)
```
Internet → Cloudflare (DDoS protection + TLS termination)
        ↓
        NGINX + ModSecurity + OWASP CRS (WAF)
        ↓
        Keycloak (OAuth2/JWT authentication)
        ↓
        Tornado (localhost:8888 only, not exposed)
```

## ModSecurity + NGINX (Open Source WAF)

### Components
- **NGINX**: Reverse proxy
- **ModSecurity 3.x**: WAF engine
- **OWASP CRS**: Core Rule Set (attack signatures)

### Docker Compose Setup

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  # WAF: NGINX + ModSecurity + OWASP CRS
  waf:
    image: owasp/modsecurity-crs:nginx
    container_name: schedulezero-waf
    ports:
      - "80:80"
      - "443:443"
    environment:
      # Backend: Tornado app server
      BACKEND: http://tornado:8888
      
      # ModSecurity engine mode
      MODSEC_RULE_ENGINE: "On"
      
      # Paranoia level (1-4, higher = stricter)
      PARANOIA: "1"
      
      # Anomaly scoring thresholds
      ANOMALY_INBOUND: "5"
      ANOMALY_OUTBOUND: "4"
      
      # Allowed HTTP methods
      ALLOWED_METHODS: "GET POST PUT DELETE"
      
      # Max request body size (10MB)
      MAX_REQUEST_BODY_SIZE: "10485760"
      
      # Rate limiting (100 req/min per IP)
      RATE_LIMIT: "100"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/waf:/var/log/nginx
    depends_on:
      - tornado
    restart: unless-stopped

  # OAuth/JWT: Keycloak
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: schedulezero-keycloak
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: change_me_in_production
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: change_me_in_production
      KC_HOSTNAME: auth.yourdomain.com
    command: start-dev
    expose:
      - "8080"
    depends_on:
      - postgres
    restart: unless-stopped

  # Application: Tornado + ScheduleZero
  tornado:
    build: .
    container_name: schedulezero-tornado
    expose:
      - "8888"  # NOT exposed to internet, only to WAF
    environment:
      DEPLOYMENT: production
      JWT_ISSUER: http://keycloak:8080/realms/schedulezero
      JWT_AUDIENCE: schedulezero-api
    volumes:
      - ./deployments/production:/app/deployments/production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Database: PostgreSQL
  postgres:
    image: postgres:16
    container_name: schedulezero-postgres
    environment:
      POSTGRES_DB: schedulezero
      POSTGRES_USER: schedulezero
      POSTGRES_PASSWORD: change_me_in_production
    volumes:
      - postgres_data:/var/lib/postgresql/data
    expose:
      - "5432"
    restart: unless-stopped

  # Cache/Queue: Redis
  redis:
    image: redis:7-alpine
    container_name: schedulezero-redis
    expose:
      - "6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### NGINX Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    # Rate limiting zone (100 req/min per IP)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    
    # Connection limiting (max 10 concurrent per IP)
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
    
    upstream tornado_backend {
        server tornado:8888;
    }
    
    server {
        listen 80;
        server_name api.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;
        
        # TLS configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        # ModSecurity enabled
        modsecurity on;
        modsecurity_rules_file /etc/modsecurity.d/owasp-crs/crs-setup.conf;
        
        # Security headers
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000" always;
        
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 10;
        
        # Max request size
        client_max_body_size 10M;
        
        # Proxy to Tornado
        location / {
            proxy_pass http://tornado_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # WebSocket support (for live updates)
        location /ws {
            proxy_pass http://tornado_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## Keycloak Setup

### 1. Access Admin Console
```
http://localhost:8080/admin
Username: admin
Password: (from KEYCLOAK_ADMIN_PASSWORD)
```

### 2. Create Realm
- Name: `schedulezero`
- Enabled: `On`

### 3. Create Client
- Client ID: `schedulezero-api`
- Client Protocol: `openid-connect`
- Access Type: `bearer-only` (for API)
- Valid Redirect URIs: `https://api.yourdomain.com/*`

### 4. Configure Token Settings
- Access Token Lifespan: `5 minutes`
- Refresh Token Lifespan: `30 minutes`
- Include user roles in token: `On`

### 5. Add Custom Claims (Guild IDs)
- Create mapper: `guild_ids`
- Mapper Type: `User Attribute`
- User Attribute: `guild_ids`
- Token Claim Name: `guild_ids`
- Claim JSON Type: `JSON`

## Tornado JWT Validation

```python
# src/schedule_zero/auth/jwt_validator.py
import os
import jwt
from typing import Optional, List
from tornado.web import HTTPError

class JWTValidator:
    def __init__(self):
        self.issuer = os.getenv("JWT_ISSUER")
        self.audience = os.getenv("JWT_AUDIENCE")
        # In production, fetch from Keycloak JWKS endpoint
        self.public_key = self._fetch_public_key()
    
    def _fetch_public_key(self) -> str:
        """Fetch public key from Keycloak JWKS endpoint"""
        import requests
        jwks_url = f"{self.issuer}/protocol/openid-connect/certs"
        # Implementation: Parse JWKS, extract public key
        # TODO: Cache with TTL, handle key rotation
        pass
    
    def validate_token(self, token: str) -> dict:
        """Validate JWT and return claims"""
        try:
            claims = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer
            )
            return claims
        except jwt.ExpiredSignatureError:
            raise HTTPError(401, "Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPError(401, f"Invalid token: {e}")
    
    def extract_guild_ids(self, claims: dict) -> List[str]:
        """Extract guild IDs from token claims"""
        return claims.get("guild_ids", [])


# src/schedule_zero/api/base_handler.py
class AuthenticatedHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jwt_validator = JWTValidator()
    
    def get_current_user(self) -> Optional[dict]:
        """Extract and validate JWT from Authorization header"""
        auth_header = self.request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        try:
            claims = self.jwt_validator.validate_token(token)
            return claims
        except HTTPError:
            return None
    
    def get_user_guild_ids(self) -> List[str]:
        """Get guild IDs the authenticated user can access"""
        user = self.get_current_user()
        if not user:
            raise HTTPError(401, "Authentication required")
        
        return self.jwt_validator.extract_guild_ids(user)
    
    def prepare(self):
        """Require authentication for all requests"""
        if not self.get_current_user():
            raise HTTPError(401, "Authentication required")


# src/schedule_zero/api/job_scheduling_api.py
class ScheduleHandler(AuthenticatedHandler):
    async def get(self):
        """Get schedules - filtered by user's guild access"""
        guild_ids = self.get_user_guild_ids()
        
        all_schedules = await self.application.scheduler.get_schedules()
        
        # Filter: only schedules for guilds user can access
        user_schedules = [
            s for s in all_schedules
            if s.metadata.get('tenant_id') in guild_ids
        ]
        
        self.write({"schedules": user_schedules})
    
    async def post(self):
        """Create schedule - validate tenant_id against user's guilds"""
        guild_ids = self.get_user_guild_ids()
        
        data = tornado.escape.json_decode(self.request.body)
        tenant_id = data.get('metadata', {}).get('tenant_id')
        
        # Authorization check: user must have access to this guild
        if tenant_id not in guild_ids:
            raise HTTPError(403, f"Access denied to guild {tenant_id}")
        
        # Proceed with schedule creation
        schedule = await self.application.scheduler.add_schedule(**data)
        self.write({"schedule": schedule})
```

## Alternative: Python-Native WAFs

### 1. **Tencent Cloud WAF** (Python middleware)
```python
# Not widely adopted, limited community support
from tencent_waf import WAFMiddleware

app = WAFMiddleware(tornado_app, rules="owasp-crs")
```

### 2. **AWS WAF / Cloudflare** (Managed SaaS)
- Best for production if you're on AWS/Cloudflare
- No self-hosting, scales automatically
- $$$ cost scales with traffic

## Deployment Checklist

- [ ] NGINX + ModSecurity + OWASP CRS deployed
- [ ] Keycloak configured with realm + client
- [ ] JWT validation implemented in Tornado
- [ ] Guild IDs stored in JWT claims
- [ ] Authorization checks in all API handlers
- [ ] TLS certificates configured (Let's Encrypt)
- [ ] Rate limiting tuned for expected traffic
- [ ] ModSecurity paranoia level set (start with 1)
- [ ] Cloudflare/DDoS protection enabled
- [ ] Tornado only listening on localhost (not 0.0.0.0)
- [ ] Security headers configured
- [ ] Audit logging enabled
- [ ] Secrets moved to environment variables
- [ ] PostgreSQL/Redis not exposed to internet

## Testing WAF Rules

```bash
# Test SQL injection blocking
curl -X POST https://api.yourdomain.com/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "task_id": "1 OR 1=1"}'
# Expected: 403 Forbidden (blocked by WAF)

# Test XSS blocking
curl -X POST https://api.yourdomain.com/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "<script>alert(1)</script>"}'
# Expected: 403 Forbidden (blocked by WAF)

# Test rate limiting
for i in {1..150}; do
  curl https://api.yourdomain.com/api/schedules
done
# Expected: 429 Too Many Requests after ~100 requests
```

## Resources

- **ModSecurity**: https://github.com/SpiderLabs/ModSecurity
- **OWASP CRS**: https://coreruleset.org/
- **Keycloak**: https://www.keycloak.org/
- **NGINX Security**: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- **Docker Images**: https://hub.docker.com/r/owasp/modsecurity-crs

## Summary

**For localhost/testing**: No WAF needed
**For internet-facing production**: NGINX + ModSecurity + OWASP CRS + Keycloak (JWT)

This stack is:
- ✅ Open source
- ✅ Battle-tested at scale
- ✅ Compatible with Tornado (any Python framework)
- ✅ Industry standard
- ✅ Actively maintained
