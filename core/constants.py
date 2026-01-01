#!/usr/bin/env python3
"""
Centralized Constants for Media Organizer Pro

This module contains all shared constants to avoid duplication across the codebase.
Import from here instead of defining constants in multiple places.
"""

from pathlib import Path

# ============================================================================
# Download Settings
# ============================================================================

def get_download_base_dir() -> Path:
    """Get the base directory for AllDebrid downloads."""
    return Path.home() / "alldebrid_downloads"


# Minimum free disk space (GB) before warning
MIN_DISK_SPACE_GB = 5

# Default max age for download cleanup (hours)
DEFAULT_CLEANUP_AGE_HOURS = 24


# ============================================================================
# Video Extensions
# ============================================================================

VIDEO_EXTENSIONS = frozenset({'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'})


# ============================================================================
# NAS Category Mappings
# ============================================================================

# Lharmony (Synology) - uses lowercase folder names
LHARMONY_CATEGORY_MAP = {
    'movies': 'movies',
    'malayalam movies': 'malayalam movies',
    'malayalam-movies': 'malayalam movies',
    'bollywood movies': 'bollywood movies',
    'bollywood-movies': 'bollywood movies',
    'tv': 'tv',
    'tv-shows': 'tv',
    'malayalam tv shows': 'malayalam tv shows',
    'malayalam-tv-shows': 'malayalam tv shows',
    'hindi tv shows': 'tv',
    'hindi-tv-shows': 'tv',
    'music': 'music',
}

# Streamwave (Unraid) - uses mixed case folder names
STREAMWAVE_CATEGORY_MAP = {
    'movies': 'movies',
    'malayalam movies': 'Malayalam Movies',
    'malayalam-movies': 'Malayalam Movies',
    'bollywood movies': 'Bollywood Movies',
    'bollywood-movies': 'Bollywood Movies',
    'tv': 'tv-shows',
    'tv-shows': 'tv-shows',
    'malayalam tv shows': 'malayalam-tv-shows',
    'malayalam-tv-shows': 'malayalam-tv-shows',
    'hindi tv shows': 'tv-shows',
    'hindi-tv-shows': 'tv-shows',
    'music': 'music',
}


def get_nas_category_map(nas_name: str) -> dict[str, str]:
    """
    Get the category mapping for a specific NAS.
    
    Args:
        nas_name: NAS name (case-insensitive)
    
    Returns:
        Category mapping dictionary
    """
    nas_lower = nas_name.lower()
    if 'lharmony' in nas_lower:
        return LHARMONY_CATEGORY_MAP
    elif 'streamwave' in nas_lower:
        return STREAMWAVE_CATEGORY_MAP
    else:
        # Default to Lharmony style
        return LHARMONY_CATEGORY_MAP


# ============================================================================
# Plex Library Mappings
# ============================================================================

# Maps NAS folder names to Plex library names
PLEX_LIBRARY_MAP = {
    'movies': 'Movies',
    'malayalam movies': 'Malayalam Movies',
    'malayalam-movies': 'Malayalam Movies',
    'bollywood movies': 'Bollywood Movies',
    'bollywood-movies': 'Bollywood Movies',
    'tv': 'TV Shows',
    'tv-shows': 'TV Shows',
    'malayalam tv shows': 'Malayalam TV Shows',
    'malayalam-tv-shows': 'Malayalam TV Shows',
    'hindi tv shows': 'TV Shows',
    'hindi-tv-shows': 'TV Shows',
    'music': 'Music',
}


def get_plex_library_name(category: str) -> str:
    """
    Get the Plex library name for a category.
    
    Args:
        category: NAS category name
    
    Returns:
        Plex library name
    """
    return PLEX_LIBRARY_MAP.get(category.lower(), category)


# ============================================================================
# UI Display Labels
# ============================================================================

