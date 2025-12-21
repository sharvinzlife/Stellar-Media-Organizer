#!/bin/bash
# Development environment setup script for Media Organizer Pro
# Run: chmod +x scripts/setup-dev.sh && ./scripts/setup-dev.sh

set -e

echo "🎬 Setting up Media Organizer Pro development environment..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python $(python3 --version | cut -d' ' -f2) found"

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi
print_success "Node.js $(node --version) found"

if ! command -v pnpm &> /dev/null; then
    print_warning "pnpm not found, installing..."
    npm install -g pnpm
fi
print_success "pnpm $(pnpm --version) found"

echo ""

# Install Python dependencies
print_step "Installing Python dependencies..."
pip install -r requirements.txt --quiet
pip install ruff pylint mypy bandit pre-commit --quiet
print_success "Python dependencies installed"

# Install backend dependencies
print_step "Installing backend dependencies..."
pip install -r webapp/backend/requirements.txt --quiet
print_success "Backend dependencies installed"

# Install frontend dependencies
print_step "Installing frontend dependencies..."
cd webapp/frontend
pnpm install --silent
cd ../..
print_success "Frontend dependencies installed"

# Install root dependencies
print_step "Installing root dependencies..."
pnpm install --silent
print_success "Root dependencies installed"

echo ""

# Setup pre-commit hooks
print_step "Setting up pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg
print_success "Pre-commit hooks installed"

# Create secrets baseline for detect-secrets
print_step "Creating secrets baseline..."
if command -v detect-secrets &> /dev/null; then
    detect-secrets scan > .secrets.baseline 2>/dev/null || true
    print_success "Secrets baseline created"
else
    print_warning "detect-secrets not found, skipping baseline creation"
fi

echo ""

# Run initial lint check
print_step "Running initial lint checks..."
echo ""

echo "  Python (ruff):"
cd webapp/backend
if ruff check . --quiet 2>/dev/null; then
    print_success "  No Python linting issues"
else
    print_warning "  Some Python linting issues found (run 'ruff check . --fix' to auto-fix)"
fi
cd ../..

echo "  JavaScript (eslint):"
cd webapp/frontend
if npx eslint . --quiet 2>/dev/null; then
    print_success "  No JavaScript linting issues"
else
    print_warning "  Some JavaScript linting issues found (run 'npm run lint:fix' to auto-fix)"
fi
cd ../..

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Development environment setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Available commands:"
echo "  pnpm run dev          - Start all services (GPU + API + Frontend)"
echo "  pnpm run lint         - Run all linters"
echo "  pre-commit run --all  - Run all pre-commit hooks"
echo ""
echo "Linting commands:"
echo "  cd webapp/backend && ruff check . --fix    - Fix Python issues"
echo "  cd webapp/frontend && npm run lint:fix     - Fix JS issues"
echo "  cd webapp/frontend && npm run format       - Format with Prettier"
echo ""
