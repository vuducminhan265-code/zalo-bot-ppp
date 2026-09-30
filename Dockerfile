FROM python:3.11-slim

# Install system dependencies & Node.js 24.x (>=24.0.0 requirement)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gnupg \
    && (curl -fsSL https://deb.nodesource.com/setup_24.x | bash - || curl -fsSL https://deb.nodesource.com/setup_current.x | bash -) \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install modern n8n 2.x and sqlite3 database driver
RUN npm install -g n8n@latest sqlite3 --production --ignore-scripts --legacy-peer-deps \
    && (cd /usr/lib/node_modules/n8n 2>/dev/null || cd /usr/local/lib/node_modules/n8n) && npm install sqlite3 --save --legacy-peer-deps

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Grant execution rights to start script
RUN chmod +x /app/start.sh

# Set environment variables
ENV PORT=10000
ENV N8N_PORT=10000
ENV N8N_HOST=0.0.0.0
ENV N8N_BASIC_AUTH_ACTIVE=false
ENV N8N_DIAGNOSTICS_ENABLED=false
ENV N8N_VERSION_NOTIFICATIONS_ENABLED=false
ENV N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
ENV N8N_SKIP_WEBHOOK_DEREGISTRATION=true
ENV PYTHONPATH="/app:/app/Function department"

EXPOSE 10000

# Start Zalo Bot & Cloud n8n Service
CMD ["/bin/bash", "/app/start.sh"]
