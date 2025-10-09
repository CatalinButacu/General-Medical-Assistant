#!/bin/bash

# Start script for Google Cloud Run
# Optimized for production deployment

set -e

echo "🚀 Starting RAG Medical Assistant on Google Cloud Run..."

# Set environment variables
export NODE_ENV=production
export FLASK_ENV=production
export PORT=${PORT:-8080}

# Create necessary directories
mkdir -p /tmp/nginx /var/log/nginx /var/cache/nginx

# Start Nginx in background
echo "📡 Starting Nginx reverse proxy..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Start Node.js API server
echo "🔧 Starting Node.js API server..."
cd /app
node api/dist/server.js &
NODE_PID=$!

# Start Python ML backend
echo "🧠 Starting Python ML backend..."
cd /app/ml_backend
python -m gunicorn --config /app/gunicorn.conf.py app:app &
PYTHON_PID=$!

# Function to handle shutdown
shutdown() {
    echo "🛑 Shutting down services..."
    kill $NGINX_PID $NODE_PID $PYTHON_PID 2>/dev/null || true
    wait
    exit 0
}

# Trap signals for graceful shutdown
trap shutdown SIGTERM SIGINT

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    echo "🔍 Performing health checks..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8080/health >/dev/null 2>&1; then
            echo "✅ Health check passed!"
            return 0
        fi
        
        echo "⏳ Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ Health check failed after $max_attempts attempts"
    return 1
}

# Wait for services to start
sleep 5

# Perform health check
if health_check; then
    echo "🎉 All services started successfully!"
    echo "📱 RAG Medical Assistant is ready on port $PORT"
else
    echo "💥 Failed to start services properly"
    shutdown
    exit 1
fi

# Keep the script running and monitor processes
while true; do
    # Check if any process died
    if ! kill -0 $NGINX_PID 2>/dev/null; then
        echo "❌ Nginx died, restarting..."
        nginx -g "daemon off;" &
        NGINX_PID=$!
    fi
    
    if ! kill -0 $NODE_PID 2>/dev/null; then
        echo "❌ Node.js died, restarting..."
        cd /app
        node api/dist/server.js &
        NODE_PID=$!
    fi
    
    if ! kill -0 $PYTHON_PID 2>/dev/null; then
        echo "❌ Python ML backend died, restarting..."
        cd /app/ml_backend
        python -m gunicorn --config /app/gunicorn.conf.py app:app &
        PYTHON_PID=$!
    fi
    
    sleep 10
done