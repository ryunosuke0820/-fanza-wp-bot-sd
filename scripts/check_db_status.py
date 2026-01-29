import sqlite3
from pathlib import Path

db_path = Path("data/posted.sqlite3")
if not db_path.exists():
    print("Database file not found.")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT status, count(*) FROM posted_items GROUP BY status")
    rows = cursor.fetchall()
    print("Post Status Statistics:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
    
    print("\nLatest 5 items:")
    cursor = conn.execute("SELECT product_id, status, created_at FROM posted_items ORDER BY created_at DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {row['product_id']} | {row['status']} | {row['created_at']}")
    conn.close()
