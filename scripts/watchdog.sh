#!/usr/bin/env bash
#
# Stellar Media Organizer - Watchdog System
# Ensures all services are running and handles crashes/restarts
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/pids"
LOCK_FILE="$RUN_DIR/watchdog.lock"
LOG_FILE="$RUN_DIR/watchdog.log"

# Ports
API_PORT=8000
GPU_PORT=8888
FRONTEND_PORT=5173

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$RUN_DIR"

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" >> "$LOG_FILE"
    
    case "$level" in
        INFO)  echo -e "${BLUE}[$timestamp]${NC} $msg" ;;
        OK)    echo -e "${GREEN}[$timestamp]${NC} ✅ $msg" ;;
        WARN)  echo -e "${YELLOW}[$timestamp]${NC} ⚠️  $msg" ;;
        ERROR) echo -e "${RED}[$timestamp]${NC} ❌ $msg" ;;
    esac
}

# Load environment
load_env() {
    if [ -f "$PROJECT_ROOT/config.env" ]; then
        set -a
        source "$PROJECT_ROOT/config.env"
        set +a
    fi
}

# Kill process on a specific port
kill_port() {
    local port="$1"
    local pids=$(lsof -ti ":$port" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        log WARN "Killing processes on port $port: $pids"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Kill all related processes
kill_all_processes() {
    log INFO "Stopping all Stellar Media Organizer processes..."
    
    # Kill by port
    kill_port $API_PORT
    kill_port $GPU_PORT
    kill_port $FRONTEND_PORT
    
    # Kill by process name
    pkill -9 -f "standalone_backend.py" 2>/dev/null || true
    pkill -9 -f "gpu_converter_service.py" 2>/dev/null || true
    pkill -9 -f "vite.*5173" 2>/dev/null || true
    pkill -9 -f "node.*stellar.*frontend" 2>/dev/null || true
    
    # Kill from PID file
    if [ -f "$PID_FILE" ]; then
        while IFS='=' read -r key value; do
            if [[ "${value:-}" =~ ^[0-9]+$ ]] && kill -0 "$value" 2>/dev/null; then
                kill -9 "$value" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    sleep 2
    log OK "All processes stopped"
}

# Check if port is available
port_available() {
    local port="$1"
    ! lsof -ti ":$port" >/dev/null 2>&1
}

# Wait for port to be available
wait_for_port_free() {
    local port="$1"
    local max_wait=10
    local waited=0
    
    while ! port_available "$port" && [ $waited -lt $max_wait ]; do
        sleep 1
        ((waited++))
    done
    
    if ! port_available "$port"; then
        kill_port "$port"
        sleep 1
    fi
}

# Detect Python
detect_python() {
    local venv_python="$PROJECT_ROOT/.venv/bin/python"
    
    if [ -x "$venv_python" ]; then
        echo "$venv_python"
        return
    fi
    
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
        return
    fi
    
    echo ""
}

# Setup Python venv
setup_venv() {
    local venv_dir="$PROJECT_ROOT/.venv"
    
    if [ ! -d "$venv_dir" ]; then
        log INFO "Creating Python virtual environment..."
        python3 -m venv "$venv_dir"
    fi
    
    local venv_pip="$venv_dir/bin/pip"
    
    if [ ! -f "$venv_dir/.deps-installed" ] || [ "$PROJECT_ROOT/requirements.txt" -nt "$venv_dir/.deps-installed" ]; then
        log INFO "Installing Python dependencies..."
        "$venv_pip" install --upgrade pip -q
        "$venv_pip" install -r "$PROJECT_ROOT/requirements.txt" -q
        touch "$venv_dir/.deps-installed"
    fi
}

# Detect frontend package manager
detect_frontend_pm() {
    if command -v pnpm >/dev/null 2>&1; then
        echo "pnpm"
    elif command -v npm >/dev/null 2>&1; then
        echo "npm"
    else
        echo ""
    fi
}

# Setup frontend
setup_frontend() {
    local frontend_dir="$PROJECT_ROOT/webapp/frontend"
    local pm=$(detect_frontend_pm)
    
    if [ -z "$pm" ]; then
        log ERROR "No Node.js package manager found"
        return 1
    fi
    
    if [ ! -d "$frontend_dir/node_modules" ]; then
        log INFO "Installing frontend dependencies with $pm..."
        (cd "$frontend_dir" && $pm install -q)
    fi
}

# Check if service is healthy
check_service_health() {
    local name="$1"
    local port="$2"
    local endpoint="${3:-/}"
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$endpoint" --connect-timeout 2 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ] || [ "$response" = "404" ] || [ "$response" = "307" ]; then
        return 0
    fi
    return 1
}

# Start GPU service
start_gpu_service() {
    local python_cmd=$(detect_python)
    
    if [ -z "$python_cmd" ]; then
        log ERROR "Python not found"
        return 1
    fi
    
    wait_for_port_free $GPU_PORT
    
    log INFO "Starting GPU Service on port $GPU_PORT..."
    
    nohup "$python_cmd" "$PROJECT_ROOT/gpu_converter_service.py" \
        >> "$RUN_DIR/gpu.log" 2>&1 &
    
    local pid=$!
    echo "GPU_PID=$pid" >> "$PID_FILE"
    
    # Wait for startup
    local waited=0
    while [ $waited -lt 10 ]; do
        if check_service_health "GPU" $GPU_PORT "/health"; then
            log OK "GPU Service started (PID: $pid)"
            return 0
        fi
        sleep 1
        ((waited++))
    done
    
    log WARN "GPU Service may not be fully ready"
    return 0
}

# Start API backend
start_api_service() {
    local python_cmd=$(detect_python)
    
    if [ -z "$python_cmd" ]; then
        log ERROR "Python not found"
        return 1
    fi
    
    wait_for_port_free $API_PORT
    
    log INFO "Starting API Backend on port $API_PORT..."
    
    nohup "$python_cmd" "$PROJECT_ROOT/standalone_backend.py" \
        >> "$RUN_DIR/api.log" 2>&1 &
    
    local pid=$!
    echo "API_PID=$pid" >> "$PID_FILE"
    
    # Wait for startup
    local waited=0
    while [ $waited -lt 15 ]; do
        if check_service_health "API" $API_PORT "/api/v1/health"; then
            log OK "API Backend started (PID: $pid)"
            return 0
        fi
        sleep 1
        ((waited++))
    done
    
    log WARN "API Backend may not be fully ready"
    return 0
}

# Start frontend
start_frontend_service() {
    local pm=$(detect_frontend_pm)
    local frontend_dir="$PROJECT_ROOT/webapp/frontend"
    
    if [ -z "$pm" ]; then
        log ERROR "No Node.js package manager found"
        return 1
    fi
    
    wait_for_port_free $FRONTEND_PORT
    
    log INFO "Starting Frontend on port $FRONTEND_PORT..."
    
    (cd "$frontend_dir" && nohup $pm run dev >> "$RUN_DIR/frontend.log" 2>&1 &)
    
    local pid=$!
    echo "FRONTEND_PID=$pid" >> "$PID_FILE"
    
    # Wait for startup
    local waited=0
    while [ $waited -lt 20 ]; do
        if check_service_health "Frontend" $FRONTEND_PORT "/"; then
            log OK "Frontend started (PID: $pid)"
            return 0
        fi
        sleep 1
        ((waited++))
    done
    
    log WARN "Frontend may not be fully ready"
    return 0
}

# Start all services
start_all() {
    log INFO "=========================================="
    log INFO "Starting Stellar Media Organizer"
    log INFO "=========================================="
    
    load_env
    
    # Clear old PID file
    rm -f "$PID_FILE"
    touch "$PID_FILE"
    
    # Setup
    setup_venv
    setup_frontend
    
    # Start services
    start_gpu_service
    start_api_service
    start_frontend_service
    
    log OK "=========================================="
    log OK "All services started!"
    log OK "=========================================="
    log INFO "Frontend:  http://localhost:$FRONTEND_PORT"
    log INFO "Backend:   http://localhost:$API_PORT"
    log INFO "GPU:       http://localhost:$GPU_PORT"
}

# Stop all services
stop_all() {
    kill_all_processes
}

# Restart all services
restart_all() {
    stop_all
    sleep 2
    start_all
}

# Check status of all services
status() {
    echo ""
    echo "Stellar Media Organizer - Service Status"
    echo "=========================================="
    
    local all_ok=true
    
    # GPU Service
    if check_service_health "GPU" $GPU_PORT "/health"; then
        echo -e "GPU Service:    ${GREEN}● Running${NC} (port $GPU_PORT)"
    else
        echo -e "GPU Service:    ${RED}○ Stopped${NC}"
        all_ok=false
    fi
    
    # API Backend
    if check_service_health "API" $API_PORT "/api/v1/health"; then
        echo -e "API Backend:    ${GREEN}● Running${NC} (port $API_PORT)"
    else
        echo -e "API Backend:    ${RED}○ Stopped${NC}"
        all_ok=false
    fi
    
    # Frontend
    if check_service_health "Frontend" $FRONTEND_PORT "/"; then
        echo -e "Frontend:       ${GREEN}● Running${NC} (port $FRONTEND_PORT)"
    else
        echo -e "Frontend:       ${RED}○ Stopped${NC}"
        all_ok=false
    fi
    
    echo ""
    
    if $all_ok; then
        return 0
    else
        return 1
    fi
}

# Watchdog loop - monitors and restarts crashed services
watchdog_loop() {
    log INFO "Starting watchdog monitoring..."
    
    while true; do
        local restart_needed=false
        
        # Check GPU
        if ! check_service_health "GPU" $GPU_PORT "/health"; then
            log WARN "GPU Service is down, restarting..."
            kill_port $GPU_PORT
            start_gpu_service
            restart_needed=true
        fi
        
        # Check API
        if ! check_service_health "API" $API_PORT "/api/v1/health"; then
            log WARN "API Backend is down, restarting..."
            kill_port $API_PORT
            start_api_service
            restart_needed=true
        fi
        
        # Check Frontend
        if ! check_service_health "Frontend" $FRONTEND_PORT "/"; then
            log WARN "Frontend is down, restarting..."
            kill_port $FRONTEND_PORT
            start_frontend_service
            restart_needed=true
        fi
        
        if $restart_needed; then
            log OK "Services recovered"
        fi
        
        sleep 30
    done
}

# Main
case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status
        ;;
    watch)
        # Start services then monitor
        start_all
        watchdog_loop
        ;;
    kill-ports)
        kill_port $API_PORT
        kill_port $GPU_PORT
        kill_port $FRONTEND_PORT
        log OK "All ports cleared"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|watch|kill-ports}"
        echo ""
        echo "Commands:"
        echo "  start       Start all services"
        echo "  stop        Stop all services"
        echo "  restart     Restart all services"
        echo "  status      Check service status"
        echo "  watch       Start services and monitor (watchdog mode)"
        echo "  kill-ports  Kill any processes using our ports"
        exit 1
        ;;
esac
