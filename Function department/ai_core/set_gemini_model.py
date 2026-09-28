import sqlite3
import json

conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()

# 1. Update workflow_entity
cursor.execute("SELECT nodes FROM workflow_entity WHERE id='OTLJmB2EqNZoEIFt'")
row = cursor.fetchone()
if row:
    nodes = json.loads(row[0])
    for n in nodes:
        if "Google Gemini" in n.get("name", "") or "GoogleGemini" in n.get("type", ""):
            # Let's set models/gemini-3.1-flash-lite (high throughput, light, fast)
            n["parameters"]["modelName"] = "models/gemini-3.1-flash-lite"
    cursor.execute("UPDATE workflow_entity SET nodes=? WHERE id='OTLJmB2EqNZoEIFt'", (json.dumps(nodes, ensure_ascii=False),))

# 2. Update workflow_history
cursor.execute("SELECT versionId, nodes FROM workflow_history WHERE workflowId='OTLJmB2EqNZoEIFt'")
rows = cursor.fetchall()
for version_id, nodes_raw in rows:
    nodes = json.loads(nodes_raw)
    for n in nodes:
        if "Google Gemini" in n.get("name", "") or "GoogleGemini" in n.get("type", ""):
            n["parameters"]["modelName"] = "models/gemini-3.1-flash-lite"
    cursor.execute("UPDATE workflow_history SET nodes=? WHERE versionId=?", (json.dumps(nodes, ensure_ascii=False), version_id))

conn.commit()
conn.close()
print("Updated modelName to models/gemini-3.1-flash-lite")
