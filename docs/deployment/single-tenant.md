# Single-Tenant Deployment Guide

## Architecture Decision

**ScheduleZero will support two deployment models:**

1. **Single-Tenant** (Recommended for Discord guilds)
   - One ScheduleZero instance per guild
   - Complete data isolation
   - VPN access for guild leadership
   - Simple security model

2. **Multi-Tenant** (Future - For SaaS/hosting providers)
   - Shared infrastructure
   - OAuth/JWT authentication
   - WAF + full security stack
   - NOT recommended for individual guilds

## Why Single-Tenant for Gaming Guilds?

**Security through isolation:**
- No shared database = No cross-guild data leaks
- No authentication complexity = Fewer attack vectors
- VPN access = Network-level security
- One breach doesn't affect other guilds

**Operational simplicity:**
- Easy to backup/restore per guild
- Guild leaders can self-host
- Clear ownership (guild owns their data)
- No "noisy neighbor" problems

**Trust model:**
- Guild leaders are paranoid (rightfully so)
- Single-tenant = Easy to audit
- No third-party trust required
- Complete control over deployment

## Deployment Architecture

```
Per-Guild Stack:

Server (VPS, home server, etc.)
├─ Tailscale VPN (network security)
│  └─ Only approved guild members can connect
│
├─ ScheduleZero (localhost:8888 or Tailscale IP)
│  ├─ Tornado web server
│  ├─ APScheduler
│  └─ SQLite database (guild_schedules.db)
│
├─ Discord Bot
│  ├─ Connected to ScheduleZero API
│  └─ Discord token for this guild only
│
└─ Optional: PostgreSQL instead of SQLite
```

## VPN Setup: WireGuard (Recommended)

### Why WireGuard?

- ✅ **Open source** (no third-party service dependencies)
- ✅ **Self-hosted** (complete control over infrastructure)
- ✅ **Mobile apps** for iOS/Android (guild leaders on the go)
- ✅ **Fast** (modern cryptography, minimal overhead)
- ✅ **Simple** (minimal configuration, ~4000 lines of code)
- ✅ **Secure** (audited, used by Tailscale under the hood)
- ✅ **Free** (no device limits, no subscription)

### Installation (Windows Server)

```powershell
# Install WireGuard
winget install WireGuard.WireGuard

# Or download from: https://www.wireguard.com/install/

# Verify installation
wg --version
```

### Server Configuration

**1. Generate server keys:**

```powershell
# Create WireGuard config directory
New-Item -ItemType Directory -Force -Path "C:\WireGuard"
Set-Location "C:\WireGuard"

# Generate private key
$privateKey = (wg genkey)
$privateKey | Out-File -NoNewline -Encoding ASCII server_private.key

# Generate public key from private key
$publicKey = ($privateKey | wg pubkey)
$publicKey | Out-File -NoNewline -Encoding ASCII server_public.key

Write-Host "Server Public Key: $publicKey"
Write-Host "(Share this with clients)"
```

**2. Create server config:**

File: `C:\Program Files\WireGuard\Data\Configurations\wg-schedulezero.conf`

```ini
[Interface]
# Server private key (generated above)
PrivateKey = <paste server_private.key contents>

# VPN subnet for this guild
Address = 10.88.88.1/24

# WireGuard listen port
ListenPort = 51820

# Optional: DNS server for clients
# DNS = 1.1.1.1

# Save config (no auto-save on Windows)
# SaveConfig = false

### Clients ###

# Client 1: Guild Leader
[Peer]
PublicKey = <client1_public_key>
AllowedIPs = 10.88.88.2/32

# Client 2: Officer 1
[Peer]
PublicKey = <client2_public_key>
AllowedIPs = 10.88.88.3/32

# Client 3: Officer 2
[Peer]
PublicKey = <client3_public_key>
AllowedIPs = 10.88.88.4/32

# Add more clients as needed (10.88.88.5, 10.88.88.6, etc.)
```

**3. Start WireGuard:**

```powershell
# Import tunnel via WireGuard GUI
# Or via PowerShell:
wg-quick up wg-schedulezero

# Check status
wg show

# Enable auto-start
# (Configure via WireGuard GUI: Right-click tray icon → "Tunnel: wg-schedulezero" → Check "Run at startup")
```

**4. Configure Windows Firewall:**

```powershell
# Allow WireGuard port (UDP 51820)
New-NetFirewallRule -DisplayName "WireGuard VPN" `
    -Direction Inbound `
    -LocalPort 51820 `
    -Protocol UDP `
    -Action Allow `
    -Profile Any

