@echo off
title Zalo Bot Giao Su PPP Engine
echo ==================================================
echo KICH HOAT BOT GIAO SU PPP VA N8N LOCAL
echo ==================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path 'D:\Personal' -Filter 'run_bot2_giao_su.py' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 | ForEach-Object { Start-Process n8n.cmd -ArgumentList 'start' -WindowStyle Hidden; Write-Host '1. Dang khoi dong n8n Engine ngam (vui long cho 5s)...'; Start-Sleep -Seconds 5; Write-Host '2. Mo trinh duyet web n8n...'; Start-Process 'http://localhost:5678'; Write-Host '3. Dang ket noi Bot Giao su PPP...'; Set-Location $_.DirectoryName; python run_bot2_giao_su.py }"
pause
