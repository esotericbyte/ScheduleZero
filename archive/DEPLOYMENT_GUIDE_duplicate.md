---
title: Deployment Guide
tags:
  - deployment
  - user-guide
  - production
status: complete
---

# ScheduleZero Deployment Guide

## Overview

ScheduleZero supports multiple deployment patterns, from single-machine development to distributed production systems. Choose the pattern that best fits your infrastructure and scale requirements.

## Deployment Decision Matrix

| Scenario | Recommended Approach | Tooling |
|----------|---------------------|---------|
| **Local Development** | ProcessGovernor | Python script |
| **Single Server (Linux)** | systemd services | systemd + Ansible |
| **Single Server (Windows)** | Windows Services | NSSM + PowerShell |
| **Multiple Servers** | Autonomous handlers | systemd/Docker + Ansible |
| **Container Dev** | Docker Compose | Docker |
| **Production Containers** | Docker Swarm | Docker Swarm |
| **Cloud Native** | Kubernetes | K8s + Helm |
| **Serverless** | Mixed deployment | Lambda + ECS/Fargate |

---

## Pattern 1: ProcessGovernor (Development/Testing)

### Purpose
- **Local development** and testing
- **Single-machine** simple deployments
- **Testbed** for ScheduleZero features
- **Edge devices** with resource constraints

### Architecture
```
ProcessGovernor (Python)
  ├── Manages server process
  ├── Manages handler processes
  ├── PID file tracking
  ├── Signal handling
  └── Graceful shutdown
```

### Usage
```powershell
# Start everything
python governor.py start

# Check status
python governor.py status

# Stop everything
python governor.py stop

# Or use new ProcessGovernor directly
poetry run python -c "
from src.schedule_zero.process_governor import ProcessGovernor
gov = ProcessGovernor('production')
gov.start()
"
```

### Pros
✅ Simple single-command startup  
✅ Integrated logging  
✅ Easy debugging  
✅ No external dependencies  
✅ Cross-platform (Windows/Linux/macOS)

### Cons
❌ Single point of failure  
❌ No redundancy  
❌ Limited to one machine  
❌ Manual intervention for crashes

### When to Use
- Development and testing
- Small deployments (< 5 handlers)
- Edge/IoT devices
- Desktop applications

---

## Pattern 2: systemd Services (Linux Production)

### Purpose
- **Linux servers** production deployment
- **OS-native** process management
- **Automatic restart** on failure
- **Dependency management** between services

### Architecture
```
systemd
  ├── schedulezero-server.service
  ├── schedulezero-handler@ding-aling.service
  ├── schedulezero-handler@notifications.service
  └── (one service per handler)
```

### Implementation

#### Server Service
```ini
# /etc/systemd/system/schedulezero-server.service
[Unit]
Description=ScheduleZero Job Scheduling Server
Documentation=https://github.com/esotericbyte/ScheduleZero
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=schedulezero
Group=schedulezero
WorkingDirectory=/opt/schedulezero
Environment="PATH=/opt/schedulezero/.venv/bin:/usr/bin"

# Use Poetry virtual environment
ExecStart=/opt/schedulezero/.venv/bin/python -m src.schedule_zero.server --deployment production

# Restart on failure
Restart=on-failure
RestartSec=10s
StartLimitInterval=5min
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=schedulezero-server

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/schedulezero/deployments

[Install]
WantedBy=multi-user.target
```

#### Handler Service Template
```ini
# /etc/systemd/system/schedulezero-handler@.service
[Unit]
Description=ScheduleZero Handler (%i)
Documentation=https://github.com/esotericbyte/ScheduleZero
After=network-online.target schedulezero-server.service
Wants=network-online.target
Requires=schedulezero-server.service

[Service]
Type=simple
User=schedulezero
Group=schedulezero
WorkingDirectory=/opt/schedulezero
Environment="PATH=/opt/schedulezero/.venv/bin:/usr/bin"
Environment="HANDLER_ID=%i"

# Handler-specific configuration loaded from file
EnvironmentFile=/etc/schedulezero/handlers/%i.env

ExecStart=/opt/schedulezero/.venv/bin/python -m src.schedule_zero.zmq_handler_base \
    --handler-id %i \
    --module ${HANDLER_MODULE} \
    --class ${HANDLER_CLASS} \
    --port ${HANDLER_PORT}

Restart=on-failure
RestartSec=10s
StartLimitInterval=5min
StartLimitBurst=3

StandardOutput=journal
StandardError=journal
SyslogIdentifier=schedulezero-handler-%i

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/schedulezero/deployments

[Install]
WantedBy=multi-user.target
```

