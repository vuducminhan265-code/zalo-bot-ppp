#!/bin/bash
echo "=================================================="
echo "🚀 CLOUD INTEGRATED N8N + ZALO BOT AGENT ENGINE"
echo "=================================================="

# Use Render's assigned PORT for n8n native binding
export N8N_PORT=${PORT:-10000}
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

# 1. Restore persistent pre-seeded SQLite database (Preserves Owner User + Active Workflow)
echo "💾 Restoring pre-seeded n8n database with persistent Owner session..."
mkdir -p /root/.n8n
if [ -f "/app/data/database/n8n_database.sqlite" ]; then
    cp -f "/app/data/database/n8n_database.sqlite" "/root/.n8n/database.sqlite"
    echo "✅ Database restored successfully!"
fi

# 2. Start Zalo Bot Python Agent Service in background (Long-Polling 24/7)
echo "🤖 Starting Zalo Bot Python Agent Service in background..."
python "Function department/zalo_service/zalo_bot_service.py" &

# 3. Start n8n as main process directly on PORT (Native Cloud Web App)
echo "⚡ Starting n8n natively on port ${N8N_PORT}..."
exec n8n start
