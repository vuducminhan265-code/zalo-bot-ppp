@echo off
title Zalo Bot Giao Su PPP Engine
echo ==================================================
echo KICH HOAT BOT GIAO SU PPP VA N8N LOCAL
echo ==================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process n8n.cmd -ArgumentList 'start' -WindowStyle Hidden; Write-Host '1. Dang khoi dong n8n Engine ngam (vui long cho 5s)...'; Start-Sleep -Seconds 5; Write-Host '2. Mo trinh duyet web n8n...'; Start-Process 'http://localhost:5678'; Write-Host '3. Dang ket noi Bot Giao su PPP...'; Set-Location 'd:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot'; python run_bot2_giao_su.py"
pause
