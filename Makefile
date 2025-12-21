# Media Organizer Pro - Development Makefile
# Usage: make <target>

.PHONY: help install install-dev dev run lint format typecheck test check clean setup

# Default target
help:
	@echo "🎬 Media Organizer Pro - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup        - Full development environment setup"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies (ruff, mypy, pytest)"
	@echo ""
	@echo "Development:"
	@echo "  make run          - Start the application (./start.sh)"
	@echo "  make dev          - Start development servers (frontend + backend)"
	@echo "  make lint         - Run linter (ruff check)"
	@echo "  make format       - Format code (ruff format + fix)"
	@echo "  make typecheck    - Run type checker (mypy)"
	@echo "  make test         - Run tests with coverage"
	@echo "  make check        - Run all checks (lint + typecheck + test)"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "Docker (legacy):"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo ""

# Full setup
setup:
	@chmod +x scripts/setup-dev.sh
	@./scripts/setup-dev.sh

# Install dependencies
install:
	@echo "📦 Installing production dependencies..."
	pip install -r requirements.txt

install-dev: install
	@echo "🛠️  Installing development dependencies..."
	pip install "ruff>=0.8.5" "mypy>=1.13.0" "pytest>=8.3.4" "pytest-asyncio>=0.24.0" "pytest-cov>=6.0.0"
	@echo "✅ Development environment ready!"

# Start application
run:
	@echo "🚀 Starting Media Organizer Pro..."
	./start.sh

# Start development servers (full stack)
dev:
	@echo "🚀 Starting development servers..."
	./start.sh

# Run linter
lint:
	@echo "🔍 Running Ruff linter..."
	ruff check .

# Format code
format:
	@echo "✨ Formatting code with Ruff..."
	ruff format .
	ruff check --fix .
	@echo "✅ Code formatted!"

# Type checking
typecheck:
	@echo "🔎 Running mypy type checker..."
	mypy core/ config.py standalone_backend.py gpu_converter_service.py

# Run tests
test:
	@echo "🧪 Running tests with coverage..."
	pytest --cov=core --cov=config --cov-report=term-missing --cov-report=html

# Run all checks
check: lint typecheck test
	@echo "✅ All checks passed!"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf webapp/frontend/dist 2>/dev/null || true
	rm -rf webapp/frontend/node_modules/.cache 2>/dev/null || true
	@echo "✓ Clean complete"

# Build for production
build:
	cd webapp/frontend && pnpm run build

# Docker commands
docker-up:
	cd webapp && docker-compose up -d

docker-down:
	cd webapp && docker-compose down

docker-logs:
	cd webapp && docker-compose logs -f
