#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Port & Address Binding
export PORT=10000
export N8N_PORT=10000
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com
export WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com

# Memory & Task Runner Configuration
export NODE_OPTIONS="--max-old-space-size=384"
export WEB_CONCURRENCY=1
export N8N_RUNNERS_MODE=external
export N8N_RUNNERS_AUTH_TOKEN="alexander_ppp_task_runner_secret_2026"
export N8N_UNVERIFIED_PACKAGES_ENABLED=true
export N8N_RUNNERS_TASK_TIMEOUT=300
export N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES=2147483648
export N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES=5000
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_BASIC_AUTH_ACTIVE=false
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_PERSONALIZATION_ENABLED=false
export N8N_ENCRYPTION_KEY="alexander_ppp_master_encryption_key_2026"

# Native Owner Auto-Provisioning (n8n 2.x+)
export N8N_INSTANCE_OWNER_MANAGED_BY_ENV=true
export N8N_INSTANCE_OWNER_EMAIL="canimarun123@gmail.com"
export N8N_INSTANCE_OWNER_FIRST_NAME="Alex"
export N8N_INSTANCE_OWNER_LAST_NAME="Vu"
export N8N_INSTANCE_OWNER_PASSWORD_HASH='$2b$10$RMTKPT0XhqJMWIjNvQjTx.TP4yIgKn/wA0XsdRs2sTnpPaXojg.hG'

# Alias python to python3 if missing
if ! command -v python &> /dev/null; then
    alias python=python3
fi

# 1. Auto-import Credentials & Workflows
echo "📥 Auto-importing Gemini Credentials & Zalo AI Agent Workflows into Cloud n8n..."
python3 "Function department/zalo_service/generate_n8n_credentials.py" || true
n8n import:credentials --input="/app/Function department/zalo_service/n8n_credentials.json" || true
rm -f "/app/Function department/zalo_service/n8n_credentials.json" || true
n8n import:workflow --input="/app/Function department/zalo_service/n8n_workflow_bot1_tasks.json" || true
n8n import:workflow --input="/app/Function department/zalo_service/n8n_workflow_bot2_legal.json" || true

# 2. Start Zalo Bot Python Agent Service in background (Long-Polling 24/7)
echo "🤖 Starting Zalo Bot Python Agent Service in background..."
python3 "Function department/zalo_service/zalo_bot_service.py" &

# 3. Start n8n natively as main process
echo "⚡ Starting n8n natively on port ${N8N_PORT}..."
exec n8n start
