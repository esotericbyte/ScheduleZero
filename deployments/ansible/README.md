# Ansible Deployment for ScheduleZero

Automated deployment using Ansible for single or multiple servers.

## Prerequisites

- Ansible 2.9+
- SSH access to target servers
- Python 3 on target servers
- sudo privileges on target servers

## Quick Start

### 1. Configure Inventory

Edit `inventory/production.yml` with your servers:

```yaml
schedulezero_servers:
  hosts:
    your-server.example.com:
      schedulezero_deployment: production
```

### 2. Deploy

```bash
# Deploy everything
ansible-playbook -i inventory/production.yml playbooks/deploy-all.yml

# Or step by step:
ansible-playbook -i inventory/production.yml playbooks/deploy-server.yml
ansible-playbook -i inventory/production.yml playbooks/deploy-handlers.yml
```

### 3. Verify

```bash
# Check service status on all servers
ansible all -i inventory/production.yml -m shell -a "systemctl status schedulezero-*"
```

## Directory Structure

```
ansible/
├── inventory/               # Server inventories
│   ├── production.yml      # Production servers
│   └── staging.yml         # Staging servers
├── group_vars/             # Variables by group
│   ├── all.yml            # Variables for all hosts
│   └── production.yml     # Production-specific
├── roles/                  # Ansible roles
│   ├── schedulezero-server/
│   └── schedulezero-handler/
├── playbooks/              # Playbooks
│   ├── deploy-all.yml
│   ├── deploy-server.yml
│   └── deploy-handlers.yml
└── ansible.cfg            # Ansible configuration
```

## Configuration

### Inventory Variables

```yaml
# Common variables (group_vars/all.yml)
schedulezero_repo: "https://github.com/esotericbyte/ScheduleZero.git"
schedulezero_version: "main"
schedulezero_deploy_path: "/opt/schedulezero"
schedulezero_user: "schedulezero"
```

### Handler Configuration

Add handlers to your inventory:

```yaml
schedulezero_handlers:
  hosts:
    worker01.example.com:
      handlers:
        - name: ding-aling
          module: examples.ding_aling_handler
          class: DingAlongHandler
          port: 4244
        - name: notifications
          module: handlers.notification_handler  
          class: NotificationHandler
          port: 4245
```

## Playbooks

### deploy-all.yml
Deploys both server and handlers to appropriate hosts.

### deploy-server.yml
Deploys only the ScheduleZero server.

### deploy-handlers.yml
Deploys handlers to worker nodes.

## Advanced Usage

### Secrets Management

Use Ansible Vault for sensitive data:

```bash
# Create encrypted variables file
ansible-vault create group_vars/production/vault.yml

# Edit encrypted file
ansible-vault edit group_vars/production/vault.yml

# Deploy with vault password
ansible-playbook -i inventory/production.yml playbooks/deploy-all.yml --ask-vault-pass
```

### Deployment with Tags

```bash
# Only install dependencies
ansible-playbook playbooks/deploy-all.yml --tags install

# Only restart services
ansible-playbook playbooks/deploy-all.yml --tags restart

# Skip tests
ansible-playbook playbooks/deploy-all.yml --skip-tags test
```

### Rolling Updates

Update handlers one at a time:

```bash
ansible-playbook playbooks/deploy-handlers.yml --serial 1
```

## Troubleshooting

### Check Ansible Connectivity

```bash
ansible all -i inventory/production.yml -m ping
```

### View Service Status

```bash
ansible all -i inventory/production.yml -a "systemctl status schedulezero-server"
```

### View Logs

```bash
ansible all -i inventory/production.yml -a "journalctl -u schedulezero-server -n 50"
```

## Next Steps

1. Customize inventory for your infrastructure
2. Adjust variables in `group_vars/`
3. Add handlers to inventory
4. Run playbooks
5. Set up monitoring/alerting

## See Also

- [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md)
- [systemd Services](../systemd/README.md)
- [Ansible Documentation](https://docs.ansible.com/)
