# ScheduleZero: APScheduler 4.0.0a6 Upgrade - Executive Summary

## Current Status

**Branch**: `feature/fe-htmx-and-vuetify`
**APScheduler Version**: 4.0.0a5 → upgrading to 4.0.0a6
**Test Status**: Schema mismatch causing failures

## What We've Created

### 1. Discord Bot ZeroMQ Integration ✅
- **ZMQ Listener Cog**: Receives events from ScheduleZero server
- **Configuration**: `discord/config/zmq_listener.yaml`
- **Documentation**: `discord/ZMQ_LISTENER_GUIDE.md`
- **Example Bot**: `discord/discord_zmq_example.py`

**Status**: Code complete, needs testing

### 2. Nginx Reverse Proxy Configuration ✅
- **Simple Config**: Quick subdomain setup
- **Full Config**: All options, both subdomain and path-based
- **Setup Script**: Automated nginx configuration
- **Documentation**: Complete setup guide with troubleshooting

**Status**: Code complete, ready for deployment

### 3. Comprehensive Test Plan ✅
- **Test Categories**: Unit, Integration, Functional, Performance, Discord
- **Organization**: New directory structure for tests
- **Documentation**: TEST_PLAN.md with 6-week execution plan
- **Cleanup Checklist**: Step-by-step project reorganization

**Status**: Planning complete, execution pending

## Key Issues Identified

### 1. Database Schema Outdated ⚠️
**Problem**: APScheduler 4.0.0a6 added `metadata` column to `tasks` table
**Impact**: 60+ tests failing
**Solution**: Delete old databases, let APScheduler recreate schema

### 2. Missing Component Tests ⚠️
**Problem**: No isolated tests for portal/frontend components
**Impact**: Can't verify individual component behavior
**Solution**: Create unit tests in `tests/unit/`

### 3. No Discord Bot Tests ⚠️
**Problem**: New Discord integration has no tests
**Impact**: Can't verify functionality
**Solution**: Create `tests/discord/` with mocked Discord environment

## Recommended Next Steps

### Option A: Quick Fix (1-2 days)
1. Delete all `schedulezero_jobs.db` files
2. Run existing tests
3. Fix failing tests
4. Verify APScheduler a6 works

**Pros**: Fast, gets tests passing
**Cons**: Doesn't address structural issues

### Option B: Comprehensive Approach (6 weeks)
1. **Week 1**: Project cleanup and reorganization
2. **Week 2**: Unit tests for components
3. **Week 3**: Fix integration tests
4. **Week 4**: Discord bot tests
5. **Week 5**: Functional tests
6. **Week 6**: Merge and deploy

**Pros**: Proper test coverage, maintainable
**Cons**: Takes time

### Option C: Hybrid Approach (2 weeks) 👈 RECOMMENDED
1. **Days 1-2**: Create branch, delete old DBs, fix critical tests
2. **Days 3-5**: Add portal unit tests
3. **Days 6-8**: Add Discord bot tests
4. **Days 9-10**: Documentation and final testing

**Pros**: Balances speed with quality
**Cons**: Still leaves some technical debt

## Branch Strategy

### Recommended Flow

```bash
# Current work
git checkout feature/fe-htmx-and-vuetify
git add discord/ deployments/ansible/ docs/testing/
git commit -m "Add Discord bot and nginx integration"

# Create upgrade branch from main
git checkout main
git pull origin main
git checkout -b feature/apscheduler-4.0.0a6

# Cherry-pick Discord/nginx work if needed
git cherry-pick <commit-hash>

# Start testing
rm schedulezero_jobs.db deployments/*/schedulezero_jobs.db
poetry run pytest tests/ -v
```

## Critical Decisions Needed

### 1. Branch Strategy
- [ ] Create new branch `feature/apscheduler-4.0.0a6`?
- [ ] Continue on `feature/fe-htmx-and-vuetify`?
- [ ] Merge frontend work first, then upgrade?

### 2. Test Approach
- [ ] Option A: Quick fix
- [ ] Option B: Comprehensive
- [ ] Option C: Hybrid

### 3. Discord Bot Testing
- [ ] Test now (before server upgrade)
- [ ] Test after (with stable server)
- [ ] Skip for now (test manually)

### 4. Database Migration
- [ ] Delete and recreate (simple)
- [ ] Migrate existing data (complex)
- [ ] Keep old format (not possible)

## Files Created Today

### Documentation
- `docs/testing/TEST_PLAN.md` - Comprehensive test strategy
- `docs/testing/CLEANUP_CHECKLIST.md` - Project cleanup tasks
- `docs/deployment/nginx-proxy-setup.md` - Nginx guide
- `DISCORD_NGINX_QUICKSTART.md` - Quick reference

### Code
- `discord/cogs/zmq_listener_cog.py` - Discord ZMQ listener
- `discord/config/zmq_listener.yaml` - Configuration
- `discord/discord_zmq_example.py` - Example bot
- `discord/ZMQ_LISTENER_GUIDE.md` - Complete guide

### Configuration
- `deployments/ansible/nginx-schedulezero.conf` - Full nginx config
- `deployments/ansible/nginx-schedulezero-simple.conf` - Simple config
- `deployments/ansible/setup-nginx.sh` - Setup script

## What to Do Right Now

### Immediate Actions (Next 30 minutes)

1. **Review Documents**
   - Read TEST_PLAN.md
   - Read CLEANUP_CHECKLIST.md
   - Decide on approach

2. **Make Decisions**
   - Choose Option A, B, or C
   - Decide on branch strategy
   - Set timeline

3. **Start Execution**
   - Create branch if needed
   - Delete old databases
   - Run one simple test

### Example: Quick Start (Option C)

```bash
# 1. Create branch
git checkout -b feature/apscheduler-4.0.0a6

# 2. Clean databases
rm schedulezero_jobs.db
rm deployments/test/schedulezero_jobs.db

# 3. Run simple test
poetry run pytest tests/test_execution_logging.py -v

# 4. Check results
# If passes: Great! Move to next test
# If fails: Debug and fix

# 5. Commit progress
git add -A
git commit -m "Clean databases and verify APScheduler 4.0.0a6"
```

## Questions to Answer

1. **Timeline**: How urgent is the APScheduler upgrade?
2. **Resources**: Who will work on tests? Just you or team?
3. **Risk**: What's the impact if we stay on a5?
4. **Dependencies**: Does Discord bot need working server first?
5. **Deployment**: When do we need this in production?

## Support Materials

- [Test Plan](docs/testing/TEST_PLAN.md) - Detailed test strategy
- [Cleanup Checklist](docs/testing/CLEANUP_CHECKLIST.md) - Step-by-step tasks
- [Testing Status](docs/testing-status.md) - Current state
- [Discord Guide](discord/ZMQ_LISTENER_GUIDE.md) - Discord integration
- [Nginx Guide](docs/deployment/nginx-proxy-setup.md) - Reverse proxy setup

## Recommendation

**Start with Option C (Hybrid Approach)**:
1. Create branch today
2. Clean databases and run basic tests (1 day)
3. Add critical unit tests (3 days)
4. Test Discord bot with stable server (2 days)
5. Integration testing (2 days)
6. Documentation and merge (2 days)

This gives you working tests in 2 weeks while setting foundation for better coverage.

---

**Next Step**: Choose your approach and let's create the branch!
