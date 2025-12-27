"""
Core package for Media Organizer Pro
Shared logic used by both CLI and API
"""
# Lazy imports to avoid dependency issues
__version__ = "6.1.0"

# Database (optional - requires sqlalchemy)
def get_db():
    from .database import get_db as _get_db
    return _get_db()

def get_database_manager():
    from .database import DatabaseManager
    return DatabaseManager

# IMDB Client
def get_imdb_lookup():
    from .imdb_client import lookup_series
    return lookup_series

# TMDB Client
def get_tmdb_client(api_key=None, access_token=None):
    from .tmdb_client import get_tmdb_client as _get_tmdb_client
    return _get_tmdb_client(api_key, access_token)

# Smart Renamer
def get_smart_renamer(**kwargs):
    from .smart_renamer import SmartRenamer
    return SmartRenamer(**kwargs)

# Direct imports for commonly used items
try:
    from .imdb_client import lookup_series, IMDBSeriesInfo, IMDBEpisodeInfo
except ImportError:
    pass

try:
    from .tmdb_client import (
        TMDBClient,
        TMDBSeriesInfo,
        TMDBMovieInfo,
        TMDBEpisodeInfo,
        TMDBFilenameGenerator,
    )
except ImportError:
    pass

try:
    from .smart_renamer import SmartRenamer, FilenameParser, MediaType, RenameResult
except ImportError:
    pass

# Exceptions (always available)
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

__all__ = [
    # Version
    "__version__",
    # Factory functions
    "get_db",
    "get_database_manager",
    "get_imdb_lookup",
    "get_tmdb_client",
    "get_smart_renamer",
    # IMDB
    "IMDBSeriesInfo",
    "IMDBEpisodeInfo",
    "lookup_series",
    # TMDB
    "TMDBClient",
    "TMDBSeriesInfo",
    "TMDBMovieInfo",
    "TMDBEpisodeInfo",
    "TMDBFilenameGenerator",
    # Smart Renamer
    "SmartRenamer",
    "FilenameParser",
    "MediaType",
    "RenameResult",
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