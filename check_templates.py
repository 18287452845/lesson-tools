import asyncio
import sys
sys.path.insert(0, '/home/liyang/lesson-tools')

from backend.models.database import get_db

async def check_templates():
    db = await get_db()
    
    # Query templates
    rows = await db.fetch_all("SELECT id, name, subject, grade, file_path FROM templates")
    
    print(f"Found {len(rows)} templates:")
    for row in rows:
        print(f"  ID: {dict(row)['id']}")
        print(f"  Name: {dict(row)['name']}")
        print(f"  Subject: {dict(row)['subject']}")
        print(f"  Grade: {dict(row)['grade']}")
        print(f"  File: {dict(row)['file_path']}")
        print()

asyncio.run(check_templates())
