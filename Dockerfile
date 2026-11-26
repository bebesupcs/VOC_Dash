# Synology DS716+ (Intel x86_64) Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 기본 유틸 및 cloudflared (외부 접속 보안 터널) 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts /app/scripts
COPY dashboard /app/dashboard
COPY config /app/config
COPY templates /app/templates

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/run_dashboard_server.py"]
