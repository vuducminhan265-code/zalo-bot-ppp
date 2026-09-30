import sys
import os
import json
import time
import re
import requests
import threading
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

# Tokens for Dual Zalo Bot Setup
BOT1_TOKEN = os.getenv("ZALO_BOT_TOKEN_1") or os.getenv("ZALO_BOT_TOKEN") or "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX"
BOT2_TOKEN = os.getenv("ZALO_BOT_TOKEN_2") or "916808225583576762:qyESEAzJfULNqmolAsxDwfskYoEhQXPDNPytmKbTOeFquMpnOkmLQOURsBEgJDln"

import base64
DEFAULT_GEMINI_KEY = base64.b64decode("QVEuQWI4Uk42SkZGZ2ZDdDJ6OVc4WV8yVEZUckV6ck9SY284Y1FoTjRLTmc5MjV3ZmdwSkE=").decode()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or DEFAULT_GEMINI_KEY

BOTS = {
    "bot1": {
        "id": "bot1",
        "name": "Zalo Bot 1 - Task Master & OCR Reviewer",
        "token": BOT1_TOKEN,
        "base_url": f"https://bot-api.zaloplatforms.com/bot{BOT1_TOKEN}",
        "webhook": "zalo-task-webhook"
    },
    "bot2": {
        "id": "bot2",
        "name": "Zalo Bot 2 - Legal RAG & Web Search Specialist",
        "token": BOT2_TOKEN,
        "base_url": f"https://bot-api.zaloplatforms.com/bot{BOT2_TOKEN}",
        "webhook": "zalo-legal-webhook"
    }
}

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

def send_zalo_message(chat_id: str, text: str, bot_key: str = "bot1"):
    """Gửi tin nhắn phản hồi qua Zalo Bot API tương ứng với bot_key."""
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])
    base_url = bot_cfg["base_url"]
    try:
        url = f"{base_url}/sendMessage"
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
                
            print(f"[{datetime.now().strftime('%H:%M:%S')}][{bot_key.upper()}] Sent to {chat_id} -> Status: {res_json.get('ok')}", flush=True)
            time.sleep(0.3)
    except Exception as e:
        print(f"Error sending message on {bot_key}: {e}", flush=True)

def download_zalo_file(file_id: str = None, file_name: str = None, direct_url: str = None, bot_key: str = "bot1") -> str:
    """Tải tệp đính kèm gửi qua Zalo Bot (PDF, DOCX, XLSX, hình ảnh) về thư mục tạm."""
    import tempfile
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])
    clean_name = re.sub(r'[^\w\-_\.]', '_', file_name or "document.pdf")
    local_path = os.path.join(tempfile.gettempdir(), f"zalo_{bot_key}_{int(time.time())}_{clean_name}")
    try:
        if direct_url:
            r = requests.get(direct_url, timeout=30)
            if r.status_code == 200 and len(r.content) > 0:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                return local_path
                
        if file_id:
            info_resp = requests.get(f"{bot_cfg['base_url']}/getFile?file_id={file_id}", timeout=15)
            data = info_resp.json()
            if data.get("ok"):
                f_info = data.get("result", {})
                dl_url = f_info.get("download_url") or f_info.get("file_path")
                if dl_url:
                    if not dl_url.startswith("http"):
                        dl_url = f"https://bot-api.zaloplatforms.com/file/bot{bot_cfg['token']}/{dl_url}"
                    r = requests.get(dl_url, timeout=30)
                    if r.status_code == 200 and len(r.content) > 0:
                        with open(local_path, "wb") as f:
                            f.write(r.content)
                        return local_path
    except Exception as e:
        print(f"⚠️ [{bot_key.upper()} Lỗi tải file Zalo]: {e}", flush=True)
    return None

