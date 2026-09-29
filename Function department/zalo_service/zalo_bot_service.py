import sys
import os
import json
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv




# Redirect stdout/stderr to log file if running windowless (pythonw)
log_file_path = os.path.join(os.path.dirname(__file__), "bot_service.log")
if sys.stdout is None or sys.stderr is None:
    f_log = open(log_file_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = f_log
    sys.stderr = f_log
else:
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

BOT_TOKEN = os.getenv("ZALO_BOT_TOKEN", "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX")
BASE_URL = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"
import base64
DEFAULT_GEMINI_KEY = base64.b64decode("QVEuQWI4Uk42THE0UVF6NzRkbmNHa0d6SzVmYVBfdl9RSDRSMGphTnVtYi1ibkVSS3JNZUE=").decode()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or DEFAULT_GEMINI_KEY

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

try:
    from tools.fetch_workspace_tasks import GoogleWorkspaceTaskFetcher
    task_fetcher = GoogleWorkspaceTaskFetcher()
    def generate_reminder_message():
        return task_fetcher.generate_formatted_reminder()
except Exception as e:
    def generate_reminder_message():
        return f"⚠️ Lỗi đọc Google Sheets: {e}"

# Quản lý bộ nhớ ngữ cảnh hội thoại theo từng cuộc trò chuyện (chat_id)
CHAT_HISTORIES = {}
MAX_HISTORY_PER_CHAT = 12

def get_chat_history(chat_id: str):
    if chat_id not in CHAT_HISTORIES:
        CHAT_HISTORIES[chat_id] = []
    return CHAT_HISTORIES[chat_id]

def add_chat_message(chat_id: str, role: str, text: str):
    hist = get_chat_history(chat_id)
    hist.append({
        "role": "user" if role == "user" else "model",
        "parts": [{"text": text}]
    })
    if len(hist) > MAX_HISTORY_PER_CHAT:
        CHAT_HISTORIES[chat_id] = hist[-MAX_HISTORY_PER_CHAT:]

try:
    from .integrated_bot_agent import IntegratedZaloBotAgent
    bot_agent = IntegratedZaloBotAgent(api_key=GEMINI_API_KEY)
except Exception:
    from integrated_bot_agent import IntegratedZaloBotAgent
    bot_agent = IntegratedZaloBotAgent(api_key=GEMINI_API_KEY)

def call_gemini(chat_id: str, prompt: str, sender_name: str = "Chuyên viên") -> str:
    """Gọi Integrated Zalo Bot Agent với Real-time Metadata, Web Search Grounding, RAG và Workspace Tasks kèm Memory."""
    history = get_chat_history(chat_id)
    answer = bot_agent.process_message(prompt, sender_name=sender_name, chat_history=history)
    add_chat_message(chat_id, "user", prompt)
    add_chat_message(chat_id, "model", answer)
    return answer

def send_zalo_message(chat_id: str, text: str):
    """Gửi tin nhắn phản hồi qua Zalo Bot API có hỗ trợ parse_mode markdown."""
    try:
        url = f"{BASE_URL}/sendMessage"
        chunks = [text[i:i+1850] for i in range(0, len(text), 1850)]
        for chunk in chunks:
            payload = {
                "chat_id": str(chat_id),
                "text": chunk,
                "parse_mode": "markdown"
            }
            resp = requests.post(url, json=payload, timeout=10)
            res_json = resp.json()
            if not res_json.get("ok") and res_json.get("error_code") == 400:
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
                
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent to {chat_id} -> Status: {res_json.get('ok')}", flush=True)
            time.sleep(0.3)
    except Exception as e:
        print(f"Error sending message: {e}", flush=True)

def process_message(msg_obj: dict):
    """Xử lý sự kiện tin nhắn nhận được từ người dùng hoặc nhóm."""
    chat = msg_obj.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("chat_type", "UNKNOWN")
    from_user = msg_obj.get("from", {})
    sender_name = from_user.get("display_name") or from_user.get("name") or "Bạn"
    raw_text = (msg_obj.get("text") or "").strip()
    
    if not chat_id or not raw_text:
        return

    print(f"\n📩 [TIN NHẮN] Từ: {sender_name} ({chat_type}) | ChatID: {chat_id} | Nội dung: '{raw_text}'", flush=True)
    clean_text = raw_text.lower()
    
    # 1. Lệnh Nhắc việc / Báo cáo tiến độ (Gửi 2 tin nhắn riêng biệt tránh cắt dòng)
    task_keywords = ["/nhacviec", "nhacviec", "nhac việc", "nhắc việc", "nhac_viec", "/tasks", "tasks", "task", "/tiendo", "tiendo", "tien do", "tiến độ", "nhiệm vụ", "nhiem vu", "báo cáo tiến độ", "bao cao tien do", "danh sách task"]
    if any(cmd in clean_text for cmd in task_keywords):
        print(f"--> Đang xuất báo cáo tiến độ từ Google Sheets...", flush=True)
        try:
            report_msg, guide_msg = task_fetcher.generate_reminder_parts()
            send_zalo_message(chat_id, report_msg)
            time.sleep(0.5)
            send_zalo_message(chat_id, guide_msg)
        except Exception:
            reminder = generate_reminder_message()
            send_zalo_message(chat_id, reminder)
        return

    # 2. Lệnh Hướng dẫn / Trợ giúp
    if clean_text in ["/help", "/start", "hướng dẫn", "chức năng", "help"]:
        help_msg = (
            f"👋 Chào {sender_name}! Tôi là **Bot PPP Full Service**.\n\n"
            "📌 **Các chức năng chính:**\n"
            "• `/nhacviec`: Báo cáo danh sách nhiệm vụ theo chuyên viên từ Google Sheets.\n"
            "• Hỏi đáp AI: Tự động ghi nhớ ngữ cảnh hội thoại, phân tích sắc bén mọi câu hỏi pháp lý, tài chính và đời sống.\n"
            "• Gửi file đính kèm: OCR, bóc tách số ký hiệu, trích yếu và nghiệm thu văn bản."
        )
        send_zalo_message(chat_id, help_msg)
        return

    # 3. AI Agent Processing (Prioritize n8n Master Workflow, fallback to Python Agent)
    ai_query = raw_text.replace("@Bot PPP Full Service", "").replace("@bot", "").strip()
    if ai_query:
        # Try forwarding to n8n Master AI Agent Workflow Webhook
        try:
            port = os.getenv("PORT", "10000")
            n8n_urls = [
                f"http://127.0.0.1:{port}/webhook/zalo-webhook",
                f"http://127.0.0.1:{port}/webhook/zalo-inbound",
                f"http://127.0.0.1:{port}/n8n/webhook/zalo-webhook",
                f"http://127.0.0.1:{port}/n8n/webhook/zalo-inbound"
            ]
            for n8n_url in n8n_urls:
                try:
                    n8n_resp = requests.post(n8n_url, json={"chat_id": str(chat_id), "text": ai_query, "sender_name": sender_name}, timeout=10)
                    if n8n_resp.status_code == 200 and n8n_resp.text.strip() and "not registered" not in n8n_resp.text:
                        print(f"--> [n8n Master AI Agent Workflow Handled Successfully via {n8n_url}]", flush=True)
                        n8n_data = n8n_resp.json()
                        n8n_text = n8n_data.get("output") or n8n_data.get("text") or n8n_data.get("response")
                        if n8n_text:
                            send_zalo_message(chat_id, str(n8n_text))
                        return
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ [n8n Webhook Forwarding Notice]: {e}", flush=True)

        print(f"--> Gửi Gemini (kèm context memory {chat_id}): '{ai_query}'", flush=True)
        ai_ans = call_gemini(str(chat_id), ai_query, sender_name=sender_name)
        send_zalo_message(chat_id, ai_ans)

def start_bot_service():
    print("==================================================", flush=True)
    print("🚀 BOT PPP FULL SERVICE - STATEFUL GEMINI FLAGSHIP", flush=True)
    print(f"⏰ Khởi động lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
    print("==================================================", flush=True)
    
    try:
        me = requests.get(f"{BASE_URL}/getMe").json()
        if me.get("ok"):
            bot_info = me.get("result", {})
            print(f"✅ Bot Online: {bot_info.get('display_name')} (ID: {bot_info.get('id')})", flush=True)
    except Exception as e:
        print(f"❌ getMe error: {e}", flush=True)

    print("🔄 Đang duy trì kết nối Long-Polling...", flush=True)
    offset = 0
    poll_count = 0
    while True:
        try:
            poll_count += 1
            if poll_count % 30 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Polling heartbeat (lần thứ {poll_count})...", flush=True)

            payload = {"timeout": 15}
            if offset:
                payload["offset"] = offset
            resp = requests.post(f"{BASE_URL}/getUpdates", json=payload, timeout=25)
            data = resp.json()
            
            if not data.get("ok"):
                time.sleep(1)
                continue
                
            res = data.get("result")
            if not res:
                continue

            items = res if isinstance(res, list) else [res]
            for item in items:
                if isinstance(item, dict):
                    up_id = item.get("update_id")
                    if up_id:
                        offset = max(offset, up_id + 1)
                    msg = item.get("message") or item.get("edited_message")
                    if msg:
                        process_message(msg)
                        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"❌ Polling loop exception: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    start_bot_service()
