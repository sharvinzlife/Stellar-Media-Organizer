# 📋 Changelog

All notable changes to Stellar Media Organizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] - 2024-12-26 🚀

### 🌐 NAS Integration
- **SMB/NAS Support** - Direct file transfer to Synology (Lharmony) & Unraid (Streamwave) NAS devices
- **Smart Routing** - Automatic organization: Movies → movies, TV → tv, Malayalam → malayalam tv shows
- **Music to NAS** - Direct music library sync to Lharmony NAS
- **NAS Status Panel** - Real-time storage monitoring with capacity indicators for all locations
- **Primary Destination** - NAS is now the default destination in both Video and Music panels

### ✨ UI/UX Enhancements
- **Glitchy Animations** - Cyberpunk-inspired header with random glitch bursts and rotating rings
- **Footer Redesign** - New glitchy footer with social links, features, and floating particles
- **Download Animation** - Green sparkling effects during file transfers
- **Hero Text Animation** - Word-by-word appearance with gradient flow effect
- **Bigger Tab Toggle** - Enhanced Video/Music mode switcher with better visibility
- **Hidden Scrollbars** - Clean, distraction-free interface (no visible scrollbars)
- **Hover Effects** - Interactive animations on all cards, icons, and buttons app-wide
- **Page Loading Bar** - Enhanced gradient glow loading indicator

### 🔧 Technical Improvements
- **spotdl Fix** - Proper virtual environment detection for Spotify downloads
- **TMDB Client** - New robust client with caching, retry logic, and rate limiting
- **OMDb Integration** - OMDb as PRIMARY metadata source, TMDB as secondary for episode titles
- **Smart Renamer** - AllDebrid integration with automatic metadata lookup
- **Metadata Client** - Unified metadata fetching from multiple sources

### 🐛 Bug Fixes
- Fixed spotdl showing red in UI (venv path detection)
- Fixed NAS storage not showing on initial page load
- Fixed Lharmony folder names (tv, malayalam tv shows)
- Fixed config.env password escaping with single quotes

---

## [2.0.0] - 2024-12-20 ⭐

### 🎵 Music Features
- **Multi-source Download** - YouTube Music, Spotify, AllDebrid support
- **Professional Audio Enhancement** - 6 FFmpeg presets (Optimal, Clarity, Bass Boost, Warm, Bright, Flat)
- **MusicBrainz Integration** - Automatic metadata lookup (artist, album, track, year, genre)
- **EBU R128 Normalization** - Broadcast-standard loudness (-14 LUFS)
- **Format Conversion** - FLAC, MP3, M4A, Opus output options

### 🎬 Video Features
- **IMDB Integration** - Automatic series lookup for accurate naming
- **GPU Video Conversion** - VideoToolbox acceleration on macOS for HEVC encoding
- **Audio Track Filtering** - Filter MKV audio tracks by language
- **Volume Boost** - Adjustable audio volume levels (0.5x to 3.0x)

### 🖥️ UI/UX
- **Space-themed Design** - Glassmorphism with purple/cyan gradients
- **Real-time Job Tracking** - Dashboard with progress indicators
- **Activity Monitoring** - Live logs and job history
- **Responsive Layout** - Mobile-friendly design

### 🔧 Technical
- **FastAPI Backend** - Async support with WebSocket for real-time updates
- **React 18 Frontend** - TypeScript with Vite 6
- **TailwindCSS + DaisyUI** - Modern styling framework
- **Docker Support** - Container deployment ready

---

## [1.0.0] - 2024-11-01 🎉

### Initial Release
- Basic video file organization
- IMDB lookup for movies and TV series
- Audio track filtering by language
- CLI interface for batch processing
- Plex/Jellyfin compatible folder structure

---

[3.0.0]: https://github.com/sharvinzlife/stellar-media-organizer/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/sharvinzlife/stellar-media-organizer/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/sharvinzlife/stellar-media-organizer/releases/tag/v1.0.0
