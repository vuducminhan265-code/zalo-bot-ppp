@echo off
set "PATH=%LOCALAPPDATA%\Programs\node24;%PATH%"
set "N8N_DIAGNOSTICS_ENABLED=false"
set "N8N_HIRING_BANNER_ENABLED=false"
echo Starting n8n server v2.40.7 with Node 24...
"%LOCALAPPDATA%\Programs\node24\n8n.cmd" start
pause
