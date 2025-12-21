#!/bin/bash
# Quick restart script for debugging

echo "🔄 Restarting services..."

# Stop all
pkill -f "standalone_backend.py" 2>/dev/null
pkill -f "gpu_converter_service.py" 2>/dev/null
pkill -f "vite" 2>/dev/null

sleep 2

# Start
echo "✅ Services stopped. Restarting..."
./start.sh

