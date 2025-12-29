"""
API routes for the Media Organizer
"""
import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


# ============================================================================
# NAS Endpoints
# ============================================================================

def get_nas_configs():
    """Get NAS configurations from settings"""
    nas_configs = []
    
    # Lharmony (Synology)
    if settings.lharmony_host:
        nas_configs.append({
            "name": "Lharmony",
            "host": settings.lharmony_host,
            "username": settings.lharmony_username or "",
            "share": settings.lharmony_share,
            "media_path": settings.lharmony_media_path,
            "mount_point": f"/mnt/{settings.lharmony_share}",
            "mounted": False,  # Will be updated by status check
            "type": "synology",
            "categories": ["movies", "malayalam movies", "bollywood movies", "tv", "malayalam tv shows", "music"]
        })
    
    # Streamwave (Unraid)
    if settings.streamwave_host:
        nas_configs.append({
            "name": "Streamwave",
            "host": settings.streamwave_host,
            "username": settings.streamwave_username or "",
            "share": settings.streamwave_share,
            "media_path": settings.streamwave_media_path,
            "mount_point": f"/mnt/{settings.streamwave_share}",
            "mounted": False,  # Will be updated by status check
            "type": "unraid",
            "categories": ["tv-shows", "malayalam-tv-shows", "movies", "music"]
        })
    
    return nas_configs


class NASTestRequest(BaseModel):
    nas_name: str


@router.get("/nas/list")
async def list_nas_locations():
    """List all configured NAS locations"""
    nas_configs = get_nas_configs()
    return {"nas_locations": nas_configs}


@router.get("/nas/{nas_name}/status")
async def get_nas_status(nas_name: str):
    """Get status of a specific NAS"""
    nas_configs = get_nas_configs()
    nas_config = next((n for n in nas_configs if n["name"].lower() == nas_name.lower()), None)
    
    if not nas_config:
        raise HTTPException(status_code=404, detail=f"NAS '{nas_name}' not found")
    
    # Check if NAS is reachable via ping
    is_connected = False
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", nas_config["host"]],
            capture_output=True,
            timeout=5
        )
        is_connected = result.returncode == 0
    except Exception as e:
        logger.warning(f"Ping failed for {nas_name}: {e}")
    
    # Update mounted status based on ping
    nas_config["mounted"] = is_connected
    nas_config["connected"] = is_connected
    nas_config["status"] = "online" if is_connected else "offline"
    
    return {"nas": nas_config}


