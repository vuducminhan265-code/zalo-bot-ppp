import sqlite3
import json
import urllib.request
import ssl

conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT data FROM credentials_entity WHERE type='googlePalmApi'")
row = cursor.fetchone()
print("Credentials row found:", bool(row))

# In n8n credentials might be encrypted, let's see
# But we can also check if we have the API key or list models via standard endpoint
conn.close()