CATEGORY_DISPLAY_LABELS = {
    'movies': 'Movies',
    'malayalam movies': 'Malayalam Movies',
    'malayalam-movies': 'Malayalam Movies',
    'bollywood movies': 'Bollywood Movies',
    'bollywood-movies': 'Bollywood Movies',
    'tv': 'TV Shows',
    'tv-shows': 'TV Shows',
    'malayalam tv shows': 'Malayalam TV Shows',
    'malayalam-tv-shows': 'Malayalam TV Shows',
    'hindi tv shows': 'Hindi TV Shows',
    'hindi-tv-shows': 'Hindi TV Shows',
    'music': 'Music',
}


# ============================================================================
# Supported Languages
# ============================================================================

SUPPORTED_LANGUAGES = [
    {"value": "malayalam", "label": "Malayalam", "emoji": "🇮🇳"},
    {"value": "tamil", "label": "Tamil", "emoji": "🇮🇳"},
    {"value": "telugu", "label": "Telugu", "emoji": "🇮🇳"},
    {"value": "hindi", "label": "Hindi", "emoji": "🇮🇳"},
    {"value": "english", "label": "English", "emoji": "🇬🇧"},
    {"value": "kannada", "label": "Kannada", "emoji": "🇮🇳"},
    {"value": "bengali", "label": "Bengali", "emoji": "🇮🇳"},
    {"value": "marathi", "label": "Marathi", "emoji": "🇮🇳"},
    {"value": "gujarati", "label": "Gujarati", "emoji": "🇮🇳"},
    {"value": "punjabi", "label": "Punjabi", "emoji": "🇮🇳"},
    {"value": "odia", "label": "Odia", "emoji": "🇮🇳"},
    {"value": "spanish", "label": "Spanish", "emoji": "🇪🇸"},
    {"value": "french", "label": "French", "emoji": "🇫🇷"},
    {"value": "german", "label": "German", "emoji": "🇩🇪"},
    {"value": "italian", "label": "Italian", "emoji": "🇮🇹"},
    {"value": "portuguese", "label": "Portuguese", "emoji": "🇵🇹"},
    {"value": "russian", "label": "Russian", "emoji": "🇷🇺"},
    {"value": "japanese", "label": "Japanese", "emoji": "🇯🇵"},
    {"value": "korean", "label": "Korean", "emoji": "🇰🇷"},
    {"value": "chinese", "label": "Chinese", "emoji": "🇨🇳"},
    {"value": "arabic", "label": "Arabic", "emoji": "🇸🇦"},
    {"value": "thai", "label": "Thai", "emoji": "🇹🇭"},
    {"value": "vietnamese", "label": "Vietnamese", "emoji": "🇻🇳"},
    {"value": "indonesian", "label": "Indonesian", "emoji": "🇮🇩"},
    {"value": "malay", "label": "Malay", "emoji": "🇲🇾"},
    {"value": "turkish", "label": "Turkish", "emoji": "🇹🇷"},
    {"value": "polish", "label": "Polish", "emoji": "🇵🇱"},
    {"value": "dutch", "label": "Dutch", "emoji": "🇳🇱"},
    {"value": "swedish", "label": "Swedish", "emoji": "🇸🇪"},
    {"value": "norwegian", "label": "Norwegian", "emoji": "🇳🇴"},
    {"value": "danish", "label": "Danish", "emoji": "🇩🇰"},
    {"value": "finnish", "label": "Finnish", "emoji": "🇫🇮"},
    {"value": "greek", "label": "Greek", "emoji": "🇬🇷"},
    {"value": "hebrew", "label": "Hebrew", "emoji": "🇮🇱"},
    {"value": "czech", "label": "Czech", "emoji": "🇨🇿"},
    {"value": "hungarian", "label": "Hungarian", "emoji": "🇭🇺"},
    {"value": "romanian", "label": "Romanian", "emoji": "🇷🇴"},
    {"value": "ukrainian", "label": "Ukrainian", "emoji": "🇺🇦"},
]
