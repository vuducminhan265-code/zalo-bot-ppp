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

from collections import deque
RECENT_LOGS = deque(maxlen=250)

def log_event(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True)
    RECENT_LOGS.append(entry)

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
    from .integrated_bot_agent import IntegratedZaloBotAgent, is_task_reminder_intent
    bot_agent = IntegratedZaloBotAgent(api_key=GEMINI_API_KEY)
except Exception:
    from integrated_bot_agent import IntegratedZaloBotAgent, is_task_reminder_intent
    bot_agent = IntegratedZaloBotAgent(api_key=GEMINI_API_KEY)

def call_gemini(chat_id: str, prompt: str, sender_name: str = "Chuyên viên") -> str:
    """Gọi Integrated Zalo Bot Agent với Real-time Metadata, Web Search Grounding, RAG và Workspace Tasks kèm Memory."""
    history = get_chat_history(chat_id)
    answer = bot_agent.process_message(prompt, sender_name=sender_name, chat_history=history)
    add_chat_message(chat_id, "user", prompt)
    add_chat_message(chat_id, "model", answer)
    return answer

def sanitize_zalo_text(raw_txt: str) -> str:
    if not raw_txt: return ""
    # Strip markdown bold/italics symbols
    t = re.sub(r'\*\*(.*?)\*\*', r'\1', raw_txt)
    t = re.sub(r'\*(.*?)\*', r'\1', t)
    t = re.sub(r'_(.*?)_', r'\1', t)
    t = re.sub(r'^#{1,6}\s*(.*)', r'📌 \1', t, flags=re.MULTILINE)
    t = re.sub(r'^\s*[\-\*]\s+', '• ', t, flags=re.MULTILINE)
    t = re.sub(r'`(.*?)`', r'\1', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def smart_split_zalo_message(text: str, max_len: int = 1400) -> list:
    """Chia nhỏ tin nhắn Zalo thông minh theo đoạn/dòng, tuyệt đối không cắt giữa chừng dòng hay từ ngữ."""
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks = []
    remaining = text.strip()
    while len(remaining) > max_len:
        # 1. Cắt tại ngắt đoạn lớn (\n\n)
        cut_point = remaining.rfind("\n\n", 0, max_len)
        # 2. Cắt tại đầu dòng của một task mới (\n• ) để không xé nhỏ task
        if cut_point == -1 or cut_point < max_len * 0.35:
            cut_point = remaining.rfind("\n• ", 0, max_len)
        # 3. Cắt tại bất kỳ dấu xuống dòng nào (\n)
        if cut_point == -1 or cut_point < max_len * 0.35:
            cut_point = remaining.rfind("\n", 0, max_len)
        # 4. Cắt tại dấu cách từ cuối cùng trước max_len
        if cut_point == -1 or cut_point < max_len * 0.35:
            cut_point = remaining.rfind(" ", 0, max_len)

        if cut_point == -1 or cut_point <= 0:
            cut_point = max_len

        chunk = remaining[:cut_point].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut_point:].strip()

    if remaining:
        chunks.append(remaining)
    return chunks

def send_zalo_message(chat_id: str, text: str, bot_key: str = "bot1"):
    """Gửi tin nhắn phản hồi qua Zalo Bot API tương ứng với bot_key."""
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])
    base_url = bot_cfg["base_url"]
    clean_text = sanitize_zalo_text(text)
    try:
        url = f"{base_url}/sendMessage"
        chunks = smart_split_zalo_message(clean_text, max_len=1400)
        for chunk in chunks:
            payload = {
                "chat_id": str(chat_id),
                "text": chunk
            }
            resp = requests.post(url, json=payload, timeout=10)
            res_json = resp.json()
            print(f"[{datetime.now().strftime('%H:%M:%S')}][{bot_key.upper()}] Sent to {chat_id} -> Status: {res_json.get('ok')}", flush=True)
            time.sleep(0.3)
    except Exception as e:
        print(f"Error sending message on {bot_key}: {e}", flush=True)