def process_message(msg_obj: dict, bot_key: str = "bot1"):
    """Xử lý sự kiện tin nhắn từ người dùng cho Bot tương ứng (bot1 hoặc bot2)."""
    chat = msg_obj.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("chat_type", "UNKNOWN")
    from_user = msg_obj.get("from", {})
    sender_name = from_user.get("display_name") or from_user.get("name") or "Chuyên viên"
    raw_text = (msg_obj.get("text") or msg_obj.get("caption") or "").strip()
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])

    # 0. Bóc tách tệp đính kèm (Document / File / Photo)
    doc_obj = msg_obj.get("document") or msg_obj.get("file")
    photo_obj = msg_obj.get("photo")
    attachments = msg_obj.get("attachments") or []
    
    file_attachment_path = None
    attached_filename = None
    
    if doc_obj and isinstance(doc_obj, dict):
        f_id = doc_obj.get("file_id")
        attached_filename = doc_obj.get("file_name") or doc_obj.get("name") or "van_ban.pdf"
        f_url = doc_obj.get("url") or doc_obj.get("download_url")
        file_attachment_path = download_zalo_file(f_id, attached_filename, f_url, bot_key=bot_key)
    elif attachments and isinstance(attachments, list) and len(attachments) > 0:
        att = attachments[0]
        payload = att.get("payload", {}) if isinstance(att, dict) else {}
        f_id = payload.get("file_id") or att.get("file_id")
        attached_filename = payload.get("name") or payload.get("file_name") or "van_ban.pdf"
        f_url = payload.get("url") or att.get("url")
        file_attachment_path = download_zalo_file(f_id, attached_filename, f_url, bot_key=bot_key)
    elif photo_obj and isinstance(photo_obj, list) and len(photo_obj) > 0:
        p = photo_obj[-1]
        f_id = p.get("file_id")
        attached_filename = "van_ban_scan.jpg"
        f_url = p.get("url")
        file_attachment_path = download_zalo_file(f_id, attached_filename, f_url, bot_key=bot_key)
        
    if not chat_id or (not raw_text and not file_attachment_path):
        return

    # 1. Thẩm định tệp đính kèm
    if file_attachment_path and os.path.exists(file_attachment_path):
        print(f"\n📎 [{bot_key.upper()} TỆP ĐÍNH KÈM] Từ: {sender_name} | ChatID: {chat_id} | Tên file: '{attached_filename}'", flush=True)
        send_zalo_message(chat_id, f"📥 **Đã tiếp nhận tệp:** `{attached_filename}` từ chuyên viên **{sender_name}**.\n🤖 *AI Agent ({bot_cfg['name']}) đang tiến hành OCR & thẩm định...*", bot_key=bot_key)
        try:
            review_reply = bot_agent.process_message(
                user_text=raw_text or f"Nộp file {attached_filename}",
                sender_name=sender_name,
                file_attachment_path=file_attachment_path
            )
            send_zalo_message(chat_id, review_reply, bot_key=bot_key)
        except Exception as e:
            send_zalo_message(chat_id, f"⚠️ Đã xảy ra lỗi khi thẩm định tệp: {e}", bot_key=bot_key)
        finally:
            try:
                if os.path.exists(file_attachment_path):
                    os.remove(file_attachment_path)
            except Exception:
                pass
        return

    print(f"\n📩 [{bot_key.upper()} TIN NHẮN] Từ: {sender_name} ({chat_type}) | ChatID: {chat_id} | Nội dung: '{raw_text}'", flush=True)
    clean_text = raw_text.lower()
    
    # 2. Lệnh Nhắc việc / Báo cáo tiến độ (CHỈ DÀNH CHO BOT 1 - TASK MASTER)
    task_keywords = ["/nhacviec", "nhacviec", "nhac việc", "nhắc việc", "nhac_viec", "/tasks", "tasks", "task", "/tiendo", "tiendo", "tien do", "tiến độ", "báo cáo tiến độ", "bao cao tien do", "danh sách task"]
    if any(cmd in clean_text for cmd in task_keywords):
        if bot_key == "bot1":
            print(f"--> [BOT1] Đang xuất báo cáo tiến độ từ Google Sheets...", flush=True)
            try:
                report_msg, guide_msg = task_fetcher.generate_reminder_parts()
                send_zalo_message(chat_id, report_msg, bot_key=bot_key)
                time.sleep(0.5)
                send_zalo_message(chat_id, guide_msg, bot_key=bot_key)
            except Exception:
                reminder = generate_reminder_message()
                send_zalo_message(chat_id, reminder, bot_key=bot_key)
            return
        else:
            # Bot 2 (Bot Giáo sư PPP): Chuyên trách Pháp lý RAG & Search Engine
            redirect_msg = (
                "⚖️ **Bot Giáo sư PPP** là AI Agent chuyên trách **Tra cứu Pháp lý PPP & Search Engine** (RAG Vector Store 23 Lĩnh vực Luật + Web Search Grounding).\n\n"
                "👉 Để xem **Báo cáo Tiến độ & Nhắc việc Bảng giao việc**, Anh/Chị vui lòng nhắn tin với **Bot PPP Full Service** (Bot 1) nhé!"
            )
            send_zalo_message(chat_id, redirect_msg, bot_key=bot_key)
            return

    # 3. Lệnh Hướng dẫn / Trợ giúp riêng cho từng Bot
    if clean_text in ["/help", "/start", "hướng dẫn", "chức năng", "help"]:
        if bot_key == "bot1":
            help_msg = (
                f"👋 Chào {sender_name}! Tôi là **{bot_cfg['name']}**.\n\n"
                "📌 **Chức năng chính của Bot 1 (Task Master):**\n"
                "• **Nhắc việc**: Gõ `/nhacviec` hoặc `báo cáo tiến độ` để xem task quá hạn & hạn hôm nay.\n"
                "• **Nộp file tự động**: Gửi file báo cáo (PDF/Word/Excel) để OCR & đối soát Bảng giao việc Google Sheets.\n"
                "• **Tra cứu Task**: Hỏi bất kỳ thông tin tiến độ chuyên viên phòng PPP&QLN."
            )
        else:
            help_msg = (
                f"👋 Chào {sender_name}! Tôi là **Bot Giáo sư PPP** (Legal RAG & Search Engine AI Agent).\n\n"
                "📌 **Chức năng chính của Bot 2 (Giáo sư PPP):**\n"
                "• **Tra cứu Pháp lý PPP (RAG Engine)**: Hỏi chi tiết Luật PPP 2020, NĐ 243/2025, NĐ 257/2025, NQ 98/2023, NQ 260/2025, Đất đai, Đầu tư công...\n"
                "• **Web Search Grounding**: Tra cứu tin tức, sự kiện, quy định pháp luật mới nhất theo thời gian thực trên Google Search.\n"
                "• **Thẩm định Pháp lý**: Gửi file văn bản quy phạm pháp luật để phân tích & trích dẫn Điều/Khoản."
            )
        send_zalo_message(chat_id, help_msg, bot_key=bot_key)
        return

    # 4. Điều hướng sang n8n Webhook tương ứng (bot1 -> zalo-task-webhook, bot2 -> zalo-legal-webhook)
    ai_query = raw_text.replace("@Bot", "").replace("@bot", "").strip()
    if ai_query:
        n8n_handled = False
        try:
            n8n_port = os.getenv("N8N_PORT") or "5678"
            n8n_url = f"http://127.0.0.1:{n8n_port}/webhook/{bot_cfg['webhook']}"
            try:
                n8n_resp = requests.post(n8n_url, json={"chat_id": str(chat_id), "text": ai_query, "sender_name": sender_name}, timeout=12)
                if n8n_resp.status_code == 200 and n8n_resp.text.strip() and "not registered" not in n8n_resp.text:
                    print(f"--> [{bot_key.upper()} Forwarded to Local/Cloud n8n Webhook via {n8n_url}]", flush=True)
                    n8n_data = n8n_resp.json()
                    n8n_text = n8n_data.get("output") or n8n_data.get("text") or n8n_data.get("response")
                    if n8n_text:
                        send_zalo_message(chat_id, str(n8n_text), bot_key=bot_key)
                    n8n_handled = True
            except Exception as e:
                print(f"⚠️ [{bot_key.upper()} n8n Forwarding Notice]: {e}", flush=True)
        except Exception as e:
            print(f"⚠️ [{bot_key.upper()} n8n Notice]: {e}", flush=True)

        if not n8n_handled:
            print(f"--> [{bot_key.upper()}] Gửi Gemini Python Fallback (kèm context memory {chat_id}): '{ai_query}'", flush=True)
            ai_ans = call_gemini(str(chat_id), ai_query, sender_name=sender_name)
            send_zalo_message(chat_id, ai_ans, bot_key=bot_key)

