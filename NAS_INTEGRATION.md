# NAS/SMB Integration Guide

## Overview
Media Organizer Pro now supports automatic organization to your two NAS locations with smart categorization.

## Configured NAS Locations

### 1. Lharmony (Synology DS925+)
- **Host**: 10.1.0.122
- **Share**: `data`
- **Mount Point**: `/Volumes/data`
- **Media Path**: `/Volumes/data/media`

**Supported Categories:**
- ✅ Movies → `/Volumes/data/media/movies`
- ✅ Malayalam Movies → `/Volumes/data/media/malayalam movies`
- ✅ Bollywood Movies → `/Volumes/data/media/bollywood movies`
- ✅ TV Shows → `/Volumes/data/media/tv-shows`
- ✅ Malayalam TV Shows → `/Volumes/data/media/malayalam-tv-shows`
- ✅ Music → `/Volumes/data/media/music`

### 2. Streamwave (Unraid)
- **Host**: 10.1.0.105
- **Share**: `Data-Streamwave`
- **Mount Point**: `/Volumes/Data-Streamwave`
- **Media Path**: `/Volumes/Data-Streamwave/media`

**Supported Categories:**
- ✅ Movies → `/Volumes/Data-Streamwave/media/movies`
- ✅ Malayalam Movies → `/Volumes/Data-Streamwave/media/malayalam movies`
- ✅ Bollywood Movies → `/Volumes/Data-Streamwave/media/bollywood movies`
- ✅ TV Shows → `/Volumes/Data-Streamwave/media/tv-shows`
- ✅ Malayalam TV Shows → `/Volumes/Data-Streamwave/media/malayalam-tv-shows`

## Metadata Sources

### Primary: OMDb API
- IMDb ratings and votes
- Rotten Tomatoes scores
- Metacritic scores
- Box office data
- Awards information
- Cast and crew details

### Secondary: TMDB
- Episode titles with colons
- Accurate year ranges
- Season/episode counts
- Network information
- Poster and backdrop images

## File Organization Rules

### Movies
- **Format**: `Movie Name (Year)/Movie Name (Year).mkv`
- **Example**: `Inception (2010)/Inception (2010).mkv`
- **Location**: Movies folder (creates subfolder per movie)

### TV Shows
- **Format**: `Show Name (Year) - S01E01 - Episode Title.mkv`
- **Example**: `Stranger Things (2016–) - S05E01 - Chapter One: The Crawl.mkv`
- **Location**: TV Shows folder (no subfolder, direct placement)
- **Structure**: 
  ```
  tv-shows/
    Stranger Things (2016–)/
      Season 01/
        Stranger Things (2016–) - S01E01 - Episode Title.mkv
  ```

### Music
- **Format**: `Artist/Album (Year)/01 - Track.flac`
- **Example**: `Daft Punk/Random Access Memories (2013)/01 - Give Life Back to Music.flac`
- **Location**: Music folder (Lharmony only)

## Usage

### CLI Usage

```bash
# Test NAS connections
python3 core/smb_manager.py

# Copy file to NAS
python3 << 'EOF'
from core.smb_manager import create_smb_manager_from_env, MediaCategory
from pathlib import Path

manager = create_smb_manager_from_env()

# Copy movie to Lharmony
manager.copy_to_nas(
    "Lharmony",
    Path("/path/to/movie.mkv"),
    MediaCategory.MOVIES
)

# Copy TV show to Streamwave
manager.copy_to_nas(
    "Streamwave",
    Path("/path/to/show.mkv"),
    MediaCategory.TV_SHOWS
)
EOF
```

### Python API

```python
from core.smb_manager import SMBManager, SMBConfig, MediaCategory
from pathlib import Path

# Create manager
manager = SMBManager()

# Add NAS
lharmony = SMBConfig(
    name="Lharmony",
    host="10.1.0.122",
    username="sharvinzlife",
    password="your_password",
    share="data",
    media_path="/media"
)
manager.add_nas(lharmony)

# Mount and copy
if manager.mount("Lharmony"):
    manager.copy_to_nas(
        "Lharmony",
        Path("/path/to/file.mkv"),
        MediaCategory.MOVIES
    )
```

## Environment Variables

All credentials are stored in `config.env`:

```bash
# Lharmony (Synology DS925+)
LHARMONY_HOST=10.1.0.122
LHARMONY_USERNAME=sharvinzlife
LHARMONY_PASSWORD=mXU@$L9rcFc^*T
LHARMONY_SHARE=data
LHARMONY_MEDIA_PATH=/media

# Streamwave (Unraid)
STREAMWAVE_HOST=10.1.0.105
STREAMWAVE_USERNAME=sharvinzlife
STREAMWAVE_PASSWORD=i6hyYm43I5!3RzqR
STREAMWAVE_SHARE=Data-Streamwave
STREAMWAVE_MEDIA_PATH=/media

# Metadata APIs
OMDB_API_KEY=8800e3b1
TMDB_ACCESS_TOKEN=your_token
TMDB_API_KEY=your_key
```

## Features

### Auto-Mounting
- Automatically mounts SMB shares when needed
- Checks if already mounted before attempting
- Handles mount failures gracefully

### Smart Categorization
- Detects media type (movie/TV/music)
- Routes to appropriate NAS and folder
- Creates subfolders for movies
- Maintains Plex/Jellyfin structure

### Connection Testing
- Tests both NAS connections
- Verifies media paths exist
- Reports status for each NAS

### File Operations
- **Copy**: Copies file to NAS (keeps original)
- **Move**: Copies then deletes original
- **Folder Creation**: Auto-creates movie subfolders

## Troubleshooting

### Mount Issues
```bash
# Check if mounted
ls /Volumes/data
ls /Volumes/Data-Streamwave

# Manual mount (if needed)
mount -t smbfs //sharvinzlife:password@10.1.0.122/data /Volumes/data

# Unmount
umount /Volumes/data
```

### Permission Issues
- Ensure credentials are correct in `config.env`
- Check network connectivity: `ping 10.1.0.122`
- Verify SMB is enabled on NAS

### Path Issues
- Lharmony uses lowercase: `malayalam movies`, `tv-shows`
- Streamwave uses hyphens: `malayalam-tv-shows`
- Music only available on Lharmony

## Next Steps

### Web UI Integration (Coming Soon)
- Visual NAS selector
- Category dropdown
- Connection status indicators
- Progress bars for copying
- Drag-and-drop file upload

### Planned Features
- Batch operations
- Automatic categorization based on filename
- Duplicate detection
- Space usage monitoring
- Transfer speed optimization
