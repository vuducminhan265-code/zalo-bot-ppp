import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()

cursor.execute("SELECT id, status, startedAt, stoppedAt FROM execution_entity ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()
print("Executions:")
for r in rows:
    print(r)

if rows:
    last_id = rows[0][0]
    cursor.execute("SELECT data FROM execution_data WHERE executionId = ?", (last_id,))
    row = cursor.fetchone()
    if row:
        data = json.loads(row[0])
        print(f"\n--- Last Execution Data (ID {last_id}) ---")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

conn.close()
