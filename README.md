# ⭐ Stellar Media Organizer

Organize movies, TV series & music for Plex/Jellyfin with IMDB/MusicBrainz integration, GPU video conversion, and professional audio enhancement.

## Features

### 🎬 Video Organization
- **Smart File Naming** - Auto-detects movies/series with IMDB lookup
- **Audio Track Filtering** - Keep only specific languages (Malayalam, Tamil, Hindi, Telugu, English, etc.)
- **GPU Video Conversion** - Hardware-accelerated HEVC encoding (VideoToolbox on macOS)
- **Volume Boost** - Adjust audio levels (0.5x to 3.0x)

### 🎵 Music Organization
- **Multi-Source Download** - YouTube Music, Spotify, AllDebrid
- **MusicBrainz Integration** - Auto metadata lookup (artist, album, track #, year)
- **Audio Enhancement** - Professional FFmpeg processing with presets:
  - Optimal, Clarity, Bass Boost, Warm, Bright, Flat
- **EBU R128 Loudness** - Broadcast-standard normalization
- **Plex/Jellyfin Structure** - `/Artist/Album (Year)/01 - Track.flac`

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/stellar-media-organizer.git
cd stellar-media-organizer

# 2. Copy and edit config
cp config.env.example config.env
# Edit config.env with your API keys and paths

# 3. Start all services
./start.sh
```

Open http://localhost:5173

## Requirements

- Python 3.10+
- Node.js 18+ (pnpm or npm)
- FFmpeg: `brew install ffmpeg`
- MKVToolNix: `brew install mkvtoolnix`

## Configuration

Edit `config.env`:

```bash
# Output directories
MEDIA_PATH=/path/to/processed/videos
MUSIC_OUTPUT_PATH=/path/to/music

# AllDebrid API Key (https://alldebrid.com/apikeys)
ALLDEBRID_API_KEY=your_key

# MusicBrainz (optional, for higher rate limits)
MUSICBRAINZ_CLIENT_ID=
MUSICBRAINZ_CLIENT_SECRET=
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | React web UI |
| Backend | 8000 | FastAPI server |
| GPU | 8888 | Video conversion |

## CLI Usage

```bash
# Organize video files
python media_organizer.py organize /path/to/media

# Filter audio tracks
python media_organizer.py filter /path/to/media --language malayalam

# Organize music
python music_organizer.py /path/to/music --output /path/to/output --preset optimal
```

## Tech Stack

- **Backend**: FastAPI, Pydantic, FFmpeg, MKVToolNix
- **Frontend**: React 18, Vite, TailwindCSS, DaisyUI
- **Tools**: yt-dlp, spotdl, MusicBrainz API

## License

MIT
