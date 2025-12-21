# Tech Stack

## Backend (Python)

- **Framework**: FastAPI 0.115+
- **Server**: Uvicorn (ASGI)
- **Validation**: Pydantic 2.x with pydantic-settings
- **Media Processing**: pymkv2, MKVToolNix, FFmpeg
- **HTTP Client**: requests, aiofiles
- **Linting**: Ruff (linter + formatter), Pylint, MyPy, Bandit

## Frontend (React)

- **Framework**: React 18
- **Build Tool**: Vite 6
- **Styling**: TailwindCSS 3.x + DaisyUI 5.x
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Notifications**: Sonner
- **File Upload**: react-dropzone
- **Linting**: ESLint 9 (flat config), Prettier

## Infrastructure

- **Containerization**: Docker + Docker Compose
- **Process Management**: concurrently (for dev)
- **Package Manager**: pnpm (root), pip (backend), npm (frontend)
- **Pre-commit Hooks**: pre-commit with Ruff, ESLint, Prettier, Bandit, shellcheck

## System Dependencies

- Python 3.10+
- Node.js 18+
- MKVToolNix: `brew install mkvtoolnix`
- FFmpeg: `brew install ffmpeg`

## Common Commands

```bash
# Full dev setup (recommended for first time)
make setup
# or
chmod +x scripts/setup-dev.sh && ./scripts/setup-dev.sh

# Install all dependencies
pip install -r requirements.txt
pnpm install
pnpm --dir webapp/frontend install

# Start all services (GPU + API + Frontend)
pnpm run dev
# or
./start.sh

# Individual services
pnpm run gpu    # GPU converter (port 8888)
pnpm run api    # FastAPI backend (port 8000)
pnpm run web    # Vite frontend (port 5173)

# Build frontend
pnpm run build

# Docker deployment
cd webapp && docker-compose up -d

# CLI usage
python media_organizer.py organize /path/to/media
python media_organizer.py filter /path/to/media --language malayalam
```

## Linting & Formatting

```bash
# Run all linters
pnpm run lint
make lint

# Auto-fix all issues
pnpm run lint:fix
make lint-fix

# Python only
cd webapp/backend && ruff check . --fix && ruff format .

# JavaScript only
cd webapp/frontend && npm run lint:fix && npm run format

# Run pre-commit hooks manually
pre-commit run --all-files
```

## API Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | Vite dev server |
| Backend API | 8000 | FastAPI |
| GPU Converter | 8888 | Video conversion service |
| Docker Frontend | 80 | Nginx (production) |
