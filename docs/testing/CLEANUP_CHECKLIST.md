# Project Cleanup Checklist

## Status: In Progress

This document tracks the cleanup and reorganization of the ScheduleZero project in preparation for APScheduler 4.0.0a6 upgrade.

## Branch Strategy

**Current branch**: `feature/fe-htmx-and-vuetify`
**Target branch**: `feature/apscheduler-4.0.0a6` (to be created)

### Action Items
- [ ] Commit current work on frontend branch
- [ ] Create new branch: `feature/apscheduler-4.0.0a6`
- [ ] Base on main (or current stable branch)

## File Organization

### Archive Files (Already Deleted from Root)
- [x] CLEANUP_PLAN.md → archive/
- [x] COMPLETE_IMPLEMENTATION.md → archive/
- [x] CONDUCTOR_ZERO_COMPARISON.md → archive/
- [x] DEPLOYMENT_DOCUMENTATION_SUMMARY.md → archive/
- [x] REFACTORING_SUMMARY.md → archive/
- [x] TEST_SUITE_SUMMARY.md → archive/
- [x] TESTING_STATUS.md → moved to docs/testing-status.md

### Documentation Consolidation
- [x] Move old docs to archive/
- [x] Organize new docs in docs/
- [x] Create docs/testing/ directory
- [x] Create docs/deployment/ directory
- [ ] Update README.md links to new locations

### New Discord Integration Files
- [x] Created discord/ directory with:
  - discord/cogs/zmq_listener_cog.py
  - discord/config/zmq_listener.yaml
  - discord/ZMQ_LISTENER_GUIDE.md
  - discord/discord_zmq_example.py

### New Nginx Files
- [x] Created deployments/ansible/ with:
  - nginx-schedulezero.conf
  - nginx-schedulezero-simple.conf
  - setup-nginx.sh
  - docs/deployment/nginx-proxy-setup.md

### Test Organization
- [ ] Create tests/unit/
- [ ] Create tests/integration/
- [ ] Create tests/functional/
- [ ] Create tests/discord/
- [ ] Create tests/performance/
- [ ] Create tests/fixtures/
- [ ] Move existing tests to appropriate directories

## Database Cleanup

### Test Databases
- [ ] Delete `schedulezero_jobs.db` (root)
- [ ] Delete `deployments/default/schedulezero_jobs.db`
- [ ] Delete `deployments/test/schedulezero_jobs.db`
- [ ] Delete `deployments/production/schedulezero_jobs.db` (if exists)
- [ ] Delete `deployments/clock/schedulezero_jobs.db` (if exists)

### Test Artifacts
- [ ] Clean up `tests/test_output/`
- [ ] Clean up `test_output/` (if exists in root)
- [ ] Update `.gitignore` to exclude test databases

## Code Cleanup

### Remove Dead Code
- [ ] Check for unused imports
- [ ] Remove commented-out code
- [ ] Remove debug print statements
- [ ] Clean up __pycache__ directories

### Update Imports
- [ ] Verify all imports work after reorganization
- [ ] Update relative imports if needed
- [ ] Check for circular dependencies

## Configuration Files

### Environment Files
- [x] Keep `config.yaml.old` in root (reference)
- [x] Keep `portal_config.yaml` (active)
- [x] Keep `portal_config_portal2.yaml` (example)
- [ ] Review handler_registry.yaml structure

### Deployment Configs
- [ ] Verify deployments/default/ config
- [ ] Verify deployments/test/ config
- [ ] Verify deployments/production/ config
- [ ] Verify deployments/clock/ config

## Git Management

### Untracked Files to Add
High priority (core functionality):
- [ ] discord/ directory
- [ ] deployments/ansible/ configs
- [ ] docs/testing/TEST_PLAN.md
- [ ] docs/deployment/nginx-proxy-setup.md
- [ ] DISCORD_NGINX_QUICKSTART.md