# Block ScheduleZero from internet (port 8888)
New-NetFirewallRule -DisplayName "ScheduleZero - Block Public" `
    -Direction Inbound `
    -LocalPort 8888 `
    -Protocol TCP `
    -Action Block `
    -Profile Any `
    -Priority 100

# Allow ScheduleZero from VPN subnet only (10.88.88.0/24)
New-NetFirewallRule -DisplayName "ScheduleZero - Allow VPN" `
    -Direction Inbound `
    -LocalPort 8888 `
    -Protocol TCP `
    -Action Allow `
    -RemoteAddress "10.88.88.0/24" `
    -Profile Any `
    -Priority 1
```

### Client Configuration (Guild Members)

**1. Generate client keys:**

```powershell
# Guild member runs on their machine:
wg genkey | Out-File -NoNewline client_private.key
Get-Content client_private.key | wg pubkey | Out-File -NoNewline client_public.key

# Client sends their PUBLIC key to server admin
Get-Content client_public.key
```

**2. Server admin adds client to server config:**

```ini
# Add to wg-schedulezero.conf [Peer] section
[Peer]
PublicKey = <client_public_key>
AllowedIPs = 10.88.88.5/32  # Next available IP
```

```powershell
# Restart WireGuard to apply changes
wg-quick down wg-schedulezero
wg-quick up wg-schedulezero
```

**3. Client config file (send to guild member):**

File: `wg-schedulezero-client.conf`

```ini
[Interface]
# Client private key (NEVER share this)
PrivateKey = <client_private_key>

# Client VPN IP address
Address = 10.88.88.5/32

# Optional: DNS server
DNS = 1.1.1.1

[Peer]
# Server public key
PublicKey = <server_public_key>

# Server endpoint (public IP:port)
Endpoint = your-server-public-ip:51820

# Route only VPN traffic through tunnel (split-tunnel)
AllowedIPs = 10.88.88.0/24

# Keep connection alive (important for mobile)
PersistentKeepalive = 25
```

**4. Client installation:**

**Windows:**
```powershell
# Install WireGuard
winget install WireGuard.WireGuard

# Import config file
# (Open WireGuard GUI → "Import tunnel(s) from file" → Select wg-schedulezero-client.conf)

# Activate tunnel
# (WireGuard GUI → Toggle switch)
```

**iOS:**
1. Install WireGuard from App Store
2. Open app → "+" → "Create from file or archive"
3. Select `wg-schedulezero-client.conf`
4. Toggle connection

**Android:**
1. Install WireGuard from Play Store
2. Open app → "+" → "Import from file or archive"
3. Select `wg-schedulezero-client.conf`
4. Toggle connection

**Linux:**
```bash
# Install WireGuard
sudo apt install wireguard

# Copy config
sudo cp wg-schedulezero-client.conf /etc/wireguard/

# Start tunnel
sudo wg-quick up wg-schedulezero-client

# Enable auto-start
sudo systemctl enable wg-quick@wg-schedulezero-client
```

**macOS:**
```bash
# Install WireGuard
brew install wireguard-tools

# Or use WireGuard.app from App Store (same as iOS)
```

### Access Dashboard

**Once connected to VPN:**

```
http://10.88.88.1:8888/
```

- `10.88.88.1` = Server VPN IP
- Only accessible when WireGuard is connected
- Mobile users can access from phones/tablets

### Managing Access

**Add new member:**
```powershell
# 1. Member generates keys, sends public key
# 2. Admin adds [Peer] section to server config
# 3. Admin assigns next IP (10.88.88.6, etc.)
# 4. Admin restarts WireGuard
# 5. Admin sends client config to member
```

**Revoke access:**
```powershell
# Remove [Peer] section from server config
# Restart WireGuard
wg-quick down wg-schedulezero
wg-quick up wg-schedulezero
```

**List active connections:**
```powershell
wg show wg-schedulezero
```

### Alternative: Tailscale (Third-Party Service)

**If you prefer zero-config setup:**

```powershell
# Install Tailscale (uses WireGuard protocol under the hood)
winget install tailscale.tailscale

# Authenticate with Tailscale service
tailscale up

# Get VPN IP
tailscale ip -4
```

**Pros**: Zero config, NAT traversal automatic
**Cons**: Third-party service (Tailscale Inc.), free tier limits

## Docker Deployment (Per-Guild)

### Directory Structure

