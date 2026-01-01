"""
Pydantic models for API request/response schemas
"""
from enum import Enum

from pydantic import BaseModel, Field


class LanguageEnum(str, Enum):
    """Supported audio languages"""
    MALAYALAM = "malayalam"
    TAMIL = "tamil"
    TELUGU = "telugu"
    HINDI = "hindi"
    ENGLISH = "english"
    KANNADA = "kannada"
    BENGALI = "bengali"


class OperationType(str, Enum):
    """Types of operations"""
    ORGANIZE = "organize"
    FILTER_AUDIO = "filter_audio"
    BOTH = "both"


class LanguageInfo(BaseModel):
    """Language information"""
    value: str
    label: str
    emoji: str


class MediaFileInfo(BaseModel):
    """Media file information"""
    path: str
    original_name: str
    cleaned_name: str | None = None
    format_detected: str | None = None
    is_series: bool = False
    series_name: str | None = None
    season: int | None = None
    episode: int | None = None
    year: int | None = None
    audio_tracks: list[dict] | None = None
    video_tracks: list[dict] | None = None
    subtitle_tracks: list[dict] | None = None


class ProcessRequest(BaseModel):
    """Request to process media files"""
    operation: OperationType
    directory_path: str | None = None
    target_language: LanguageEnum = LanguageEnum.MALAYALAM
    volume_boost: float = Field(default=1.0, ge=0.5, le=3.0)


class ProcessResponse(BaseModel):
    """Response after processing"""
    success: bool
    message: str
    processed_files: list[MediaFileInfo]
    errors: list[str] = []


class AnalyzeRequest(BaseModel):
    """Request to analyze files"""
    directory_path: str


class AnalyzeResponse(BaseModel):
    """Response with file analysis"""
    files: list[MediaFileInfo]
    total_files: int
    series_count: int
    movies_count: int


class ProgressUpdate(BaseModel):
    """Progress update for WebSocket"""
    operation: str
    current: int
    total: int
    current_file: str
    status: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    app_name: str
    version: str
    mkvtoolnix_available: bool
    ffmpeg_available: bool


class VideoConversionRequest(BaseModel):
    """Request model for video conversion"""
    directory_path: str
    output_path: str | None = None
    preset: str = "hevc_best"
    keep_audio: bool = True
    keep_subtitles: bool = True


class ProcessedFileInfo(BaseModel):
    """Processed file information"""
    original_name: str
    new_name: str


class VideoConversionResponse(BaseModel):
    """Response model for video conversion"""
    success: bool
    message: str
    total_files: int | None = None
    successful: int | None = None
    failed: int | None = None
    compression_ratio: float | None = None
    errors: list[str] = []
    processed_files: list[ProcessedFileInfo] = []
