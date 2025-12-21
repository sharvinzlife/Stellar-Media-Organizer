"""
API routes for the Media Organizer
"""
import asyncio
import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ProcessRequest, ProcessResponse, AnalyzeRequest, AnalyzeResponse,
    MediaFileInfo, HealthResponse, ProgressUpdate, VideoConversionRequest,
    VideoConversionResponse
)
from app.services.media_service import MediaOrganizer, AudioTrackFilter
from app.services.video_converter import VideoConverter
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Global instances
media_organizer = MediaOrganizer()
audio_filter = AudioTrackFilter()
video_converter = VideoConverter()
video_converter.use_host_ffmpeg = settings.use_host_ffmpeg


def translate_path(path_str: str) -> Path:
    """Translate Docker paths to Mac paths when running in standalone mode"""
    import os
    path_str = path_str.strip()
    
    # If running standalone (not in Docker), translate /host-documents/ to Mac path
    if not os.path.exists('/.dockerenv'):  # Not in Docker
        if path_str.startswith('/host-documents/'):
            # Running standalone, translate Docker path to Mac path
            relative_path = path_str.replace('/host-documents/', '')
            mac_path = Path.home() / 'Documents' / relative_path
            logger.info(f"🔄 Translated Docker path to Mac path: {path_str} -> {mac_path}")
            return mac_path
    
    return Path(path_str)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        mkvtoolnix_available=audio_filter.check_mkvtoolnix_available(),
        ffmpeg_available=audio_filter.check_ffmpeg_available()
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_files(request: AnalyzeRequest):
    """Analyze files in a directory without processing"""
    try:
        directory = Path(request.directory_path)
        if not directory.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        files = []
        series_count = 0
        movies_count = 0
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in settings.ALLOWED_EXTENSIONS:
                media_file = media_organizer.analyze_media_file(file_path)
                files.append(MediaFileInfo(**media_file.to_dict()))
                
                if media_file.is_series:
                    series_count += 1
                else:
                    movies_count += 1
        
        return AnalyzeResponse(
            files=files,
            total_files=len(files),
            series_count=series_count,
            movies_count=movies_count
        )
    
    except Exception as e:
        logger.error(f"Error analyzing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process", response_model=ProcessResponse)
async def process_files(request: ProcessRequest):
    """Process media files based on operation type"""
    try:
        if not request.directory_path:
            raise HTTPException(status_code=400, detail="Directory path is required")
        
        directory = translate_path(request.directory_path)
        if not directory.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        
        processed_files = []
        errors = []
        
        # Organize files
        if request.operation in ["organize", "both"]:
            try:
                org_files = media_organizer.organize_files(directory)
                processed_files.extend([MediaFileInfo(**f.to_dict()) for f in org_files])
            except Exception as e:
                errors.append(f"Organization error: {str(e)}")
                logger.error(f"Organization error: {e}")
        
        # Filter audio
        if request.operation in ["filter_audio", "both"]:
            try:
                filtered = audio_filter.batch_filter_directory(
                    directory, 
                    request.target_language.value,
                    request.volume_boost
                )
                logger.info(f"Filtered {len(filtered)} files")
            except Exception as e:
                errors.append(f"Audio filtering error: {str(e)}")
                logger.error(f"Audio filtering error: {e}")
        
        return ProcessResponse(
            success=len(errors) == 0,
            message=f"Processed {len(processed_files)} files" if not errors else "Processing completed with errors",
            processed_files=processed_files,
            errors=errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload files for processing"""
    try:
        uploaded_paths = []
        
        for file in files:
            if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                continue
            
            file_path = settings.UPLOAD_DIR / file.filename
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            uploaded_paths.append(str(file_path))
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Uploaded {len(uploaded_paths)} files",
                "files": uploaded_paths
            }
        )
    
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_progress(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    languages = [
        {"value": "eng", "label": "English", "emoji": "🇬🇧"},
        {"value": "spa", "label": "Spanish", "emoji": "🇪🇸"},
        {"value": "fra", "label": "French", "emoji": "🇫🇷"},
        {"value": "deu", "label": "German", "emoji": "🇩🇪"},
        {"value": "ita", "label": "Italian", "emoji": "🇮🇹"},
        {"value": "por", "label": "Portuguese", "emoji": "🇵🇹"},
        {"value": "jpn", "label": "Japanese", "emoji": "🇯🇵"},
        {"value": "kor", "label": "Korean", "emoji": "🇰🇷"},
        {"value": "chi", "label": "Chinese", "emoji": "🇨🇳"},
        {"value": "rus", "label": "Russian", "emoji": "🇷🇺"},
    ]
    return {"languages": languages}


@router.get("/conversion/presets")
async def get_conversion_presets():
    """Get available video conversion presets"""
    presets = VideoConverter.get_available_presets()
    return {"presets": presets}


@router.post("/convert", response_model=VideoConversionResponse)
async def convert_videos(request: VideoConversionRequest):
    """Convert videos using GPU acceleration"""
    try:
        if not request.directory_path:
            raise HTTPException(status_code=400, detail="Directory path is required")
        
        directory = translate_path(request.directory_path)
        if not directory.exists():
            # Provide helpful error message
            error_msg = f"Source directory not found: {directory}"
            if request.directory_path.startswith('/host-documents/'):
                error_msg += f"\n\n💡 Running in standalone mode. Use Mac paths like:\n/Users/{os.getenv('USER')}/Documents/movie renames"
            raise HTTPException(status_code=404, detail=error_msg)
        
        # Determine output directory
        if request.output_path:
            output_dir = Path(request.output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = directory / "converted"
            output_dir.mkdir(exist_ok=True)
        
        logger.info(f"🎬 Starting video conversion in: {directory}")
        logger.info(f"📝 Using preset: {request.preset}")
        
        # Convert videos
        result = video_converter.batch_convert(
            input_dir=directory,
            output_dir=output_dir,
            preset=request.preset
        )
        
        # Check if no files were found
        if result['total_files'] == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"No video files found in {directory}. Looking for .mkv, .mp4, .avi, .mov files."
            )
        
        if result['success']:
            message = f"✅ Converted {result['successful']} files successfully!"
            if result['compression_ratio'] > 0:
                message += f" Saved {result['compression_ratio']:.1f}% space"
        else:
            message = f"⚠️ Converted {result['successful']}/{result['total_files']} files"
        
        # Format processed files for display
        processed_files = []
        for r in result['results']:
            if r['success']:
                processed_files.append({
                    'original_name': r.get('input_name', ''),
                    'new_name': r.get('output_name', '')
                })
        
        return VideoConversionResponse(
            success=result['success'],
            message=message,
            total_files=result['total_files'],
            successful=result['successful'],
            failed=result['failed'],
            compression_ratio=result['compression_ratio'],
            errors=[r.get('error', '') for r in result['results'] if not r['success']],
            processed_files=processed_files
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    cleaners = media_organizer.cleaners
    return {
        "formats": [
            {"name": cleaner.get_format_name(), "icon": "📁"}
            for cleaner in cleaners
        ]
    }