```
schedulezero/
├─ deployments/
│  ├─ guild-awesome/
│  │  ├─ schedules.db
│  │  ├─ logs/
│  │  └─ pids/
│  ├─ guild-raiders/
│  │  ├─ schedules.db
│  │  ├─ logs/
│  │  └─ pids/
│  └─ guild-elite/
│     ├─ schedules.db
│     ├─ logs/
│     └─ pids/
├─ docker-compose.guild-awesome.yml
├─ docker-compose.guild-raiders.yml
└─ docker-compose.guild-elite.yml
```

### docker-compose.guild-awesome.yml

```yaml
version: '3.8'

services:
  schedulezero:
    build: .
    container_name: sz-guild-awesome
    ports:
      - "8888:8888"  # Accessible on Tailscale network
    environment:
      DEPLOYMENT: guild-awesome
      GUILD_ID: "123456789012345678"
      GUILD_NAME: "Awesome Raiders"
      
      # Database
      DATABASE_URL: "sqlite+aiosqlite:///deployments/guild-awesome/schedules.db"
      
      # Logging
      LOG_LEVEL: INFO
      LOG_FILE: /app/deployments/guild-awesome/logs/schedulezero.log
      
      # Security (since we're on VPN, simpler auth)
      REQUIRE_AUTH: "false"  # VPN is the security boundary
      
    volumes:
      - ./deployments/guild-awesome:/app/deployments/guild-awesome
      - ./src:/app/src
      - ./templates:/app/templates
    
    restart: unless-stopped
    
    networks:
      - guild-awesome-net

  discord-bot:
    build: ./discord-bot
    container_name: bot-guild-awesome
    environment:
      DISCORD_TOKEN: "${DISCORD_BOT_TOKEN_AWESOME}"
      SCHEDULEZERO_URL: "http://schedulezero:8888"
      GUILD_ID: "123456789012345678"
    
    depends_on:
      - schedulezero
    
    restart: unless-stopped
    
    networks:
      - guild-awesome-net

networks:
  guild-awesome-net:
    driver: bridge
```

### Start a Guild Instance

```powershell
# Set environment variables
$env:DISCORD_BOT_TOKEN_AWESOME = "your-bot-token-here"

# Start the stack
docker-compose -f docker-compose.guild-awesome.yml up -d

# View logs
docker-compose -f docker-compose.guild-awesome.yml logs -f

# Stop the stack
docker-compose -f docker-compose.guild-awesome.yml down
```

## Running Multiple Guilds on Same Server

```powershell
# Guild 1: Port 8888
docker-compose -f docker-compose.guild-awesome.yml up -d

# Guild 2: Port 8889
docker-compose -f docker-compose.guild-raiders.yml up -d

# Guild 3: Port 8890
docker-compose -f docker-compose.guild-elite.yml up -d
```

**Adjust ports in each docker-compose file:**
```yaml
ports:
  - "8889:8888"  # External:Internal (change external port)
```

## Security Model

### Network Security (VPN)

```
Internet
   ↓
   ✗ (no route)
   
Tailscale VPN (100.64.0.0/10)
   ↓
   ✓ (approved members only)
   ↓
ScheduleZero (binds to Tailscale IP only)
```

**CRITICAL: Bind to VPN interface, NOT 0.0.0.0**

**Option 1: Bind to WireGuard VPN IP (Recommended)**
```python
# tornado_app_server.py
import os

# VPN IP from environment or config
vpn_ip = os.getenv("VPN_SERVER_IP", "10.88.88.1")

# Bind ONLY to VPN interface
app.listen(8888, address=vpn_ip)
print(f"ScheduleZero listening on VPN: http://{vpn_ip}:8888/")
print("Only accessible via WireGuard VPN")
```

**Option 2: Bind to Localhost + Firewall (Defense in Depth)**
```python
# Bind to localhost ONLY
app.listen(8888, address="127.0.0.1")

# Then use NGINX or firewall to allow VPN subnet only
# See "Option 3: Firewall Rules" below
```

**Option 3: Firewall Rules (If you must bind to 0.0.0.0)**
```bash
# Linux (iptables)
# CRITICAL: Block all external access to port 8888
iptables -A INPUT -p tcp --dport 8888 -j DROP

# Allow only from WireGuard VPN subnet
iptables -I INPUT -p tcp --dport 8888 -s 10.88.88.0/24 -j ACCEPT

# Allow localhost
iptables -I INPUT -p tcp --dport 8888 -s 127.0.0.1 -j ACCEPT

# Save rules
iptables-save > /etc/iptables/rules.v4
```

