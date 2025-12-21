"""
Core package for Media Organizer Pro
Shared logic used by both CLI and API
"""
# Database
from .database import (
    get_db,
    DatabaseManager,
    Job,
    JobStatus,
    JobType,
)

# IMDB Client (available)
from .imdb_client import lookup_series, IMDBSeriesInfo, IMDBEpisodeInfo

# Exceptions
from .exceptions import (
    MediaOrganizerError,
    DirectoryNotFoundError,
    FFmpegNotFoundError,
    MKVToolNixNotFoundError,
    VideoConversionError,
    AudioFilterError,
    IMDBLookupError,
    InvalidFormatError,
    ConfigurationError,
    PermissionError as MediaPermissionError,
    DiskSpaceError,
)

__version__ = "6.1.0"

__all__ = [
    # Database
    "get_db",
    "DatabaseManager",
    "Job",
    "JobStatus",
    "JobType",
    # IMDB
    "IMDBSeriesInfo",
    "IMDBEpisodeInfo",
    "lookup_series",
    # Exceptions
    "MediaOrganizerError",
    "DirectoryNotFoundError",
    "FFmpegNotFoundError",
    "MKVToolNixNotFoundError",
    "VideoConversionError",
    "AudioFilterError",
    "IMDBLookupError",
    "InvalidFormatError",
    "ConfigurationError",
    "MediaPermissionError",
    "DiskSpaceError",
]

# TODO: Extract from media_organizer.py
# from .organizer import MediaOrganizer, MediaFile, SeriesDetector
# from .audio_filter import AudioTrackFilter
# from .video_converter import VideoConverter