#### Handler Configuration
```bash
# /etc/schedulezero/handlers/ding-aling.env
HANDLER_MODULE=examples.ding_aling_handler
HANDLER_CLASS=DingAlongHandler
HANDLER_PORT=4244
```

### Management Commands
```bash
# Enable services to start on boot
sudo systemctl enable schedulezero-server
sudo systemctl enable schedulezero-handler@ding-aling

# Start services
sudo systemctl start schedulezero-server
sudo systemctl start schedulezero-handler@ding-aling

# Check status
sudo systemctl status schedulezero-server
sudo systemctl status schedulezero-handler@*

# View logs
sudo journalctl -u schedulezero-server -f
sudo journalctl -u schedulezero-handler@ding-aling -f

# Restart
sudo systemctl restart schedulezero-server

# Stop
sudo systemctl stop schedulezero-handler@ding-aling
```

### Pros
✅ OS-native, battle-tested  
✅ Automatic restart on crash  
✅ Integrated logging (journald)  
✅ Dependency management  
✅ Resource limits (via cgroups)  
✅ Security hardening built-in

### Cons
❌ Linux-only  
❌ Manual service file creation  
❌ No dynamic handler addition  
❌ Requires root for management

### When to Use
- Linux production servers
- Long-running services
- Need automatic restart
- Security-conscious deployments

---

## Pattern 3: Ansible Automation

### Purpose
- **Automated deployment** to one or many servers
- **Configuration management**
- **Idempotent operations**
- **Version control** of infrastructure

### Directory Structure
```
deployments/ansible/
├── inventory/
│   ├── production.yml
│   └── staging.yml
├── group_vars/
│   ├── all.yml
│   └── production.yml
├── roles/
│   ├── schedulezero-server/
│   │   ├── tasks/main.yml
│   │   ├── templates/
│   │   │   └── schedulezero-server.service.j2
│   │   └── handlers/main.yml
│   └── schedulezero-handler/
│       ├── tasks/main.yml
│       ├── templates/
│       │   └── schedulezero-handler@.service.j2
│       └── handlers/main.yml
├── playbooks/
│   ├── deploy-server.yml
│   ├── deploy-handlers.yml
│   └── deploy-all.yml
└── ansible.cfg
```

### Inventory Example
```yaml
# inventory/production.yml
all:
  vars:
    ansible_user: deploy
    ansible_python_interpreter: /usr/bin/python3
    schedulezero_version: "main"
    schedulezero_deploy_path: /opt/schedulezero
    
schedulezero_servers:
  hosts:
    scheduler01.example.com:
      schedulezero_deployment: production
      
schedulezero_handlers:
  hosts:
    worker01.example.com:
      handlers:
        - name: ding-aling
          module: examples.ding_aling_handler
          class: DingAlongHandler
          port: 4244
    worker02.example.com:
      handlers:
        - name: notifications
          module: handlers.notification_handler
          class: NotificationHandler
          port: 4245
```

### Server Role Playbook
```yaml
# roles/schedulezero-server/tasks/main.yml
---
- name: Create schedulezero user
  user:
    name: schedulezero
    system: yes
    home: "{{ schedulezero_deploy_path }}"
    shell: /bin/bash

- name: Install system dependencies
  apt:
    name:
      - python3
      - python3-pip
      - python3-venv
      - git
    state: present
    update_cache: yes

- name: Clone ScheduleZero repository
  git:
    repo: https://github.com/esotericbyte/ScheduleZero.git
    dest: "{{ schedulezero_deploy_path }}"
    version: "{{ schedulezero_version }}"
    force: yes
  become_user: schedulezero

- name: Install Poetry
  shell: |
    curl -sSL https://install.python-poetry.org | python3 -
  args:
    creates: /home/schedulezero/.local/bin/poetry
  become_user: schedulezero

- name: Install Python dependencies
  shell: |
    cd {{ schedulezero_deploy_path }}
    /home/schedulezero/.local/bin/poetry install --no-dev
  become_user: schedulezero

- name: Create deployment directories
  file:
    path: "{{ schedulezero_deploy_path }}/deployments/{{ schedulezero_deployment }}/{{ item }}"
    state: directory
    owner: schedulezero
    group: schedulezero
    mode: '0755'
  loop:
    - logs
    - pids
    - data

- name: Template systemd service
  template:
    src: schedulezero-server.service.j2
    dest: /etc/systemd/system/schedulezero-server.service
    owner: root
    group: root
    mode: '0644'
  notify: reload systemd

- name: Enable and start service
  systemd:
    name: schedulezero-server
    enabled: yes
    state: started
    daemon_reload: yes
```

