# Multi-stage Docker build for RAG Medical Assistant
# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/ ./src/
COPY public/ ./public/
COPY index.html ./

# Build frontend
RUN npm run build

# Stage 2: Python ML Backend
FROM python:3.9-slim AS ml-backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements
COPY ml_backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML backend code
COPY ml_backend/ ./ml_backend/

# Create necessary directories
RUN mkdir -p ./models ./data ./logs

# Stage 3: Production Runtime
FROM python:3.9-slim AS production

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies and ML backend
COPY --from=ml-backend /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=ml-backend /usr/local/bin /usr/local/bin
COPY --from=ml-backend /app/ml_backend ./ml_backend

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy Node.js backend
COPY api/ ./api/
COPY package*.json ./
RUN npm ci --only=production

# Copy configuration files
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY gunicorn.conf.py ./gunicorn.conf.py

# Create necessary directories
RUN mkdir -p ./models ./data ./logs /var/log/supervisor

# Set permissions
RUN chown -R www-data:www-data /app
RUN chmod +x ./ml_backend/app.py

# Expose ports
EXPOSE 80 3001 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start services with supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]