import requests
import json
import time
import sys

BOT_TOKEN = "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX"
BASE_URL = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

print("=== STARTING INTERACTIVE TEST ===", flush=True)

# Test getMe
me = requests.get(f"{BASE_URL}/getMe").json()
print("getMe:", json.dumps(me, ensure_ascii=False), flush=True)

while True:
    try:
        r = requests.post(f"{BASE_URL}/getUpdates", json={"timeout": 15}, timeout=20)
        data = r.json()
        
        if not data.get("ok"):
            if data.get("error_code") != 408:
                print("Polling non-timeout error:", data, flush=True)
            continue
            
        print(">>> INCOMING EVENT RAW:", json.dumps(data, ensure_ascii=False, indent=2), flush=True)
        
        res = data.get("result")
        items = res if isinstance(res, list) else ([res] if res else [])
        
        for item in items:
            if isinstance(item, dict):
                msg = item.get("message") or item.get("edited_message")
                if msg:
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    sender = msg.get("from", {}).get("display_name", "User")
                    print(f"--> Received from {sender} in chat {chat_id}: '{text}'", flush=True)
                    
                    reply = f"Bot đã nhận được: '{text}'. Chào {sender}!"
                    send_resp = requests.post(f"{BASE_URL}/sendMessage", json={
                        "chat_id": str(chat_id),
                        "text": reply
                    }).json()
                    print(f"<-- Reply status: {send_resp}", flush=True)
    except Exception as e:
        print("Polling exception:", e, flush=True)
        time.sleep(2)
