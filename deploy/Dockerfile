# SYNAPTIQ backend — production image
# Build: docker build -t synaptiq-backend -f deploy/Dockerfile .
# Run:   see deploy/docker-compose.prod.yml

FROM python:3.11-slim

# Security: run as non-root user
RUN groupadd --gid 1001 synaptiq && \
    useradd --uid 1001 --gid synaptiq --shell /bin/bash --create-home synaptiq

WORKDIR /app

# Install system deps (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cached unless requirements.txt changes)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ /app/

# Drop to non-root
USER synaptiq

# Gunicorn with uvicorn workers; override WORKERS via env in docker-compose
ENV WORKERS=2
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -sf http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "gunicorn server:app -k uvicorn.workers.UvicornWorker --workers ${WORKERS} --bind ${HOST}:${PORT} --timeout 120 --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile -"]
