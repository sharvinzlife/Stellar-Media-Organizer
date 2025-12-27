"""
Configuration settings for the Media Organizer Web App
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # App Info
    app_name: str = "🎬 Media Organizer Pro"
    app_version: str = "1.0.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    
    # Paths - use relative paths for local dev, absolute for Docker
    upload_dir: Path = Path(__file__).parent.parent.parent / "uploads"
    temp_dir: Path = Path(__file__).parent.parent.parent / "temp"
    output_dir: Path = Path(__file__).parent.parent.parent / "output"
    
    # Video conversion settings
    use_host_ffmpeg: bool = True  # Use host machine's ffmpeg for GPU acceleration
    
    # API Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Upload Settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024 * 1024  # 10GB
    ALLOWED_EXTENSIONS: List[str] = [".mkv", ".mp4", ".avi"]
    
    # Processing Settings
    TEMP_DIR: Path = Path("temp")
    OUTPUT_DIR: Path = Path("output")
    
    # NAS Settings - Lharmony (Synology)
    lharmony_host: Optional[str] = Field(default=None, alias="LHARMONY_HOST")
    lharmony_username: Optional[str] = Field(default=None, alias="LHARMONY_USERNAME")
    lharmony_password: Optional[str] = Field(default=None, alias="LHARMONY_PASSWORD")
    lharmony_share: str = Field(default="data", alias="LHARMONY_SHARE")
    lharmony_media_path: str = Field(default="/media", alias="LHARMONY_MEDIA_PATH")
    
    # NAS Settings - Streamwave (Unraid)
    streamwave_host: Optional[str] = Field(default=None, alias="STREAMWAVE_HOST")
    streamwave_username: Optional[str] = Field(default=None, alias="STREAMWAVE_USERNAME")
    streamwave_password: Optional[str] = Field(default=None, alias="STREAMWAVE_PASSWORD")
    streamwave_share: str = Field(default="Data-Streamwave", alias="STREAMWAVE_SHARE")
    streamwave_media_path: str = Field(default="/media", alias="STREAMWAVE_MEDIA_PATH")
    
    # AllDebrid API Key
    alldebrid_api_key: Optional[str] = Field(default=None, alias="ALLDEBRID_API_KEY")
    
    class Config:
        env_file = ["../../config.env", ".env"]
        case_sensitive = False
        populate_by_name = True
        extra = "ignore"


settings = Settings()

# Create required directories
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)


# Create required directories
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
