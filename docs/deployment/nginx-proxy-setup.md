# Nginx Reverse Proxy Setup for ScheduleZero

This guide explains how to configure nginx as a reverse proxy for the ScheduleZero Tornado server, enabling HTTPS access and allowing multiple services to run on the same server without opening multiple ports.

## Why Use a Reverse Proxy?

Benefits of using nginx with ScheduleZero:

1. **HTTPS/SSL Termination**: Nginx handles SSL certificates, encrypting traffic to ScheduleZero
2. **Single Port**: Serve multiple applications on standard ports (80/443)
3. **Load Balancing**: Distribute traffic across multiple ScheduleZero instances
4. **Caching**: Cache static assets for better performance
5. **Security**: Add authentication, rate limiting, IP filtering
6. **Logging**: Centralized access logs
7. **WebSocket Support**: Proxy WebSocket connections for future real-time features

## Architecture

```
Internet
    ↓
Nginx (Port 80/443)
    ↓
    ├→ schedulezero.example.com → ScheduleZero (Port 8888)
    ├→ example.com/schedulezero/ → ScheduleZero (Port 8888)
    └→ example.com/ → Other applications
```

## Quick Start

### Option 1: Subdomain-Based Routing (Recommended)

Access ScheduleZero at: `https://schedulezero.yourdomain.com`

**Step 1:** Create nginx configuration

```bash
sudo nano /etc/nginx/sites-available/schedulezero
```

**Step 2:** Add configuration (use the simple config):

```nginx
server {
    listen 80;
    server_name schedulezero.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name schedulezero.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/schedulezero.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/schedulezero.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Step 3:** Enable and test

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/schedulezero /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**Step 4:** Get SSL certificate

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d schedulezero.yourdomain.com

# Auto-renewal is configured automatically
```

### Option 2: Path-Based Routing

Access ScheduleZero at: `https://yourdomain.com/schedulezero/`

Add to your existing nginx server block:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # ... your existing SSL config ...
    
    location /schedulezero/ {
        rewrite ^/schedulezero/(.*)$ /$1 break;
        
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /schedulezero;
    }
}
```

## Configuration Files

We provide two nginx configuration templates:

### 1. Simple Configuration
**File:** `deployments/ansible/nginx-schedulezero-simple.conf`

- Minimal setup for quick deployment
- Subdomain-based routing only
- Good for development and small deployments

### 2. Full Configuration
**File:** `deployments/ansible/nginx-schedulezero.conf`

- Complete configuration with all options
- Both subdomain and path-based routing examples
- Production recommendations
- Security hardening
- Performance optimization
- Multi-instance support

## Prerequisites

### 1. Install Nginx

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install nginx
```

**CentOS/RHEL:**
```bash
sudo yum install nginx
```

**macOS:**
```bash
brew install nginx
```

### 2. Configure DNS

For subdomain-based routing, create a DNS A record:

```
Type: A
Host: schedulezero
Value: YOUR_SERVER_IP
TTL: 3600
```

Verify DNS propagation:
```bash
nslookup schedulezero.yourdomain.com
# or
dig schedulezero.yourdomain.com
```

### 3. Configure Firewall

Allow HTTP and HTTPS traffic:

**UFW (Ubuntu):**
```bash
sudo ufw allow 'Nginx Full'
sudo ufw status
```

**firewalld (CentOS):**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## SSL/TLS Configuration

### Let's Encrypt (Recommended)

Free, automated SSL certificates:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate (subdomain)
sudo certbot --nginx -d schedulezero.yourdomain.com

# Get certificate (main domain + subdomain)
sudo certbot --nginx -d yourdomain.com -d schedulezero.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

Certbot will:
- Obtain the certificate
- Automatically update nginx configuration
- Set up auto-renewal (runs twice daily)

### Self-Signed Certificate (Development Only)

For testing without a domain:

```bash
# Generate certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/schedulezero.key \
    -out /etc/nginx/ssl/schedulezero.crt

# Update nginx config to use certificate
ssl_certificate /etc/nginx/ssl/schedulezero.crt;
ssl_certificate_key /etc/nginx/ssl/schedulezero.key;
```