@router.post("/nas/test")
async def test_nas_connection(request: NASTestRequest):
    """Test connection to a NAS"""
    nas_configs = get_nas_configs()
    nas_config = next((n for n in nas_configs if n["name"].lower() == request.nas_name.lower()), None)
    
    if not nas_config:
        raise HTTPException(status_code=404, detail=f"NAS '{request.nas_name}' not found")
    
    # Test connection via ping
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", nas_config["host"]],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"success": True, "message": f"✅ Successfully connected to {request.nas_name}"}
        else:
            return {"success": False, "message": f"❌ Cannot reach {request.nas_name} at {nas_config['host']}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"❌ Connection to {request.nas_name} timed out"}
    except Exception as e:
        return {"success": False, "message": f"❌ Error testing connection: {str(e)}"}


# ============================================================================
# AllDebrid Endpoints
# ============================================================================

@router.get("/alldebrid/status")
async def get_alldebrid_status():
    """Check if AllDebrid API key is configured"""
    # Also check if aria2c is available
    aria2c_available = False
    try:
        result = subprocess.run(['aria2c', '--version'], capture_output=True, timeout=5)
        aria2c_available = result.returncode == 0
    except:
        pass
    
    return {
        "configured": bool(settings.alldebrid_api_key),
        "aria2c_available": aria2c_available
    }


class NASDestination(BaseModel):
    nas_name: str
    category: str


class AllDebridDownloadRequest(BaseModel):
    links: List[str]
    language: str = "auto"
    auto_detect_language: bool = True
    download_only: bool = False
    output_path: Optional[str] = None
    nas_destination: Optional[NASDestination] = None


# In-memory job tracking for AllDebrid downloads
alldebrid_jobs: dict = {}
job_counter = [0]

# Job persistence file
JOBS_FILE = Path(__file__).parent.parent.parent.parent.parent / '.run' / 'job_history.json'


def load_jobs_from_file():
    """Load job history from file on startup."""
    global alldebrid_jobs, job_counter
    try:
        if JOBS_FILE.exists():
            import json
            with open(JOBS_FILE, 'r') as f:
                data = json.load(f)
                alldebrid_jobs = {int(k): v for k, v in data.get('jobs', {}).items()}
                job_counter[0] = data.get('counter', 0)
                logger.info(f"📂 Loaded {len(alldebrid_jobs)} jobs from history")
    except Exception as e:
        logger.warning(f"Could not load job history: {e}")


def save_jobs_to_file():
    """Save job history to file."""
    try:
        import json
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(JOBS_FILE, 'w') as f:
            json.dump({
                'jobs': alldebrid_jobs,
                'counter': job_counter[0]
            }, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not save job history: {e}")


# Load jobs on module import
load_jobs_from_file()


def run_alldebrid_download_task(job_id: int, request: AllDebridDownloadRequest):
    """Background task to run AllDebrid download."""
    import sys
    import time
    import shutil
    from pathlib import Path as PathLib
    
    # Add parent directory to path to import alldebrid_downloader
    parent_dir = PathLib(__file__).parent.parent.parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    job = alldebrid_jobs[job_id]
    job['status'] = 'running'
    job['started_at'] = datetime.now().isoformat()
    start_time = time.time()
    
    def add_log(message: str, level: str = 'info'):
        job['logs'].append({
            'message': message, 
            'level': level,
            'timestamp': datetime.now().isoformat()
        })
    
    add_log(f'🚀 Starting download of {len(request.links)} links...', 'info')
    
    try:
        from alldebrid_downloader import AllDebridDownloader
        
        # Always download to temp first
        output_path = f"/tmp/alldebrid_downloads/{job_id}"
        
        if request.nas_destination:
            add_log(f'📁 NAS destination: {request.nas_destination.nas_name} → {request.nas_destination.category}', 'info')
        
        job['output_path'] = output_path
        job['current_status'] = 'Initializing...'
        PathLib(output_path).mkdir(parents=True, exist_ok=True)
        add_log(f'📂 Temp directory: {output_path}', 'info')
        
        def progress_callback(message: str, level: str = "info"):
            add_log(message, level)
            # Parse progress
            import re
            percent_match = re.search(r'(\d+)%', message)
            if percent_match:
                job['progress'] = min(int(percent_match.group(1)), 90)  # Cap at 90% until NAS transfer
            
            # Update current status based on message content
            if 'Downloading' in message or 'downloading' in message:
                job['current_status'] = 'Downloading...'
                # Extract filename if present
                if ':' in message:
                    job['current_file'] = message.split(':')[-1].strip()[:60]
            elif 'Renaming' in message or 'TMDB' in message or 'metadata' in message.lower():
                job['current_status'] = 'Renaming with metadata...'
            elif 'Filtering' in message or 'audio' in message.lower():
                job['current_status'] = 'Filtering audio tracks...'
            elif 'Uploading' in message or 'Transfer' in message:
                job['current_status'] = 'Uploading to NAS...'
            elif '✅' in message:
                job['processed_files'] = job.get('processed_files', 0) + 1
        
        downloader = AllDebridDownloader(
            settings.alldebrid_api_key,
            download_dir=output_path,
            tmdb_token=settings.tmdb_access_token,
            tmdb_api_key=settings.tmdb_api_key,
            omdb_api_key=settings.omdb_api_key,
            progress_callback=progress_callback
        )
        
        job['current_status'] = 'Connecting to AllDebrid...'
        
        # Log metadata source status
        if settings.omdb_api_key:
            add_log('🎬 IMDB (primary) + TMDB (fallback) enabled for Plex/Jellyfin naming', 'info')
        elif settings.tmdb_access_token or settings.tmdb_api_key:
            add_log('🎬 TMDB enabled - files will be renamed for Plex/Jellyfin', 'info')
        else:
            add_log('⚠️ No metadata API configured - using original filenames', 'warning')
        
        language = request.language if not request.auto_detect_language else None
        lang_label = 'Auto-detect' if request.auto_detect_language else request.language
        add_log(f'🎬 Language mode: {lang_label}', 'info')
        
        if request.download_only:
            add_log('📥 Download-only mode (no organizing)', 'info')
            downloaded = downloader.download_links(request.links)
            job['summary']['downloaded'] = len(downloaded)
            job['summary']['total_files'] = len(downloaded)
            add_log(f'✅ Downloaded {len(downloaded)} files', 'success')
        else:
            add_log('🔄 Download + Smart Organize mode (TMDB)', 'info')
            # Use smart TMDB-based organize for clean Plex/Jellyfin naming
            results = downloader.download_and_organize_smart(
                request.links, 
                output_path, 
                language=language or 'malayalam',
                filter_audio=True
            )
            downloaded_count = len(results.get('downloaded', []))
            renamed_count = len(results.get('renamed', []))
            filtered_count = len(results.get('filtered', []))
            
            # Update summary
            job['summary']['downloaded'] = downloaded_count
            job['summary']['renamed'] = renamed_count
            job['summary']['filtered'] = filtered_count
            job['summary']['total_files'] = downloaded_count
            
            # Store the filter language for category detection
            job['filter_language'] = language or 'malayalam'
            
            # Track individual files with sizes
            from pathlib import Path as P
            total_size_after = 0
            
            for f in results.get('renamed', []):
                try:
                    # Handle both string paths and Path objects
                    if isinstance(f, str):
                        file_path = P(f)
                        file_name = f.split('/')[-1]
                    else:
                        file_path = f
                        file_name = f.name if hasattr(f, 'name') else str(f).split('/')[-1]
                    
                    # Get file size safely
                    try:
                        if file_path.exists():
                            size_mb = file_path.stat().st_size / (1024 * 1024)
                        else:
                            size_mb = 0
                    except Exception:
                        size_mb = 0
                    
                    total_size_after += size_mb
                    
                    # Check if this file was filtered
                    was_filtered = str(f) in [str(x) for x in results.get('filtered', [])]
                    
                    job['summary']['files'].append({
                        'name': file_name,
                        'size_mb': round(size_mb, 1),
                        'filtered': was_filtered,
                        'status': 'renamed'
                    })
                except Exception as e:
                    add_log(f'⚠️ Error tracking file: {str(e)}', 'warning')
            
            # Calculate space saved if filtering was done
            job['summary']['total_size_mb'] = round(total_size_after, 1)
            
            add_log(f"✅ Download complete! Downloaded: {downloaded_count}, Renamed: {renamed_count}", 'success')
            if filtered_count > 0:
                add_log(f"🎵 Audio filtered: {filtered_count} files (kept {language})", 'success')
        
        # Transfer to NAS if destination specified
        if request.nas_destination:
            add_log(f'📤 Transferring to NAS: {request.nas_destination.nas_name}...', 'info')
            job['progress'] = 92
            job['current_status'] = 'Transferring to NAS...'
            
            try:
                nas_result = transfer_to_nas(
                    output_path,
                    request.nas_destination.nas_name,
                    request.nas_destination.category,
                    add_log,
                    job_id  # Pass job_id for UI updates
                )
                if nas_result:
                    # Get the detected category from job if available
                    detected_cat = job.get('detected_category', request.nas_destination.category)
                    add_log(f'✅ Successfully transferred to {request.nas_destination.nas_name}/{detected_cat}', 'success')
                    job['progress'] = 98
                    job['current_status'] = 'Cleaning up...'
                    
                    # Clean up temp files
                    add_log('🧹 Cleaning up temp files...', 'info')
                    shutil.rmtree(output_path, ignore_errors=True)
                    add_log('✅ Temp files cleaned', 'success')
                    
                    # Trigger Plex library scan if enabled
                    if settings.plex_enabled and settings.plex_auto_scan:
                        job['current_status'] = 'Scanning Plex library...'
                        try:
                            plex_scan_result = trigger_plex_scan(detected_cat, add_log)
                            if plex_scan_result:
                                add_log(f'📺 Plex library scan triggered for {detected_cat}', 'success')
                        except Exception as plex_error:
                            add_log(f'⚠️ Plex scan failed: {str(plex_error)}', 'warning')
                else:
                    add_log(f'⚠️ NAS transfer failed, files remain in {output_path}', 'warning')
            except Exception as nas_error:
                add_log(f'⚠️ NAS transfer error: {str(nas_error)}', 'warning')
                add_log(f'📁 Files remain in: {output_path}', 'info')
        
        job['status'] = 'completed'
        job['progress'] = 100
        job['current_status'] = 'Completed'
        job['completed_at'] = datetime.now().isoformat()
        job['duration'] = time.time() - start_time
        add_log(f'🎉 Job completed in {job["duration"]:.1f}s', 'success')
        save_jobs_to_file()  # Persist job history
        
    except ImportError as e:
        add_log(f'❌ Import error: {str(e)} - alldebrid_downloader module not found', 'error')
        job['status'] = 'failed'
        job['error'] = str(e)
        job['completed_at'] = datetime.now().isoformat()
        job['duration'] = time.time() - start_time
        logger.error(f"AllDebrid import error: {e}")
        save_jobs_to_file()  # Persist job history
    except Exception as e:
        add_log(f'❌ Error: {str(e)}', 'error')
        job['status'] = 'failed'
        job['error'] = str(e)
        job['completed_at'] = datetime.now().isoformat()
        job['duration'] = time.time() - start_time
        logger.error(f"AllDebrid download error: {e}")
        save_jobs_to_file()  # Persist job history


def transfer_to_nas(source_dir: str, nas_name: str, category: str, log_func, job_id: int = None) -> bool:
    """Transfer files to NAS using smbclient with smart category detection."""
    from pathlib import Path as PathLib
    import shutil
    import os
    import re
    import time
    
    # Get NAS config
    nas_name_lower = nas_name.lower()
    
    if 'lharmony' in nas_name_lower:
        host = settings.lharmony_host
        username = settings.lharmony_username
        password = settings.lharmony_password
        share = settings.lharmony_share
        media_path = settings.lharmony_media_path or 'media'
        # Lharmony folder names (lowercase)
        category_map = {
            'malayalam movies': 'malayalam movies',
            'movies': 'movies',
            'bollywood movies': 'bollywood movies',
            'tv-shows': 'tv',
            'tv': 'tv',
            'malayalam-tv-shows': 'malayalam tv shows',
            'malayalam tv shows': 'malayalam tv shows',
            'hindi-tv-shows': 'tv',
            'music': 'music',
        }
    elif 'streamwave' in nas_name_lower:
        host = settings.streamwave_host
        username = settings.streamwave_username
        password = settings.streamwave_password
        share = settings.streamwave_share
        media_path = settings.streamwave_media_path or 'Media'
        # Streamwave folder names
        category_map = {
            'malayalam movies': 'Malayalam Movies',
            'movies': 'movies',
            'bollywood movies': 'Bollywood Movies',
            'tv-shows': 'tv-shows',
            'tv': 'tv-shows',
            'malayalam-tv-shows': 'malayalam-tv-shows',
            'malayalam tv shows': 'malayalam-tv-shows',
            'hindi-tv-shows': 'tv-shows',
            'music': 'music',
        }
    else:
        log_func(f'❌ Unknown NAS: {nas_name}', 'error')
        return False
    
    if not host or not username:
        log_func(f'❌ NAS {nas_name} not configured properly', 'error')
        return False
    
    # Find all media files
    source_path = PathLib(source_dir)
    media_files = []
    for ext in ['*.mkv', '*.mp4', '*.avi', '*.mov']:
        media_files.extend(source_path.rglob(ext))
    
    if not media_files:
        log_func('⚠️ No media files found to transfer', 'warning')
        return False
    
    log_func(f'📦 Found {len(media_files)} file(s) to transfer', 'info')
    
    success_count = 0
    for media_file in media_files:
        file_name = media_file.name
        
        # Smart detect: Movie vs TV Show (pass job_id for UI update)
        detected_category = detect_content_type(file_name, category, log_func, job_id)
        
        # Get folder name from NAS-specific category map
        folder_name = category_map.get(detected_category.lower(), detected_category)
        remote_path = f"{media_path.strip('/')}/{folder_name}"
        
        # Determine folder structure based on content type
        is_tv = 'tv' in detected_category.lower()
        
        if is_tv:
            # TV shows: Series Name/Season XX/filename.mkv
            # Extract series name and season from filename
            import re
            season_match = re.search(r'[Ss](\d{1,2})[Ee]\d{1,2}', file_name)
            if season_match:
                season_num = int(season_match.group(1))
                # Get series name (everything before SxxExx)
                series_name = re.split(r'\s*-?\s*[Ss]\d{1,2}[Ee]\d{1,2}', file_name)[0].strip()
                series_name = series_name.rstrip(' -')
                target_folder = f"{series_name}/Season {season_num:02d}"
            else:
                # Fallback: use filename stem as folder
                target_folder = media_file.stem
        else:
            # Movies: Movie Name (Year)/filename.mkv
            target_folder = media_file.stem
        
        log_func(f'📤 Uploading to {folder_name}/{target_folder}: {file_name}...', 'info')
        
        # Use smbclient for transfer - create nested folders
        smb_commands = f'mkdir "{remote_path}/{target_folder}"; cd "{remote_path}/{target_folder}"; put "{media_file}" "{file_name}"'
        
        # For TV shows with season folders, need to create parent first
        if is_tv and '/' in target_folder:
            series_folder = target_folder.split('/')[0]
            smb_commands = f'mkdir "{remote_path}/{series_folder}"; mkdir "{remote_path}/{target_folder}"; cd "{remote_path}/{target_folder}"; put "{media_file}" "{file_name}"'
        
        cmd = [
            'smbclient', f'//{host}/{share}',
            '-U', f'{username}%{password}',
            '-c', smb_commands
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            elapsed = time.time() - start_time
            file_size_mb = media_file.stat().st_size / (1024 * 1024)
            speed = file_size_mb / elapsed if elapsed > 0 else 0
            
            if result.returncode == 0 or 'NT_STATUS_OBJECT_NAME_COLLISION' in result.stderr:
                log_func(f'✅ Uploaded in {elapsed:.1f}s ({speed:.1f} MB/s): {file_name}', 'success')
                success_count += 1
                
                # Update job summary with transfer details
                if job_id and job_id in alldebrid_jobs:
                    alldebrid_jobs[job_id]['summary']['transferred'] += 1
                    # Add file transfer info
                    file_info = {
                        'name': file_name,
                        'destination': f"{nas_name}/{folder_name}/{target_folder}",
                        'size_mb': round(file_size_mb, 1),
                        'speed_mbps': round(speed, 1),
                        'category': detected_category,
                        'status': 'transferred'
                    }
                    # Update existing file entry or add new one
                    found = False
                    for f in alldebrid_jobs[job_id]['summary']['files']:
                        if f.get('renamed', f.get('original', '')) == file_name or f.get('name') == file_name:
                            f.update(file_info)
                            found = True
                            break
                    if not found:
                        alldebrid_jobs[job_id]['summary']['files'].append(file_info)
            else:
                log_func(f'⚠️ Upload issue: {result.stderr[:100]}', 'warning')
                if job_id and job_id in alldebrid_jobs:
                    alldebrid_jobs[job_id]['summary']['failed'] += 1
        except subprocess.TimeoutExpired:
            log_func(f'⏱️ Upload timeout for: {file_name}', 'error')
            if job_id and job_id in alldebrid_jobs:
                alldebrid_jobs[job_id]['summary']['failed'] += 1
        except Exception as e:
            log_func(f'❌ Upload error: {str(e)}', 'error')
            if job_id and job_id in alldebrid_jobs:
                alldebrid_jobs[job_id]['summary']['failed'] += 1
    
    return success_count > 0


def detect_content_type(filename: str, default_category: str, log_func, job_id: int = None) -> str:
    """
    Smart detect if content is Movie or TV Show based on:
    1. Filename keywords (quick check)
    2. OMDB/TMDB metadata lookup (accurate language detection)
    Returns the appropriate category.
    """
    import re
    import requests
    
    filename_lower = filename.lower()
    
    # TV Show patterns: S01E01, Season 1, Episode, etc.
    tv_patterns = [
        r's\d{1,2}e\d{1,2}',      # S01E01
        r'season\s*\d+',          # Season 1
        r'episode\s*\d+',         # Episode 1
        r'\d{1,2}x\d{1,2}',       # 1x01
        r'e\d{2,3}',              # E01, E001
        r'ep\d{1,3}',             # EP01
    ]
    
    is_tv_show = any(re.search(pattern, filename_lower) for pattern in tv_patterns)
    
    # Check for Malayalam content - from filename keywords
    malayalam_keywords = ['malayalam', ' mal ', '-mal-', '.mal.', 'mlm', 'mal-', '-mal', '+mal+', '[mal]', '(mal)']
    is_malayalam = any(kw in filename_lower for kw in malayalam_keywords)
    
    # Check for Hindi/Bollywood content - from filename keywords
    hindi_keywords = ['hindi', 'bollywood', ' hin ', '-hin-', '.hin.', 'hin-', '-hin', '+hin+', '[hin]', '(hin)']
    is_hindi = any(kw in filename_lower for kw in hindi_keywords)
    
    # Check for Tamil content
    tamil_keywords = ['tamil', ' tam ', '-tam-', '.tam.', '+tam+', '[tam]', '(tam)', 'tamilmv']
    is_tamil = any(kw in filename_lower for kw in tamil_keywords)
    
    # Check for Telugu content
    telugu_keywords = ['telugu', ' tel ', '-tel-', '.tel.', '+tel+', '[tel]', '(tel)']
    is_telugu = any(kw in filename_lower for kw in telugu_keywords)
    
    # If no language detected from filename, lookup from OMDB/TMDB
    if not any([is_malayalam, is_hindi, is_tamil, is_telugu]):
        detected_lang = lookup_language_from_metadata(filename, is_tv_show, log_func)
        if detected_lang:
            if detected_lang == 'malayalam':
                is_malayalam = True
            elif detected_lang == 'hindi':
                is_hindi = True
            elif detected_lang == 'tamil':
                is_tamil = True
            elif detected_lang == 'telugu':
                is_telugu = True
    
    # Determine final category based on DETECTED language
    if is_tv_show:
        if is_malayalam:
            detected = 'malayalam-tv-shows'
        elif is_hindi:
            detected = 'hindi-tv-shows'
        else:
            detected = 'tv-shows'  # English/Other TV Shows
    else:
        # It's a movie
        if is_malayalam:
            detected = 'malayalam movies'
        elif is_hindi:
            detected = 'bollywood movies'
        elif is_tamil:
            detected = 'movies'  # Tamil goes to general movies
        elif is_telugu:
            detected = 'movies'  # Telugu goes to general movies
        else:
            detected = 'movies'  # English/Other movies
    
    # Log the detection result
    if any([is_malayalam, is_hindi, is_tamil, is_telugu]):
        lang_detected = 'Malayalam' if is_malayalam else 'Hindi' if is_hindi else 'Tamil' if is_tamil else 'Telugu'
        log_func(f'🎯 Detected language: {lang_detected}', 'info')
    else:
        log_func(f'🎯 Language: English/General', 'info')
    
    # Log if category changed from UI selection
    if detected.lower().replace('-', ' ').replace('_', ' ') != default_category.lower().replace('-', ' ').replace('_', ' '):
        log_func(f'🔍 Auto-detected category: {default_category} → {detected}', 'info')
    
    # Update job with detected category
    if job_id and job_id in alldebrid_jobs:
        alldebrid_jobs[job_id]['detected_category'] = detected
    
    return detected


def extract_title_and_year(filename: str) -> tuple:
    """Extract movie/show title and year from filename."""
    import re
    
    # Remove file extension
    name = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm)$', '', filename, flags=re.IGNORECASE)
    
    # Remove common tags and quality indicators
    name = re.sub(r'\[.*?\]|\((?!19|20)\d+\)|{.*?}', '', name)  # Remove brackets except year
    name = re.sub(r'(720p|1080p|2160p|4k|uhd|hdr|bluray|brrip|webrip|web-dl|hdtv|dvdrip|x264|x265|hevc|aac|dts|atmos|10bit|remux)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(yts|yify|rarbg|ettv|eztv|sparks|geckos|tigole|qxr)', '', name, flags=re.IGNORECASE)
    
    # Extract year
    year_match = re.search(r'[\.\s\-\(]*((?:19|20)\d{2})[\.\s\-\)]*', name)
    year = year_match.group(1) if year_match else None
    
    # Clean title - remove year and everything after
    if year:
        title = re.split(r'[\.\s\-]*(?:19|20)\d{2}', name)[0]
    else:
        # Remove season/episode info for TV shows
        title = re.split(r'[Ss]\d{1,2}[Ee]\d{1,2}', name)[0]
    
    # Clean up title
    title = re.sub(r'[\.\-_]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title, year


def lookup_language_from_metadata(filename: str, is_tv_show: bool, log_func) -> str:
    """
    Lookup language from OMDB (primary) and TMDB (fallback).
    Returns: 'malayalam', 'hindi', 'tamil', 'telugu', or None for English/other
    """
    import requests
    
    title, year = extract_title_and_year(filename)
    if not title:
        return None
    
    log_func(f'🔍 Looking up metadata for: "{title}" ({year or "unknown year"})', 'info')
    
    # Language mapping
    indian_languages = {
        'malayalam': 'malayalam',
        'hindi': 'hindi', 
        'tamil': 'tamil',
        'telugu': 'telugu',
        'ml': 'malayalam',
        'hi': 'hindi',
        'ta': 'tamil',
        'te': 'telugu',
    }
    
    # Try OMDB first (primary)
    if settings.omdb_api_key:
        try:
            params = {
                'apikey': settings.omdb_api_key,
                't': title,
                'type': 'series' if is_tv_show else 'movie'
            }
            if year:
                params['y'] = year
            
            resp = requests.get('http://www.omdbapi.com/', params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Response') == 'True':
                    language = data.get('Language', '').lower()
                    country = data.get('Country', '').lower()
                    log_func(f'📺 OMDB: {data.get("Title")} - Language: {language}, Country: {country}', 'info')
                    
                    # Check language field
                    for lang_key, lang_val in indian_languages.items():
                        if lang_key in language:
                            log_func(f'✅ OMDB detected: {lang_val.title()}', 'success')
                            return lang_val
                    
                    # Check if it's an Indian movie by country (fallback for Hindi)
                    if 'india' in country and 'english' not in language:
                        # Indian movie not in English - likely Hindi/Bollywood
                        log_func(f'✅ OMDB: Indian production, assuming Hindi', 'info')
                        return 'hindi'
        except Exception as e:
            log_func(f'⚠️ OMDB lookup failed: {str(e)}', 'warning')
    
    # Try TMDB as fallback
    if settings.tmdb_api_key or settings.tmdb_access_token:
        try:
            headers = {}
            if settings.tmdb_access_token:
                headers['Authorization'] = f'Bearer {settings.tmdb_access_token}'
            
            # Search for the movie/show
            search_type = 'tv' if is_tv_show else 'movie'
            search_url = f'https://api.themoviedb.org/3/search/{search_type}'
            params = {
                'query': title,
                'api_key': settings.tmdb_api_key
            }
            if year:
                params['year' if not is_tv_show else 'first_air_date_year'] = year
            
            resp = requests.get(search_url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    result = results[0]
                    original_language = result.get('original_language', '').lower()
                    log_func(f'📺 TMDB: {result.get("title") or result.get("name")} - Language: {original_language}', 'info')
                    
                    # Check language
                    for lang_key, lang_val in indian_languages.items():
                        if lang_key == original_language:
                            log_func(f'✅ TMDB detected: {lang_val.title()}', 'success')
                            return lang_val
        except Exception as e:
            log_func(f'⚠️ TMDB lookup failed: {str(e)}', 'warning')
    
    log_func(f'ℹ️ No Indian language detected, using English/General', 'info')
    return None


# ========== Plex Integration ==========

# Plex library name mapping (NAS folder -> Plex library name)
PLEX_LIBRARY_MAP = {
    'movies': 'Movies',
    'malayalam movies': 'Malayalam Movies',
    'bollywood movies': 'Bollywood Movies',
    'tv': 'TV Shows',
    'tv-shows': 'TV Shows',
    'malayalam tv shows': 'Malayalam TV Shows',
    'malayalam-tv-shows': 'Malayalam TV Shows',
    'hindi-tv-shows': 'TV Shows',
}


def get_plex_client():
    """Get Plex client instance if configured."""
    if not settings.plex_enabled or not settings.plex_server_url or not settings.plex_token:
        return None
    
    try:
        import sys
        from pathlib import Path as P
        # Add parent directory to path to import core modules
        parent_dir = P(__file__).parent.parent.parent.parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        from core.plex_client import PlexClient
        return PlexClient(settings.plex_server_url, settings.plex_token)
    except ImportError as e:
        logger.warning(f"Plex client not available: {e}")
        return None


def get_tautulli_client():
    """Get Tautulli client instance if configured."""
    if not settings.tautulli_enabled or not settings.tautulli_url or not settings.tautulli_api_key:
        return None
    
    try:
        import sys
        from pathlib import Path as P
        parent_dir = P(__file__).parent.parent.parent.parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        from core.tautulli_client import TautulliClient
        return TautulliClient(settings.tautulli_url, settings.tautulli_api_key)
    except ImportError as e:
        logger.warning(f"Tautulli client not available: {e}")
        return None


def trigger_plex_scan(category: str, log_func=None) -> bool:
    """
    Trigger a Plex library scan for the given category.
    
    Args:
        category: The NAS folder category (e.g., 'malayalam movies', 'tv-shows')
        log_func: Optional logging function
    
    Returns:
        True if scan was triggered successfully
    """
    plex = get_plex_client()
    if not plex:
        if log_func:
            log_func('⚠️ Plex not configured, skipping scan', 'warning')
        return False
    
    # Map category to Plex library name
    category_lower = category.lower().replace('_', ' ').replace('-', ' ')
    library_name = PLEX_LIBRARY_MAP.get(category_lower, category)
    
    if log_func:
        log_func(f'📺 Triggering Plex scan for library: {library_name}', 'info')
    
    try:
        # Find the library
        library = plex.get_library_by_name(library_name)
        if library:
            success = plex.scan_library(library.key)
            if success and log_func:
                log_func(f'✅ Plex scan started for {library_name}', 'success')
            return success
        else:
            # Try scanning all libraries if specific one not found
            if log_func:
                log_func(f'⚠️ Library "{library_name}" not found, trying all libraries', 'warning')
            libraries = plex.get_libraries()
            for lib in libraries:
                if category_lower in lib.title.lower() or lib.title.lower() in category_lower:
                    success = plex.scan_library(lib.key)
                    if success and log_func:
                        log_func(f'✅ Plex scan started for {lib.title}', 'success')
                    return success
            
            if log_func:
                log_func(f'⚠️ No matching Plex library found for {category}', 'warning')
            return False
    except Exception as e:
        logger.error(f"Plex scan error: {e}")
        if log_func:
            log_func(f'❌ Plex scan error: {str(e)}', 'error')
        return False


@router.post("/alldebrid")
async def download_from_alldebrid(request: AllDebridDownloadRequest):
    """Download files from AllDebrid links"""
    if not settings.alldebrid_api_key:
        raise HTTPException(status_code=400, detail="AllDebrid API key not configured")
    
    if not request.links:
        raise HTTPException(status_code=400, detail="No links provided")
    
    # Create job
    job_counter[0] += 1
    job_id = job_counter[0]
    
    alldebrid_jobs[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': 0,
        'links': request.links,
        'logs': [],
        'error': None,
        'language': request.language,
        'auto_detect_language': request.auto_detect_language,  # Store auto-detect flag for category detection
        'output_path': request.output_path or '',
        'created_at': datetime.now().isoformat(),
        'started_at': None,
        'completed_at': None,
        'current_file': None,
        'processed_files': 0,
        'duration': None,
        'detected_category': None,
        'detected_language': None,
        'nas_destination': {
            'nas_name': request.nas_destination.nas_name if request.nas_destination else None,
            'category': request.nas_destination.category if request.nas_destination else None,
        } if request.nas_destination else None,
        # Detailed tracking
        'summary': {
            'total_files': 0,
            'downloaded': 0,
            'renamed': 0,
            'filtered': 0,
            'transferred': 0,
            'failed': 0,
            'total_size_mb': 0,
            'space_saved_mb': 0,
            'files': [],  # List of file details
        },
    }
    
    # Start background thread
    import threading
    thread = threading.Thread(
        target=run_alldebrid_download_task,
        args=(job_id, request),
        daemon=True
    )
    thread.start()
    
    save_jobs_to_file()  # Persist new job
    
    return {
        "success": True,
        "message": f"🚀 Download started! Job #{job_id} - {len(request.links)} links",
        "job_id": job_id
    }


@router.get("/alldebrid/jobs")
async def get_alldebrid_jobs():
    """Get all AllDebrid download jobs."""
    return {"jobs": list(alldebrid_jobs.values())}


@router.get("/alldebrid/jobs/{job_id}")
async def get_alldebrid_job(job_id: int):
    """Get a specific AllDebrid job status."""
    if job_id not in alldebrid_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job": alldebrid_jobs[job_id]}


@router.get("/alldebrid/jobs/{job_id}/logs")
async def get_alldebrid_job_logs(job_id: int):
    """Get logs for a specific AllDebrid job."""
    if job_id not in alldebrid_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"logs": alldebrid_jobs[job_id].get('logs', [])}


# ============================================================================
# Unified Job Endpoints (for LogViewer and ActiveConversions)
# ============================================================================

@router.get("/jobs/active")
async def get_active_jobs():
    """Get all active jobs (running or pending)."""
    active = []
    for job_id, job in alldebrid_jobs.items():
        if job.get('status') in ['pending', 'running']:
            summary = job.get('summary', {})
            active.append({
                'id': job_id,
                'job_type': 'download',
                'status': job.get('status', 'unknown'),
                'input_path': ', '.join(job.get('links', [])[:2]) + ('...' if len(job.get('links', [])) > 2 else ''),
                'output_path': job.get('output_path', ''),
                'language': job.get('language', 'auto'),
                'progress': job.get('progress', 0),
                'current_file': job.get('current_file'),
                'current_status': job.get('current_status', 'Processing...'),
                'total_files': len(job.get('links', [])),
                'processed_files': job.get('processed_files', 0),
                'created_at': job.get('created_at', ''),
                'started_at': job.get('started_at'),
                'completed_at': job.get('completed_at'),
                'duration': job.get('duration'),
                'error_message': job.get('error'),
                'summary': {
                    'downloaded': summary.get('downloaded', 0),
                    'renamed': summary.get('renamed', 0),
                    'filtered': summary.get('filtered', 0),
                    'transferred': summary.get('transferred', 0),
                    'failed': summary.get('failed', 0),
                    'total_size_mb': summary.get('total_size_mb', 0),
                    'space_saved_mb': summary.get('space_saved_mb', 0),
                    'files': summary.get('files', []),
                },
            })
    return {"success": True, "jobs": active}


@router.get("/jobs/recent")
async def get_recent_jobs(limit: int = 10):
    """Get recent jobs (completed or failed)."""
    recent = []
    for job_id, job in alldebrid_jobs.items():
        summary = job.get('summary', {})
        nas_dest = job.get('nas_destination', {})
        
        recent.append({
            'id': job_id,
            'job_type': 'download',
            'status': job.get('status', 'unknown'),
            'input_path': ', '.join(job.get('links', [])[:2]) + ('...' if len(job.get('links', [])) > 2 else ''),
            'output_path': job.get('output_path', ''),
            'language': job.get('language', 'auto'),
            'progress': job.get('progress', 0),
            'current_file': job.get('current_file'),
            'current_status': job.get('current_status', ''),
            'total_files': summary.get('total_files', len(job.get('links', []))),
            'processed_files': job.get('processed_files', 0),
            'created_at': job.get('created_at', ''),
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'duration': job.get('duration'),
            'error_message': job.get('error'),
            # Detailed summary
            'summary': {
                'downloaded': summary.get('downloaded', 0),
                'renamed': summary.get('renamed', 0),
                'filtered': summary.get('filtered', 0),
                'transferred': summary.get('transferred', 0),
                'failed': summary.get('failed', 0),
                'total_size_mb': summary.get('total_size_mb', 0),
                'space_saved_mb': summary.get('space_saved_mb', 0),
                'files': summary.get('files', []),
            },
            'detected_category': job.get('detected_category'),
            'nas_destination': {
                'nas_name': nas_dest.get('nas_name') if nas_dest else None,
                'category': nas_dest.get('category') if nas_dest else None,
            } if nas_dest else None,
        })
    # Sort by id descending (most recent first)
    recent.sort(key=lambda x: x['id'], reverse=True)
    return {"success": True, "jobs": recent[:limit]}


@router.get("/jobs/stats")
async def get_job_stats():
    """Get job statistics."""
    total = len(alldebrid_jobs)
    running = sum(1 for j in alldebrid_jobs.values() if j.get('status') == 'running')
    pending = sum(1 for j in alldebrid_jobs.values() if j.get('status') == 'pending')
    completed = sum(1 for j in alldebrid_jobs.values() if j.get('status') == 'completed')
    failed = sum(1 for j in alldebrid_jobs.values() if j.get('status') == 'failed')
    in_progress = running + pending
    
    # Calculate success rate
    finished = completed + failed
    success_rate = (completed / finished * 100) if finished > 0 else 100.0
    
    return {
        "success": True,
        "stats": {
            "total": total,
            "running": running,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "active": in_progress,
            "in_progress": in_progress,
            "success_rate": success_rate,
        }
    }


@router.get("/jobs/{job_id}")
async def get_job_by_id(job_id: int):
    """Get a specific job by ID."""
    if job_id not in alldebrid_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    job = alldebrid_jobs[job_id]
    return {
        "success": True,
        "job": {
            'id': job_id,
            'job_type': 'download',
            'status': job.get('status', 'unknown'),
            'progress': job.get('progress', 0),
            'error_message': job.get('error'),
        }
    }


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: int):
    """Get logs for a specific job."""
    if job_id not in alldebrid_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = alldebrid_jobs[job_id]
    logs = []
    for i, log in enumerate(job.get('logs', [])):
        logs.append({
            'message': log.get('message', ''),
            'level': log.get('level', 'info'),
            'timestamp': log.get('timestamp', datetime.now().isoformat()),
        })
    return {"success": True, "logs": logs}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int):
    """Cancel a running job."""
    if job_id not in alldebrid_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = alldebrid_jobs[job_id]
    if job.get('status') in ['pending', 'running']:
        job['status'] = 'cancelled'
        job['logs'].append({'message': '🛑 Job cancelled by user', 'level': 'warning'})
        save_jobs_to_file()  # Persist cancellation
        return {"success": True, "message": f"Job {job_id} cancelled"}
    else:
        return {"success": False, "detail": f"Job {job_id} is not running (status: {job.get('status')})"}


# ============================================================================
# Smart Routing Endpoints
# ============================================================================

@router.post("/analyze/routing")
async def analyze_file_routing(file_path: str):
    """
    Analyze a media file and get smart routing recommendations.
    Returns detected language, recommended NAS, and category.
    """
    from app.services.media_service import SmartNASRouter
    
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    router_service = SmartNASRouter()
    nas_configs = get_nas_configs()
    
    result = router_service.analyze_and_route(path, {n['name']: n for n in nas_configs})
    
    return {
        "success": True,
        "routing": result
    }


@router.get("/analyze/languages/{file_path:path}")
async def detect_file_languages(file_path: str):
    """Detect available audio languages in a media file."""
    from app.services.media_service import AudioTrackFilter
    
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    audio_filter = AudioTrackFilter()
    
    if not audio_filter.check_mkvtoolnix_available():
        raise HTTPException(status_code=503, detail="MKVToolNix not available")
    
    languages = audio_filter.detect_available_languages(path)
    auto_selected = audio_filter.auto_select_language(path)
    
    return {
        "file": file_path,
        "available_languages": languages,
        "auto_selected": auto_selected,
        "priority_order": audio_filter.language_priority
    }


# ========== Plex API Endpoints ==========

@router.get("/plex/status")
async def get_plex_status():
    """Get Plex server status and connection info."""
    plex = get_plex_client()
    if not plex:
        return {
            "success": False,
            "enabled": settings.plex_enabled,
            "configured": bool(settings.plex_server_url and settings.plex_token),
            "message": "Plex not configured"
        }
    
    try:
        identity = plex.get_server_identity()
        sessions = plex.get_active_sessions()
        
        return {
            "success": True,
            "enabled": True,
            "configured": True,
            "server": {
                "name": identity.get('friendly_name'),
                "version": identity.get('version'),
                "platform": identity.get('platform'),
                "machine_id": identity.get('machine_identifier'),
                "plex_pass": identity.get('my_plex_subscription', False),
            },
            "active_sessions": len(sessions),
            "sessions": [
                {
                    "user": s.user,
                    "title": s.title,
                    "type": s.type,
                    "player": s.player,
                    "platform": s.platform,
                    "state": s.state,
                    "progress": s.progress,
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error(f"Plex status error: {e}")
        return {
            "success": False,
            "enabled": True,
            "configured": True,
            "error": str(e)
        }


@router.get("/plex/libraries")
async def get_plex_libraries():
    """Get all Plex libraries."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        libraries = plex.get_libraries()
        return {
            "success": True,
            "libraries": [
                {
                    "key": lib.key,
                    "title": lib.title,
                    "type": lib.type,
                    "agent": lib.agent,
                    "locations": lib.locations,
                    "updated_at": lib.updated_at,
                    "scanned_at": lib.scanned_at,
                }
                for lib in libraries
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get Plex libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plex/scan/{library_key}")
async def scan_plex_library(library_key: str, path: str = None):
    """Trigger a Plex library scan."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        success = plex.scan_library(library_key, path)
        return {
            "success": success,
            "message": f"Scan triggered for library {library_key}" if success else "Scan failed"
        }
    except Exception as e:
        logger.error(f"Plex scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plex/scan-by-name/{library_name}")
async def scan_plex_library_by_name(library_name: str):
    """Trigger a Plex library scan by library name."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        success = plex.scan_library_by_name(library_name)
        return {
            "success": success,
            "message": f"Scan triggered for {library_name}" if success else f"Library '{library_name}' not found"
        }
    except Exception as e:
        logger.error(f"Plex scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plex/recently-added")
async def get_plex_recently_added(library_key: str = None, limit: int = 20):
    """Get recently added items from Plex."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        items = plex.get_recently_added(library_key, limit)
        return {
            "success": True,
            "items": [
                {
                    "rating_key": item.rating_key,
                    "title": item.title,
                    "type": item.type,
                    "year": item.year,
                    "imdb_id": item.imdb_id,
                    "tmdb_id": item.tmdb_id,
                    "added_at": item.added_at,
                    "library": item.library_section_title,
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get recently added: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plex/match/{rating_key}")
async def match_plex_item(rating_key: str, imdb_id: str = None, title: str = None, year: str = None):
    """Match a Plex item with IMDB/TMDB metadata."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    if not imdb_id and not title:
        raise HTTPException(status_code=400, detail="Either imdb_id or title is required")
    
    try:
        if imdb_id:
            success = plex.match_with_imdb(rating_key, imdb_id, title, year)
        else:
            # Search for matches by title
            matches = plex.get_matches(rating_key, title, year)
            if matches:
                # Use the first match
                success = plex.match_item(rating_key, matches[0]['guid'], title, year)
            else:
                success = False
        
        return {
            "success": success,
            "message": "Item matched successfully" if success else "Failed to match item"
        }
    except Exception as e:
        logger.error(f"Plex match error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plex/refresh/{rating_key}")
async def refresh_plex_item(rating_key: str):
    """Refresh metadata for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        success = plex.refresh_item(rating_key)
        return {
            "success": success,
            "message": "Metadata refresh triggered" if success else "Refresh failed"
        }
    except Exception as e:
        logger.error(f"Plex refresh error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Tautulli API Endpoints ==========

@router.get("/tautulli/status")
async def get_tautulli_status():
    """Get Tautulli/Plex server status."""
    tautulli = get_tautulli_client()
    if not tautulli:
        return {
            "success": False,
            "enabled": settings.tautulli_enabled,
            "configured": bool(settings.tautulli_url and settings.tautulli_api_key),
            "message": "Tautulli not configured"
        }
    
    try:
        status = tautulli.get_server_status()
        activity = tautulli.get_activity()
        
        return {
            "success": True,
            "enabled": True,
            "configured": True,
            "server": {
                "connected": status.connected if status else False,
                "version": status.version if status else None,
                "platform": status.platform if status else None,
                "remote_access": status.remote_access if status else None,
            },
            "activity": {
                "stream_count": activity.get('stream_count', 0),
                "total_bandwidth": activity.get('total_bandwidth', 0),
                "wan_bandwidth": activity.get('wan_bandwidth', 0),
                "lan_bandwidth": activity.get('lan_bandwidth', 0),
            }
        }
    except Exception as e:
        logger.error(f"Tautulli status error: {e}")
        return {
            "success": False,
            "enabled": True,
            "configured": True,
            "error": str(e)
        }


@router.get("/tautulli/libraries")
async def get_tautulli_libraries():
    """Get library statistics from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        libraries = tautulli.get_libraries()
        return {
            "success": True,
            "libraries": [
                {
                    "section_id": lib.section_id,
                    "name": lib.section_name,
                    "type": lib.section_type,
                    "count": lib.count,
                    "parent_count": lib.parent_count,
                    "child_count": lib.child_count,
                    "is_active": lib.is_active,
                }
                for lib in libraries
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get Tautulli libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tautulli/stats/users")
async def get_tautulli_user_stats(days: int = 30):
    """Get user statistics from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        from core.tautulli_client import format_duration
        users = tautulli.get_user_stats(days)
        return {
            "success": True,
            "period_days": days,
            "users": [
                {
                    "user_id": u.user_id,
                    "username": u.username,
                    "friendly_name": u.friendly_name,
                    "total_plays": u.total_plays,
                    "total_duration": u.total_duration,
                    "total_duration_formatted": format_duration(u.total_duration),
                    "last_seen": u.last_seen,
                    "last_played": u.last_played,
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tautulli/stats/popular")
async def get_tautulli_popular(media_type: str = "movies", days: int = 30, count: int = 10):
    """Get popular content from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        if media_type == "movies":
            items = tautulli.get_popular_movies(days, count)
        elif media_type == "tv":
            items = tautulli.get_popular_tv(days, count)
        else:
            items = tautulli.get_most_watched(days, count)
        
        return {
            "success": True,
            "media_type": media_type,
            "period_days": days,
            "items": items
        }
    except Exception as e:
        logger.error(f"Failed to get popular content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tautulli/history")
async def get_tautulli_history(user: str = None, section_id: int = None, 
                               length: int = 25, days: int = None):
    """Get watch history from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        from core.tautulli_client import format_duration
        history = tautulli.get_history(user, section_id, length, days)
        return {
            "success": True,
            "count": len(history),
            "history": [
                {
                    "date": item.date,
                    "title": item.title,
                    "full_title": item.full_title,
                    "media_type": item.media_type,
                    "user": item.user,
                    "friendly_name": item.friendly_name,
                    "platform": item.platform,
                    "player": item.player,
                    "duration": item.duration,
                    "duration_formatted": format_duration(item.duration),
                    "percent_complete": item.percent_complete,
                    "year": item.year,
                }
                for item in history
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