Medium priority (documentation):
- [ ] docs/architecture.md
- [ ] docs/autonomous-handler-architecture.md
- [ ] docs/frontend-architecture.md
- [ ] docs/testing-status.md
- [ ] docs/README.md

Low priority (can be generated):
- [ ] docs/api/ (if contains manual docs)
- [ ] planning/ (if still relevant)

### Files to .gitignore
```gitignore
# Databases
*.db
*.db-journal
schedulezero_jobs.db
deployments/*/schedulezero_jobs.db

# Test artifacts
test_output/
tests/test_output/
tests/test_logs/
*.log

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Poetry
.venv/
poetry.lock  # Controversial - some keep it
```

## Documentation Updates

### README.md
- [ ] Update installation instructions
- [ ] Update quick start guide
- [ ] Fix broken links to moved files
- [ ] Add Discord integration section
- [ ] Add nginx proxy section
- [ ] Update testing section

### Test Documentation
- [x] Create docs/testing/TEST_PLAN.md
- [ ] Update tests/index.md
- [ ] Create tests/fixtures/README.md
- [ ] Document test execution workflow

### API Documentation
- [ ] Update API endpoint docs
- [ ] Document APScheduler a6 changes
- [ ] Add examples for new features

## APScheduler Upgrade Prep

### Pre-upgrade Checklist
- [ ] All current tests documented
- [ ] Database backup strategy defined
- [ ] Rollback plan documented
- [ ] Breaking changes identified
- [ ] Code review for affected areas

### Migration Tasks
- [ ] Delete old databases
- [ ] Update schema if needed
- [ ] Test with APScheduler 4.0.0a6
- [ ] Verify all fixtures work
- [ ] Update test assertions

## Testing Infrastructure

### Fixtures
- [ ] Review conftest.py
- [ ] Create shared fixtures module
- [ ] Document fixture usage
- [ ] Add cleanup fixtures

### Test Data
- [ ] Create test data generators
- [ ] Define test scenarios
- [ ] Document test data requirements

### CI/CD Preparation
- [ ] Draft GitHub Actions workflow
- [ ] Define test stages
- [ ] Set up code coverage
- [ ] Configure test reporting

## Timeline

### Week 1: Cleanup & Organization
- [ ] Complete file reorganization
- [ ] Clean git history
- [ ] Update documentation
- [ ] Create feature branch

### Week 2: Database & Schema
- [ ] Delete old databases
- [ ] Test APScheduler a6 schema creation
- [ ] Verify migrations work
- [ ] Document schema changes

### Week 3: Test Infrastructure
- [ ] Reorganize tests
- [ ] Fix broken tests
- [ ] Add missing unit tests
- [ ] Verify fixtures

### Week 4: Discord & Portal Tests
- [ ] Create Discord bot tests
- [ ] Create portal unit tests
- [ ] Integration testing
- [ ] Documentation

### Week 5: Integration & Functional
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Bug fixes
- [ ] Final review

### Week 6: Merge & Deploy
- [ ] All tests passing
- [ ] Documentation complete
- [ ] PR review
- [ ] Merge to main

## Success Criteria

### Phase 1: Cleanup Complete
- [ ] No dead/duplicate files
- [ ] Clear directory structure
- [ ] Updated documentation
- [ ] Clean git status

### Phase 2: Tests Pass
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No schema errors
- [ ] Code coverage > 80%

### Phase 3: Ready for Production
- [ ] All features tested
- [ ] Documentation complete
- [ ] Performance verified
- [ ] Rollback plan tested

## Notes

- Keep archive/ directory for historical reference
- Don't delete examples/ - they may be useful
- Be careful with poetry.lock - track changes carefully
- Test thoroughly before merging

## References

- [Test Plan](TEST_PLAN.md)
- [Testing Status](../testing-status.md)
- [APScheduler Changelog](https://github.com/agronholm/apscheduler/blob/master/docs/versionhistory.rst)