### Handler Role Playbook
```yaml
# roles/schedulezero-handler/tasks/main.yml
---
- name: Create handler configuration directory
  file:
    path: /etc/schedulezero/handlers
    state: directory
    owner: root
    group: root
    mode: '0755'

- name: Template handler service
  template:
    src: schedulezero-handler@.service.j2
    dest: /etc/systemd/system/schedulezero-handler@.service
    owner: root
    group: root
    mode: '0644'
  notify: reload systemd

- name: Create handler configuration files
  template:
    src: handler.env.j2
    dest: "/etc/schedulezero/handlers/{{ item.name }}.env"
    owner: root
    group: root
    mode: '0644'
  loop: "{{ handlers }}"
  notify: restart handlers

- name: Enable and start handlers
  systemd:
    name: "schedulezero-handler@{{ item.name }}"
    enabled: yes
    state: started
    daemon_reload: yes
  loop: "{{ handlers }}"
```

### Deployment Commands
```bash
# Deploy everything to production
ansible-playbook -i inventory/production.yml playbooks/deploy-all.yml

# Deploy only server
ansible-playbook -i inventory/production.yml playbooks/deploy-server.yml

# Deploy only handlers
ansible-playbook -i inventory/production.yml playbooks/deploy-handlers.yml

# Deploy to staging
ansible-playbook -i inventory/staging.yml playbooks/deploy-all.yml

# Check what would change (dry-run)
ansible-playbook -i inventory/production.yml playbooks/deploy-all.yml --check

# Deploy specific handler
ansible-playbook -i inventory/production.yml playbooks/deploy-handlers.yml \
  --extra-vars "handler_name=ding-aling"
```

### Pros
✅ **Idempotent** - safe to run multiple times  
✅ **Multi-server** deployment  
✅ **Version controlled** infrastructure  
✅ **Consistent** across environments  
✅ **Rollback** capability  
✅ **Secrets management** with Ansible Vault

### Cons
❌ Learning curve for Ansible  
❌ Requires SSH access  
❌ Playbook maintenance overhead

### When to Use
- Multiple servers to manage
- Need consistent deployments
- Infrastructure as code
- Team collaboration

---

## Pattern 4: Docker Compose (Development)

### Purpose
- **Containerized development** environment
- **Reproducible** setup
- **Isolation** from host system
- **Easy cleanup**

### docker-compose.yml
```yaml
version: '3.8'

services:
  server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: schedulezero-server
    ports:
      - "8000:8000"
    environment:
      - DEPLOYMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./deployments/production:/app/deployments/production
      - server-data:/app/data
    networks:
      - schedulezero
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  handler-ding-aling:
    build:
      context: .
      dockerfile: Dockerfile.handler
    container_name: schedulezero-handler-ding-aling
    environment:
      - HANDLER_ID=ding-aling-1
      - HANDLER_MODULE=examples.ding_aling_handler
      - HANDLER_CLASS=DingAlongHandler
      - HANDLER_PORT=4244
      - SERVER_ADDRESS=tcp://server:8000
    depends_on:
      - server
    networks:
      - schedulezero
    restart: unless-stopped

  handler-notifications:
    build:
      context: .
      dockerfile: Dockerfile.handler
    container_name: schedulezero-handler-notifications
    environment:
      - HANDLER_ID=notifications-1
      - HANDLER_MODULE=handlers.notification_handler
      - HANDLER_CLASS=NotificationHandler
      - HANDLER_PORT=4245
      - SERVER_ADDRESS=tcp://server:8000
    depends_on:
      - server
    networks:
      - schedulezero
    restart: unless-stopped

networks:
  schedulezero:
    driver: bridge

volumes:
  server-data:
```

### Dockerfile.server
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY src/ ./src/

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Create deployment directories
RUN mkdir -p deployments/production/{logs,pids,data}

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "-m", "src.schedule_zero.server", "--deployment", "production"]
```

### Dockerfile.handler
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
COPY src/ ./src/
COPY examples/ ./examples/
COPY handlers/ ./handlers/

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

CMD ["python", "-m", "src.schedule_zero.zmq_handler_base", \
     "--handler-id", "${HANDLER_ID}", \
     "--module", "${HANDLER_MODULE}", \
     "--class", "${HANDLER_CLASS}", \
     "--port", "${HANDLER_PORT}"]
```

