<div align="center">

<img src="assets/stellar-animated-logo.gif" alt="Stellar Media Organizer" width="400">

# ⭐ Stellar Media Organizer

### *Your Media, Perfectly Organized* ✨

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**Organize movies, TV series & music for Plex/Jellyfin with IMDB/MusicBrainz integration, GPU video conversion, and professional audio enhancement.**

[🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [🏗️ Architecture](#️-architecture) • [📦 Tech Stack](#-tech-stack) • [📖 Documentation](#-documentation)

</div>

---

## 🎯 What is Stellar?

Stellar Media Organizer is an all-in-one solution for managing your media library. Whether you're downloading movies, TV series, or music - Stellar automatically organizes, enhances, and prepares everything for your media server.

```
🎬 Messy Downloads  →  ⭐ Stellar  →  📺 Perfect Plex Library
```

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎬 Video Organization
- 🔍 **IMDB Integration** - Auto-lookup for accurate naming
- 🎯 **Smart Detection** - Movies, TV series, anime
- 🔊 **Audio Filtering** - Keep only your languages
- ⚡ **GPU Conversion** - Hardware-accelerated HEVC
- 📁 **Plex/Jellyfin Ready** - Perfect folder structure

</td>
<td width="50%">

### 🎵 Music Organization
- 🎼 **MusicBrainz Lookup** - Artist, album, track metadata
- 📥 **Multi-Source Download** - YouTube, Spotify, AllDebrid
- 🎛️ **Audio Enhancement** - Professional FFmpeg presets
- 📊 **EBU R128** - Broadcast-standard loudness
- 🎧 **Format Options** - FLAC, MP3, M4A, Opus

</td>
</tr>
</table>

### 🎛️ Audio Enhancement Presets

| Preset | Description | Best For |
|--------|-------------|----------|
| ✨ **Optimal** | Rich, loud, professional | Most music |
| 🎯 **Clarity** | Crystal clear vocals | Podcasts, acoustic |
| 🔊 **Bass Boost** | Deep, punchy bass | EDM, hip-hop |
| 🌅 **Warm** | Vintage analog warmth | Jazz, classical |
| ☀️ **Bright** | Crisp, sparkling highs | Pop, rock |
| 📊 **Flat** | Just loudness normalization | Purists |

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client Layer"]
        UI["⚛️ React Frontend<br/>Port 5173"]
    end

    subgraph API["🔌 API Layer"]
        Backend["⚡ FastAPI Backend<br/>Port 8000"]
        GPU["🎮 GPU Service<br/>Port 8888"]
    end

    subgraph Services["⚙️ Service Layer"]
        VideoOrg["🎬 Video Organizer"]
        MusicOrg["🎵 Music Organizer"]
        Downloader["📥 Multi-Source Downloader"]
    end

    subgraph External["🌐 External APIs"]
        IMDB["🎬 IMDB/OMDb"]
        MusicBrainz["🎵 MusicBrainz"]
        YouTube["📺 YouTube Music"]
        Spotify["💚 Spotify"]
        AllDebrid["☁️ AllDebrid"]
    end

    subgraph Tools["🛠️ Processing Tools"]
        FFmpeg["🎞️ FFmpeg"]
        MKVToolNix["📦 MKVToolNix"]
        YtDlp["⬇️ yt-dlp"]
        SpotDL["🎵 spotdl"]
    end

    subgraph Output["📂 Output"]
        Plex["📺 Plex Library"]
        Jellyfin["🎬 Jellyfin Library"]
    end

    UI <--> Backend
    Backend <--> GPU
    Backend --> VideoOrg
    Backend --> MusicOrg
    Backend --> Downloader

    VideoOrg --> IMDB
    MusicOrg --> MusicBrainz
    Downloader --> YouTube
    Downloader --> Spotify
    Downloader --> AllDebrid

    VideoOrg --> FFmpeg
    VideoOrg --> MKVToolNix
    MusicOrg --> FFmpeg
    Downloader --> YtDlp
    Downloader --> SpotDL

    VideoOrg --> Plex
    MusicOrg --> Jellyfin

    style UI fill:#61DAFB,color:#000
    style Backend fill:#009688,color:#fff
    style GPU fill:#76B900,color:#fff
    style IMDB fill:#F5C518,color:#000
    style MusicBrainz fill:#BA478F,color:#fff
    style YouTube fill:#FF0000,color:#fff
    style Spotify fill:#1DB954,color:#fff
```

### 📊 Data Flow

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant F as ⚛️ Frontend
    participant B as ⚡ Backend
    participant D as 📥 Downloader
    participant P as 🎛️ Processor
    participant O as 📂 Output

    U->>F: Paste URLs / Upload Files
    F->>B: POST /api/v1/music/download
    B->>B: Create Job 📋
    B-->>F: Job ID + Status
    
    B->>D: Download from Source
    D->>D: yt-dlp / spotdl / AllDebrid
    D-->>B: Raw Files 📁
    
    B->>P: Process & Enhance
    P->>P: MusicBrainz Lookup 🔍
    P->>P: FFmpeg Enhancement 🎛️
    P-->>B: Enhanced Files ✨
    
    B->>O: Organize to Library
    O-->>B: Complete ✅
    B-->>F: Job Complete
    F-->>U: Success! 🎉
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# macOS
brew install python node ffmpeg mkvtoolnix

# Ubuntu/Debian
sudo apt install python3 nodejs npm ffmpeg mkvtoolnix
```

### Installation

```bash
# 1️⃣ Clone the repo
git clone https://github.com/yourusername/stellar-media-organizer.git
cd stellar-media-organizer

# 2️⃣ Configure environment
cp config.env.example config.env
# Edit config.env with your API keys and paths

# 3️⃣ Start all services
./start.sh
```

### 🌐 Open in Browser

```
http://localhost:5173
```

---

## ⚙️ Configuration

Edit `config.env`:

```bash
# 📂 Output Directories
MEDIA_PATH=/path/to/processed/videos
MUSIC_OUTPUT_PATH=/path/to/music

# 🔑 API Keys
ALLDEBRID_API_KEY=your_key_here

# 🎵 MusicBrainz (optional - higher rate limits)
MUSICBRAINZ_CLIENT_ID=
MUSICBRAINZ_CLIENT_SECRET=
```

---

## 📦 Tech Stack

<table>
<tr>
<td align="center" width="20%">

### ⚡ Backend
![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)

</td>
<td align="center" width="20%">

### ⚛️ Frontend
![React](https://img.shields.io/badge/-React_18-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/-Vite_6-646CFF?style=flat-square&logo=vite&logoColor=white)

</td>
<td align="center" width="20%">

### 🎨 Styling
![TailwindCSS](https://img.shields.io/badge/-Tailwind-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![DaisyUI](https://img.shields.io/badge/-DaisyUI-5A0EF8?style=flat-square&logo=daisyui&logoColor=white)

</td>
<td align="center" width="20%">

### 🛠️ Tools
![FFmpeg](https://img.shields.io/badge/-FFmpeg-007808?style=flat-square&logo=ffmpeg&logoColor=white)
![Docker](https://img.shields.io/badge/-Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

</td>
<td align="center" width="20%">

### 📡 APIs
![IMDB](https://img.shields.io/badge/-IMDB-F5C518?style=flat-square&logo=imdb&logoColor=black)
![Spotify](https://img.shields.io/badge/-Spotify-1DB954?style=flat-square&logo=spotify&logoColor=white)

</td>
</tr>
</table>

### Full Stack Details

| Layer | Technology | Version |
|-------|------------|---------|
| 🐍 Runtime | Python | 3.10+ |
| ⚡ API Framework | FastAPI | 0.115+ |
| 🔄 ASGI Server | Uvicorn | Latest |
| ✅ Validation | Pydantic | 2.x |
| ⚛️ UI Framework | React | 18 |
| 📦 Build Tool | Vite | 6 |
| 🎨 CSS Framework | TailwindCSS | 3.x |
| 🧩 UI Components | DaisyUI | 5.x |
| 🎞️ Video Processing | FFmpeg | Latest |
| 📦 MKV Tools | MKVToolNix | Latest |
| ⬇️ YouTube | yt-dlp | Latest |
| 🎵 Spotify | spotdl | Latest |
| 🐳 Containers | Docker | Latest |

---

## 🖥️ Services

| Service | Port | Description |
|---------|------|-------------|
| ⚛️ Frontend | `5173` | React web UI |
| ⚡ Backend | `8000` | FastAPI server |
| 🎮 GPU | `8888` | Video conversion |

---

## 💻 CLI Usage

```bash
# 🎬 Organize video files
python media_organizer.py organize /path/to/media

# 🔊 Filter audio tracks
python media_organizer.py filter /path/to/media --language malayalam

# 🎵 Organize music with enhancement
python music_organizer.py /path/to/music \
  --output /path/to/output \
  --preset optimal \
  --format flac
```

---

## 📖 Documentation

- [🏗️ Project Structure](.kiro/steering/structure.md)
- [🛠️ Tech Stack Details](.kiro/steering/tech.md)
- [📋 Product Features](.kiro/steering/product.md)

---

## 📝 Changelog

### v2.0.0 - *Stellar Release* ⭐ (December 2024)

#### 🎵 Music Features
- ✨ Multi-source download (YouTube Music, Spotify, AllDebrid)
- 🎛️ Professional audio enhancement with 6 presets
- 🎼 MusicBrainz metadata integration
- 📊 EBU R128 loudness normalization
- 🎧 Format conversion (FLAC, MP3, M4A, Opus)

#### 🎬 Video Features  
- 🔍 IMDB integration for accurate naming
- ⚡ GPU-accelerated video conversion
- 🔊 Audio track filtering by language
- 📁 Plex/Jellyfin compatible structure

#### 🖥️ UI/UX
- 🌌 Space-themed glassmorphism design
- 📊 Real-time job tracking dashboard
- 🎯 Activity monitoring with live logs
- 📱 Responsive mobile-friendly layout

#### 🔧 Technical
- ⚡ FastAPI backend with async support
- ⚛️ React 18 with TypeScript
- 🎨 TailwindCSS + DaisyUI styling
- 🐳 Docker support for deployment

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for media enthusiasts**

⭐ Star this repo if you find it useful!

</div>
