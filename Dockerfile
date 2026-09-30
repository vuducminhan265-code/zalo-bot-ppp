FROM n8nio/n8n:latest

USER root

# Universal package manager detection for Python 3 & tools (Alpine vs Debian/Ubuntu)
RUN if command -v apk > /dev/null; then \
        apk add --no-cache python3 py3-pip bash curl git; \
    elif command -v apt-get > /dev/null; then \
        apt-get update && apt-get install -y python3 python3-pip bash curl git && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt --break-system-packages || pip install --no-cache-dir -r requirements.txt

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
ENV PYTHONPATH="/app:/app/Function department"

EXPOSE 10000

# Start Zalo Bot & Cloud n8n Service
CMD ["/bin/bash", "/app/start.sh"]
