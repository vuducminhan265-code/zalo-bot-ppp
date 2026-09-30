FROM n8nio/n8n:latest

USER root

ENV PATH="/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin:$PATH"

# Install Python 3 & tools with explicit path detection & verification
RUN if [ -x /sbin/apk ] || command -v apk >/dev/null 2>&1; then \
        apk add --no-cache python3 py3-pip bash curl git; \
    elif [ -x /usr/bin/apt-get ] || command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y python3 python3-pip bash curl git && rm -rf /var/lib/apt/lists/*; \
    else \
        echo "No supported package manager found!" && exit 1; \
    fi && python3 --version

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt --break-system-packages || pip3 install --no-cache-dir -r requirements.txt

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