def download_zalo_file(file_id: str = None, file_name: str = None, direct_url: str = None, bot_key: str = "bot1") -> str:
    """Tải tệp đính kèm gửi qua Zalo Bot về thư mục tạm với TÊN GỐC CHUẨN XÁC để nhận diện Task ID."""
    import tempfile
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])
    orig_name = (file_name or "van_ban.pdf").strip()
    safe_name = os.path.basename(orig_name)
    
    unique_dir = os.path.join(tempfile.gettempdir(), f"zalo_file_{bot_key}_{int(time.time() * 1000)}")
    os.makedirs(unique_dir, exist_ok=True)
    local_path = os.path.join(unique_dir, safe_name)
    log_event(f"[{bot_key.upper()}] Bắt đầu tải file: '{orig_name}' (id={file_id}, direct_url={bool(direct_url)})")

    try:
        if direct_url:
            log_event(f"[{bot_key.upper()}] Tải trực tiếp qua direct_url: {direct_url[:120]}...")
            r = requests.get(direct_url, timeout=30)
            if r.status_code == 200 and len(r.content) > 0:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                log_event(f"[{bot_key.upper()}] Tải file thành công ({len(r.content)} bytes) -> {local_path}")
                return local_path
            else:
                log_event(f"[{bot_key.upper()}] Direct URL returned status {r.status_code}")
                
        if file_id:
            dl_url = None
            # 1. Thử GET /getFile?file_id=...
            try:
                r1 = requests.get(f"{bot_cfg['base_url']}/getFile?file_id={file_id}", timeout=15)
                d1 = r1.json()
                if d1.get("ok"):
                    res = d1.get("result", {})
                    dl_url = res.get("download_url") or res.get("file_path") or res.get("url")
            except Exception as e1:
                log_event(f"[{bot_key.upper()}] GET getFile error: {e1}")

            # 2. Thử POST /getFile {"file_id": ...}
            if not dl_url:
                try:
                    r2 = requests.post(f"{bot_cfg['base_url']}/getFile", json={"file_id": file_id}, timeout=15)
                    d2 = r2.json()
                    if d2.get("ok"):
                        res = d2.get("result", {})
                        dl_url = res.get("download_url") or res.get("file_path") or res.get("url")
                except Exception as e2:
                    log_event(f"[{bot_key.upper()}] POST getFile error: {e2}")

            # 3. Thử fallback GET /getFile?file_token=...
            if not dl_url:
                try:
                    r3 = requests.get(f"{bot_cfg['base_url']}/getFile?file_token={file_id}", timeout=15)
                    d3 = r3.json()
                    if d3.get("ok"):
                        res = d3.get("result", {})
                        dl_url = res.get("download_url") or res.get("file_path") or res.get("url")
                except Exception as e3:
                    log_event(f"[{bot_key.upper()}] GET file_token error: {e3}")

            if dl_url:
                if not dl_url.startswith("http"):
                    dl_url = f"https://bot-api.zaloplatforms.com/file/bot{bot_cfg['token']}/{dl_url}"
                log_event(f"[{bot_key.upper()}] Tải file từ resolved URL: {dl_url[:120]}...")
                r = requests.get(dl_url, timeout=30)
                if r.status_code == 200 and len(r.content) > 0:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    log_event(f"[{bot_key.upper()}] Tải file thành công ({len(r.content)} bytes) -> {local_path}")
                    return local_path
                else:
                    log_event(f"[{bot_key.upper()}] Download URL returned status {r.status_code}")
            else:
                log_event(f"[{bot_key.upper()}] Không thể resolve dl_url cho file_id {file_id}")
    except Exception as e:
        log_event(f"⚠️ [{bot_key.upper()} Lỗi tải file Zalo]: {e}")
    return None

