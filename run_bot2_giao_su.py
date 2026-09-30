# run_bot2_giao_su.py - Local PC Launcher for Bot Giáo sư PPP
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
zalo_service_dir = os.path.join(current_dir, "Function department", "zalo_service")
func_dept_dir = os.path.join(current_dir, "Function department")

if zalo_service_dir not in sys.path:
    sys.path.insert(0, zalo_service_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

os.environ["RUN_MODE"] = "bot2_only"

from zalo_bot_service import start_bot_service

if __name__ == "__main__":
    print("==================================================")
    print("🎓 ZALO BOT GIÁO SƯ PPP - KÍCH HOẠT TRÊN MÁY TÍNH CÁ NHÂN")
    print("==================================================")
    print("⚡ Bot 2 (Bot Giáo sư PPP) đang chạy bằng sức mạnh CPU/RAM máy tính cá nhân.")
    print("📚 Đã tích hợp: NotebookLM, RAG Vector Store 23 Lĩnh vực Luật, Google Web Search Grounding.")
    print("📌 Bot PPP Full Service (Bot 1 - Nhắc việc) vẫn đang chạy 24/7 trên Cloud Render độc lập.")
    print("==================================================")
    start_bot_service()
