"""
Core package for Media Organizer Pro
Shared logic used by both CLI and API
"""
# Lazy imports to avoid dependency issues
import contextlib

__version__ = "6.2.0"

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
with contextlib.suppress(ImportError):
    from .imdb_client import IMDBEpisodeInfo, IMDBSeriesInfo, lookup_series

with contextlib.suppress(ImportError):
    from .tmdb_client import (
        TMDBClient,
        TMDBEpisodeInfo,
        TMDBFilenameGenerator,
        TMDBMovieInfo,
        TMDBSeriesInfo,
    )

with contextlib.suppress(ImportError):
    from .smart_renamer import FilenameParser, MediaType, RenameResult, SmartRenamer

# Exceptions (always available)
from .exceptions import (
    AudioFilterError,
    ConfigurationError,
    DirectoryNotFoundError,
    DiskSpaceError,
    FFmpegNotFoundError,
    IMDBLookupError,
    InvalidFormatError,
    MediaOrganizerError,
    MKVToolNixNotFoundError,
    VideoConversionError,
)
from .exceptions import (
    PermissionError as MediaPermissionError,
)

# Constants (always available)
from .constants import (
    CATEGORY_DISPLAY_LABELS,
    DEFAULT_CLEANUP_AGE_HOURS,
    LHARMONY_CATEGORY_MAP,
    MIN_DISK_SPACE_GB,
    PLEX_LIBRARY_MAP,
    STREAMWAVE_CATEGORY_MAP,
    SUPPORTED_LANGUAGES,
    VIDEO_EXTENSIONS,
    get_download_base_dir,
    get_nas_category_map,
    get_plex_library_name,
)

__all__ = [
    "AudioFilterError",
    "ConfigurationError",
    "DirectoryNotFoundError",
    "DiskSpaceError",
    "FFmpegNotFoundError",
    "FilenameParser",
    "IMDBEpisodeInfo",
    "IMDBLookupError",
    # IMDB
    "IMDBSeriesInfo",
    "InvalidFormatError",
    "MKVToolNixNotFoundError",
    # Exceptions
    "MediaOrganizerError",
    "MediaPermissionError",
    "MediaType",
    "RenameResult",
    # Smart Renamer
    "SmartRenamer",
    # TMDB
    "TMDBClient",
    "TMDBEpisodeInfo",
    "TMDBFilenameGenerator",
    "TMDBMovieInfo",
    "TMDBSeriesInfo",
    "VideoConversionError",
    # Version
    "__version__",
    "get_database_manager",
    # Factory functions
    "get_db",
    "get_imdb_lookup",
    "get_smart_renamer",
    "get_tmdb_client",
    "lookup_series",
    # Language utilities
    "LANGUAGE_KEYWORDS",
    "detect_language_from_filename",
    "detect_language_from_mkv",
    "get_category_for_language",
    "is_tv_content",
    "normalize_language",
    # Constants
    "CATEGORY_DISPLAY_LABELS",
    "DEFAULT_CLEANUP_AGE_HOURS",
    "LHARMONY_CATEGORY_MAP",
    "MIN_DISK_SPACE_GB",
    "PLEX_LIBRARY_MAP",
    "STREAMWAVE_CATEGORY_MAP",
    "SUPPORTED_LANGUAGES",
    "VIDEO_EXTENSIONS",
    "get_download_base_dir",
    "get_nas_category_map",
    "get_plex_library_name",
]

# Language utilities
with contextlib.suppress(ImportError):
    from .language_utils import (
        LANGUAGE_KEYWORDS,
        detect_language_from_filename,
        detect_language_from_mkv,
        get_category_for_language,
        is_tv_content,
        normalize_language,
    )