def extract_attachment_info(msg_obj: dict) -> tuple:
    """Bóc tách triệt để mọi dạng tệp đính kèm (document, file, attachment, photo...) từ Zalo Bot API."""
    f_id = None
    f_name = None
    f_url = None

    def scan_dict(d: dict):
        nonlocal f_id, f_name, f_url
        if not isinstance(d, dict): return
        
        # Check id / token
        for k in ["file_id", "token", "fileToken", "id"]:
            if d.get(k) and isinstance(d[k], (str, int)) and not str(d[k]).startswith("http"):
                if not f_id: f_id = str(d[k])
                break
                
        # Check filename
        for k in ["file_name", "fileName", "name", "title"]:
            val = str(d.get(k) or "").strip()
            if val and any(val.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".png", ".jpg", ".jpeg"]):
                if not f_name: f_name = val
                break
                
        # Check url / download_url
        for k in ["url", "download_url", "downloadUrl", "file_url", "fileUrl", "href"]:
            val = str(d.get(k) or "").strip()
            if val and val.startswith("http"):
                if not f_url: f_url = val
                break

    # 1. Quét đối tượng gốc
    scan_dict(msg_obj)

    # 2. Quét các trường lồng nhau
    for subkey in ["document", "file", "attachment", "attachments", "photo", "image", "images", "media", "payload", "data"]:
        val = msg_obj.get(subkey)
        if isinstance(val, dict):
            scan_dict(val)
            if isinstance(val.get("payload"), dict):
                scan_dict(val["payload"])
        elif isinstance(val, list):
            for elem in val:
                if isinstance(elem, dict):
                    scan_dict(elem)
                    if isinstance(elem.get("payload"), dict):
                        scan_dict(elem["payload"])

    # 3. Quét attachments dạng mảng
    atts = msg_obj.get("attachments")
    if isinstance(atts, list):
        for att in atts:
            if isinstance(att, dict):
                scan_dict(att)
                if isinstance(att.get("payload"), dict):
                    scan_dict(att["payload"])

    # Fallback tên tệp nếu có url hoặc id nhưng chưa có tên
    if (f_id or f_url) and not f_name:
        if f_url:
            path_part = f_url.split("?")[0].rstrip("/")
            candidate = os.path.basename(path_part)
            if "." in candidate and len(candidate) > 3:
                f_name = candidate
        if not f_name:
            f_name = f"van_ban_{f_id or 'dinh_kem'}.pdf"

    return f_id, f_name, f_url

