#!/bin/bash
# FIE Web Server Restart Script
# Usage: ./restart_web.sh

set -e

PORT=8080
VENV=~/venvs/megatron/bin/activate
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔄 Restarting FIE Web Server..."

# Kill any existing process on the port
echo "  → Stopping existing processes on port $PORT..."
pkill -9 -f "python.*web_ui" 2>/dev/null || true
fuser -k $PORT/tcp 2>/dev/null || true
sleep 1

# Activate venv and start server
echo "  → Starting server..."
cd "$PROJECT_DIR"
source "$VENV"

# Start in background with nohup so it survives terminal close
nohup python -m fie.web_ui > /tmp/fie_web.log 2>&1 &

# Wait for server to be ready
echo "  → Waiting for server..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:$PORT > /dev/null 2>&1; then
        echo ""
        echo "✅ FIE is running!"
        echo ""
        echo "   🌐 http://fie.local:$PORT"
        echo "   🌐 http://127.0.0.1:$PORT"
        echo ""
        echo "   📋 Logs: tail -f /tmp/fie_web.log"
        echo "   🛑 Stop: pkill -f 'python.*web_ui'"
        exit 0
    fi
    sleep 0.5
    echo -n "."
done

echo ""
echo "⚠️  Server may still be starting. Check logs: tail -f /tmp/fie_web.log"
