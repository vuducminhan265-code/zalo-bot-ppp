#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Export n8n environment variables
export N8N_PORT=5678
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_LOG_LEVEL=info
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com/n8n/
export WEBHOOK_URL=http://127.0.0.1:5678/

# Auto-restart daemon loop for n8n to guarantee 100% uptime
run_n8n() {
    while true; do
        echo "🔄 Starting n8n daemon..."
        n8n start
        echo "⚠️ n8n process exited, restarting in 3 seconds..."
        sleep 3
    done
}

# Start n8n daemon in background
run_n8n &

# Wait for n8n initialization
echo "⏳ Waiting 8 seconds for n8n server startup..."
sleep 8

# Start Zalo Bot Python Service
echo "🤖 Starting Zalo Bot Python Agent Service..."
exec python "Function department/zalo_service/zalo_bot_service.py"