def process_message(msg_obj: dict, bot_key: str = "bot1"):
    """Xử lý sự kiện tin nhắn từ người dùng cho Bot tương ứng (bot1 hoặc bot2)."""
    chat = msg_obj.get("chat", {}) if isinstance(msg_obj.get("chat"), dict) else {}
    chat_id = chat.get("id") or msg_obj.get("chat_id")
    chat_type = chat.get("chat_type", "UNKNOWN")
    from_user = msg_obj.get("from", {}) if isinstance(msg_obj.get("from"), dict) else {}
    sender_name = from_user.get("display_name") or from_user.get("name") or "Chuyên viên"
    raw_text = (msg_obj.get("text") or msg_obj.get("caption") or msg_obj.get("data") or msg_obj.get("content") or "").strip()
    bot_cfg = BOTS.get(bot_key, BOTS["bot1"])

    if not chat_id:
        log_event(f"⚠️ [{bot_key.upper()}] Bỏ qua message không có chat_id: {msg_obj}")
        return

    # 0. Bóc tách tệp đính kèm (Document / File / Photo / Attachment)
    f_id, attached_filename, f_url = extract_attachment_info(msg_obj)
    
    file_attachment_path = None
    if f_id or f_url:
        display_fn = attached_filename or "Tài liệu văn bản"
        log_event(f"📎 [{bot_key.upper()} NHẬN TỆP] Từ: {sender_name} | ChatID: {chat_id} | Tên file: '{display_fn}' (id={f_id})")
        send_zalo_message(chat_id, f"📥 Đã tiếp nhận tệp: {display_fn} từ chuyên viên {sender_name}.\n🤖 AI Agent ({bot_cfg['name']}) đang tải xuống và tiến hành OCR & thẩm định...", bot_key=bot_key)
        
        file_attachment_path = download_zalo_file(f_id, attached_filename, f_url, bot_key=bot_key)
        if not file_attachment_path:
            log_event(f"⚠️ [{bot_key.upper()}] Thất bại khi tải tệp '{display_fn}'")
            send_zalo_message(chat_id, f"⚠️ Hệ thống đã ghi nhận tệp '{display_fn}' nhưng không thể tải xuống từ Zalo Platform. Vui lòng gửi lại dưới dạng Tệp tin/Tài liệu (Document).", bot_key=bot_key)
            return

    # Kiểm tra sự kiện tệp không được Zalo Platform hỗ trợ truyền trực tiếp (PDF/Word/Docx)
    if msg_obj.get("event_name") == "message.unsupported.received":
        log_event(f"⚠️ [{bot_key.upper()}] Zalo Platform gửi 'message.unsupported.received' từ {sender_name}")
        unsupported_msg = (
            f"⚠️ **Thông báo tiếp nhận tệp từ Chuyên viên {sender_name}:**\n\n"
            "Nền tảng **Zalo Bot Platform hiện tại chỉ hỗ trợ truyền tải Hình ảnh scan/Ảnh chụp (JPG/PNG)** và chặn các tệp tài liệu PDF/Word truyền trực tiếp qua khung chat cá nhân.\n\n"
            "👉 **Để AI thẩm định và tự động tích 'Đã hoàn thành' trên Bảng giao việc Google Sheets:**\n"
            "1. **Gửi ảnh chụp hoặc scan (JPG/PNG)** trang văn bản (có Tiêu ngữ, Số ký hiệu, Trích yếu và Nơi nhận/Ký lưu) trực tiếp vào đây.\n"
            "2. Hoặc nộp file vào Thư mục Bảng giao việc / Google Drive kèm cú pháp: `Nộp task [ID]` (ví dụ: `Nộp task 4`) để hệ thống đối soát ngay."
        )
        send_zalo_message(chat_id, unsupported_msg, bot_key=bot_key)
        return

    if not raw_text and not file_attachment_path:
        keys_str = ", ".join(list(msg_obj.keys())[:8])
        log_event(f"⚠️ [{bot_key.upper()} KHÔNG RÕ NỘI DUNG]: keys=[{keys_str}] | msg={msg_obj}")
        send_zalo_message(chat_id, f"👋 Chào {sender_name}! Bot 1 đã nhận được tín hiệu nhưng chưa nhận diện được nội dung hoặc tệp tin hợp lệ. (Các trường: {keys_str})", bot_key=bot_key)
        return

    # 1. Thẩm định tệp đính kèm (Ảnh Scan / PDF hợp lệ)
    if file_attachment_path and os.path.exists(file_attachment_path):
        log_event(f"🔍 [{bot_key.upper()} OCR THẨM ĐỊNH] Đang gọi bot_agent để review file: '{attached_filename}'")
        try:
            review_reply = bot_agent.process_message(
                user_text=raw_text or f"Nộp file {attached_filename}",
                sender_name=sender_name,
                file_attachment_path=file_attachment_path
            )
            send_zalo_message(chat_id, review_reply, bot_key=bot_key)
        except Exception as e:
            log_event(f"❌ [{bot_key.upper()} Lỗi review file]: {e}")
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
    if is_task_reminder_intent(raw_text):
        if bot_key == "bot1":
            print(f"--> [BOT1] Đang xuất báo cáo tiến độ từ Google Sheets theo yêu cầu ({raw_text})...", flush=True)
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
                "• **Nhắc việc**: Gõ `nv` hoặc `tiến độ` để xem task quá hạn & hạn hôm nay.\n"
                "• **Tra cứu Task**: Gõ `task [số]` (ví dụ: `task 4`) để xem thông tin chi tiết trên Bảng giao việc.\n"
                "• **Đối soát nộp bài**: Gửi ảnh scan văn bản (JPG/PNG) để AI đối soát và tự động tích 'Đã hoàn thành'."
            )
        else:
            help_msg = (
                f"👋 Chào {sender_name}! Tôi là **Bot Giáo sư PPP** (Legal RAG & Search Engine AI Agent).\n\n"
                "📌 **Chức năng chính của Bot 2 (Giáo sư PPP):**\n"
                "• **Tra cứu Pháp lý PPP (RAG Engine)**: Hỏi chi tiết Luật PPP 2020, NĐ 243/2025, NĐ 257/2025, NQ 98/2023, NQ 260/2025, Đất đai, Đầu tư công...\n"
                "• **Web Search Grounding**: Tra cứu tin tức, sự kiện, quy định pháp luật mới nhất theo thời gian thực trên Google Search.\n"
                "• **Thẩm định Pháp lý**: Phân tích & trích dẫn Điều/Khoản chính xác."
            )
        send_zalo_message(chat_id, help_msg, bot_key=bot_key)
        return

    # 4. PHÂN LUỒNG XỬ LÝ RIÊNG BIỆT - TUYỆT ĐỐI KHÔNG TRỘN LẪN CÔNG VIỆC BOT 1 VÀ BOT 2
    if bot_key == "bot1":
        # Tra cứu Task cụ thể theo ID hoặc tên chuyên viên trên Bảng giao việc Google Sheets
        task_id_match = re.search(r'\b(?:task|nhiệm vụ|stt|số)?\s*#?([0-9]{1,3})\b', clean_text)
        if task_id_match:
            t_id = task_id_match.group(1)
            try:
                live_tasks = task_fetcher.fetch_live_tasks()
                matched = [t for t in live_tasks if str(t.get("task_id", "")).strip() == t_id]
                if matched:
                    task_info = matched[0]
                    reply_task = (
                        f"📌 **Thông tin Bảng giao việc - Task #{t_id}:**\n"
                        f"• **Nhiệm vụ**: {task_info.get('task_name')}\n"
                        f"• **Chuyên viên phụ trách**: {task_info.get('assigned_to')}\n"
                        f"• **Hạn hoàn thành**: {task_info.get('deadline')}\n"
                        f"• **Trạng thái**: {task_info.get('status')}\n"
                        f"• **Sản phẩm**: {task_info.get('deliverable', 'Văn bản')}"
                    )
                    send_zalo_message(chat_id, reply_task, bot_key=bot_key)
                    return
            except Exception as e:
                log_event(f"Lỗi tra cứu task #{t_id}: {e}")

        # Với mọi tin nhắn khác không thuộc Bảng giao việc, Bot 1 KHÔNG gọi RAG Pháp lý mà hướng dẫn sang Bot 2
        redirect_msg = (
            f"👋 Chào {sender_name}! Tôi là **Bot 1 (Task Master)** - chuyên trách **Quản lý Tiến độ & Bảng giao việc** Phòng Hợp tác Công tư và Quản lý Nợ.\n\n"
            "📌 **Để xem tiến độ**: Gõ `nv` hoặc `tiến độ`.\n"
            "📌 **Để tra cứu nhiệm vụ**: Gõ `task [số]` (ví dụ: `task 4`).\n"
            "📌 **Để đối soát hoàn thành**: Gửi ảnh scan văn bản (JPG/PNG) có tiêu ngữ & nơi nhận.\n\n"
            "⚖️ **Tra cứu Pháp luật**: Để tra cứu **Văn bản quy phạm pháp luật, Nghị định, Luật PPP** hoặc tài liệu chuyên ngành, Anh/Chị vui lòng nhắn tin với **Bot Giáo sư PPP (Bot 2)** nhé!"
        )
        send_zalo_message(chat_id, redirect_msg, bot_key=bot_key)
        return

    # Bot 2: Tra cứu AI Agent độc bản (Single-Dispatch Engine: RAG + Web Grounding + Memory)
    ai_query = raw_text.replace("@Bot", "").replace("@bot", "").strip()
    if ai_query:
        print(f"--> [BOT2] Xử lý qua Master AI Agent (Single Dispatch): '{ai_query}'", flush=True)
        ai_ans = call_gemini(str(chat_id), ai_query, sender_name=sender_name)
        send_zalo_message(chat_id, ai_ans, bot_key=bot_key)

        def safe_n8n_post():
            try:
                n8n_port = os.getenv("N8N_PORT") or "5678"
                n8n_url = f"http://127.0.0.1:{n8n_port}/webhook/{bot_cfg['webhook']}"
                requests.post(n8n_url, json={"chat_id": str(chat_id), "text": ai_query, "sender_name": sender_name}, timeout=2)
            except Exception:
                pass
        threading.Thread(target=safe_n8n_post, daemon=True).start()

