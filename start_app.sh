#!/bin/bash

# Bioprocess Web Application Startup Script

echo "🚀 Starting Bioprocess Web Application..."
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if backend is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use. Stopping existing process..."
    kill $(lsof -Pi :8000 -sTCP:LISTEN -t)
    sleep 2
fi

# Start the backend server
echo "📦 Starting backend server on port 8000..."
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend started successfully
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend server started successfully!"
else
    echo "❌ Failed to start backend server"
    exit 1
fi

echo ""
echo "=================================="
echo "🎉 Application is ready!"
echo "=================================="
echo ""
echo "📌 Access the application at:"
echo "   Web UI:  http://localhost:8000/app"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "💡 Tips:"
echo "   - Use Ctrl+C to stop the server"
echo "   - Logs are displayed in this terminal"
echo "   - The server auto-reloads on code changes"
echo ""
echo "=================================="
echo ""

# Keep the script running and show logs
tail -f /dev/null & wait $BACKEND_PID
