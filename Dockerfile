FROM python:3.11-slim

# Install system dependencies & Node.js 20
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install n8n globally
RUN npm install -g n8n@1.75.2 --production

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Grant execution rights to start script
RUN chmod +x /app/start.sh

# Set environment variables to bypass login screens
ENV PORT=10000
ENV N8N_PORT=5679
ENV N8N_HOST=0.0.0.0
ENV N8N_USER_MANAGEMENT_DISABLED=true
ENV N8N_BASIC_AUTH_ACTIVE=false
ENV N8N_DIAGNOSTICS_ENABLED=false
ENV N8N_VERSION_NOTIFICATIONS_ENABLED=false
ENV N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
ENV PYTHONPATH="/app:/app/Function department"

EXPOSE 10000 5679

# Start Zalo Bot & Cloud n8n Service
CMD ["/bin/bash", "/app/start.sh"]