### Commands
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f
docker-compose logs -f server
docker-compose logs -f handler-ding-aling

# Scale handlers
docker-compose up -d --scale handler-ding-aling=3

# Stop
docker-compose down

# Clean up everything
docker-compose down -v
```

### Pros
✅ Isolated environment  
✅ Reproducible builds  
✅ Easy multi-container orchestration  
✅ Port mapping  
✅ Volume management  
✅ Cross-platform

### Cons
❌ Docker overhead  
❌ Networking complexity  
❌ Not for production (use Swarm/K8s)

### When to Use
- Development with multiple developers
- Testing deployment setup
- CI/CD pipelines
- Need isolation

---

## Pattern 5: Kubernetes (Cloud Native)

### Purpose
- **Cloud-native** production
- **Auto-scaling** handlers
- **High availability**
- **Rolling updates**
- **Service discovery**

### K8s has Built-in Schedulers

**CronJobs**: K8s native job scheduling
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: example-job
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: job
            image: my-job:latest
          restartPolicy: OnFailure
```

**ScheduleZero vs K8s CronJobs:**
| Feature | ScheduleZero | K8s CronJobs |
|---------|--------------|--------------|
| **Dynamic scheduling** | ✅ API-driven | ❌ YAML-based |
| **Custom handlers** | ✅ ZMQ RPC | ❌ New containers |
| **Immediate execution** | ✅ Run now API | ❌ Create Job manually |
| **Execution logs** | ✅ Built-in tracking | ⚠️ Check pod logs |
| **Programmatic control** | ✅ REST API | ⚠️ K8s API |

**When to use ScheduleZero in K8s:**
- Need dynamic job scheduling via API
- Want persistent handlers (not ephemeral pods)
- Custom execution patterns beyond cron
- Centralized job management UI

### Kubernetes Manifests

#### Namespace
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: schedulezero
```

#### Server Deployment
```yaml
# server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: schedulezero-server
  namespace: schedulezero
spec:
  replicas: 1  # Single instance for simplicity
  selector:
    matchLabels:
      app: schedulezero-server
  template:
    metadata:
      labels:
        app: schedulezero-server
    spec:
      containers:
      - name: server
        image: schedulezero/server:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DEPLOYMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: data
          mountPath: /app/deployments/production
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: schedulezero-data
---
apiVersion: v1
kind: Service
metadata:
  name: schedulezero-server
  namespace: schedulezero
spec:
  selector:
    app: schedulezero-server
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: schedulezero-data
  namespace: schedulezero
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

#### Handler Deployment
```yaml
# handler-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: schedulezero-handler-ding-aling
  namespace: schedulezero
spec:
  replicas: 2  # Scale handlers independently!
  selector:
    matchLabels:
      app: schedulezero-handler
      handler: ding-aling
  template:
    metadata:
      labels:
        app: schedulezero-handler
        handler: ding-aling
    spec:
      containers:
      - name: handler
        image: schedulezero/handler:latest
        env:
        - name: HANDLER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name  # Use pod name as handler ID
        - name: HANDLER_MODULE
          value: "examples.ding_aling_handler"
        - name: HANDLER_CLASS
          value: "DingAlongHandler"
        - name: HANDLER_PORT
          value: "4244"
        - name: SERVER_ADDRESS
          value: "tcp://schedulezero-server:8000"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: schedulezero-handler-ding-aling-hpa
  namespace: schedulezero
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: schedulezero-handler-ding-aling
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### Ingress
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: schedulezero-ingress
  namespace: schedulezero
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - schedulezero.example.com
    secretName: schedulezero-tls
  rules:
  - host: schedulezero.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: schedulezero-server
            port:
              number: 8000
```

### Deployment Commands
```bash
# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f server-deployment.yaml
kubectl apply -f handler-deployment.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n schedulezero
kubectl get svc -n schedulezero
kubectl get ingress -n schedulezero

# Scale handlers
kubectl scale deployment schedulezero-handler-ding-aling --replicas=5 -n schedulezero

# View logs
kubectl logs -n schedulezero deployment/schedulezero-server -f
kubectl logs -n schedulezero deployment/schedulezero-handler-ding-aling -f

# Port forward for local access
kubectl port-forward -n schedulezero svc/schedulezero-server 8000:8000

# Delete everything
kubectl delete namespace schedulezero
```

