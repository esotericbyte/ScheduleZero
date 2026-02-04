# ScheduleZero Deployment Architecture Decision

## Executive Summary

ProcessGovernor is **essential for testing** but **not the primary production pattern**. ScheduleZero is designed as a distributed system where handlers are autonomous.

## Governor Use Cases

### ✅ Keep ProcessGovernor For:
1. **Development/Testing** - Primary use case
2. **Local deployments** - Single developer machine
3. **Edge/IoT devices** - Resource-constrained environments
4. **Simple deployments** - < 5 handlers, single machine
5. **Desktop applications** - Embedded job scheduling

### ❌ Don't Use ProcessGovernor For:
1. **Distributed production** - Handlers on multiple servers
2. **Cloud deployments** - Use K8s/orchestration
3. **High availability** - Need redundancy across machines
4. **Large scale** - 10+ handlers or high job volume

## Architecture Patterns by Environment

### Pattern 1: Development (Current - ProcessGovernor)
```
ProcessGovernor
  ├── Server process
  └── Handler processes
```
**Status**: ✅ Keep as-is for testbed

### Pattern 2: Single Server Production
```
systemd (or Windows Services)
  ├── schedulezero-server.service
  ├── schedulezero-handler@ding-aling.service
  └── schedulezero-handler@notifications.service
```
**Recommended**: Ansible + systemd for automation

### Pattern 3: Distributed Production
```
ScheduleZero Server (Machine 1)
         ↑
         │ ZMQ over network
         │
    ┌────┴────┬─────────┐
Handler A  Handler B  Handler C
(Machine 2) (Machine 3) (Machine 4)
```
**Recommended**: Handlers self-manage with systemd/Docker

### Pattern 4: Cloud Native
```
Kubernetes Cluster
  ├── schedulezero-server (Deployment)
  └── schedulezero-handler-X (Deployments with HPA)
```
**Recommended**: K8s manifests or Helm chart

## Decision Matrix

| Deployment Type | Tool | Governor Role |
|----------------|------|---------------|
| **Local Dev** | ProcessGovernor | ✅ Primary |
| **CI/CD Testing** | ProcessGovernor or Docker Compose | ✅ For integration tests |
| **Single Server Prod** | Ansible + systemd | ❌ Not needed (systemd handles it) |
| **Multi-Server Prod** | Ansible + systemd | ❌ Not needed (handlers autonomous) |
| **Container Dev** | Docker Compose | ❌ Not needed (Compose handles it) |
| **Production Cloud** | Kubernetes | ❌ Not needed (K8s handles it) |

## Comparison to Other Schedulers

### vs. K8s CronJobs
- **K8s CronJobs**: Static YAML-defined schedules, creates pods per job
- **ScheduleZero**: Dynamic API-driven schedules, persistent handlers

### vs. Airflow/Celery
- **Airflow**: Workflow orchestration, DAGs, heavyweight
- **ScheduleZero**: Lightweight job scheduling, simpler model

### vs. cron/systemd.timer
- **cron/systemd.timer**: Static config files, runs scripts
- **ScheduleZero**: Dynamic scheduling, RPC to handlers, API control

## Architectural Principles

### 1. **Handlers Are Autonomous**
Handlers should manage their own lifecycle:
- Start independently
- Register with server
- Reconnect on failure
- No dependency on central control

### 2. **Server Is Scheduler Only**
Server responsibilities:
- ✅ Schedule jobs (APScheduler)
- ✅ Track executions
- ✅ Manage handler registry
- ❌ Control handler processes (in distributed mode)

### 3. **ProcessGovernor Is Optional Tool**
- For convenience in development
- For simple single-machine deployments
- Not required for production
- Not part of core architecture

## Integration Approach

### Option A: Current (Recommended)
**Keep ProcessGovernor as standalone tool for dev/testing**

```
src/schedule_zero/
  ├── server.py              # Core server
  ├── process_governor.py    # Optional tool
  └── governor_base.py       # ABC for future governors
```

**Pros**:
- Clear separation of concerns
- Server stays simple
- Governor optional
- Easy to document different deployment patterns

### Option B: Integrate into Server
**Add `--manage-local-handlers` flag**

```bash
poetry run python -m src.schedule_zero.server \
    --deployment production \
    --manage-local-handlers
```

**Pros**:
- One process to start in dev
- Convenient flag for local development

**Cons**:
- Complicates server code
- Blurs responsibilities
- Confusing for distributed deployments

### Option C: Split by Deployment Type
**Different entry points**

```bash
# Development (with process management)
schedulezero-dev start

# Production (server only)
schedulezero-server --deployment production
```

**Cons**:
- More complex packaging
- User confusion about which to use

## Recommendation

### ✅ **Option A: Keep Current Architecture**

**Document clearly**:
1. ProcessGovernor = development/testing tool
2. Production = handlers self-manage
3. Multiple deployment patterns supported
4. Governor ABC enables future extensions (ThreadGovernor, etc.)

**Communication Strategy**:
- README: Emphasize "Quick Start with ProcessGovernor for testing"
- Docs: Separate "Development Guide" vs "Production Deployment"
- Examples: Show both patterns clearly

## Implementation Plan

### Immediate (Documentation)
1. ✅ Update README with clear use case guidance
2. ✅ Create comprehensive deployment guide
3. ✅ Add deployment templates (systemd, Ansible, Docker, K8s)
4. ✅ Document when to use which pattern

### Short Term (Examples)
5. 🔨 Create example systemd units
6. 🔨 Create Ansible playbooks
7. 🔨 Create Docker Compose example
8. 🔨 Create K8s manifests

### Medium Term (Tooling)
9. 🔨 Add health check API endpoint
10. 🔨 Add metrics export (Prometheus)
11. 🔨 Create Helm chart
12. 🔨 CI/CD for container images

## Conclusion

**ProcessGovernor** is valuable but specialized:
- ✅ Essential for **testbed and development**
- ✅ Useful for **simple single-machine deployments**
- ❌ Not the pattern for **distributed production**
- ❌ Not needed when **using orchestration** (K8s, systemd, etc.)

**Key Message**: ScheduleZero is a **distributed job scheduler**, and handlers are **autonomous services**. ProcessGovernor is a **convenience tool** for development, not a production requirement.

---

**Status**: Architecture decision documented, deployment guide complete, ready to proceed with examples and templates.
