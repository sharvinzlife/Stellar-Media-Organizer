#!/usr/bin/env python3
"""
Configuration Management for Media Organizer Pro
Uses pydantic-settings for type-safe configuration with environment variable support
"""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # ========== Application Info ==========
    app_name: str = Field(default="Media Organizer Pro", description="Application name")
    app_version: str = Field(default="6.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")

    # ========== Paths ==========
    media_path: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / "Processed",
        description="Default media processing directory"
    )
    upload_dir: Path = Field(
        default=Path("uploads"),
        description="Directory for uploaded files"
    )
    temp_dir: Path = Field(
        default=Path("temp"),
        description="Temporary directory for processing"
    )
    output_dir: Path = Field(
        default=Path("output"),
        description="Output directory for converted files"
    )

    # ========== API Settings ==========
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost",
            "http://localhost:80",
            "http://localhost:3000",
            "http://localhost:5173"
        ],
        description="Allowed CORS origins"
    )

    # ========== GPU/Conversion Settings ==========
    gpu_service_url: str = Field(
        default="http://localhost:8888",
        description="GPU conversion service URL"
    )
    gpu_service_enabled: bool = Field(
        default=True,
        description="Enable GPU conversion service"
    )
    use_host_ffmpeg: bool = Field(
        default=True,
        description="Use host machine's ffmpeg (for GPU acceleration)"
    )
    default_conversion_preset: str = Field(
        default="hevc_best",
        description="Default video conversion preset"
    )

    # ========== IMDB/OMDb Settings ==========
    omdb_api_key: str = Field(
        default="8800e3b1",
        description="OMDb API key for IMDB lookups (PRIMARY)"
    )
    use_omdb_primary: bool = Field(
        default=True,
        description="Use OMDb as primary metadata source"
    )
    imdb_cache_enabled: bool = Field(
        default=True,
        description="Enable IMDB lookup caching"
    )

    # ========== TMDB Settings ==========
    tmdb_access_token: str | None = Field(
        default=None,
        description="TMDB Read Access Token (Bearer auth, for episode titles)"
    )
    tmdb_api_key: str | None = Field(
        default=None,
        description="TMDB API key (v3 auth)"
    )
    tmdb_enabled: bool = Field(
        default=True,
        description="Enable TMDB lookups for metadata"
    )

    # ========== SMB/NAS Settings ==========
    # Lharmony (Synology)
    lharmony_host: str | None = Field(default=None, description="Lharmony NAS host")
    lharmony_username: str | None = Field(default=None, description="Lharmony username")
    lharmony_password: str | None = Field(default=None, description="Lharmony password")
    lharmony_share: str = Field(default="data", description="Lharmony share name")
    lharmony_media_path: str = Field(default="/media", description="Lharmony media path")

    # Streamwave (Unraid)
    streamwave_host: str | None = Field(default=None, description="Streamwave NAS host")
    streamwave_username: str | None = Field(default=None, description="Streamwave username")
    streamwave_password: str | None = Field(default=None, description="Streamwave password")
    streamwave_share: str = Field(default="Data-Streamwave", description="Streamwave share name")
    streamwave_media_path: str = Field(default="/media", description="Streamwave media path")

    # ========== Plex Media Server Settings ==========
    plex_enabled: bool = Field(
        default=False,
        description="Enable Plex integration"
    )
    plex_server_url: str | None = Field(
        default=None,
        description="Plex server URL (e.g., http://192.168.1.100:32400)"
    )
    plex_token: str | None = Field(
        default=None,
        description="Plex authentication token"
    )
    plex_external_url: str | None = Field(
        default=None,
        description="External Plex URL (e.g., Cloudflare tunnel)"
    )
    plex_auto_scan: bool = Field(
        default=True,
        description="Automatically scan library after file transfer"
    )
    plex_auto_match: bool = Field(
        default=True,
        description="Automatically match metadata with IMDB after scan"
    )

    # Plex Library Mappings (NAS folder -> Plex library name)
    # These map the NAS destination folders to Plex library names for auto-scanning
    plex_library_map: dict[str, str] = Field(
        default={
            'movies': 'Movies',
            'malayalam movies': 'Malayalam Movies',
            'bollywood movies': 'Bollywood Movies',
            'tv': 'TV Shows',
            'tv-shows': 'TV Shows',
            'malayalam tv shows': 'Malayalam TV Shows',
            'malayalam-tv-shows': 'Malayalam TV Shows',
        },
        description="Mapping of NAS folders to Plex library names"
    )

    # ========== Tautulli Settings ==========
    tautulli_enabled: bool = Field(
        default=False,
        description="Enable Tautulli integration"
    )
    tautulli_url: str | None = Field(
        default=None,
        description="Tautulli server URL (e.g., http://192.168.1.100:8181)"
    )
    tautulli_api_key: str | None = Field(
        default=None,
        description="Tautulli API key"
    )

    # ========== AllDebrid Settings ==========
    alldebrid_api_key: str | None = Field(
        default=None,
        description="AllDebrid API key for downloading"
    )

    # ========== Processing Settings ==========
    max_upload_size: int = Field(
        default=10 * 1024 * 1024 * 1024,  # 10GB
        description="Maximum upload file size in bytes"
    )
    allowed_extensions: list[str] = Field(
        default=[".mkv", ".mp4", ".avi", ".mov"],
        description="Allowed video file extensions"
    )
    default_language: str = Field(
        default="malayalam",
        description="Default audio track language"
    )
    default_volume_boost: float = Field(
        default=1.0,
        ge=0.5,
        le=3.0,
        description="Default volume boost multiplier"
    )

    # ========== External Tools ==========
    mkvmerge_path: str | None = Field(
        default=None,
        description="Path to mkvmerge binary (auto-detected if None)"
    )
    ffmpeg_path: str | None = Field(
        default=None,
        description="Path to ffmpeg binary (auto-detected if None)"
    )

    # ========== Logging Settings ==========
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file: Path | None = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="MEDIA_ORG_",  # Environment variables: MEDIA_ORG_API_PORT, etc.
        extra="ignore"  # Ignore extra fields in .env
    )

    @field_validator("media_path", "upload_dir", "temp_dir", "output_dir", mode="before")
    @classmethod
    def expand_path(cls, v):
        """Expand user home directory and resolve paths"""
        if isinstance(v, str):
            v = Path(v)
        if isinstance(v, Path):
            return v.expanduser().resolve()
        return v

    def create_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_path in [self.upload_dir, self.temp_dir, self.output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return self.model_dump()


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.create_directories()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment/file"""
    global _settings
    _settings = Settings()
    _settings.create_directories()
    return _settings


# Convenience exports
settings = get_settings()


if __name__ == "__main__":
    # Test configuration
    import json

    print("Media Organizer Pro - Configuration")
    print("=" * 50)
    config = get_settings()

    # Pretty print configuration
    config_dict = config.to_dict()
    print(json.dumps(config_dict, indent=2, default=str))

    print("\n" + "=" * 50)
    print("✅ Configuration loaded successfully!")
    print(f"📁 Media path: {config.media_path}")
    print(f"🎮 GPU service: {config.gpu_service_url}")
    print(f"🔧 API: {config.api_host}:{config.api_port}{config.api_prefix}")

