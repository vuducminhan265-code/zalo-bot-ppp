#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Export n8n environment variables
export N8N_PORT=5679
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_USER_MANAGEMENT_DISABLED=true
export N8N_BASIC_AUTH_ACTIVE=false
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_LOG_LEVEL=info
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com/
export WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com/

# 1. Import Zalo AI Agent workflow BEFORE starting n8n server (prevents SQLite database lock race condition)
echo "📥 Importing Zalo AI Agent Workflow into Cloud n8n..."
n8n import:workflow --input="/app/Function department/zalo_service/zalo_n8n_workflow_template.json" || true

# 2. Auto-restart daemon loop for n8n to guarantee 100% uptime
run_n8n() {
    while true; do
        echo "🔄 Starting n8n daemon on port 5679..."
        n8n start
        echo "⚠️ n8n process exited, restarting in 3 seconds..."
        sleep 3
    done
}

# Start n8n daemon in background
run_n8n &

# Start Zalo Bot Python Service
echo "🤖 Starting Zalo Bot Python Agent Service..."
exec python "Function department/zalo_service/zalo_bot_service.py"
