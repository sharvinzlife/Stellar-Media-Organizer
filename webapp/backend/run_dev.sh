#!/bin/bash

echo "🎬 Starting Media Organizer Backend (Development Mode)..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run the application
echo "🚀 Starting FastAPI server..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
