# Function department/zalo_service/auto_scheduler.py
import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

BOT_TOKEN = os.getenv("ZALO_BOT_TOKEN", "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX")
TARGET_GROUP_ID = os.getenv("ZALO_TARGET_GROUP_ID", "2327925421752384731")
BASE_URL = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

try:
    from tools.fetch_workspace_tasks import GoogleWorkspaceTaskFetcher
except ImportError:
    from ..tools.fetch_workspace_tasks import GoogleWorkspaceTaskFetcher

class ZaloAutoScheduler:
    """Automated Scheduler to dispatch Task Reminders at 08:00 and 17:30 daily."""

    def __init__(self, target_group_id: str = None):
        self.target_group_id = target_group_id or TARGET_GROUP_ID
        self.fetcher = GoogleWorkspaceTaskFetcher()
        self.last_dispatched = ""

    def send_group_message(self, text: str) -> bool:
        """Sends a message to the target Zalo Group."""
        url = f"{BASE_URL}/sendMessage"
        try:
            chunks = [text[i:i+1850] for i in range(0, len(text), 1850)]
            for chunk in chunks:
                payload = {
                    "chat_id": str(self.target_group_id),
                    "text": chunk,
                    "parse_mode": "markdown"
                }
                resp = requests.post(url, json=payload, timeout=15)
                res_json = resp.json()
                if not res_json.get("ok") and res_json.get("error_code") == 400:
                    payload.pop("parse_mode", None)
                    requests.post(url, json=payload, timeout=15)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatched scheduled message to Group {self.target_group_id}")
                time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error dispatching scheduled message: {e}")
            return False

    def trigger_scheduled_reminder(self, slot_name: str):
        """Fetches live workspace tasks and dispatches reminder."""
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"\n⏰ [{slot_name.upper()} TRIGGER] Executing scheduled reminder at {now_str}...")
        reminder_msg = self.fetcher.generate_formatted_reminder()
        self.send_group_message(reminder_msg)
        self.last_dispatched = f"{slot_name}_{datetime.now().strftime('%Y%m%d')}"

    def run_scheduler_loop(self):
        """Background loop checking time for 08:00 and 17:30 daily dispatch."""
        print("==================================================", flush=True)
        print("⏰ ZALO AUTOMATED TASK SCHEDULER STARTED (08:00 & 17:30)", flush=True)
        print(f"🎯 Target Group ID: {self.target_group_id}", flush=True)
        print("==================================================", flush=True)

        while True:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")
            today_str = now.strftime("%Y%m%d")

            # Morning Trigger: 08:00
            if current_hhmm == "08:00" and self.last_dispatched != f"morning_{today_str}":
                self.trigger_scheduled_reminder("Sáng (08:00)")
                time.sleep(60)

            # Evening Trigger: 17:30
            elif current_hhmm == "17:30" and self.last_dispatched != f"evening_{today_str}":
                self.trigger_scheduled_reminder("Chiều (17:30)")
                time.sleep(60)

            time.sleep(15)

if __name__ == "__main__":
    scheduler = ZaloAutoScheduler()
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        scheduler.trigger_scheduled_reminder("Kiểm thử Tức thì")
    else:
        scheduler.run_scheduler_loop()
