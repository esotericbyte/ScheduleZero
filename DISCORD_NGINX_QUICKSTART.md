# Discord Bot & Nginx Integration - Quick Start

This document provides a quick overview of the new Discord bot ZeroMQ listener and nginx reverse proxy setup.

## What Was Created

### 1. Discord Bot ZeroMQ Listener Cog
- **File:** `discord/cogs/zmq_listener_cog.py`
- **Config:** `discord/config/zmq_listener.yaml`
- **Documentation:** `discord/ZMQ_LISTENER_GUIDE.md`

### 2. Nginx Reverse Proxy Configuration
- **Full Config:** `deployments/ansible/nginx-schedulezero.conf`
- **Simple Config:** `deployments/ansible/nginx-schedulezero-simple.conf`
- **Documentation:** `docs/deployment/nginx-proxy-setup.md`

## Quick Start: Discord Bot

### Step 1: Load the Cog

In your bot's main file:

```python
bot.load_extension("cogs.zmq_listener_cog")
```

### Step 2: Configure

Edit `discord/config/zmq_listener.yaml`:

```yaml
zmq_pub_address: "tcp://127.0.0.1:4243"
topics:
  - "job."
  - "handler."
```

### Step 3: Test

In Discord, run:
```
/zmq_status
```

**Features:**
- Receives real-time events from ScheduleZero server
- Job execution/failure notifications
- Handler status updates
- Extensible event handlers
- Thread-safe message queue

## Quick Start: Nginx

### Step 1: Copy Configuration

**For subdomain access (schedulezero.yourdomain.com):**
```bash
sudo cp deployments/ansible/nginx-schedulezero-simple.conf \
    /etc/nginx/sites-available/schedulezero

# Edit the file and replace 'yourdomain.com'
sudo nano /etc/nginx/sites-available/schedulezero
```

### Step 2: Enable Configuration

```bash
sudo ln -s /etc/nginx/sites-available/schedulezero \
    /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Get SSL Certificate

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d schedulezero.yourdomain.com
```

**Features:**
- HTTPS/SSL termination
- Subdomain or path-based routing
- WebSocket support
- Rate limiting
- Security headers

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 ScheduleZero Server                  │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │   Tornado    │         │ ZMQ Publisher │         │
│  │   :8888      │         │    :4243      │         │
│  └──────┬───────┘         └───────┬───────┘         │
│         │                         │                  │
└─────────┼─────────────────────────┼──────────────────┘
          │                         │
          │ HTTP                    │ ZMQ PUB/SUB
          │                         │
          ↓                         ↓
┌─────────────────┐       ┌─────────────────────┐
│  Nginx Proxy    │       │   Discord Bot       │
│  :80, :443      │       │                     │
│                 │       │  ZMQ Listener Cog   │
│  - SSL          │       │  - Event Handlers   │
│  - Security     │       │  - Notifications    │
│  - Routing      │       │  - Commands         │
└─────────────────┘       └─────────────────────┘
```

## Use Cases

### Discord Bot Integration

1. **Job Monitoring**: Get notified when scheduled jobs execute or fail
2. **Status Updates**: Track handler registrations and health
3. **Admin Alerts**: Receive critical failure notifications in Discord
4. **Audit Trail**: Log all job executions to Discord channels
5. **Real-time Dashboard**: Display scheduler status in Discord

### Nginx Reverse Proxy

1. **HTTPS Access**: Secure access to ScheduleZero web interface
2. **Multi-Service**: Run multiple apps on same server (port 80/443)
3. **Load Balancing**: Distribute traffic across multiple instances
4. **Security**: Add authentication, IP filtering, rate limiting
5. **Professional URLs**: Use branded subdomains instead of IP:port

## Configuration Files

| File | Purpose |
|------|---------|
| `discord/cogs/zmq_listener_cog.py` | Discord cog that receives ZMQ events |
| `discord/config/zmq_listener.yaml` | ZMQ listener configuration |
| `discord/ZMQ_LISTENER_GUIDE.md` | Complete Discord integration guide |
| `deployments/ansible/nginx-schedulezero.conf` | Full nginx config with all options |
| `deployments/ansible/nginx-schedulezero-simple.conf` | Minimal nginx config for quick setup |
| `docs/deployment/nginx-proxy-setup.md` | Complete nginx setup guide |

## Commands

### Discord Bot Commands

- `/zmq_status` - Check ZMQ listener status
- `/zmq_restart` - Restart the ZMQ listener (admin only)

### Nginx Management Commands

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# View logs
sudo tail -f /var/log/nginx/schedulezero.access.log
sudo tail -f /var/log/nginx/schedulezero.error.log
```

## Customization

### Custom Event Handlers

```python
# In your bot cog
zmq_cog = bot.get_cog("ZMQListenerCog")
zmq_cog.listener.register_handler("job.failed", my_custom_handler)

async def my_custom_handler(bot, topic, data):
    # Your custom logic
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(f"Job failed: {data['job_name']}")
```

### Nginx Authentication

```bash
# Add basic auth
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Add to nginx config
location / {
    auth_basic "ScheduleZero Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... proxy settings ...
}
```

## Troubleshooting

### Discord Bot

**Problem:** Listener not connecting

**Solution:**
1. Check ZMQ server is running: `netstat -tlnp | grep 4243`
2. Verify config: `discord/config/zmq_listener.yaml`
3. Check bot logs for errors

### Nginx

**Problem:** 502 Bad Gateway

**Solution:**
1. Check ScheduleZero is running: `curl http://127.0.0.1:8888`
2. Verify port in nginx config matches ScheduleZero port
3. Check nginx error log: `sudo tail /var/log/nginx/error.log`

## Next Steps

1. **Test the setup**: Verify both Discord bot and nginx are working
2. **Customize handlers**: Add your own event handlers for Discord
3. **Security**: Configure authentication, rate limiting, IP filtering
4. **Monitoring**: Set up log monitoring and alerting
5. **Production**: Deploy with proper SSL certificates and DNS

## Full Documentation

- **Discord Bot**: See `discord/ZMQ_LISTENER_GUIDE.md`
- **Nginx Proxy**: See `docs/deployment/nginx-proxy-setup.md`
- **ScheduleZero**: See `docs/` directory

## Support

For issues or questions:
1. Check the full documentation guides
2. Review the example configurations
3. Test with the provided commands
4. Check logs for detailed error messages
