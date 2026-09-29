#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Export n8n environment variables
export N8N_PORT=5678
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com/n8n/
export WEBHOOK_URL=http://127.0.0.1:5678/

# Start n8n engine in background
n8n start &

# Wait 10 seconds for n8n initialization & database migration
echo "⏳ Waiting 10 seconds for n8n initialization..."
sleep 10

# Import & activate Zalo AI Agent workflow in n8n
echo "📥 Importing and activating Zalo AI Agent Workflow in Cloud n8n..."
n8n import:workflow --input="/app/Function department/zalo_service/zalo_n8n_workflow_template.json" || true

# Start Zalo Bot Python Service
echo "🤖 Starting Zalo Bot Python Agent Service..."
exec python "Function department/zalo_service/zalo_bot_service.py"
