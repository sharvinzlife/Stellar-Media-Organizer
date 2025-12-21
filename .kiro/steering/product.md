# Media Organizer Pro

A comprehensive media file organization tool with IMDB/MusicBrainz integration, GPU video conversion, and professional audio enhancement.

## Core Features

### Video Organization
- **Smart File Organization**: Automatically detects and renames movies/TV series with proper naming conventions (Plex/Jellyfin compatible)
- **Audio Track Filtering**: Filter MKV audio tracks by language (Malayalam, Tamil, Hindi, Telugu, English, etc.)
- **Volume Boost**: Adjust audio volume levels (0.5x to 3.0x)
- **GPU Video Conversion**: VideoToolbox acceleration on macOS for HEVC encoding
- **IMDB Integration**: Automatic series lookup for accurate naming with year ranges

### Music Organization (NEW)
- **MusicBrainz Integration**: Automatic metadata lookup (artist, album, track number, year, genre)
- **Plex/Jellyfin Structure**: Organizes to `/Artist/Album (Year)/01 - Track.flac` format
- **Audio Enhancement**: Professional FFmpeg-based audio processing with presets:
  - **Optimal**: Balanced enhancement (bass +2dB, treble +2.5dB, clarity boost)
  - **Clarity**: Focus on vocals/instruments (high-mid boost, harmonic enhancement)
  - **Bass Boost**: Enhanced low frequencies (+5dB bass)
  - **Warm**: Fuller, warmer sound profile
  - **Bright**: Crisp, enhanced highs
  - **Flat**: Normalization only (EBU R128)
- **EBU R128 Loudness Normalization**: Broadcast-standard loudness (-14 LUFS)
- **Format Conversion**: FLAC, MP3, M4A/AAC output options
- **Metadata Writing**: Updates ID3/Vorbis tags with MusicBrainz data

## Supported Formats

### Video
- MovieRulz, TamilMV, Sanet.st releases
- Standard scene/P2P releases (YTS, RARBG)
- TV series formats (S01E01, 1x01, Season X Episode Y)

### Audio
- MP3, FLAC, M4A, AAC, OGG, Opus, WAV, WMA, ALAC

## Target Users

Users who download media files and need to organize them for media servers like Plex, Jellyfin, or Emby.
