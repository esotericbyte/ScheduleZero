"""Check what schedules are in the test database."""
import sqlite3
from pathlib import Path

db_path = Path("deployments/test/schedulezero_jobs.db")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables in database: {tables}\n")

# Check schedules
cursor.execute("SELECT id, task_id, trigger, next_fire_time FROM schedules")
rows = cursor.fetchall()

print(f"Schedules ({len(rows)} total):")
print("-" * 80)
for row in rows:
    schedule_id, task_id, trigger, next_fire_time = row
    print(f"ID: {schedule_id}")
    print(f"  Task: {task_id}")
    print(f"  Trigger: {trigger[:100]}...")  # Truncate trigger data
    print(f"  Next Fire: {next_fire_time}")
    print()

# Check tasks
cursor.execute("SELECT id, func, executor, max_running_jobs FROM tasks")
rows = cursor.fetchall()

print(f"\nTasks ({len(rows)} total):")
print("-" * 80)
for row in rows:
    task_id, func, executor, max_running = row
    print(f"ID: {task_id}")
    print(f"  Function: {func}")
    print(f"  Executor: {executor}")
    print(f"  Max Running: {max_running}")
    print()

conn.close()
