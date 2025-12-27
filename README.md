<div align="center">

<img src="assets/stellar-animated-logo.gif" alt="Stellar Media Organizer" width="400">

# ⭐ Stellar Media Organizer

### *Your Media, Perfectly Organized* ✨

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**🎬 Organize movies, TV series & music for Plex, Jellyfin, Emby with IMDB/TMDB/MusicBrainz integration, GPU video conversion, NAS support, and professional audio enhancement.**

[🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [💻 Installation](#-installation) • [📦 Tech Stack](#-tech-stack) • [📖 Documentation](#-documentation)

---

### 🏷️ Keywords
`plex` `jellyfin` `emby` `media-server` `media-organizer` `movie-renamer` `tv-series` `music-organizer` `nas` `synology` `unraid` `imdb` `tmdb` `musicbrainz` `ffmpeg` `hevc` `gpu-encoding` `audio-enhancement` `metadata` `file-organizer`

</div>

---

## 🎯 What is Stellar?

Stellar Media Organizer is an **all-in-one solution** for managing your media library. Whether you're downloading movies, TV series, or music - Stellar automatically organizes, enhances, and prepares everything for your **Plex**, **Jellyfin**, or **Emby** media server.

```
🎬 Messy Downloads  →  ⭐ Stellar  →  📺 Perfect Media Library
```

### 🎯 Perfect For:
- 📺 **Plex** users who want perfectly named media
- 🎬 **Jellyfin** enthusiasts with large libraries
- 🎵 **Music collectors** who need proper metadata
- 🖥️ **NAS owners** (Synology, Unraid, TrueNAS)
- 🎮 **Home theater** builders

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎬 Video Organization
- 🔍 **IMDB/TMDB Integration** - Auto-lookup for accurate naming
- 🎯 **Smart Detection** - Movies, TV series, anime
- 🔊 **Audio Filtering** - Keep only your languages
- ⚡ **GPU Conversion** - Hardware-accelerated HEVC
- 📁 **Plex/Jellyfin Ready** - Perfect folder structure
- 🌐 **NAS Support** - Direct transfer to Synology/Unraid

</td>
<td width="50%">

### 🎵 Music Organization
- 🎼 **MusicBrainz Lookup** - Artist, album, track metadata
- 📥 **Multi-Source Download** - YouTube, Spotify, AllDebrid
- 🎛️ **Audio Enhancement** - Professional FFmpeg presets
- 📊 **EBU R128** - Broadcast-standard loudness
- 🎧 **Format Options** - FLAC, MP3, M4A, Opus
- 📂 **Plex Music Structure** - Artist/Album (Year)/Track

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

## 💻 Installation

### 📋 Prerequisites

<details>
<summary><b>🍎 macOS</b></summary>

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node ffmpeg mkvtoolnix

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pnpm
npm install -g pnpm
```
</details>

<details>
<summary><b>🪟 Windows</b></summary>

```powershell
# Install Chocolatey if not installed (Run as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install dependencies
choco install python311 nodejs ffmpeg mkvtoolnix -y

# Install uv (Python package manager)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install pnpm
npm install -g pnpm

# Restart terminal after installation
```

**Alternative: Manual Installation**
1. [Python 3.11+](https://www.python.org/downloads/)
2. [Node.js 18+](https://nodejs.org/)
3. [FFmpeg](https://ffmpeg.org/download.html) - Add to PATH
4. [MKVToolNix](https://mkvtoolnix.download/downloads.html)
</details>

<details>
<summary><b>🐧 Linux (Ubuntu/Debian)</b></summary>

```bash
# Update package list
sudo apt update

# Install dependencies
sudo apt install python3.11 python3.11-venv nodejs npm ffmpeg mkvtoolnix -y

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pnpm
npm install -g pnpm
```
</details>

---

### 🚀 Quick Start

```bash
# 1️⃣ Clone the repository
git clone https://github.com/sharvinzlife/Stellar-Media-Organizer.git
cd Stellar-Media-Organizer

# 2️⃣ Run setup script (creates venv, installs dependencies)
make setup
# OR manually:
# chmod +x scripts/setup-dev.sh && ./scripts/setup-dev.sh

# 3️⃣ Configure environment
cp config.env.example config.env
# Edit config.env with your API keys and NAS settings

# 4️⃣ Start all services
./start.sh
# OR on Windows:
# start.bat
```

### 🌐 Open in Browser

```
http://localhost:5173
```

---

## ⚙️ Configuration

Edit `config.env` with your settings:

```bash
# 📂 Output Directories
MEDIA_PATH=~/Documents/Processed
MUSIC_OUTPUT_PATH=~/Music

# 🔑 API Keys (Required)
ALLDEBRID_API_KEY=your_key_here
OMDB_API_KEY=your_key_here        # Get free: http://www.omdbapi.com/apikey.aspx

# 🎬 TMDB (Optional - for episode titles)
TMDB_ACCESS_TOKEN=your_token_here  # Get: https://www.themoviedb.org/settings/api

# 🌐 NAS Configuration (Optional)
# Synology NAS
LHARMONY_HOST=10.1.0.122
LHARMONY_USERNAME=your_username
LHARMONY_PASSWORD='your_password'  # Use single quotes for special chars
LHARMONY_SHARE=data
LHARMONY_MEDIA_PATH=/media

# Unraid NAS
STREAMWAVE_HOST=10.1.0.105
STREAMWAVE_USERNAME=your_username
STREAMWAVE_PASSWORD='your_password'
STREAMWAVE_SHARE=Data-Streamwave
STREAMWAVE_MEDIA_PATH=/media
```

See [config.env.example](config.env.example) for all options.

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

# 🔊 Filter audio tracks by language
python media_organizer.py filter /path/to/media --language malayalam

# 🎵 Organize music with enhancement
python music_organizer.py /path/to/music \
  --output /path/to/output \
  --preset optimal \
  --format flac

# 📥 Download music from URL
python music_downloader.py "https://open.spotify.com/playlist/..."
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

---

## 📝 Changelog

### v3.0.0 - *NAS Integration & UI Overhaul* 🚀 (December 2025)

#### 🌐 NAS Integration
- 🔗 **SMB/NAS Support** - Direct transfer to Synology (Lharmony) & Unraid (Streamwave)
- 📂 **Smart Routing** - Movies, TV shows, Malayalam content auto-organized
- 🎵 **Music to NAS** - Direct music library sync to Lharmony
- 📊 **NAS Status Panel** - Real-time storage monitoring for all locations

#### ✨ UI/UX Enhancements
- 🎨 **Glitchy Animations** - Cyberpunk-inspired header & footer effects
- 🌟 **Download Animation** - Green sparkling effects during transfers
- 🎭 **Hero Text Animation** - Word-by-word appearance with gradient flow
- 📱 **Bigger Tab Toggle** - Enhanced Video/Music mode switcher
- 🚫 **Hidden Scrollbars** - Clean, distraction-free interface
- 🔘 **Hover Effects** - Interactive animations on all cards, icons, buttons

#### 🔧 Technical Improvements
- 🐍 **spotdl Fix** - Proper venv detection for Spotify downloads
- 🎬 **TMDB Client** - Robust episode title fetching with caching
- 🎯 **OMDb Primary** - OMDb as primary metadata source, TMDB secondary
- 📦 **Smart Renamer** - AllDebrid integration with metadata lookup

### v2.0.0 - *Stellar Release* ⭐ (December 2025)

- 🎵 Multi-source music download (YouTube, Spotify, AllDebrid)
- 🎛️ Professional audio enhancement with 6 presets
- 🎬 IMDB integration for accurate naming
- ⚡ GPU-accelerated video conversion
- 🌌 Space-themed glassmorphism UI

---

## 📖 Documentation

- [🏗️ Project Structure](.kiro/steering/structure.md)
- [🛠️ Tech Stack Details](.kiro/steering/tech.md)
- [📋 Product Features](.kiro/steering/product.md)
- [🌐 NAS Integration](NAS_INTEGRATION.md)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [sharvinzlife](https://github.com/sharvinzlife)**

⭐ Star this repo if you find it useful!

[![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat-square&logo=github)](https://github.com/sharvinzlife)
[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://instagram.com/sharvinzlife)
[![Twitter](https://img.shields.io/badge/-Twitter-1DA1F2?style=flat-square&logo=twitter&logoColor=white)](https://x.com/sharvinzlife)

</div>
