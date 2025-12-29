#!/usr/bin/env bash
#
# Stellar Media Organizer - Unified Service Manager
# ALWAYS kills existing processes and starts fresh - NO CONFLICTS
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/stellar.pids"
LOG_FILE="$RUN_DIR/service.log"
LOCK_FILE="$RUN_DIR/stellar.lock"

# Ports - FIXED, never change
API_PORT=8000
GPU_PORT=8888
FRONTEND_PORT=5173

# Timeouts
STARTUP_TIMEOUT=30
HEALTH_CHECK_INTERVAL=30

mkdir -p "$RUN_DIR"

# ============================================================================
# LOGGING
# ============================================================================
log() {
    local level="$1"
    shift
    local msg="$*"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] [$level] $msg" | tee -a "$LOG_FILE"
}

# ============================================================================
# AGGRESSIVE PORT/PROCESS CLEANUP - ALWAYS RUN BEFORE START
# ============================================================================
force_kill_port() {
    local port="$1"
    
    # Method 1: lsof
    local pids=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        log "KILL" "Port $port - killing PIDs: $pids"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
    fi
    
    # Method 2: fuser
    fuser -k "$port/tcp" 2>/dev/null || true
    
    # Method 3: ss + kill
    local ss_pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K\d+' || true)
    if [ -n "$ss_pids" ]; then
        echo "$ss_pids" | xargs -r kill -9 2>/dev/null || true
    fi
}

force_kill_by_pattern() {
    local pattern="$1"
    pkill -9 -f "$pattern" 2>/dev/null || true
}

# NUCLEAR CLEANUP - kills EVERYTHING related to our app
nuclear_cleanup() {
    log "CLEANUP" "=== NUCLEAR CLEANUP - Killing ALL related processes ==="
    
    # Kill by port (most reliable)
    force_kill_port $API_PORT
    force_kill_port $GPU_PORT
    force_kill_port $FRONTEND_PORT
    
    # Kill by process patterns
    force_kill_by_pattern "standalone_backend"
    force_kill_by_pattern "gpu_converter_service"
    force_kill_by_pattern "uvicorn.*8000"
    force_kill_by_pattern "uvicorn.*8888"
    force_kill_by_pattern "vite.*5173"
    force_kill_by_pattern "node.*stellar"
    force_kill_by_pattern "node.*frontend.*dev"
    
    # Kill from PID file
    if [ -f "$PID_FILE" ]; then
        while IFS='=' read -r key value; do
            if [[ "${value:-}" =~ ^[0-9]+$ ]]; then
                kill -9 "$value" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    # Wait for ports to be free
    sleep 2
    
    # Verify ports are free
    local still_blocked=""
    for port in $API_PORT $GPU_PORT $FRONTEND_PORT; do
        if lsof -ti ":$port" >/dev/null 2>&1; then
            still_blocked="$still_blocked $port"
        fi
    done
    
    if [ -n "$still_blocked" ]; then
        log "WARN" "Ports still blocked:$still_blocked - forcing again..."
        for port in $still_blocked; do
            force_kill_port "$port"
        done
        sleep 2
    fi
    
    log "CLEANUP" "=== Cleanup complete ==="
}

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================
load_env() {
    if [ -f "$PROJECT_ROOT/config.env" ]; then
        set -a
        source "$PROJECT_ROOT/config.env"
        set +a
    fi
}

get_python() {
    local venv_py="$PROJECT_ROOT/.venv/bin/python"
    if [ -x "$venv_py" ]; then
        echo "$venv_py"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo ""
    fi
}

setup_venv() {
    local venv_dir="$PROJECT_ROOT/.venv"
    
    if [ ! -d "$venv_dir" ]; then
        log "SETUP" "Creating Python venv..."
        python3 -m venv "$venv_dir"
    fi
    
    if [ ! -f "$venv_dir/.deps-ok" ] || [ "$PROJECT_ROOT/requirements.txt" -nt "$venv_dir/.deps-ok" ]; then
        log "SETUP" "Installing Python dependencies..."
        "$venv_dir/bin/pip" install --upgrade pip -q 2>/dev/null
        "$venv_dir/bin/pip" install -r "$PROJECT_ROOT/requirements.txt" -q 2>/dev/null
        touch "$venv_dir/.deps-ok"
    fi
}