```powershell
# Windows Firewall
# Block all external access
New-NetFirewallRule -DisplayName "ScheduleZero - Block All" `
    -Direction Inbound -LocalPort 8888 -Protocol TCP `
    -Action Block -Profile Any -Priority 100

# Allow Tailscale subnet (100.64.0.0/10)
New-NetFirewallRule -DisplayName "ScheduleZero - Allow VPN" `
    -Direction Inbound -LocalPort 8888 -Protocol TCP `
    -Action Allow -RemoteAddress "100.64.0.0/10" `
    -Profile Any -Priority 1

# Allow localhost
New-NetFirewallRule -DisplayName "ScheduleZero - Allow Localhost" `
    -Direction Inbound -LocalPort 8888 -Protocol TCP `
    -Action Allow -RemoteAddress "127.0.0.1" `
    -Profile Any -Priority 1
```

**Key points:**
- ⚠️ **NEVER bind to 0.0.0.0 without firewall rules**
- ✅ Bind to WireGuard VPN IP (10.88.88.1) directly
- ✅ Firewall blocks public internet access to port 8888
- ✅ Only accessible via WireGuard VPN (10.88.88.0/24)
- ✅ No authentication needed (VPN is the auth layer)
- ✅ Fully open source, self-hosted, no third-party dependencies

### Data Security (Single-Tenant)

```
Guild A Data:
├─ deployments/guild-a/schedules.db
└─ ONLY accessible by Guild A instance

Guild B Data:
├─ deployments/guild-b/schedules.db
└─ ONLY accessible by Guild B instance

No shared database = No cross-guild leaks
```

### Application Security

**Simple model (VPN-only access):**
- No user authentication in ScheduleZero
- VPN membership = authorization
- Audit logging: Track actions in logs
- Read-only roles: Configure in Tailscale ACLs

**Future enhancement (optional):**
- Add Discord OAuth for per-user audit trails
- Role-based access (guild leader vs. officer)
- Implement after VPN deployment is stable

## Backup Strategy

### Automated Backups

```powershell
# Backup script per guild
# backup-guild-awesome.ps1

$GUILD = "guild-awesome"
$BACKUP_DIR = "backups/$GUILD"
$DATE = Get-Date -Format "yyyy-MM-dd-HHmmss"

# Create backup directory
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/$DATE"

# Stop containers (optional, for consistency)
docker-compose -f docker-compose.$GUILD.yml stop

# Backup database
Copy-Item "deployments/$GUILD/schedules.db" "$BACKUP_DIR/$DATE/"

# Backup logs
Copy-Item -Recurse "deployments/$GUILD/logs" "$BACKUP_DIR/$DATE/"

# Backup config
Copy-Item "docker-compose.$GUILD.yml" "$BACKUP_DIR/$DATE/"

# Restart containers
docker-compose -f docker-compose.$GUILD.yml start

# Keep last 30 days
Get-ChildItem $BACKUP_DIR | 
    Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} |
    Remove-Item -Recurse

Write-Host "Backup complete: $BACKUP_DIR/$DATE"
```

**Schedule with Task Scheduler:**
```powershell
# Run backup daily at 3 AM
schtasks /create /tn "ScheduleZero-Backup-GuildAwesome" `
    /tr "powershell.exe -File C:\path\to\backup-guild-awesome.ps1" `
    /sc daily /st 03:00
```

## Monitoring

### Health Checks

```powershell
# Check if ScheduleZero is responding
Invoke-WebRequest -Uri "http://100.101.102.103:8888/api/health" -UseBasicParsing

# Check Docker containers
docker-compose -f docker-compose.guild-awesome.yml ps

# View recent logs
docker-compose -f docker-compose.guild-awesome.yml logs --tail=50
```

### Alerting (Optional)

```python
# Simple uptime monitor (run as systemd service or cron)
import requests
import time
import logging

GUILDS = {
    "guild-awesome": "http://100.101.102.103:8888",
    "guild-raiders": "http://100.101.102.104:8889",
}

WEBHOOK_URL = "https://discord.com/api/webhooks/..."  # Alert channel

while True:
    for guild_name, url in GUILDS.items():
        try:
            resp = requests.get(f"{url}/api/health", timeout=5)
            if resp.status_code != 200:
                # Alert: Service down
                requests.post(WEBHOOK_URL, json={
                    "content": f"🚨 {guild_name} is DOWN (status {resp.status_code})"
                })
        except Exception as e:
            # Alert: Service unreachable
            requests.post(WEBHOOK_URL, json={
                "content": f"🚨 {guild_name} is UNREACHABLE: {e}"
            })
    
    time.sleep(300)  # Check every 5 minutes
```

