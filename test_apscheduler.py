"""Quick test to see if APScheduler with AsyncJobExecutor works."""
import logging
import asyncio
from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.executors.async_ import AsyncJobExecutor

logging.basicConfig(level=logging.DEBUG)

async def my_job(msg):
    print(f"JOB EXECUTED: {msg}")

async def test():
    ds = SQLAlchemyDataStore('sqlite+aiosqlite:///test_scheduler.db')
    s = AsyncScheduler(ds, job_executors={'default': AsyncJobExecutor()})
    
    async with s:
        await s.configure_task('my_task', func=my_job)
        await s.add_schedule('my_task', 'interval', seconds=2, args=['Hello from schedule!'], id='test_schedule')
        print("Schedule added, waiting 6 seconds for executions...")
        await asyncio.sleep(6)
        print("Done waiting")

asyncio.run(test())
