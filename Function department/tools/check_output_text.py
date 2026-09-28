import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT data FROM execution_data WHERE executionId = 44")
row = cursor.fetchone()
if row:
    raw = json.loads(row[0])
    # Search for text or output
    def find_strings(obj):
        if isinstance(obj, str):
            if "Sở Tài chính" in obj or "ngày" in obj or "chào" in obj:
                print("FOUND TEXT IN EXECUTION:")
                print(obj)
                print("="*40)
        elif isinstance(obj, dict):
            for v in obj.values(): find_strings(v)
        elif isinstance(obj, list):
            for item in obj: find_strings(item)
    find_strings(raw)
conn.close()
