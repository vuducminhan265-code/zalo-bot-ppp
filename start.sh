#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Use Render's assigned PORT for n8n native binding
export N8N_PORT=${PORT:-10000}
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_PROTOCOL=https
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_BASIC_AUTH_ACTIVE=false
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_LOG_LEVEL=info
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com
export WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com/
export N8N_WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com/

# 1. Clean slate migration & Workflow Import
echo "📥 Importing Zalo AI Agent Workflow into Cloud n8n..."
n8n import:workflow --input="/app/Function department/zalo_service/zalo_n8n_workflow_template.json" || true
n8n update:workflow --all --active=true || true

# 2. Start Zalo Bot Python Agent Service in background (Long-Polling 24/7)
echo "🤖 Starting Zalo Bot Python Agent Service in background..."
python "Function department/zalo_service/zalo_bot_service.py" &

# 3. Start n8n as main process directly on PORT (Native Cloud Web App)
echo "⚡ Starting n8n natively on port ${N8N_PORT}..."
exec n8n start