### Helm Chart (Future)
```bash
# Install with Helm
helm repo add schedulezero https://charts.schedulezero.io
helm install my-schedulezero schedulezero/schedulezero \
  --set server.replicas=1 \
  --set handlers.dingAling.replicas=2
```

### Pros
✅ **Auto-scaling** handlers  
✅ **High availability**  
✅ **Rolling updates** zero-downtime  
✅ **Service discovery** built-in  
✅ **Load balancing**  
✅ **Health checks** and restarts  
✅ **Cloud-agnostic**

### Cons
❌ **Complex** setup and learning curve  
❌ **Resource overhead**  
❌ **Overkill** for small deployments

### When to Use
- Cloud production deployments
- Need high availability
- Auto-scaling required
- Multi-tenant systems

---

## Pattern 6: Distributed Autonomous Handlers

### Purpose
- **Handlers anywhere** on network
- **No central control** of handler processes
- **Heterogeneous** deployment (mix systemd, Docker, K8s)
- **Maximum flexibility**

### Architecture
```
ScheduleZero Server (scheduler only)
         ↑
         │ Handlers register themselves
         │
    ┌────┴────┬────────┬─────────┐
    │         │        │         │
Handler 1  Handler 2  Handler 3  Handler 4
(systemd)  (Docker)   (K8s Pod)  (Lambda)
Server A   Server B   K8s       AWS
```

### Implementation
Handlers are completely self-managed:

```python
# Handler runs independently
# /opt/handler/start.sh
#!/bin/bash
cd /opt/handler
poetry run python -m src.schedule_zero.zmq_handler_base \
    --handler-id "worker-$(hostname)" \
    --module my_handlers.work_handler \
    --class WorkHandler \
    --port 4244 \
    --server tcp://schedulezero.example.com:5555
```

Server just receives registrations:
```python
# No handler management in server
# Handlers connect and register themselves
# Server tracks which handlers are available
```

### Pros
✅ **Maximum flexibility**  
✅ **No SPOF** for handler management  
✅ **Mix deployment methods**  
✅ **Scale independently**  
✅ **Fault isolation**

### Cons
❌ **No central control** of handler lifecycle  
❌ **Each handler needs own deployment**  
❌ **Discovery/registration required**

### When to Use
- Large distributed systems
- Heterogeneous infrastructure
- Need maximum flexibility
- Handlers owned by different teams

---

## Comparison Matrix

| Feature | ProcessGovernor | systemd | Ansible | Docker Compose | Kubernetes |
|---------|----------------|---------|---------|----------------|------------|
| **Complexity** | Low | Medium | Medium | Medium | High |
| **Setup Time** | Minutes | Hours | Hours | Minutes | Days |
| **Multi-Machine** | ❌ | ⚠️ Manual | ✅ | ❌ | ✅ |
| **Auto-Restart** | ⚠️ Manual | ✅ | ✅ | ✅ | ✅ |
| **Auto-Scale** | ❌ | ❌ | ❌ | ⚠️ Manual | ✅ |
| **Rolling Updates** | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Resource Limits** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Health Checks** | ⚠️ Basic | ✅ | ✅ | ✅ | ✅ |
| **Logging** | File | journald | journald | Docker logs | K8s logs |
| **Cost** | Free | Free | Free | Free | $$$ (cloud) |

---

## Recommendations by Scale

### 1-10 Jobs/Day, 1-2 Handlers
→ **ProcessGovernor** or **systemd**

### 10-100 Jobs/Day, 2-5 Handlers, Single Server
→ **systemd + Ansible**

### 100-1000 Jobs/Day, 5-20 Handlers, Multiple Servers
→ **Ansible + systemd** or **Docker Swarm**

### 1000+ Jobs/Day, 20+ Handlers, Distributed
→ **Kubernetes**

### Mixed/Hybrid Environment
→ **Autonomous Handlers** (each deployment method where appropriate)

---

## Next Steps

1. ✅ Documentation complete
2. 🔨 Create deployment templates:
   - `deployments/systemd/` - systemd units
   - `deployments/ansible/` - Ansible playbooks
   - `deployments/docker/` - Docker Compose files
   - `deployments/kubernetes/` - K8s manifests
3. 🔨 Test each deployment pattern
4. 🔨 CI/CD for container builds
5. 🔨 Helm chart for K8s

---

## Questions?

- Which pattern fits your use case?
- Need help with specific deployment?
- See individual deployment READMEs in `deployments/` directory
