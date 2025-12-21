# 🎬 Media Organizer Pro

A modern, elegant web application for organizing media files and filtering audio tracks. Built with FastAPI and React, featuring a beautiful contemporary design with emojis and robust functionality.

![Made with Love](https://img.shields.io/badge/Made%20with-❤️-red)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)

## ✨ Features

### 🎯 Core Functionality
- **🗂️ Smart Organization**: Automatically detects and organizes movies and TV series
- **📺 Series Detection**: Recognizes S01E01, 1x01, and other series naming formats
- **🎵 Audio Filtering**: Filter audio tracks by language (Malayalam, Tamil, Hindi, Telugu, etc.)
- **🔊 Volume Boost**: Adjust audio volume levels (0.5x to 3.0x)
- **📦 Batch Processing**: Process multiple files efficiently
- **🎨 Format Support**: Handles MKV, MP4, and AVI files

### 🎨 User Experience
- **✨ Modern UI**: Contemporary design with gradients, shadows, and smooth animations
- **😊 Emoji Integration**: Intuitive visual feedback throughout the interface
- **📱 Responsive**: Works perfectly on desktop, tablet, and mobile
- **🌓 Dark Mode**: Eye-friendly dark theme support
- **⚡ Real-time Updates**: WebSocket support for live progress tracking
- **🎪 Drag & Drop**: Intuitive file upload interface

### 🏗️ Architecture
- **🔧 Modular Backend**: Clean separation of concerns with FastAPI
- **⚛️ React Frontend**: Component-based architecture with Vite
- **🎨 TailwindCSS**: Utility-first CSS framework
- **🐳 Docker Ready**: Containerized deployment with Docker Compose
- **📡 RESTful API**: Well-documented API endpoints
- **🔌 WebSocket**: Real-time communication for progress updates

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose (recommended)
- OR Python 3.11+ and Node.js 20+ (for manual setup)
- MKVToolNix and FFmpeg (required for audio processing)

### 🐳 Docker Deployment (Recommended)

1. **Clone or navigate to the webapp directory:**
   ```bash
   cd webapp
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set your MEDIA_PATH
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### 💻 Manual Setup

#### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies:**
   ```bash
   # macOS
   brew install mkvtoolnix ffmpeg

   # Ubuntu/Debian
   sudo apt install mkvtoolnix ffmpeg

   # Windows
   # Download and install from official websites
   ```

5. **Run the backend:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000

## 📖 Usage Guide

### Organizing Media Files

1. **Enter Directory Path**: Provide the path to your media directory
2. **Select Operation**:
   - 🎬 **Organize**: Rename and structure files
   - 🎵 **Filter Audio**: Keep specific language audio tracks
   - ⚡ **Both**: Organize and filter in one go
3. **Configure Options**:
   - Select target language (for audio filtering)
   - Adjust volume boost (0.5x to 3.0x)
4. **Start Processing**: Click the "Start Processing" button

### Uploading Files

1. **Drag & Drop**: Drag media files onto the upload area
2. **Or Browse**: Click to select files from your computer
3. **Upload**: Click the upload button to transfer files

### Supported Formats

The application recognizes and cleans filenames from:
- 🎬 **MovieRulz** format
- 🎥 **TamilMV** format
- 🎞️ **Sanet.st** format
- 📀 **Standard Release** format (scene/P2P)
- 📺 **TV Series** formats (S01E01, 1x01, etc.)

## 🏗️ Project Structure

```
webapp/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   │   └── ui/        # UI components
│   │   ├── lib/           # Utilities & API
│   │   ├── App.jsx        # Main app component
│   │   └── main.jsx       # Entry point
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Docker orchestration
└── README.md
```

## 🎨 Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI web server
- **WebSockets** - Real-time communication
- **MKVToolNix** - MKV manipulation
- **FFmpeg** - Audio/video processing

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Lucide React** - Beautiful icon library
- **Axios** - HTTP client
- **React Dropzone** - File upload interface
- **Sonner** - Toast notifications

## 🔌 API Endpoints

### Health & Status
- `GET /` - Root endpoint
- `GET /api/v1/health` - Health check with system status

### Media Operations
- `POST /api/v1/analyze` - Analyze files without processing
- `POST /api/v1/process` - Process media files
- `POST /api/v1/upload` - Upload files

### Metadata
- `GET /api/v1/languages` - Get supported languages
- `GET /api/v1/formats` - Get supported file formats

### WebSocket
- `WS /api/v1/ws/progress` - Real-time progress updates

## 🌟 Key Features Explained

### Smart Organization
The app automatically:
- Detects movie vs TV series
- Extracts season/episode numbers
- Creates proper folder structures (Plex/Emby/Jellyfin compatible)
- Cleans filenames from various torrent sources

### Audio Filtering
- Detects audio tracks by language code and track name
- Keeps only selected language audio
- Preserves all video and subtitle tracks
- Optional volume boost using FFmpeg

### Volume Boost
- Adjustable from 0.5x (quieter) to 3.0x (louder)
- Non-destructive (creates new files)
- Preserves original quality

## 🛠️ Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

### Building for Production
```bash
# Docker
docker-compose -f docker-compose.prod.yml up -d

# Manual
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run build && npm run preview
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- React team for the excellent UI library
- TailwindCSS for the utility-first CSS framework
- Lucide for the beautiful icons
- MKVToolNix and FFmpeg communities

## 📧 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

Made with ❤️ and ✨ by the Media Organizer team
