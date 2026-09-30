#!/bin/bash
echo "=================================================="
echo "🚀 LIGHTWEIGHT CLOUD ZALO BOT ENGINE (HYBRID MODE)"
echo "=================================================="

# Port & Address Binding - Strictly match Render PORT env var (5678)
export PORT=${PORT:-5678}
export N8N_WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com

# Cloud Mode: Run Bot 1 (Task Master 24/7) + HTTP Server + KeepAlive
export RUN_MODE="bot1_only"

# Alias python to python3 if missing
if ! command -v python &> /dev/null; then
    alias python=python3
fi

echo "🤖 Starting Zalo Bot 1 Task Master Cloud Engine on port ${PORT}..."
exec python3 "Function department/zalo_service/zalo_bot_service.py"
