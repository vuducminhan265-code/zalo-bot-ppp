@echo off
chcp 65001 > nul
title Zalo Bot Giao Su PPP Engine

D:
cd "d:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot"

echo ==================================================
echo KICH HOAT BOT GIAO SU PPP VA N8N LOCAL
echo ==================================================

echo 1. Dang khoi dong n8n Engine ngam (vui long cho 5 giay)...
start /b n8n.cmd start > nul 2>&1

timeout /t 5 > nul

echo 2. Mo trinh duyet web n8n...
start http://localhost:5678

echo 3. Dang ket noi Bot Giao su PPP...
echo ==================================================
python "d:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot\run_bot2_giao_su.py"
pause
