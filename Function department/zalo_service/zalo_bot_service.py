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

# Bộ đệm gom ảnh nhiều trang (Multi-page Image Buffer) và Lịch sử tin nhắn gần đây theo chat_id
USER_IMAGE_BATCH = {}
USER_IMAGE_LOCK = threading.Lock()
RECENT_USER_TEXTS = {} # chat_id -> {"text": str, "time": float}
PENDING_TASK_SUBMISSIONS = {} # chat_id -> {"task_id": str, "time": float}

def process_buffered_images(chat_id: str, sender_name: str, bot_key: str):
    with USER_IMAGE_LOCK:
        batch = USER_IMAGE_BATCH.pop(chat_id, None)
    if not batch:
        return
    files = batch.get("files", [])
    filenames = batch.get("filenames", [])
    user_hint = batch.get("user_text", "")
    
    # 1. Kiểm tra nếu chuyên viên đã bấm "Nộp task [số]" hoặc nhiều task trước khi gửi ảnh
    pending_sub = PENDING_TASK_SUBMISSIONS.pop(chat_id, None)
    if pending_sub and (time.time() - pending_sub.get("time", 0)) < 300: # Trong vòng 5 phút
        t_ids = pending_sub.get("task_ids") or ([pending_sub["task_id"]] if "task_id" in pending_sub else [])
        if t_ids:
            tasks_str = " ".join(t_ids)
            if not any(f"task {tid}" in user_hint.lower() for tid in t_ids):
                user_hint = f"nộp task {tasks_str} {user_hint}".strip()

    rec = RECENT_USER_TEXTS.get(chat_id)
    if rec and (time.time() - rec.get("time", 0)) < 180:
        if not user_hint:
            user_hint = rec.get("text", "")
        else:
            user_hint += f" {rec.get('text', '')}"

    display_fn = ", ".join(filenames) if filenames else "Tập hợp ảnh văn bản"
    log_event(f"🔍 [{bot_key.upper()} BẮT ĐẦU THẨM ĐỊNH {len(files)} TRANG] '{display_fn}' từ {sender_name}")
    send_zalo_message(chat_id, f"📥 Đã gom đủ {len(files)} trang ảnh văn bản từ chuyên viên {sender_name}.\nĐang tổng hợp toàn bộ văn bản để đối soát thể thức và đồng bộ Bảng giao việc...", bot_key=bot_key)
    
    try:
        review_reply = bot_agent.process_message(
            user_text=user_hint or f"Nộp tài liệu {display_fn}",
            sender_name=sender_name,
            file_attachment_path=files if len(files) > 1 else files[0]
        )
        send_zalo_message(chat_id, review_reply, bot_key=bot_key)
    except Exception as e:
        log_event(f"❌ [{bot_key.upper()} Lỗi review file]: {e}")
        send_zalo_message(chat_id, f"⚠️ Đã xảy ra lỗi khi thẩm định văn bản: {e}", bot_key=bot_key)
    finally:
        for p in files:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

def extract_task_submission_intents(text: str) -> list:
    """
    Nhận diện các biến thể CHỈ ĐỊNH NỘP BÀI (Hỗ trợ 1 hoặc NHIỀU Task ID):
    - nộp task 4, Nộp task 4 5 6, nop task 4-7, nộp bài task 4, 5, nộp 4 5
    """
    if not text:
        return []
    clean = text.lower().strip()
    if any(k in clean for k in ["pdf", "drive"]):
        return []
    if not any(k in clean for k in ["nộp", "nop", "gửi", "gui", "bài", "bai", "task"]):
        return []

    m_range = re.search(r'(\d{1,3})\s*[\-–]\s*(\d{1,3})', clean)
    if m_range:
        start_id = int(m_range.group(1))
        end_id = int(m_range.group(2))
        if 0 < start_id <= end_id and (end_id - start_id) <= 20:
            return [str(i) for i in range(start_id, end_id + 1)]

    nums = re.findall(r'\b\d{1,3}\b', clean)
    valid_nums = [n for n in nums if 0 < int(n) < 200]
    seen = set()
    res = []
    for n in valid_nums:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res

