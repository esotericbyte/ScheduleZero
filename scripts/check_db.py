import sqlite3

conn = sqlite3.connect('schedulezero_jobs.db')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check tasks
cursor.execute('SELECT COUNT(*) FROM tasks')
print('Tasks count:', cursor.fetchone()[0])

# Check schedules
cursor.execute('SELECT COUNT(*) FROM schedules')
print('Schedules count:', cursor.fetchone()[0])

# Get all schedules
cursor.execute('SELECT id, task_id, next_fire_time, paused FROM schedules')
schedules = cursor.fetchall()
print('Schedules:')
for s in schedules:
    print(f'  ID={s[0]}, task_id={s[1]}, next_fire_time={s[2]}, paused={s[3]}')

conn.close()
