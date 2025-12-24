import sqlite3
conn = sqlite3.connect('storage/database.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in cursor.fetchall()])

# Check templates
cursor.execute('SELECT * FROM templates')
templates = cursor.fetchall()
print(f"\nFound {len(templates)} templates:")
for t in templates:
    print(f"  ID: {t['id']}")
    print(f"  Name: {t['name']}")
    print(f"  File: {t['file_path']}")
    print()