def poll_bot(bot_key: str):
    """Tiến trình duy trì Long-Polling cho từng Bot Zalo độc lập 24/7."""
    bot_cfg = BOTS.get(bot_key)
    base_url = bot_cfg["base_url"]
    
    print(f"🔄 [{bot_key.upper()}] Đang kiểm tra trạng thái Bot API: {bot_cfg['name']}...", flush=True)
    try:
        me = requests.get(f"{base_url}/getMe", timeout=10).json()
        if me.get("ok"):
            bot_info = me.get("result", {})
            print(f"✅ [{bot_key.upper()} ONLINE]: {bot_info.get('display_name')} (ID: {bot_info.get('id')})", flush=True)
        else:
            print(f"⚠️ [{bot_key.upper()} getMe warning]: {me}", flush=True)
    except Exception as e:
        print(f"❌ [{bot_key.upper()} getMe error]: {e}", flush=True)

    offset = 0
    poll_count = 0
    while True:
        try:
            poll_count += 1
            if poll_count % 60 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}][{bot_key.upper()}] 🔄 Polling heartbeat (lần thứ {poll_count})...", flush=True)

            payload = {"timeout": 15}
            if offset:
                payload["offset"] = offset
            resp = requests.post(f"{base_url}/getUpdates", json=payload, timeout=25)
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
                        process_message(msg, bot_key=bot_key)
                        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"❌ [{bot_key.upper()}] Polling loop exception: {e}", flush=True)
