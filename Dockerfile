FROM node:20-slim

# Install Python 3 & system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install n8n globally
RUN npm install -g n8n

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy project files
COPY . .

# Set environment variables
ENV PORT=5678
ENV N8N_PORT=5678
ENV N8N_PROTOCOL=http
ENV N8N_BASIC_AUTH_ACTIVE=false

EXPOSE 5678

# Start n8n and Zalo Bridge Service concurrently
CMD n8n start & python3 "Function department/zalo_service/zalo_bot_service.py"
