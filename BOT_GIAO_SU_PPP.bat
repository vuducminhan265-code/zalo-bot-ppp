@echo off
chcp 65001 > nul
title Zalo Bot Giao Su PPP Engine

cd /d "d:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot"

echo ==================================================
echo KICH HOAT BOT GIAO SU PPP VA N8N LOCAL
echo ==================================================

echo 1. Khoi dong n8n Engine ngam...
start /b n8n start > nul 2>&1

echo 2. Mo trinh duyet web n8n...
start http://localhost:5678

echo 3. Dang ket noi Bot Giao su PPP...
echo ==================================================
python run_bot2_giao_su.py
pause
