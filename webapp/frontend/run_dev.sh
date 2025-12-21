#!/bin/bash

echo "🎨 Starting Media Organizer Frontend (Development Mode)..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run development server
echo "🚀 Starting Vite dev server..."
npm run dev