def poll_bot(bot_key: str):
    """Tiến trình duy trì Long-Polling cho từng Bot Zalo độc lập 24/7."""
    is_cloud = bool(os.getenv("RENDER")) or bool(os.getenv("RENDER_SERVICE_ID")) or ("onrender.com" in os.getenv("RENDER_EXTERNAL_URL", ""))
    if bot_key == "bot2" and is_cloud:
        print("⛔ [SECURITY GUARD] Bot 2 (Legal RAG) is FORBIDDEN on Cloud/Render instances. Polling aborted.", flush=True)
        return

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
                # 408 Request Timeout is standard Zalo long-polling response when no new updates arrive
                if data.get("error_code") == 408:
                    time.sleep(0.5)
                else:
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
                    
                    item_preview = json.dumps(item, ensure_ascii=False)[:300]
                    log_event(f"[{bot_key.upper()} UPDATE RECEIVED]: {item_preview}")
                    
                    # 1. Normal message or edited message
                    msg = item.get("message") or item.get("edited_message")
                    
                    # 2. Callback query from button click / quick reply
                    if not msg and item.get("callback_query"):
                        cb = item.get("callback_query", {})
                        msg = cb.get("message") or {}
                        if "data" in cb:
                            msg["text"] = cb["data"]
                        if "from" in cb:
                            msg["from"] = cb["from"]

                    # 3. Fallback: item itself is the message or contains message-like fields
                    if not msg and any(k in item for k in ["chat", "from", "document", "attachment", "attachments", "file", "text", "caption"]):
                        msg = item
                    
                    if msg:
                        if isinstance(msg, dict) and "event_name" not in msg and item.get("event_name"):
                            msg["event_name"] = item.get("event_name")
                        threading.Thread(target=process_message, args=(msg, bot_key), daemon=True).start()
                        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log_event(f"❌ [{bot_key.upper()}] Polling loop exception: {e}")
            time.sleep(5)
