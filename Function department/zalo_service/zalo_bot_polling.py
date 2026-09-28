import requests
import json
import time
import os

BOT_TOKEN = "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX"
BASE_URL = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

def main():
    print("=== ZALO OFFICIAL BOT LISTENER STARTING ===")
    
    # 1. Check getMe
    res = requests.get(f"{BASE_URL}/getMe")
    print("getMe:", res.json())
    
    # 2. Delete webhook just in case so getUpdates works cleanly
    try:
        del_wh = requests.post(f"{BASE_URL}/deleteWebhook")
        print("deleteWebhook:", del_wh.json())
    except Exception as e:
        print("deleteWebhook err:", e)
        
    print("\n[READY] Listening for updates... (Mention @Bot PPP Full Service in the group or chat with bot)")
    
    offset = None
    while True:
        try:
            payload = {"timeout": 20}
            if offset is not None:
                payload["offset"] = offset
                
            resp = requests.post(f"{BASE_URL}/getUpdates", json=payload, timeout=25)
            data = resp.json()
            
            if not data.get("ok"):
                if data.get("error_code") == 408:
                    # Timeout, normal for long polling
                    continue
                print(f"[getUpdates warning]: {data}")
                time.sleep(2)
                continue
                
            results = data.get("result", [])
            if results:
                print(f"\n>>> RECEIVED {len(results)} UPDATE(S):")
                for update in results:
                    print(json.dumps(update, indent=2, ensure_ascii=False))
                    update_id = update.get("update_id")
                    if update_id is not None:
                        offset = update_id + 1
                        
                    # Extract chat info
                    msg = update.get("message") or update.get("edited_message")
                    if msg:
                        chat = msg.get("chat", {})
                        chat_id = chat.get("id")
                        chat_type = chat.get("type")
                        text = msg.get("text", "")
                        from_user = msg.get("from", {}).get("display_name") or msg.get("from", {}).get("name") or "User"
                        
                        print(f"\n[EVENT] ChatID: {chat_id} ({chat_type}) | From: {from_user} | Msg: {text}")
                        
                        # Auto reply test
                        reply_text = f"Chào {from_user}! Bot PPP Full Service đã nhận được tin nhắn: '{text}'."
                        send_res = requests.post(f"{BASE_URL}/sendMessage", json={
                            "chat_id": str(chat_id),
                            "text": reply_text
                        })
                        print(f"Reply status: {send_res.json()}")
                        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Error in polling loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
