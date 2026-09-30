#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Use Render's assigned PORT for n8n native binding
export N8N_PORT=${PORT:-10000}
export N8N_HOST=0.0.0.0
export N8N_LISTEN_ADDRESS=0.0.0.0
export N8N_PROTOCOL=http
export WEBHOOK_URL=https://zalo-bot-ppp-service.onrender.com/
export N8N_EDITOR_BASE_URL=https://zalo-bot-ppp-service.onrender.com/
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_BASIC_AUTH_ACTIVE=false
export N8N_ENCRYPTION_KEY="alexander_ppp_master_encryption_key_2026"

# Native Owner Auto-Provisioning (n8n 2.x+)
export N8N_INSTANCE_OWNER_MANAGED_BY_ENV=true
export N8N_INSTANCE_OWNER_EMAIL="canimarun123@gmail.com"
export N8N_INSTANCE_OWNER_FIRST_NAME="Alex"
export N8N_INSTANCE_OWNER_LAST_NAME="Vu"
export N8N_INSTANCE_OWNER_PASSWORD_HASH='$2b$10$FNWbdfjbUtjQHdxSnO1q9u/XjiJQ7j.PR8DVyLzjT/e.2pJWblmdy'

# Alias python to python3 if missing
if ! command -v python &> /dev/null; then
    alias python=python3
fi

# 1. Clean slate migration, Seed Credentials & Workflow Import
echo "📥 Auto-importing Gemini Credentials & Zalo AI Agent Workflows into Cloud n8n..."
python3 "Function department/zalo_service/generate_n8n_credentials.py" || true
n8n import:credentials --input="/app/Function department/zalo_service/n8n_credentials.json" || true
rm -f "/app/Function department/zalo_service/n8n_credentials.json" || true
n8n import:workflow --input="/app/Function department/zalo_service/n8n_workflow_bot1_tasks.json" || true
n8n import:workflow --input="/app/Function department/zalo_service/n8n_workflow_bot2_legal.json" || true
n8n update:workflow --all --active=true || true

# Seed SQLite Owner User & Personal Project directly
python3 "Function department/zalo_service/seed_sqlite_owner.py" || true

# 2. Start Zalo Bot Python Agent Service in background (Long-Polling 24/7)
echo "🤖 Starting Zalo Bot Python Agent Service in background..."
python3 "Function department/zalo_service/zalo_bot_service.py" &

# 3. Start n8n as main process directly on PORT (Native Cloud Web App)
echo "⚡ Starting n8n natively on port ${N8N_PORT}..."
exec n8n start
