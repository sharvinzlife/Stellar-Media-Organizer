"""
Pydantic models for API request/response schemas
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


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
    cleaned_name: Optional[str] = None
    format_detected: Optional[str] = None
    is_series: bool = False
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None
    audio_tracks: Optional[List[Dict]] = None
    video_tracks: Optional[List[Dict]] = None
    subtitle_tracks: Optional[List[Dict]] = None


class ProcessRequest(BaseModel):
    """Request to process media files"""
    operation: OperationType
    directory_path: Optional[str] = None
    target_language: LanguageEnum = LanguageEnum.MALAYALAM
    volume_boost: float = Field(default=1.0, ge=0.5, le=3.0)


class ProcessResponse(BaseModel):
    """Response after processing"""
    success: bool
    message: str
    processed_files: List[MediaFileInfo]
    errors: List[str] = []


class AnalyzeRequest(BaseModel):
    """Request to analyze files"""
    directory_path: str


class AnalyzeResponse(BaseModel):
    """Response with file analysis"""
    files: List[MediaFileInfo]
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
    output_path: Optional[str] = None
    preset: str = 'hevc_best'
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
    total_files: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    compression_ratio: Optional[float] = None
    errors: List[str] = []
    processed_files: List[ProcessedFileInfo] = []