def extract_drive_pdf_intents(text: str) -> list:
    """
    Nhận diện lệnh nộp PDF qua Google Drive (Hỗ trợ 1 hoặc NHIỀU Task ID):
    - nộp task 4 pdf, Nộp task 4 5 6 7 pdf, nop task 4, 5, 6 pdf, task 4-7 drive
    """
    if not text:
        return []
    clean = text.lower().strip()
    if not any(k in clean for k in ["pdf", "drive"]):
        return []
    if not any(k in clean for k in ["nộp", "nop", "gửi", "gui", "task", "nv", "t"]):
        return []

    m_range = re.search(r'(\d{1,3})\s*[\-–]\s*(\d{1,3})', clean)
    if m_range:
        start_id = int(m_range.group(1))
        end_id = int(m_range.group(2))
        if 0 < start_id <= end_id and (end_id - start_id) <= 20:
            return [str(i) for i in range(start_id, end_id + 1)]

    nums = re.findall(r'\b\d{1,3}\b', clean)
    valid_nums = [n for n in nums if 0 < int(n) < 200]
    seen = set()
    res = []
    for n in valid_nums:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res

def extract_task_view_intent(text: str):
    """
    Nhận diện lệnh TRA CỨU / XEM THÔNG TIN NHIỆM VỤ:
    - task 4, Task 4, xem task 4, tra cứu task 4, thông tin task 4, t4, nv 4, #4
    """
    if not text:
        return None
    clean = text.lower().strip()
    m_view = re.match(r'^(?:xem|tra\s*cứu|chi\s*tiết|thông\s*tin)?\s*(?:task|nhiệm\s*vụ|nv|t)?\s*#?([0-9]{1,3})$', clean)
    if m_view:
        return m_view.group(1)
    return None

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

def extract_all_attachments(msg_obj: dict) -> list:
    """Bóc tách triệt để TOÀN BỘ các tệp/ảnh đính kèm trong tin nhắn Zalo Bot API."""
    items = []
    
    # 1. Quét attachments mảng (Zalo gửi album hoặc nhiều ảnh cùng lúc)
    atts = msg_obj.get("attachments")
    if isinstance(atts, list):
        for att in atts:
            if isinstance(att, dict):
                p = att.get("payload") if isinstance(att.get("payload"), dict) else att
                f_id = p.get("file_id") or p.get("id") or p.get("token") or att.get("file_id")
                f_url = p.get("url") or p.get("photo_url") or p.get("download_url") or p.get("file_url") or att.get("url")
                f_name = p.get("file_name") or p.get("name") or p.get("title") or att.get("file_name")
                if f_id or f_url:
                    items.append((str(f_id) if f_id else None, f_name, f_url))
                    
    # 2. Quét trường photos mảng
    photos = msg_obj.get("photo") or msg_obj.get("photos") or msg_obj.get("images")
    if isinstance(photos, list):
        for p in photos:
            if isinstance(p, dict):
                f_id = p.get("file_id") or p.get("id")
                f_url = p.get("url") or p.get("photo_url")
                f_name = p.get("file_name") or p.get("name")
                if f_id or f_url:
                    items.append((str(f_id) if f_id else None, f_name, f_url))
                    
    # 3. Fallback quét đệ quy đơn nếu không có dạng mảng
    if not items:
        f_id, f_name, f_url = extract_attachment_info(msg_obj)
        if f_id or f_url:
            items.append((f_id, f_name, f_url))
            
    # Chuẩn hóa tên tệp cho từng item nếu còn thiếu
    normalized = []
    for idx, (fid, fname, furl) in enumerate(items):
        if not fname:
            if furl:
                path_part = furl.split("?")[0].rstrip("/")
                cand = os.path.basename(path_part)
                if "." in cand and len(cand) > 3 and any(cand.lower().endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]):
                    fname = cand
            if not fname:
                fname = f"van_ban_scan_{int(time.time())}_{idx+1}.jpg"
        normalized.append((fid, fname, furl))
        
    return normalized

