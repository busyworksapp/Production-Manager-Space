#!/usr/bin/env python
"""Check what roles exist in the database"""
from backend.config.db_pool import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT id, name FROM roles')
rows = cursor.fetchall()
print(f'Found {len(rows)} roles:')
for row in rows:
    print(f'  - ID {row["id"]}: {row["name"]}')
cursor.close()
conn.close()
