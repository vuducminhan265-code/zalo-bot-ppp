FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Grant execution rights to start script
RUN chmod +x /app/start.sh

# Environment variables
ENV PORT=5678
ENV RUN_MODE=bot1_only
ENV PYTHONPATH="/app:/app/Function department"

EXPOSE 5678

CMD ["/bin/bash", "/app/start.sh"]