def extract_attachment_info(msg_obj: dict) -> tuple:
    """Bóc tách một tệp đính kèm đầu tiên từ Zalo Bot API (fallback)."""
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
        for k in ["photo_url", "photoUrl", "url", "download_url", "downloadUrl", "file_url", "fileUrl", "image_url", "imageUrl", "href"]:
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
            if "." in candidate and len(candidate) > 3 and any(candidate.lower().endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]):
                f_name = candidate
        if not f_name:
            if f_url and any(img_marker in f_url.lower() for img_marker in ["jpg", "jpeg", "png", "photo", "image", "zdn.vn"]):
                f_name = f"van_ban_scan_{int(time.time())}.jpg"
            else:
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

    # 0. Bóc tách TOÀN BỘ các tệp đính kèm trong tin nhắn (hỗ trợ nhiều ảnh gửi cùng lúc)
    all_attachments = extract_all_attachments(msg_obj)
    downloaded_files = []
    downloaded_names = []
    
    for f_id, attached_filename, f_url in all_attachments:
        display_fn = attached_filename or "Tài liệu văn bản"
        log_event(f"📎 [{bot_key.upper()} NHẬN TỆP] Từ: {sender_name} | ChatID: {chat_id} | Tên file: '{display_fn}' (id={f_id})")
        local_p = download_zalo_file(f_id, attached_filename, f_url, bot_key=bot_key)
        if local_p and os.path.exists(local_p):
            downloaded_files.append(local_p)
            downloaded_names.append(display_fn)

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

    if not raw_text and not downloaded_files:
        keys_str = ", ".join(list(msg_obj.keys())[:8])
        log_event(f"⚠️ [{bot_key.upper()} KHÔNG RÕ NỘI DUNG]: keys=[{keys_str}] | msg={msg_obj}")
        send_zalo_message(chat_id, f"👋 Chào {sender_name}! Bot 1 đã nhận được tín hiệu nhưng chưa nhận diện được nội dung hoặc tệp tin hợp lệ. (Các trường: {keys_str})", bot_key=bot_key)
        return

    # 1. Thẩm định tệp đính kèm (Hỗ trợ cả 2 cách nộp ảnh: Nộp từng ảnh rời rạc hoặc Nộp gom một thể)
    if downloaded_files:
        str_chat_id = str(chat_id)
        with USER_IMAGE_LOCK:
            is_new_batch = (str_chat_id not in USER_IMAGE_BATCH)
            if is_new_batch:
                USER_IMAGE_BATCH[str_chat_id] = {
                    "files": list(downloaded_files),
                    "filenames": list(downloaded_names),
                    "user_text": raw_text,
                    "timer": None
                }
            else:
                USER_IMAGE_BATCH[str_chat_id]["files"].extend(downloaded_files)
                USER_IMAGE_BATCH[str_chat_id]["filenames"].extend(downloaded_names)
                if raw_text:
                    if USER_IMAGE_BATCH[str_chat_id]["user_text"]:
                        USER_IMAGE_BATCH[str_chat_id]["user_text"] += f" {raw_text}"
                    else:
                        USER_IMAGE_BATCH[str_chat_id]["user_text"] = raw_text
                if USER_IMAGE_BATCH[str_chat_id]["timer"]:
                    try:
                        USER_IMAGE_BATCH[str_chat_id]["timer"].cancel()
                    except Exception:
                        pass

            total_received = len(USER_IMAGE_BATCH[str_chat_id]["files"])
            pending_sub = PENDING_TASK_SUBMISSIONS.get(str_chat_id)
            t_ids = pending_sub.get("task_ids") or ([pending_sub["task_id"]] if pending_sub and "task_id" in pending_sub else [])
            task_label = f" cho Task #{', #'.join(t_ids)}" if t_ids else ""

            # PHÂN ĐỊNH 2 CÁCH NỘP HÌNH ẢNH:
            if is_new_batch and len(downloaded_files) == 1:
                # CÁCH 1A: Nộp từng ảnh rời - Báo đã nhận ảnh 1 và chờ 6 giây để chuyên viên gửi tiếp ảnh 2 (nếu có)
                send_zalo_message(
                    chat_id,
                    f"📥 Đã tiếp nhận ảnh (Trang 1){task_label} từ chuyên viên {sender_name}.\n"
                    f"⏳ Hệ thống đang đợi trong 6 giây để Anh/Chị gửi tiếp trang tiếp theo (như trang có Nơi nhận, chữ ký) nếu có...",
                    bot_key=bot_key
                )
                wait_seconds = 6.0
            elif not is_new_batch:
                # Chuyên viên đang gửi tiếp ảnh thứ 2, 3... nối tiếp
                send_zalo_message(
                    chat_id,
                    f"📥 Đã ghi nhận thêm ảnh (Trang {total_received}){task_label}.\n"
                    f"🔄 Đang hoàn tất tổng hợp các trang để tiến hành đối soát thể thức...",
                    bot_key=bot_key
                )
                wait_seconds = 3.0
            else:
                # CÁCH 1B: Nộp gom một thể (chuyên viên chọn gửi đồng thời nhiều ảnh trong 1 lượt)
                send_zalo_message(
                    chat_id,
                    f"📥 Đã tiếp nhận trọn bộ {total_received} trang ảnh văn bản{task_label} từ chuyên viên {sender_name}.\n"
                    f"🔄 Đang tiến hành đối soát thể thức toàn bộ các trang...",
                    bot_key=bot_key
                )
                wait_seconds = 2.5

            t = threading.Timer(wait_seconds, process_buffered_images, args=(str_chat_id, sender_name, bot_key))
            USER_IMAGE_BATCH[str_chat_id]["timer"] = t
            t.daemon = True
            t.start()
        return

    if raw_text:
        RECENT_USER_TEXTS[str(chat_id)] = {"text": raw_text, "time": time.time()}

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
            redirect_msg = (
                "⚖️ **Bot Giáo sư PPP** là AI Agent chuyên trách **Tra cứu Pháp lý PPP & Search Engine** (RAG Vector Store 23 Lĩnh vực Luật + Web Search Grounding).\n\n"
                "👉 Để xem **Báo cáo Tiến độ & Nhắc việc Bảng giao việc**, Anh/Chị vui lòng nhắn tin với **Bot PPP Full Service** (Bot 1) nhé!"
            )
            send_zalo_message(chat_id, redirect_msg, bot_key=bot_key)
            return

    # 3. Lệnh Tổng kết tiến độ cuối ngày (17:30)
    if clean_text in ["tổng kết", "tổng kết ngày", "báo cáo ngày", "báo cáo cuối ngày", "tổng kết tiến độ"]:
        if bot_key == "bot1":
            summary_msg = task_fetcher.generate_evening_review_summary()
            send_zalo_message(chat_id, summary_msg, bot_key=bot_key)
            return

    # 4. Lệnh Hướng dẫn / Trợ giúp riêng cho từng Bot
    if clean_text in ["/help", "/start", "hướng dẫn", "chức năng", "help", "hướng dẫn nộp", "cách nộp", "cách nộp sản phẩm", "hd"]:
        if bot_key == "bot1":
            guide_msg = task_fetcher.generate_guide_message()
            send_zalo_message(chat_id, guide_msg, bot_key=bot_key)
            return
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

    # 5. PHÂN LUỒNG XỬ LÝ RIÊNG BIỆT - TUYỆT ĐỐI KHÔNG TRỘN LẪN CÔNG VIỆC BOT 1 VÀ BOT 2
    if bot_key == "bot1":
        str_chat_id = str(chat_id)

        # 5.0. Nếu người dùng đang gửi ảnh và ảnh đang nằm trong bộ đệm chờ thẩm định:
        with USER_IMAGE_LOCK:
            if str_chat_id in USER_IMAGE_BATCH:
                # Ghi nhận ngay tin nhắn này làm gợi ý (task 4, nộp task 4, nop task 4...)
                if USER_IMAGE_BATCH[str_chat_id]["user_text"]:
                    USER_IMAGE_BATCH[str_chat_id]["user_text"] += f" {raw_text}"
                else:
                    USER_IMAGE_BATCH[str_chat_id]["user_text"] = raw_text
                
                # Rút ngắn timer còn 2.0s để bắt đầu thẩm định ngay lập tức sau gợi ý này
                if USER_IMAGE_BATCH[str_chat_id].get("timer"):
                    try:
                        USER_IMAGE_BATCH[str_chat_id]["timer"].cancel()
                    except Exception:
                        pass
                c_pics = len(USER_IMAGE_BATCH[str_chat_id]["files"])
                send_zalo_message(chat_id, f"📌 Đã ghi nhận chỉ định `{raw_text}` cho tập {c_pics} trang ảnh vừa gửi. Đang bắt đầu đối soát ngay...", bot_key=bot_key)
                t = threading.Timer(2.0, process_buffered_images, args=(str_chat_id, sender_name, bot_key))
                USER_IMAGE_BATCH[str_chat_id]["timer"] = t
                t.daemon = True
                t.start()
                return

        # 5.1. Nộp tệp PDF qua Thư mục Google Drive của Phòng (hỗ trợ 1 hoặc nhiều task: 4, 4 5 6, 4-7...)
        pdf_task_ids = extract_drive_pdf_intents(clean_text)
        if pdf_task_ids:
            if len(pdf_task_ids) == 1:
                pid = pdf_task_ids[0]
                send_zalo_message(chat_id, f"🔍 Đang quét Thư mục Google Drive của Phòng để tìm tệp PDF cho Task #{pid}...", bot_key=bot_key)
                res_drive = bot_agent.task_manager.scan_drive_folder(pid) if (bot_agent.task_manager and hasattr(bot_agent.task_manager, 'scan_drive_folder')) else {"success": False, "error": "Chưa hỗ trợ scan drive"}
                if res_drive.get("success"):
                    local_pdf = res_drive.get("local_path")
                    fn_pdf = res_drive.get("file_name", f"task_{pid}.pdf")
                    send_zalo_message(chat_id, f"📥 Đã tìm thấy tệp `{fn_pdf}` trên Google Drive. Đang tiến hành thẩm định thể thức tự động theo Nghị định 30/2020/NĐ-CP...", bot_key=bot_key)
                    review_ans = bot_agent.process_message(
                        user_text=f"Nộp task {pid}",
                        sender_name=sender_name,
                        file_attachment_path=local_pdf
                    )
                    send_zalo_message(chat_id, review_ans, bot_key=bot_key)
                    if os.path.exists(local_pdf):
                        try: os.remove(local_pdf)
                        except Exception: pass
                    return
                else:
                    err_drive = res_drive.get("error", "Không tìm thấy tệp")
                    fail_msg = (
                        f"⚠️ **Thông báo kết quả quét Google Drive cho Task #{pid}:**\n\n"
                        f"• {err_drive}\n\n"
                        f"🔗 **Đường dẫn Thư mục Google Drive của Phòng:**\n"
                        f"https://drive.google.com/drive/folders/1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL?usp=sharing\n\n"
                        f"👉 **Hướng dẫn đặt tên tệp chuẩn:**\n"
                        f"1. Tải tệp PDF lên Thư mục Drive trên, đặt tên theo cấu trúc:\n"
                        f"   `{pid} - [Tên file / Loại văn bản] - [Tên chuyên viên].pdf`\n"
                        f"   *(Lưu ý: Tên chuyên viên chỉ cần ghi ngắn gọn như: Lộc, Hòa, Giang, Phúc... không cần họ tên đầy đủ rườm rà. Quan trọng nhất là số `{pid}` ở đầu tiên khớp với ID Task cần nộp)*.\n"
                        f"   *Ví dụ: `{pid} - To trinh - Loc.pdf` hoặc `{pid} - File - Tên chuyên viên.pdf` hoặc `{pid} - Công văn - Lộc.pdf`*\n"
                        f"2. Nhắn lại vào nhóm: `nộp task {pid} pdf` để AI đối soát và cập nhật hoàn thành!"
                    )
                    send_zalo_message(chat_id, fail_msg, bot_key=bot_key)
                    return
            else:
                # Nộp hàng loạt nhiều task qua Drive: ví dụ "nộp task 4 5 6 7 pdf" hoặc "task 4-7 pdf"
                send_zalo_message(chat_id, f"🔍 Đang quét Thư mục Google Drive của Phòng để tìm các tệp PDF cho {len(pdf_task_ids)} nhiệm vụ: Task #{', #'.join(pdf_task_ids)}...", bot_key=bot_key)
                missing_pids = []
                for pid in pdf_task_ids:
                    res_drive = bot_agent.task_manager.scan_drive_folder(pid) if (bot_agent.task_manager and hasattr(bot_agent.task_manager, 'scan_drive_folder')) else {"success": False, "error": "Chưa hỗ trợ scan drive"}
                    if res_drive.get("success"):
                        local_pdf = res_drive.get("local_path")
                        fn_pdf = res_drive.get("file_name", f"task_{pid}.pdf")
                        send_zalo_message(chat_id, f"📥 [Task #{pid}] Đã tìm thấy tệp `{fn_pdf}`. Đang tiến hành thẩm định và nghiệm thu...", bot_key=bot_key)
                        review_ans = bot_agent.process_message(
                            user_text=f"Nộp task {pid}",
                            sender_name=sender_name,
                            file_attachment_path=local_pdf
                        )
                        send_zalo_message(chat_id, review_ans, bot_key=bot_key)
                        if os.path.exists(local_pdf):
                            try: os.remove(local_pdf)
                            except Exception: pass
                    else:
                        missing_pids.append(pid)
                
                if missing_pids:
                    missing_msg = (
                        f"⚠️ **Thông báo các Task chưa tìm thấy tệp PDF trên Google Drive: Task #{', #'.join(missing_pids)}**\n\n"
                        f"🔗 **Đường dẫn Thư mục Google Drive của Phòng:**\n"
                        f"https://drive.google.com/drive/folders/1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL?usp=sharing\n\n"
                        f"👉 **Hướng dẫn đặt tên tệp chuẩn:**\n"
                        f"Tải tệp PDF lên Drive với định dạng: `[Số Task] - [Tên file] - [Tên chuyên viên].pdf`\n"
                        f"*(Ví dụ: `{missing_pids[0]} - To trinh - {sender_name}.pdf`)*\n"
                        f"Sau đó gõ lại: `nộp task {' '.join(missing_pids)} pdf` để nghiệm thu nốt các nhiệm vụ còn lại!"
                    )
                    send_zalo_message(chat_id, missing_msg, bot_key=bot_key)
                return

        # 5.2. Nhận diện hành động CHỈ ĐỊNH NỘP BÀI (Hỗ trợ nộp 1 hoặc nhiều task cùng lúc: nộp task 4, nộp task 4 5 6, nộp task 4-6...)
        sub_ids = extract_task_submission_intents(clean_text)
        if sub_ids:
            PENDING_TASK_SUBMISSIONS[str_chat_id] = {"task_ids": sub_ids, "task_id": sub_ids[0], "time": time.time()}
            RECENT_USER_TEXTS[str_chat_id] = {"text": raw_text, "time": time.time()}
            ids_label = f"Task #{', #'.join(sub_ids)}"
            
            submission_prompt = (
                f"📌 **Đã sẵn sàng tiếp nhận sản phẩm cho {ids_label} từ chuyên viên {sender_name}:**\n\n"
                f"👉 **Anh/Chị có thể chọn 1 trong 2 cách nộp hình ảnh sau:**\n"
                f"• **Cách 1A (Nộp từng ảnh lẻ)**: Gửi ảnh Trang 1 (Tiêu ngữ, Số, Trích yếu) ➔ Hệ thống sẽ xác nhận và đợi 6 giây để Anh/Chị gửi tiếp Trang cuối (Nơi nhận, Chữ ký).\n"
                f"• **Cách 1B (Nộp gom một thể)**: Chọn và gửi cùng lúc tất cả các trang ảnh văn bản (Album / Multi-select) để AI tự động gom và đối soát toàn bộ.\n\n"
                f"*(Hoặc nộp qua Google Drive: Tải tệp PDF lên Drive đặt tên `{sub_ids[0]} - [Tên file] - [Tên chuyên viên].pdf` rồi gõ `nộp task {' '.join(sub_ids)} pdf`)*"
            )
            send_zalo_message(chat_id, submission_prompt, bot_key=bot_key)
            return

        # 5.3. Tra cứu chi tiết một Task (task 4, xem task 4, t4, nv 4...)
        view_task_id = extract_task_view_intent(clean_text)
        if view_task_id:
            try:
                all_sheet_tasks = task_fetcher.task_manager.get_all_tasks_from_sheet()
                matched = [t for t in all_sheet_tasks if str(t.get("taskId") or t.get("task_id", "")).strip() == str(view_task_id).strip()]
                if matched:
                    t_info = matched[0]
                    t_name = t_info.get("taskName") or t_info.get("task_name") or ""
                    t_proj = t_info.get("project") or ""
                    t_assignee = t_info.get("assignee") or t_info.get("assigned_to") or "Chưa phân công"
                    t_leader = t_info.get("leader") or ""
                    t_deadline = t_info.get("deadline") or ""
                    t_priority = t_info.get("priority") or "Bình thường"
                    t_status = t_info.get("status") or "Chưa bắt đầu"
                    t_deliv = t_info.get("deliverable") or "Công văn"
                    t_so = t_info.get("soKyHieu") or "Chưa có"
                    t_ngay = t_info.get("ngayBanHanh") or "Chưa có"
                    t_trich = t_info.get("trichYeu") or ""
                    t_ai = t_info.get("aiSummary") or ""
                    t_sub_time = t_info.get("submittedAt") or "Chưa nộp"
                    t_fn = t_info.get("fileName") or "Chưa có"

                    status_icon = "🟢 [Đã hoàn thành]" if t_status == "Đã hoàn thành" else ("🔴 [Đang sửa lại]" if t_status == "Đang sửa lại" else "🟡 [Đang thực hiện]")
                    
                    reply_lines = [
                        f"📌 **THÔNG TIN CHI TIẾT NHIỆM VỤ - TASK #{view_task_id}:**",
                        f"• 📋 **Nhiệm vụ**: {t_name}",
                        f"• 🏢 **Dự án**: {t_proj if t_proj else 'Theo trích yếu văn bản'}",
                        f"• 👤 **Chuyên viên phụ trách**: {t_assignee}",
                        f"• 👔 **Lãnh đạo phòng**: {t_leader if t_leader else 'Lãnh đạo phòng phụ trách'}",
                        f"• ⏳ **Hạn hoàn thành**: {t_deadline} | Ưu tiên: {t_priority}",
                        f"• 📊 **Trạng thái**: {status_icon} {t_status}",
                        f"• 📦 **Sản phẩm yêu cầu**: {t_deliv}",
                        f"• 📑 **Số ký hiệu**: {t_so} | Ngày: {t_ngay}",
                        f"• 📌 **Trích yếu**: {t_trich if t_trich else t_name}"
                    ]
                    if t_status == "Đã hoàn thành" or (t_sub_time and t_sub_time != "Chưa nộp"):
                        reply_lines.extend([
                            f"• 💡 **Đánh giá AI**: {t_ai}",
                            f"• ⏰ **Thời gian nộp**: {t_sub_time} | Tệp: {t_fn}"
                        ])
                    reply_lines.extend([
                        "────────────────────────────",
                        "🔗 **Link tra cứu Bảng giao việc Google Sheets:**",
                        "https://docs.google.com/spreadsheets/d/1RRb0PJB2EJv92SPHZ3_ahv2YYEn9bxjfC8JBPpTkuG4/edit?gid=735957328"
                    ])
                    send_zalo_message(chat_id, "\n".join(reply_lines), bot_key=bot_key)
                    return
                else:
                    send_zalo_message(chat_id, f"⚠️ Không tìm thấy Task #{view_task_id} trên Bảng giao việc Google Sheets. Hiện tại phòng đang có các task từ #1 đến #{len(all_sheet_tasks)}.", bot_key=bot_key)
                    return
            except Exception as e:
                log_event(f"Lỗi tra cứu task #{view_task_id}: {e}")

        # Với mọi tin nhắn khác không thuộc Bảng giao việc, Bot 1 hướng dẫn chuẩn công vụ
        redirect_msg = (
            f"👋 Chào {sender_name}! Tôi là **Bot 1 (Task Master)** - chuyên trách **Quản lý Tiến độ & Bảng giao việc** Phòng Hợp tác Công tư và Quản lý Nợ.\n\n"
            "📌 **Để xem tiến độ**: Gõ `nv` hoặc `tiến độ`.\n"
            "📌 **Để tra cứu nhiệm vụ**: Gõ `task [số]` (ví dụ: `task 4`).\n"
            "📌 **Để xem hướng dẫn nộp**: Gõ `hướng dẫn` hoặc `hướng dẫn nộp`.\n"
            "📌 **Để đối soát hoàn thành**: Gửi ảnh scan văn bản (JPG/PNG) hoặc tải PDF lên Drive rồi gõ `nộp task [số] pdf`.\n\n"
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

            if self.path.startswith("/api/cron/morning"):
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                def run_m():
                    try:
                        rep, g = task_fetcher.generate_reminder_parts()
                        send_zalo_message("2327925421752384731", rep, bot_key="bot1")
                        time.sleep(0.5)
                        send_zalo_message("2327925421752384731", g, bot_key="bot1")
                    except Exception as e:
                        print(f"Manual morning trigger error: {e}")
                threading.Thread(target=run_m, daemon=True).start()
                self.wfile.write(json.dumps({"success": True, "message": "Triggered 07:45 morning reminder"}).encode("utf-8"))
                return

            if self.path.startswith("/api/cron/evening"):
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                def run_e():
                    try:
                        eve = task_fetcher.generate_evening_review_summary()
                        send_zalo_message("2327925421752384731", eve, bot_key="bot1")
                    except Exception as e:
                        print(f"Manual evening trigger error: {e}")
                threading.Thread(target=run_e, daemon=True).start()
                self.wfile.write(json.dumps({"success": True, "message": "Triggered 17:30 evening summary"}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            info = {
                "status": "online",
                "service": "Zalo Bot PPP Task Master (Bot 1)",
                "version": "3.4.0-drive-pdf-and-cron-sync",
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

def daily_cron_scheduler():
    """
    Tiến trình chạy nền 24/7 kiểm tra thời gian thực Việt Nam (UTC+7):
    - 07:45 Sáng: Tự động phát Bản tin nhắc việc & Báo cáo tiến độ đầu ngày.
    - 17:30 Chiều: Tự động phát Bản tin Tổng kết cuối ngày (liệt kê các task hoàn thành hoặc ghi rõ 0 sản phẩm).
    """
    from datetime import datetime, timezone, timedelta
    tz_vn = timezone(timedelta(hours=7))
    last_morning_sent = ""
    last_evening_sent = ""
    
    print("⏰ [CRON SCHEDULER] Đã khởi chạy tiến trình tự động phát bản tin 07:45 & 17:30 (Múi giờ Việt Nam)...", flush=True)
    while True:
        try:
            now_vn = datetime.now(tz_vn)
            today_str = now_vn.strftime("%Y-%m-%d")
            hour = now_vn.hour
            minute = now_vn.minute
            
            target_chats = set()
            target_chats.add("2327925421752384731")  # Group Zalo chính thức Phòng PPP&QLN
            
            env_chat = os.getenv("DEFAULT_ZALO_CHAT_ID") or os.getenv("ZALO_GROUP_CHAT_ID")
            if env_chat:
                target_chats.add(str(env_chat).strip())
                
            with USER_IMAGE_LOCK:
                for c_id in RECENT_USER_TEXTS.keys():
                    target_chats.add(str(c_id))

            # 1. Phát bản tin 07:45 sáng
            if hour == 7 and minute == 45 and last_morning_sent != today_str:
                last_morning_sent = today_str
                print(f"[{now_vn.strftime('%H:%M:%S')}][CRON] 📢 Đang phát bản tin nhắc việc 07:45 sáng...", flush=True)
                try:
                    report_msg, guide_msg = task_fetcher.generate_reminder_parts()
                    for c_id in target_chats:
                        send_zalo_message(c_id, report_msg, bot_key="bot1")
                        time.sleep(0.5)
                        send_zalo_message(c_id, guide_msg, bot_key="bot1")
                except Exception as ex_m:
                    print(f"⚠️ [CRON Morning Error]: {ex_m}", flush=True)

            # 2. Phát bản tin 17:30 chiều
            if hour == 17 and minute == 30 and last_evening_sent != today_str:
                last_evening_sent = today_str
                print(f"[{now_vn.strftime('%H:%M:%S')}][CRON] 📋 Đang phát bản tin tổng kết 17:30 chiều...", flush=True)
                try:
                    evening_msg = task_fetcher.generate_evening_review_summary()
                    for c_id in target_chats:
                        send_zalo_message(c_id, evening_msg, bot_key="bot1")
                except Exception as ex_e:
                    print(f"⚠️ [CRON Evening Error]: {ex_e}", flush=True)

        except Exception as e:
            print(f"⚠️ [CRON Exception]: {e}", flush=True)
            
        time.sleep(25)

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

    # Khởi chạy Scheduler tự động phát tin 07:45 & 17:30 (Chạy trên cả Cloud và Local)
    t_cron = threading.Thread(target=daily_cron_scheduler, daemon=True)
    t_cron.start()

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