def run_http_health_server():
    """Khởi chạy HTTP Server siêu nhẹ trên port 5678 cho Render Health Check 24/7 (chỉ tốn ~5MB RAM)."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    port = int(os.getenv("PORT", 5678))
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/logs"):
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                log_data = "\n".join(list(RECENT_LOGS))
                self.wfile.write((log_data or "No logs recorded yet.").encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            info = {
                "status": "online",
                "service": "Zalo Bot PPP Task Master (Bot 1)",
                "version": "2.7.0-file-audit-observability",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "log_count": len(RECENT_LOGS)
            }
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
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
    is_render = bool(os.getenv("RENDER")) or bool(os.getenv("RENDER_SERVICE_ID")) or ("onrender.com" in os.getenv("RENDER_EXTERNAL_URL", ""))
    if is_render:
        mode = "bot1_only"
    else:
        mode = os.getenv("RUN_MODE", "local").lower()

    print("==================================================", flush=True)
    print(f"🚀 ZALO BOT SERVICE ENGINE - MODE: {mode.upper()} (IS_RENDER: {is_render})", flush=True)
    print(f"⏰ Khởi động lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
    print("==================================================", flush=True)
    
    # 1. Khởi chạy HTTP Server & Keep-Alive ONLY khi ở chế độ CLOUD (Render)
    if is_render or mode in ["bot1_only", "cloud"]:
        t_http = threading.Thread(target=run_http_health_server, daemon=True)
        t_http.start()
        t_ping = threading.Thread(target=keep_alive_ping, daemon=True)
        t_ping.start()

    # 2. Kích hoạt Bot theo chế độ RUN_MODE (bot1_only trên Render Cloud, bot2_only/local ở máy)
    if is_render or mode in ["bot1_only", "cloud"]:
        print("📌 Chạy chế độ CLOUD (Render): Chỉ vận hành Bot 1 (Task Master 24/7)", flush=True)
        t1 = threading.Thread(target=poll_bot, args=("bot1",), daemon=True)
        t1.start()
    elif mode in ["bot2_only", "local"]:
        print("📌 Chạy chế độ LOCAL PC: Chỉ vận hành Bot 2 (Bot Giáo sư PPP + Master Legal RAG)", flush=True)
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
