#!/bin/bash
# Script triển khai tự động Zalo Bot + n8n lên Google Cloud Run 24/7

echo "=================================================="
echo "🚀 BẮT ĐẦU TRIỂN KHAI ZALO BOT PPP LÊN GOOGLE CLOUD RUN"
echo "=================================================="

# 1. Bật các dịch vụ cần thiết trên Google Cloud
echo "📌 1. Kích hoạt Cloud Run & Cloud Build API..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 2. Triển khai trực tiếp từ thư mục mã nguồn
echo "📌 2. Đang đóng gói Docker Container & đẩy lên Google Cloud Run..."
gcloud run deploy zalo-bot-ppp-service \
  --source . \
  --port 5678 \
  --allow-unauthenticated \
  --region asia-east1 \
  --set-env-vars ZALO_BOT_TOKEN="1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX",N8N_BASIC_AUTH_ACTIVE="false"

echo "=================================================="
echo "✅ TRIỂN KHAI THÀNH CÔNG! BOT ZALO + N8N ĐÃ CHẠY 24/7 TRÊN GOOGLE CLOUD."
echo "=================================================="
