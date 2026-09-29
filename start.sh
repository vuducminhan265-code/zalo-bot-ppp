#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Start n8n engine in background
export N8N_PORT=5678
export N8N_HOST=127.0.0.1
export WEBHOOK_URL=http://127.0.0.1:5678/
n8n start &

# Wait for n8n server readiness
sleep 5

# Import Zalo AI Agent workflow into n8n
echo "📥 Importing Zalo AI Agent Workflow into Cloud n8n..."
n8n import:workflow --input="/app/Function department/zalo_service/zalo_n8n_workflow_template.json" || true

# Start Zalo Bot Python Service
echo "🤖 Starting Zalo Bot Service..."
exec python "Function department/zalo_service/zalo_bot_service.py"