⚠️ **Warning:** Browsers will show security warnings for self-signed certificates.

## Production Configuration

### Security Headers

Add to your server block:

```nginx
# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### Rate Limiting

Protect against DDoS and abuse:

**Add to `http` block in `/etc/nginx/nginx.conf`:**
```nginx
# Define rate limit zone
limit_req_zone $binary_remote_addr zone=schedulezero:10m rate=10r/s;
```

**Add to `server` block:**
```nginx
# Apply rate limit
limit_req zone=schedulezero burst=20 nodelay;
```

### Basic Authentication

Add password protection:

```bash
# Install htpasswd utility
sudo apt-get install apache2-utils

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Add more users (without -c flag)
sudo htpasswd /etc/nginx/.htpasswd user2
```

**Add to `location` block:**
```nginx
location / {
    auth_basic "ScheduleZero Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://127.0.0.1:8888;
    # ... other proxy settings ...
}
```

### IP Whitelisting

Restrict access to specific IPs:

```nginx
location / {
    # Allow specific IPs or networks
    allow 192.168.1.0/24;    # Office network
    allow 10.0.0.50;         # VPN server
    deny all;                # Deny everyone else
    
    proxy_pass http://127.0.0.1:8888;
    # ... other proxy settings ...
}
```

### Logging

Configure access and error logs:

```nginx
server {
    # Detailed access logging
    access_log /var/log/nginx/schedulezero.access.log;
    error_log /var/log/nginx/schedulezero.error.log warn;
    
    # Custom log format (optional)
    log_format schedulezero '$remote_addr - $remote_user [$time_local] '
                           '"$request" $status $body_bytes_sent '
                           '"$http_referer" "$http_user_agent" '
                           '$request_time';
    
    access_log /var/log/nginx/schedulezero.access.log schedulezero;
}
```

**Disable logging for health checks:**
```nginx
location /api/health {
    proxy_pass http://127.0.0.1:8888/api/health;
    access_log off;  # Don't log health checks
}
```

## Multi-Instance Setup

Run multiple ScheduleZero instances with different subdomains:

```nginx
# Production instance
server {
    listen 443 ssl http2;
    server_name schedulezero.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8888;  # Production on port 8888
    }
}

# Staging instance
server {
    listen 443 ssl http2;
    server_name schedulezero-staging.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8889;  # Staging on port 8889
    }
}

# Development instance
server {
    listen 443 ssl http2;
    server_name schedulezero-dev.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8890;  # Dev on port 8890
    }
}
```

Configure each ScheduleZero instance with different ports:

```bash
# Production
SCHEDULEZERO_DEPLOYMENT=production python -m schedule_zero.server
# (Uses port 8888 by default)

# Staging
SCHEDULEZERO_DEPLOYMENT=staging python -m schedule_zero.server
# Configure in deployments/staging/config.yaml: tornado_port: 8889

# Dev
SCHEDULEZERO_DEPLOYMENT=dev python -m schedule_zero.server
# Configure in deployments/dev/config.yaml: tornado_port: 8890
```

## Performance Optimization

### Gzip Compression

Add to `http` block:

```nginx
# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss;
```

### Static File Caching

Cache static assets:

```nginx
location /static/ {
    proxy_pass http://127.0.0.1:8888/static/;
    
    # Cache for 1 hour
    proxy_cache_valid 200 1h;
    expires 1h;
    add_header Cache-Control "public, immutable";
}
```

### Buffer Settings

Optimize buffering:

```nginx
location / {
    proxy_pass http://127.0.0.1:8888;
    
    # Buffering
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
}
```

## Troubleshooting

### 502 Bad Gateway

**Problem:** Nginx returns 502 error.

**Causes:**
1. ScheduleZero server is not running
2. Wrong port in `proxy_pass`
3. Firewall blocking connection

**Solutions:**
```bash
# Check if ScheduleZero is running
curl http://127.0.0.1:8888

# Check ScheduleZero logs
tail -f logs/tornado.log

# Check nginx error log
sudo tail -f /var/log/nginx/schedulezero.error.log