get_npm() {
    if command -v pnpm >/dev/null 2>&1; then
        echo "pnpm"
    elif command -v npm >/dev/null 2>&1; then
        echo "npm"
    else
        echo ""
    fi
}

setup_frontend() {
    local fe_dir="$PROJECT_ROOT/webapp/frontend"
    local npm_cmd=$(get_npm)
    
    if [ -z "$npm_cmd" ]; then
        log "ERROR" "No npm/pnpm found"
        return 1
    fi
    
    if [ ! -d "$fe_dir/node_modules" ]; then
        log "SETUP" "Installing frontend deps with $npm_cmd..."
        (cd "$fe_dir" && $npm_cmd install --silent 2>/dev/null)
    fi
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================
check_health() {
    local port="$1"
    local endpoint="${2:-/}"
    curl -sf "http://localhost:$port$endpoint" --connect-timeout 2 >/dev/null 2>&1
}

wait_for_health() {
    local name="$1"
    local port="$2"
    local endpoint="${3:-/}"
    local timeout="${4:-$STARTUP_TIMEOUT}"
    
    local waited=0
    while [ $waited -lt $timeout ]; do
        if check_health "$port" "$endpoint"; then
            return 0
        fi
        sleep 1
        ((waited++))
    done
    return 1
}

# ============================================================================
# SERVICE STARTERS
# ============================================================================
start_gpu() {
    local py=$(get_python)
    [ -z "$py" ] && { log "ERROR" "Python not found"; return 1; }
    
    log "START" "GPU Service (port $GPU_PORT)..."
    
    : > "$RUN_DIR/gpu.log"
    nohup "$py" "$PROJECT_ROOT/gpu_converter_service.py" >> "$RUN_DIR/gpu.log" 2>&1 &
    local pid=$!
    echo "GPU=$pid" >> "$PID_FILE"
    
    if wait_for_health "GPU" $GPU_PORT "/health" 15; then
        log "OK" "GPU Service started (PID: $pid)"
        return 0
    else
        log "WARN" "GPU Service slow to start (PID: $pid)"
        return 0
    fi
}

start_api() {
    local py=$(get_python)
    [ -z "$py" ] && { log "ERROR" "Python not found"; return 1; }
    
    log "START" "API Backend (port $API_PORT)..."
    
    : > "$RUN_DIR/api.log"
    nohup "$py" "$PROJECT_ROOT/standalone_backend.py" >> "$RUN_DIR/api.log" 2>&1 &
    local pid=$!
    echo "API=$pid" >> "$PID_FILE"
    
    if wait_for_health "API" $API_PORT "/api/v1/health" 20; then
        log "OK" "API Backend started (PID: $pid)"
        return 0
    else
        log "WARN" "API Backend slow to start (PID: $pid)"
        return 0
    fi
}

start_frontend() {
    local npm_cmd=$(get_npm)
    [ -z "$npm_cmd" ] && { log "ERROR" "npm/pnpm not found"; return 1; }
    
    local fe_dir="$PROJECT_ROOT/webapp/frontend"
    
    log "START" "Frontend (port $FRONTEND_PORT)..."
    
    : > "$RUN_DIR/frontend.log"
    (cd "$fe_dir" && nohup $npm_cmd run dev >> "$RUN_DIR/frontend.log" 2>&1 &)
    sleep 2
    
    # Get the actual vite process PID
    local pid=$(lsof -ti ":$FRONTEND_PORT" 2>/dev/null | head -1 || echo "")
    [ -n "$pid" ] && echo "FRONTEND=$pid" >> "$PID_FILE"
    
    if wait_for_health "Frontend" $FRONTEND_PORT "/" 25; then
        log "OK" "Frontend started (PID: ${pid:-unknown})"
        return 0
    else
        log "WARN" "Frontend slow to start"
        return 0
    fi
}

# ============================================================================
# MAIN COMMANDS
# ============================================================================
cmd_start() {
    log "INFO" "============================================"
    log "INFO" "STELLAR MEDIA ORGANIZER - STARTING"
    log "INFO" "============================================"
    
    # ALWAYS cleanup first - no exceptions
    nuclear_cleanup
    
    # Fresh PID file
    rm -f "$PID_FILE"
    touch "$PID_FILE"
    
    # Load environment
    load_env
    
    # Setup
    setup_venv
    setup_frontend
    
    # Start services in order
    start_gpu
    start_api
    start_frontend
    
    log "INFO" "============================================"
    log "OK" "ALL SERVICES STARTED"
    log "INFO" "============================================"
    log "INFO" "Frontend:  http://localhost:$FRONTEND_PORT"
    log "INFO" "Backend:   http://localhost:$API_PORT"
    log "INFO" "GPU:       http://localhost:$GPU_PORT"
    log "INFO" "Logs:      $RUN_DIR/*.log"
    log "INFO" "============================================"
}

cmd_stop() {
    log "INFO" "Stopping all services..."
    nuclear_cleanup
    log "OK" "All services stopped"
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║   STELLAR MEDIA ORGANIZER - STATUS       ║"
    echo "╠══════════════════════════════════════════╣"
    
    local all_ok=true
    
    # GPU
    if check_health $GPU_PORT "/health"; then
        printf "║  GPU Service:    %-20s  ║\n" "✅ Running (:$GPU_PORT)"
    else
        printf "║  GPU Service:    %-20s  ║\n" "❌ Stopped"
        all_ok=false
    fi
    
    # API
    if check_health $API_PORT "/api/v1/health"; then
        printf "║  API Backend:    %-20s  ║\n" "✅ Running (:$API_PORT)"
    else
        printf "║  API Backend:    %-20s  ║\n" "❌ Stopped"
        all_ok=false
    fi
    
    # Frontend
    if check_health $FRONTEND_PORT "/"; then
        printf "║  Frontend:       %-20s  ║\n" "✅ Running (:$FRONTEND_PORT)"
    else
        printf "║  Frontend:       %-20s  ║\n" "❌ Stopped"
        all_ok=false
    fi
    
    echo "╚══════════════════════════════════════════╝"
    echo ""
    
    $all_ok && return 0 || return 1
}

cmd_watch() {
    log "INFO" "Starting watchdog mode..."
    
    # Initial start
    cmd_start
    
    log "INFO" "Watchdog monitoring every ${HEALTH_CHECK_INTERVAL}s..."
    
    while true; do
        sleep $HEALTH_CHECK_INTERVAL
        
        local need_restart=false
        
        # Check each service
        if ! check_health $GPU_PORT "/health"; then
            log "WARN" "GPU Service down!"
            need_restart=true
        fi
        
        if ! check_health $API_PORT "/api/v1/health"; then
            log "WARN" "API Backend down!"
            need_restart=true
        fi
        
        if ! check_health $FRONTEND_PORT "/"; then
            log "WARN" "Frontend down!"
            need_restart=true
        fi
        
        # If any service is down, restart ALL (clean slate)
        if $need_restart; then
            log "WARN" "Service(s) down - performing full restart..."
            cmd_restart
        fi
    done
}

cmd_logs() {
    local service="${2:-all}"
    
    case "$service" in
        api)      tail -f "$RUN_DIR/api.log" ;;
        gpu)      tail -f "$RUN_DIR/gpu.log" ;;
        frontend) tail -f "$RUN_DIR/frontend.log" ;;
        *)        tail -f "$RUN_DIR/api.log" "$RUN_DIR/gpu.log" "$RUN_DIR/frontend.log" ;;
    esac
}

# ============================================================================
# ENTRY POINT
# ============================================================================
case "${1:-help}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    watch)   cmd_watch ;;
    logs)    cmd_logs "$@" ;;
    *)
        echo ""
        echo "Stellar Media Organizer - Service Manager"
        echo "=========================================="
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start     Kill all & start fresh (ALWAYS clean)"
        echo "  stop      Stop all services"
        echo "  restart   Full restart (stop + start)"
        echo "  status    Show service status"
        echo "  watch     Start + auto-restart on crash"
        echo "  logs      Tail logs (logs api|gpu|frontend|all)"
        echo ""
        exit 1
        ;;
esac
