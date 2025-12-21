#!/usr/bin/env bash
# Media Organizer Pro - Local (no Docker) Start Script (macOS/Linux)
# Starts: GPU service (8888) + Backend API (8000) + Frontend (5173)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Load environment variables from config.env
if [ -f "$PROJECT_ROOT/config.env" ]; then
  set -a
  source "$PROJECT_ROOT/config.env"
  set +a
fi

echo "🎬 Media Organizer Pro (Local)"
echo "=============================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/pids"
GPU_LOG="$RUN_DIR/gpu.log"
API_LOG="$RUN_DIR/api.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

mkdir -p "$RUN_DIR"

stop_previous() {
  if [ ! -f "$PID_FILE" ]; then
    return
  fi

  echo -e "${YELLOW}Stopping previous run...${NC}"

  while IFS='=' read -r key value; do
    if [[ "${value:-}" =~ ^[0-9]+$ ]] && kill -0 "$value" 2>/dev/null; then
      kill "$value" 2>/dev/null || true
    fi
  done < "$PID_FILE"

  rm -f "$PID_FILE"
sleep 1
}

detect_python() {
  if [ -n "${PYTHON_CMD:-}" ]; then
    echo "$PYTHON_CMD"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi

  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi

  echo ""
}

setup_python_venv() {
  local python_cmd="$1"
  local venv_dir="$PROJECT_ROOT/.venv"

  if [ ! -d "$venv_dir" ]; then
    echo -e "${BLUE}Creating Python venv (.venv)...${NC}"
    "$python_cmd" -m venv "$venv_dir"
  fi

  local venv_python="$venv_dir/bin/python"
  local venv_pip="$venv_dir/bin/pip"

  if [ ! -x "$venv_python" ]; then
    echo -e "${YELLOW}⚠ venv python not found at ${venv_python}. Recreating venv...${NC}"
    rm -rf "$venv_dir"
    "$python_cmd" -m venv "$venv_dir"
  fi

  if [ ! -f "$venv_dir/.deps-installed" ]; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    "$venv_pip" install --upgrade pip >/dev/null 2>&1 || true
    "$venv_pip" install -r "$PROJECT_ROOT/requirements.txt"
    touch "$venv_dir/.deps-installed"
  fi

  echo "$venv_python"
}

detect_frontend_pm() {
  if command -v pnpm >/dev/null 2>&1; then
    echo "pnpm"
    return
  fi
  if command -v npm >/dev/null 2>&1; then
    echo "npm"
    return
  fi
  echo ""
}

cleanup() {
  echo ""
  echo -e "${YELLOW}Stopping services...${NC}"

  if [ -f "$PID_FILE" ]; then
    while IFS='=' read -r key value; do
      if [[ "${value:-}" =~ ^[0-9]+$ ]] && kill -0 "$value" 2>/dev/null; then
        kill "$value" 2>/dev/null || true
      fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi

  echo -e "${GREEN}Done!${NC}"
}

trap cleanup INT TERM EXIT

stop_previous

PYTHON_CMD_RESOLVED="$(detect_python)"
if [ -z "$PYTHON_CMD_RESOLVED" ]; then
  echo -e "${YELLOW}❌ Python not found. Install Python 3.10+ and try again.${NC}"
  exit 1
fi

VENV_PYTHON="$(setup_python_venv "$PYTHON_CMD_RESOLVED")"

FRONTEND_PM="$(detect_frontend_pm)"
if [ -z "$FRONTEND_PM" ]; then
  echo -e "${YELLOW}❌ Node package manager not found. Install Node.js + npm (or pnpm).${NC}"
  exit 1
fi

echo -e "${BLUE}Starting GPU Service (port 8888)...${NC}"
: > "$GPU_LOG"
"$VENV_PYTHON" "$PROJECT_ROOT/gpu_converter_service.py" >"$GPU_LOG" 2>&1 &
GPU_PID=$!
sleep 1

echo -e "${BLUE}Starting Backend API (port 8000)...${NC}"
: > "$API_LOG"
"$VENV_PYTHON" "$PROJECT_ROOT/standalone_backend.py" >"$API_LOG" 2>&1 &
API_PID=$!
sleep 1

echo -e "${BLUE}Starting Frontend (port 5173)...${NC}"
: > "$FRONTEND_LOG"
(
  cd "$PROJECT_ROOT/webapp/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies with ${FRONTEND_PM}..."
    if [ "$FRONTEND_PM" = "pnpm" ]; then
      pnpm install
    else
      npm install
    fi
  fi

  if [ "$FRONTEND_PM" = "pnpm" ]; then
    pnpm run dev
  else
    npm run dev
  fi
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cat > "$PID_FILE" <<EOF
GPU_PID=${GPU_PID}
API_PID=${API_PID}
FRONTEND_PID=${FRONTEND_PID}
EOF

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 All services started!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:5173"
echo -e "  ${BLUE}Backend:${NC}   http://localhost:8000"
echo -e "  ${BLUE}GPU:${NC}       http://localhost:8888"
echo ""
echo -e "  ${BLUE}Logs:${NC}      ${GPU_LOG} | ${API_LOG} | ${FRONTEND_LOG}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

wait
