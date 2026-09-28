FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements & install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variables
ENV PORT=10000
ENV PYTHONPATH="/app:/app/Function department"

EXPOSE 10000

# Start Zalo Bot Service
CMD ["python", "Function department/zalo_service/zalo_bot_service.py"]
