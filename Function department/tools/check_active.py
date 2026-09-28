import sqlite3

conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()

cursor.execute("SELECT id, name, active FROM workflow_entity WHERE id='OTLJmB2EqNZoEIFt'")
print("workflow_entity:", cursor.fetchall())

cursor.execute("SELECT * FROM webhook_entity")
print("webhook_entity:", cursor.fetchall())

conn.close()
