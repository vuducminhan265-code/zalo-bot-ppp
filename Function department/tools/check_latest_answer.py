import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT data FROM execution_data WHERE executionId = (SELECT id FROM execution_entity ORDER BY id DESC LIMIT 1)")
row = cursor.fetchone()
if row:
    raw = json.loads(row[0])
    def find_strings(obj):
        if isinstance(obj, str):
            if "lãnh đạo" in obj.lower() or "thoa" in obj.lower() or "hoàng" in obj.lower() or "2026" in obj:
                print("--- LATEST ANSWER ---")
                print(obj)
                print("="*40)
        elif isinstance(obj, dict):
            for v in obj.values(): find_strings(v)
        elif isinstance(obj, list):
            for item in obj: find_strings(item)
    find_strings(raw)
conn.close()
