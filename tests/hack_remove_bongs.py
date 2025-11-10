"""Quick hack to remove hour bongs from the clock database."""
import sqlite3

db_path = "deployments/clock/schedulezero_jobs.db"

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count bongs before
cursor.execute("SELECT COUNT(*) FROM schedules WHERE id LIKE 'bong_%'")
before_count = cursor.fetchone()[0]
print(f"Hour bongs before: {before_count}")

# Delete them
cursor.execute("DELETE FROM schedules WHERE id LIKE 'bong_%'")
conn.commit()

# Count after
cursor.execute("SELECT COUNT(*) FROM schedules WHERE id LIKE 'bong_%'")
after_count = cursor.fetchone()[0]
print(f"Hour bongs after: {after_count}")

# Show remaining schedules
cursor.execute("SELECT COUNT(*) FROM schedules")
total = cursor.fetchone()[0]
print(f"Total schedules remaining: {total}")

# Show a few quarter chimes
cursor.execute("SELECT id FROM schedules WHERE id LIKE 'chime_%' LIMIT 5")
samples = cursor.fetchall()
print(f"\nSample remaining schedules:")
for row in samples:
    print(f"  {row[0]}")

conn.close()
print(f"\n✅ Deleted {before_count} hour bongs from {db_path}")