## Cost Comparison

### Option 1: Cloud VPS per Guild

**Providers:**
- Linode: $5/month (1GB RAM, 1 CPU)
- DigitalOcean: $6/month (1GB RAM, 1 CPU)
- Vultr: $5/month (1GB RAM, 1 CPU)

**Total cost**: $5-6/guild/month

### Option 2: Single Server, Multiple Guilds

**Home server or VPS:**
- 4GB RAM, 2 CPU: $12-20/month
- Run 5-10 guilds on same server
- **Cost per guild**: $1-4/month

### Option 3: Self-Hosted (Free)

- Old PC/laptop running 24/7
- Tailscale free tier (100 devices)
- **Cost**: $0 (just electricity)

## Scaling Considerations

**Single ScheduleZero instance can handle:**
- ~1000 schedules per guild (SQLite limit)
- ~100 concurrent handlers
- ~50 requests/second (Tornado on 1 CPU)

**For larger guilds (1000+ members, complex scheduling):**
- Upgrade to PostgreSQL
- Use dedicated VPS per guild
- Horizontal scaling (multiple workers)

## Migration from Multi-Tenant (Future)

**If you ever need to consolidate:**

```python
# Export from single-tenant instances
for guild_id in guild_ids:
    schedules = export_schedules(f"deployments/guild-{guild_id}/schedules.db")
    
    # Add tenant_id metadata
    for schedule in schedules:
        schedule.metadata['tenant_id'] = guild_id
    
    # Import to multi-tenant instance
    import_schedules(schedules, multi_tenant_db)
```

**But for gaming guilds, single-tenant is recommended long-term.**

## Troubleshooting

### VPN Issues

**Can't access dashboard:**
```powershell
# Check WireGuard status
wg show wg-schedulezero

# Ping server VPN IP
ping 10.88.88.1

# Check if client is connected
# (WireGuard GUI → Should show handshake timestamp)

# Check ScheduleZero is running
docker ps | Select-String schedulezero

# Verify firewall rules
Get-NetFirewallRule -DisplayName "ScheduleZero*"

# Check if ScheduleZero is bound to VPN IP
netstat -an | Select-String "8888"
```

**WireGuard connection issues:**

```powershell
# Windows: Check WireGuard logs
# (WireGuard GUI → Right-click tray icon → "View Log")

# Verify server can reach internet
ping 1.1.1.1

# Check if UDP 51820 is open (server firewall)
Test-NetConnection -ComputerName your-server-ip -Port 51820 -InformationLevel Detailed

# Restart WireGuard
wg-quick down wg-schedulezero
wg-quick up wg-schedulezero
```

**Performance issues:**
- WireGuard is very fast (~1 Gbps on modern hardware)
- Check for packet loss: `ping -t 10.88.88.1`
- MTU issues: Try adding `MTU = 1420` to `[Interface]` section

### Database Corruption

```powershell
# Check database integrity
sqlite3 deployments/guild-awesome/schedules.db "PRAGMA integrity_check;"

# Restore from backup
Copy-Item backups/guild-awesome/2025-11-14-030000/schedules.db `
    deployments/guild-awesome/schedules.db

# Restart containers
docker-compose -f docker-compose.guild-awesome.yml restart
```

## Resources

- **WireGuard**: https://www.wireguard.com/
- **WireGuard Windows Install**: https://www.wireguard.com/install/#windows-7-8-81-10-11-2008r2-2012r2-2016-2019-2022
- **WireGuard Quick Start**: https://www.wireguard.com/quickstart/
- **Docker Compose**: https://docs.docker.com/compose/
- **SQLite**: https://www.sqlite.org/
- **ScheduleZero Docs**: http://localhost:8888/docs/

## Summary

**For Discord gaming guilds:**
- ✅ Use single-tenant deployments (one per guild)
- ✅ VPN access (WireGuard - open source, self-hosted)
- ✅ Complete data isolation
- ✅ Simple security model (VPN = auth boundary)
- ✅ Guild leaders have full control
- ✅ Easy to backup/restore
- ✅ No cross-guild attack surface
- ✅ No third-party dependencies

**Multi-tenant architecture:**
- ⏰ Future feature for SaaS hosting providers
- ⏰ Requires OAuth/JWT, WAF, audit logging
- ⏰ Not recommended for individual guilds
- ⏰ Will be documented separately when implemented
