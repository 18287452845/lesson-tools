import sqlite3

conn = sqlite3.connect('storage/database.db')
cursor = conn.cursor()

# Query batch_tasks table
print("=== batch_tasks table structure ===")
cursor.execute('PRAGMA table_info(batch_tasks)')
for row in cursor.fetchall():
    print(f"  {row}")

# Query classes table
print("\n=== classes table structure ===")
cursor.execute('PRAGMA table_info(classes)')
for row in cursor.fetchall():
    print(f"  {row}")

# Query lesson_plans table
print("\n=== lesson_plans table structure ===")
cursor.execute('PRAGMA table_info(lesson_plans)')
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
