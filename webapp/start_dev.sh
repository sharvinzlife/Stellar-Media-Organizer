#!/bin/bash

# =============================================================================
# Media Organizer Pro - Cross-Platform Development Startup Script (Mac/Linux)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}  🎬 Media Organizer Pro - Dev Server${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Cleanup function to kill background processes on exit
cleanup() {
    echo ""
    print_info "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    print_success "Servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check for Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed. Please install Python 3.8+."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python found: $($PYTHON_CMD --version)"
}

# Check for Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+."
        exit 1
    fi
    print_success "Node.js found: $(node --version)"
}

# Check for npm
check_npm() {
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm."
        exit 1
    fi
    print_success "npm found: $(npm --version)"
}

# Setup backend
setup_backend() {
    print_info "Setting up backend..."
    cd "$BACKEND_DIR"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_info "Installing backend dependencies..."
    venv/bin/pip install -r requirements.txt --quiet
    
    print_success "Backend setup complete."
}

# Setup frontend
setup_frontend() {
    print_info "Setting up frontend..."
    cd "$FRONTEND_DIR"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install
    fi
    
    print_success "Frontend setup complete."
}

# Start backend server
start_backend() {
    print_info "Starting backend server..."
    cd "$BACKEND_DIR"
    
    venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    print_success "Backend started (PID: $BACKEND_PID)"
}

# Start frontend server
start_frontend() {
    print_info "Starting frontend server..."
    cd "$FRONTEND_DIR"
    
    npm run dev &
    FRONTEND_PID=$!
    
    print_success "Frontend started (PID: $FRONTEND_PID)"
}

# Main execution
main() {
    print_header
    
    # Check prerequisites
    print_info "Checking prerequisites..."
    check_python
    check_node
    check_npm
    echo ""
    
    # Setup
    setup_backend
    setup_frontend
    echo ""
    
    # Start servers
    start_backend
    sleep 2
    start_frontend
    
    echo ""
    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  🚀 Servers are running!${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""
    echo -e "  ${BLUE}Frontend:${NC}  http://localhost:5173"
    echo -e "  ${BLUE}Backend:${NC}   http://localhost:8000"
    echo -e "  ${BLUE}API Docs:${NC}  http://localhost:8000/docs"
    echo ""
    echo -e "  ${YELLOW}Press Ctrl+C to stop all servers${NC}"
    echo ""
    
    # Wait for processes
    wait
}

main
