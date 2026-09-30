@echo off
title Zalo Bot Giao Su PPP Engine
echo ==================================================
echo KICH HOAT BOT GIAO SU PPP (PYTHON HIGH POWER ENGINE)
echo ==================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path 'D:\Personal' -Filter 'run_bot2_giao_su.py' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 | ForEach-Object { Write-Host '1. Dang ket noi Bot Giao su PPP...'; Set-Location $_.DirectoryName; python run_bot2_giao_su.py }"
pause