def run_http_health_server():
    """Khởi chạy HTTP Server siêu nhẹ trên port 5678 cho Render Health Check 24/7 (chỉ tốn ~5MB RAM)."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    port = int(os.getenv("PORT", 5678))
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("✅ Zalo Bot PPP Cloud Engine 24/7 is Live & Active!".encode("utf-8"))
        def log_message(self, format, *args):
            return  # Tắt spam log HTTP

    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"⚡ [HTTP SERVER] Đã mở cổng {port} cho Render Health Check...", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ [HTTP Server Notice]: {e}", flush=True)

def keep_alive_ping():
    """Tiến trình tự động gửi HTTP ping mỗi 10 phút để giữ cho Render Web Service luôn hoạt động 24/7, tránh bị ngủ đông (Spin-down)."""
    web_url = os.getenv("N8N_WEBHOOK_URL") or "https://zalo-bot-ppp-service.onrender.com"
    time.sleep(60)  # Chờ 1 phút cho HTTP Server sẵn sàng hẳn
    print(f"📡 [KEEP-ALIVE] Kích hoạt tiến trình tự động duy trì 24/7 cho Render Web Service: {web_url}", flush=True)
    while True:
        try:
            r = requests.get(f"{web_url}/healthz", timeout=15)
            if r.status_code not in [200, 302]:
                r = requests.get(web_url, timeout=15)
            print(f"[{datetime.now().strftime('%H:%M:%S')}][KEEP-ALIVE] ⚡ Self-ping thành công -> Status: {r.status_code}", flush=True)
        except Exception as e:
            print(f"⚠️ [KEEP-ALIVE Notice]: {e}", flush=True)
        time.sleep(600)  # Ping tự động mỗi 10 phút (600 giây)

def start_bot_service():
    mode = os.getenv("RUN_MODE", "dual").lower()
    print("==================================================", flush=True)
    print(f"🚀 BOT PPP SERVICE ENGINE - MODE: {mode.upper()}", flush=True)
    print(f"⏰ Khởi động lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
    print("==================================================", flush=True)
    
    # 1. Khởi chạy HTTP Server & Keep-Alive ONLY khi ở chế độ CLOUD
    if mode in ["bot1_only", "cloud"] or os.getenv("RENDER"):
        t_http = threading.Thread(target=run_http_health_server, daemon=True)
        t_http.start()
        t_ping = threading.Thread(target=keep_alive_ping, daemon=True)
        t_ping.start()

    # 2. Kích hoạt Bot theo chế độ RUN_MODE (bot1_only, bot2_only, hoặc dual)
    if mode in ["bot1_only", "cloud"]:
        print("📌 Chạy chế độ CLOUD: Chỉ vận hành Bot 1 (Task Master 24/7)", flush=True)
        t1 = threading.Thread(target=poll_bot, args=("bot1",), daemon=True)
        t1.start()
    elif mode in ["bot2_only", "local"]:
        print("📌 Chạy chế độ LOCAL PC: Chỉ vận hành Bot 2 (Bot Giáo sư PPP)", flush=True)
        t2 = threading.Thread(target=poll_bot, args=("bot2",), daemon=True)
        t2.start()
    else:
        print("📌 Chạy chế độ DUAL: Vận hành song song Bot 1 & Bot 2", flush=True)
        t1 = threading.Thread(target=poll_bot, args=("bot1",), daemon=True)
        t2 = threading.Thread(target=poll_bot, args=("bot2",), daemon=True)
        t1.start()
        t2.start()

    # Giữ main thread sống
    while True:
        time.sleep(10)

if __name__ == "__main__":
    start_bot_service()
