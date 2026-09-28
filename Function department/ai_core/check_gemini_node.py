import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT nodes FROM workflow_entity WHERE id='OTLJmB2EqNZoEIFt'")
nodes = json.loads(cursor.fetchone()[0])
for n in nodes:
    if "Gemini" in n.get("name", ""):
        print(n["name"], ":", json.dumps(n.get("parameters", {}), indent=2))