# Verify port in config matches ScheduleZero
grep tornado_port deployments/default/config.yaml
```

### Connection Refused

**Problem:** "Connection refused" in nginx error log.

**Solutions:**
```bash
# Verify ScheduleZero is listening
sudo netstat -tlnp | grep 8888

# Check if bound to correct interface
# Should show 127.0.0.1:8888 or 0.0.0.0:8888

# Restart ScheduleZero if needed
```

### SSL Certificate Errors

**Problem:** Browser shows certificate errors.

**Solutions:**
```bash
# Verify certificate files exist
ls -l /etc/letsencrypt/live/schedulezero.yourdomain.com/

# Check certificate expiry
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Test nginx config
sudo nginx -t
```

### Path-Based Routing Issues

**Problem:** Assets not loading with path-based routing.

**Solutions:**
1. Ensure `X-Forwarded-Prefix` header is set
2. Check rewrite rules:
   ```nginx
   # Strip /schedulezero prefix
   rewrite ^/schedulezero/(.*)$ /$1 break;
   ```
3. Verify ScheduleZero handles the prefix correctly

### Permission Denied

**Problem:** "Permission denied" when accessing files.

**Solutions:**
```bash
# Check nginx user
ps aux | grep nginx

# Ensure nginx can read certificates
sudo chmod 644 /etc/letsencrypt/live/*/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/*/privkey.pem
```

## Monitoring

### Nginx Status Page

Enable status endpoint:

```nginx
server {
    listen 127.0.0.1:8080;
    
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}
```

Access: `curl http://127.0.0.1:8080/nginx_status`

### Log Monitoring

Monitor logs in real-time:

```bash
# Access log
sudo tail -f /var/log/nginx/schedulezero.access.log

# Error log
sudo tail -f /var/log/nginx/schedulezero.error.log

# Filter for errors only
sudo tail -f /var/log/nginx/schedulezero.error.log | grep error

# Count requests per minute
sudo tail -f /var/log/nginx/schedulezero.access.log | \
    awk '{print $4}' | uniq -c
```

### Log Rotation

Nginx log rotation is typically configured automatically, but verify:

```bash
# Check logrotate config
cat /etc/logrotate.d/nginx

# Manually rotate logs
sudo logrotate -f /etc/logrotate.d/nginx
```

## Testing

### Test Configuration

```bash
# Test nginx config syntax
sudo nginx -t

# Test with more verbose output
sudo nginx -t -c /etc/nginx/nginx.conf
```

### Test SSL

```bash
# Test SSL certificate
openssl s_client -connect schedulezero.yourdomain.com:443 -servername schedulezero.yourdomain.com

# Test SSL configuration (external service)
# Visit: https://www.ssllabs.com/ssltest/
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test with 1000 requests, 10 concurrent
ab -n 1000 -c 10 https://schedulezero.yourdomain.com/

# Test specific endpoint
ab -n 100 -c 5 https://schedulezero.yourdomain.com/api/health
```

## Deployment Checklist

- [ ] DNS A record created and propagated
- [ ] Nginx installed and running
- [ ] Configuration file created in `/etc/nginx/sites-available/`
- [ ] Symlink created in `/etc/nginx/sites-enabled/`
- [ ] Configuration tested: `sudo nginx -t`
- [ ] SSL certificate obtained (Let's Encrypt or other)
- [ ] Firewall rules configured (ports 80, 443)
- [ ] ScheduleZero running on configured port
- [ ] Nginx reloaded: `sudo systemctl reload nginx`
- [ ] HTTPS works: Visit `https://schedulezero.yourdomain.com`
- [ ] Security headers configured
- [ ] Rate limiting enabled (optional)
- [ ] Authentication configured (optional)
- [ ] Logs configured and rotated
- [ ] Monitoring set up (optional)

## See Also

- [Full Nginx Configuration](../deployments/ansible/nginx-schedulezero.conf)
- [Simple Nginx Configuration](../deployments/ansible/nginx-schedulezero-simple.conf)
- [ScheduleZero Deployment Documentation](../docs/deployment/)
- [Nginx Official Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
