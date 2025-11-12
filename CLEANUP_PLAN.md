# Cleanup Plan - ScheduleZero Cruft Removal

## Phase 1: Safe Deletions (Confirmed Obsolete)

### Old Deployment Scripts (Replaced by governor.py)
- [ ] start_all.py
- [ ] start_clock_deployment.py
- [ ] start_clock_server.py
- [ ] stop_clock_deployment.py
- [ ] start_clock_with_handler.ps1

### ZeroRPC Code (Replaced by ZMQ)
- [ ] src/schedule_zero/zerorpc_registration_server.py
- [ ] src/schedule_zero/handler_example.py
- [ ] src/schedule_zero/handlers/base.py (zerorpc version)
- [ ] src/schedule_zero/schedule_zero.py (old entry point)

### Test Cruft
- [ ] test_schedule.py (root level)
- [ ] test_apscheduler.py (root level)
- [ ] test_logging_format.py (temporary)
- [ ] tests/test_handler.py.zerorpc_backup

### Database Files (Root Level)
- [ ] test_scheduler.db
- [ ] schedulezero_jobs.db (move to deployments/)

### Old Templates
- [ ] templates/ directory (moved to portal/)

## Phase 2: Careful Review

### Job Execution Logging
Decision needed: Keep database logging or go fully file-based?
- src/schedule_zero/job_execution_log.py
- src/schedule_zero/api/job_execution_*_api.py

## Phase 3: Documentation Updates

### Must Update
- [ ] README.md - Remove zerorpc, add governor
- [ ] REFACTORING_SUMMARY.md - Mark as historical or delete
- [ ] DEPLOYMENT_GUIDE.md - Use governor instead

## Commands to Execute

```powershell
# Phase 1: Delete obsolete files
Remove-Item start_all.py, start_clock_deployment.py, start_clock_server.py, stop_clock_deployment.py, start_clock_with_handler.ps1
Remove-Item src/schedule_zero/zerorpc_registration_server.py, src/schedule_zero/handler_example.py, src/schedule_zero/schedule_zero.py
Remove-Item src/schedule_zero/handlers/base.py
Remove-Item test_schedule.py, test_apscheduler.py, test_logging_format.py
Remove-Item tests/test_handler.py.zerorpc_backup -ErrorAction SilentlyContinue
Remove-Item test_scheduler.db, schedulezero_jobs.db
Remove-Item -Recurse -Force templates/

# Phase 2: Move to archive (if unsure)
New-Item -ItemType Directory -Path archive -Force
Move-Item REFACTORING_SUMMARY.md archive/
```
