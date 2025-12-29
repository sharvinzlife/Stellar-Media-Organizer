#!/usr/bin/env python3
"""
Standalone Backend Server
Runs directly on the host machine without Docker (macOS/Linux/Windows)
"""

import logging
import requests
import asyncio
import os
import re
import shutil
import threading
from collections import deque
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from functools import lru_cache
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import database for job tracking
from core.database import get_db, Job, JobStatus, JobType

# In-memory log store for real-time logs (last 100 entries per job)
job_logs: Dict[int, deque] = {}

def add_job_log(job_id: int, message: str, level: str = "info"):
    """Add a log entry for a job."""
    if job_id not in job_logs:
        job_logs[job_id] = deque(maxlen=100)
    job_logs[job_id].append({"message": message, "level": level, "timestamp": __import__('datetime').datetime.now().isoformat()})

def get_job_logs(job_id: int) -> List[dict]:
    """Get logs for a job."""
    return list(job_logs.get(job_id, []))

# Import configuration (but keep backward compatibility)
try:
    from config import get_settings
    settings = get_settings()
    USE_CONFIG = True
except ImportError:
    settings = None
    USE_CONFIG = False

# Pre-compiled patterns for performance
_CLEAN_PATTERNS = [
    re.compile(r'\[.*?\]'),
    re.compile(r'\(.*?\)'),
    re.compile(r'\.web-?dl', re.IGNORECASE),
    re.compile(r'\.webrip', re.IGNORECASE),
    re.compile(r'\.bluray', re.IGNORECASE),
    re.compile(r'\.brrip', re.IGNORECASE),
    re.compile(r'\.hdtv', re.IGNORECASE),
    re.compile(r'\d{3,4}p'),
    re.compile(r'\.x26[45]', re.IGNORECASE),
    re.compile(r'\.h26[45]', re.IGNORECASE),
    re.compile(r'\.avc', re.IGNORECASE),
    re.compile(r'\.hevc', re.IGNORECASE),
    re.compile(r'\.10bit', re.IGNORECASE),
    re.compile(r'\.8bit', re.IGNORECASE),
    re.compile(r'\.dd\d+\.\d+', re.IGNORECASE),
    re.compile(r'\.dd\d+', re.IGNORECASE),
    re.compile(r'\.dts', re.IGNORECASE),
    re.compile(r'\.aac', re.IGNORECASE),
    re.compile(r'\.ac3', re.IGNORECASE),
    re.compile(r'\-.*team.*', re.IGNORECASE),
    re.compile(r'\-.*group.*', re.IGNORECASE),
]
_MULTI_SPACE = re.compile(r'\s+')

# Video extensions as frozenset for O(1) lookup
_VIDEO_EXTENSIONS = frozenset({'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'})

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="🎬 Media Organizer Pro - Standalone",
    description="Fast backend with native GPU access",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:80", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GPU_SERVICE_URL = "http://localhost:8888"


def get_default_media_path() -> str:
    env_path = os.getenv("MEDIA_PATH")
    if env_path:
        # Expand ~ and resolve path
        return str(Path(env_path).expanduser().resolve())
    
    # Default to home directory
    home = Path.home()
    return str(home / "Documents" / "Processed")


DEFAULT_MEDIA_PATH = get_default_media_path()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).parent / "uploads"))).expanduser().resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# AllDebrid API key (set via environment variable or config)
def get_alldebrid_api_key():
    """Get AllDebrid API key from environment or config."""
    key = os.getenv("ALLDEBRID_API_KEY", "")
    if not key and USE_CONFIG and settings:
        key = getattr(settings, 'alldebrid_api_key', '') or ''
    return key

ALLDEBRID_API_KEY = get_alldebrid_api_key()

# NAS Configuration
def get_lharmony_host():
    """Get Lharmony NAS host from environment or config."""
    host = os.getenv("LHARMONY_HOST", "")
    if not host and USE_CONFIG and settings:
        host = getattr(settings, 'lharmony_host', '') or ''
    return host

LHARMONY_HOST = get_lharmony_host()

# Plex Configuration
def get_plex_enabled():
    """Check if Plex is enabled from environment or config."""
    enabled = os.getenv("PLEX_ENABLED", "").lower() in ('true', '1', 'yes')
    if not enabled and USE_CONFIG and settings:
        enabled = getattr(settings, 'plex_enabled', False)
    return enabled

PLEX_ENABLED = get_plex_enabled()


# Pydantic Models
class VideoConversionRequest(BaseModel):
    directory_path: str
    output_path: Optional[str] = None
    preset: str = 'hevc_best'


class NASDestination(BaseModel):
    nas_name: str
    category: str


class AllDebridRequest(BaseModel):
    links: List[str]
    output_path: Optional[str] = None
    language: Optional[str] = 'malayalam'
    download_only: Optional[bool] = False
    auto_detect_language: Optional[bool] = True
    nas_destination: Optional[NASDestination] = None


class ProcessedFileInfo(BaseModel):
    original_name: str
    new_name: str


class JobInfo(BaseModel):
    job_id: str
    input_file: str
    output_file: str


class VideoConversionResponse(BaseModel):
    success: bool
    message: str
    total_files: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    compression_ratio: Optional[float] = None
    errors: list = []
    processed_files: list = []
    jobs: list = []  # List of JobInfo for tracking


class ProcessRequest(BaseModel):
    operation: str
    directory_path: str
    output_path: Optional[str] = None
    target_language: Optional[str] = 'malayalam'
    volume_boost: Optional[float] = 1.0


class ProcessResponse(BaseModel):
    success: bool
    message: str
    processed_files: list = []
    errors: list = []


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    gpu_available: bool
    mkvtoolnix_available: bool
    ffmpeg_available: bool


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check with GPU status"""
    try:
        gpu_response = requests.get(f"{GPU_SERVICE_URL}/health", timeout=2)
        gpu_available = gpu_response.json().get('gpu_available', False)
    except:
        gpu_available = False

    mkvtoolnix_available = bool(shutil.which("mkvmerge"))
    ffmpeg_available = bool(
        shutil.which("ffmpeg")
        or Path("/opt/homebrew/bin/ffmpeg").exists()
        or Path("/usr/local/bin/ffmpeg").exists()
    )
    
    return HealthResponse(
        status="healthy",
        app_name="🎬 Media Organizer Pro",
        version="1.0.0",
        gpu_available=gpu_available,
        mkvtoolnix_available=mkvtoolnix_available,
        ffmpeg_available=ffmpeg_available,
    )


@app.get("/api/v1/config")
async def get_config():
    """Get application configuration including default paths"""
    return {
        "default_media_path": DEFAULT_MEDIA_PATH,
        "gpu_service_url": GPU_SERVICE_URL
    }


# Supported languages for audio filtering
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


@app.get("/api/v1/languages")
async def get_languages():
    """Get supported languages for audio filtering"""
    return {"languages": SUPPORTED_LANGUAGES}


def run_process_in_background(job_id: int, directory: Path, operation: str, output_path: str, target_language: str, volume_boost: float):
    """Run the media processing in a background thread."""
    import subprocess
    import sys
    
    db = get_db()
    
    try:
        add_job_log(job_id, f"Starting {operation} operation...", "info")
        
        # Build command
        script_path = Path(__file__).parent / "media_organizer.py"
        action_map = {"organize": "organize", "filter_audio": "filter", "both": "both"}
        action = action_map.get(operation, "organize")
        
        cmd = [sys.executable, str(script_path), action, str(directory), "--output", output_path]
        
        if operation in ['filter_audio', 'both']:
            cmd.extend(["--language", target_language, "--volume-boost", str(volume_boost)])
        
        add_job_log(job_id, f"Command: {' '.join(cmd)}", "info")
        
        # Count files
        video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        total_files = sum(1 for f in directory.iterdir() if f.is_file() and f.suffix.lower() in video_extensions)
        
        add_job_log(job_id, f"Found {total_files} media files", "info")
        db.update_job_progress(job_id, 5.0, current_file=f"Found {total_files} files")
        
        # Run process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        processed_count = 0
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                add_job_log(job_id, line, "info")
                
                if 'Moved:' in line or 'Filtered:' in line:
                    processed_count += 1
                    progress = min((processed_count / max(total_files, 1)) * 100, 95.0)
                    current_file = line.split('Moved:')[-1].split('Filtered:')[-1].strip()[:80]
                    db.update_job_progress(job_id, progress, current_file=current_file, processed_files=processed_count)
        
        process.wait()
        
        if process.returncode == 0:
            add_job_log(job_id, f"✅ Completed! Processed {processed_count} files.", "success")
            db.update_job_status(job_id, JobStatus.COMPLETED)
            db.update_job_progress(job_id, 100.0, processed_files=processed_count)
        else:
            add_job_log(job_id, "❌ Processing failed", "error")
            db.update_job_status(job_id, JobStatus.FAILED, error_message="Processing failed")
            
    except Exception as e:
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")
        db.update_job_status(job_id, JobStatus.FAILED, error_message=str(e))


@app.post("/api/v1/process", response_model=ProcessResponse)
async def process_media(request: ProcessRequest):
    """Process media files (organize/filter_audio) - returns immediately, runs in background"""
    db = get_db()
    
    try:
        if not request.directory_path:
            raise HTTPException(status_code=400, detail="Directory path is required")
        
        directory = Path(request.directory_path)
        if not directory.is_absolute():
            directory = directory.resolve()
        
        if not directory.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        
        # Create job
        job_type_map = {"organize": JobType.ORGANIZE, "filter_audio": JobType.FILTER_AUDIO, "both": JobType.BOTH}
        
        job = db.create_job(
            job_type=job_type_map.get(request.operation, JobType.ORGANIZE),
            input_path=str(directory),
            output_path=request.output_path or DEFAULT_MEDIA_PATH,
            language=request.target_language if request.operation in ['filter_audio', 'both'] else None,
            volume_boost=request.volume_boost if request.operation in ['filter_audio', 'both'] else None
        )
        
        logger.info(f"🎬 Created job #{job.id} for {request.operation}")
        db.update_job_status(job.id, JobStatus.IN_PROGRESS)
        add_job_log(job.id, f"Job #{job.id} created for {request.operation}", "info")
        
        # Start background thread
        thread = threading.Thread(
            target=run_process_in_background,
            args=(job.id, directory, request.operation, request.output_path or DEFAULT_MEDIA_PATH, 
                  request.target_language, request.volume_boost),
            daemon=True
        )
        thread.start()
        
        return ProcessResponse(
            success=True,
            message=f"🚀 Job #{job.id} started! Track progress in the dashboard.",
            processed_files=[],
            errors=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_unique_upload_path(*, directory: Path, filename: str) -> Path:
    safe_name = Path(filename).name
    candidate = directory / safe_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix

    for idx in range(1, 10_000):
        next_candidate = directory / f"{stem} ({idx}){suffix}"
        if not next_candidate.exists():
            return next_candidate

    raise RuntimeError("Too many files with the same name in upload directory")


@app.post("/api/v1/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload files for processing (saved to local UPLOAD_DIR)."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    saved_files: List[str] = []

    for upload in files:
        if not upload.filename:
            continue

        ext = Path(upload.filename).suffix.lower()
        if ext not in _VIDEO_EXTENSIONS:
            continue

        destination = get_unique_upload_path(directory=UPLOAD_DIR, filename=upload.filename)

        try:
            with destination.open("wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)
        finally:
            await upload.close()

        saved_files.append(str(destination))

    return {
        "success": True,
        "message": f"Uploaded {len(saved_files)} file(s)",
        "files": saved_files,
        "upload_dir": str(UPLOAD_DIR),
    }


def run_alldebrid_download(job_id: int, links: List[str], output_path: str, language: str, download_only: bool, nas_destination: dict = None, auto_detect_language: bool = True):
    """Run AllDebrid download in background thread with NAS transfer and enhanced progress tracking."""
    import time
    import shutil
    import subprocess
    
    db = get_db()
    start_time = time.time()
    
    # Store job info for category detection and tracking
    job_info = {
        'filter_language': language,
        'detected_category': None,
        'renamed_count': 0,
        'filtered_count': 0,
        'metadata_found': False,
    }
    
    try:
        from alldebrid_downloader import AllDebridDownloader
        import re
        
        api_key = ALLDEBRID_API_KEY
        if not api_key:
            add_job_log(job_id, "❌ AllDebrid API key not configured!", "error")
            db.update_job_status(job_id, JobStatus.FAILED, error_message="API key not configured")
            return
        
        # Always download to temp first
        temp_output = f"/tmp/alldebrid_downloads/{job_id}"
        Path(temp_output).mkdir(parents=True, exist_ok=True)
        
        # Update phase: downloading
        db.update_job_phase(job_id, phase="downloading")
        
        if nas_destination:
            nas_dest_str = f"{nas_destination.get('nas_name')}/{nas_destination.get('category')}"
            add_job_log(job_id, f"📁 NAS destination: {nas_dest_str}", "info")
            db.update_job_phase(job_id, phase="downloading", nas_destination=nas_dest_str)
        
        # Enhanced progress callback with phase tracking
        def progress_callback(message: str, level: str = "info"):
            # Strip ANSI escape codes from aria2c output
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\[\d+;\d+m|\[\d+m')
            clean_message = ansi_escape.sub('', message)
            add_job_log(job_id, clean_message, level)
            percent_match = re.search(r'(\d+)%', clean_message)
            if percent_match:
                percent = int(percent_match.group(1))
                scaled_progress = 5 + (percent * 0.45)  # 5% to 50% for download
                db.update_job_progress(job_id, scaled_progress)
            
            if "Downloading:" in clean_message:
                filename = clean_message.split("Downloading:")[-1].strip()[:60]
                db.update_job_progress(job_id, 10.0, current_file=f"⬇️ {filename}")
            elif "Unlocking" in clean_message:
                db.update_job_progress(job_id, 5.0, current_file="🔓 Unlocking links...")
            elif "Renamed:" in clean_message or "renamed" in clean_message.lower():
                job_info['renamed_count'] += 1
                db.update_job_phase(job_id, phase="organizing", renamed_files=job_info['renamed_count'])
            elif "Filtered:" in clean_message or "audio" in clean_message.lower():
                job_info['filtered_count'] += 1
                db.update_job_phase(job_id, phase="filtering", filtered_files=job_info['filtered_count'])
            elif "IMDB:" in clean_message:
                # IMDB metadata was found (primary source)
                job_info['metadata_found'] = True
                db.update_job_phase(job_id, phase="organizing", metadata_found="yes")
            elif "TMDB:" in clean_message:
                # TMDB metadata was found (fallback source)
                job_info['metadata_found'] = True
                db.update_job_phase(job_id, phase="organizing", metadata_found="yes")
            elif "No IMDB/TMDB metadata found" in clean_message or "not configured" in clean_message.lower():
                # No metadata found - will default to Malayalam
                job_info['metadata_found'] = False
                db.update_job_phase(job_id, phase="organizing", metadata_found="no")
        
        add_job_log(job_id, f"🚀 Starting AllDebrid download of {len(links)} links...", "info")
        db.update_job_progress(job_id, 5.0, current_file=f"Unlocking {len(links)} links...")
        
        # Get API keys from settings or env
        tmdb_token = os.getenv("TMDB_ACCESS_TOKEN") or (settings.tmdb_access_token if USE_CONFIG and settings else None)
        tmdb_api_key = os.getenv("TMDB_API_KEY") or (settings.tmdb_api_key if USE_CONFIG and settings else None)
        omdb_api_key = os.getenv("OMDB_API_KEY") or (settings.omdb_api_key if USE_CONFIG and settings else None)
        
        downloader = AllDebridDownloader(
            api_key,
            download_dir=temp_output,
            tmdb_token=tmdb_token,
            tmdb_api_key=tmdb_api_key,
            omdb_api_key=omdb_api_key,
            progress_callback=progress_callback
        )
        
        # Log metadata source
        if omdb_api_key:
            add_job_log(job_id, '🎬 IMDB (primary) + TMDB (fallback) enabled', 'info')
        else:
            add_job_log(job_id, '⚠️ No IMDB/TMDB API keys - will default to Malayalam library', 'warning')
        
        lang_to_use = None if auto_detect_language else language
        add_job_log(job_id, f'🎬 Language: {"Auto-detect" if auto_detect_language else language}', 'info')
        
        if download_only:
            downloaded = downloader.download_links(links)
            add_job_log(job_id, f"✅ Downloaded {len(downloaded)} files", "success")
            db.update_job_phase(job_id, phase="completed")
        else:
            add_job_log(job_id, '🔄 Download + Smart Organize mode', 'info')
            
            # Update phase: filtering
            db.update_job_phase(job_id, phase="filtering")
            db.update_job_progress(job_id, 50.0, current_file="🎵 Filtering audio tracks...")
            
            results = downloader.download_and_organize_smart(
                links, 
                temp_output, 
                language=lang_to_use or 'malayalam',
                filter_audio=True
            )
            downloaded_count = len(results.get('downloaded', []))
            renamed_count = len(results.get('renamed', []))
            filtered_count = len(results.get('filtered', []))
            metadata_found_in_results = results.get('metadata_found', False)
            
            # Update job_info with actual metadata status from renamer
            job_info['metadata_found'] = metadata_found_in_results
            
            # Update tracking
            db.update_job_phase(
                job_id, 
                phase="organizing",
                renamed_files=renamed_count,
                filtered_files=filtered_count,
                metadata_found="yes" if metadata_found_in_results else "no"
            )
            
            add_job_log(job_id, f"✅ Downloaded: {downloaded_count}, Renamed: {renamed_count}, Filtered: {filtered_count}", 'success')
            if metadata_found_in_results:
                add_job_log(job_id, '✅ IMDB/TMDB metadata found - using detected category', 'success')
            else:
                add_job_log(job_id, '⚠️ No IMDB/TMDB metadata found - will use Malayalam library', 'warning')
            db.update_job_progress(job_id, 75.0, current_file="✅ Processing complete")
            
            # If no metadata found, default to Malayalam
            if not metadata_found_in_results:
                db.update_job_phase(job_id, phase="organizing", detected_category="malayalam movies")
                job_info['detected_category'] = 'malayalam movies'
        
        # Transfer to NAS if destination specified
        if nas_destination:
            nas_name = nas_destination.get('nas_name')
            category = nas_destination.get('category')
            
            # Update phase: uploading
            db.update_job_phase(job_id, phase="uploading")
            add_job_log(job_id, f'📤 Transferring to NAS: {nas_name}...', 'info')
            db.update_job_progress(job_id, 80.0, current_file=f'📤 Uploading to {nas_name}...')
            
            nas_result = transfer_to_nas_standalone(
                temp_output, nas_name, category, 
                lambda msg, lvl: add_job_log(job_id, msg, lvl),
                job_info, language
            )
            
            if nas_result:
                detected_cat = job_info.get('detected_category', category)
                final_destination = f"{nas_name}/{detected_cat}"
                
                add_job_log(job_id, f'✅ Transferred to {final_destination}', 'success')
                db.update_job_phase(
                    job_id, 
                    phase="scanning",
                    nas_destination=final_destination,
                    detected_category=detected_cat
                )
                db.update_job_progress(job_id, 90.0, current_file='🧹 Cleaning up...')
                
                # Clean up temp
                add_job_log(job_id, '🧹 Cleaning up temp files...', 'info')
                shutil.rmtree(temp_output, ignore_errors=True)
                
                # Trigger Plex scan with enhanced tracking
                plex_enabled = os.getenv('PLEX_ENABLED', '').lower() in ('true', '1', 'yes')
                if not plex_enabled and USE_CONFIG and settings:
                    plex_enabled = getattr(settings, 'plex_enabled', False)
                
                if plex_enabled:
                    try:
                        plex = get_plex_client()
                        if plex:
                            # Map category to library
                            lib_map = {
                                'movies': 'Movies', 
                                'malayalam movies': 'Malayalam Movies',
                                'bollywood movies': 'Bollywood Movies', 
                                'tv-shows': 'TV Shows',
                                'tv': 'TV Shows', 
                                'malayalam-tv-shows': 'Malayalam TV Shows',
                                'malayalam tv shows': 'Malayalam TV Shows',
                            }
                            lib_name = lib_map.get(detected_cat.lower(), detected_cat)
                            lib = plex.get_library_by_name(lib_name)
                            
                            if lib:
                                db.update_job_phase(
                                    job_id, 
                                    phase="scanning",
                                    plex_scan_status="scanning",
                                    plex_library_name=lib_name
                                )
                                add_job_log(job_id, f'📺 Triggering Plex scan for "{lib_name}"...', 'info')
                                
                                plex.scan_library(lib.key)
                                
                                add_job_log(job_id, f'📺 Plex scan started for {lib_name}', 'success')
                                db.update_job_phase(job_id, phase="scanning", plex_scan_status="completed")
                            else:
                                add_job_log(job_id, f'⚠️ Plex library "{lib_name}" not found', 'warning')
                                db.update_job_phase(job_id, phase="completed", plex_scan_status="failed")
                    except Exception as e:
                        add_job_log(job_id, f'⚠️ Plex scan failed: {str(e)}', 'warning')
                        db.update_job_phase(job_id, phase="completed", plex_scan_status="failed")
            else:
                add_job_log(job_id, f'⚠️ NAS transfer failed, files in {temp_output}', 'warning')
        
        db.update_job_status(job_id, JobStatus.COMPLETED)
        db.update_job_phase(job_id, phase="completed")
        db.update_job_progress(job_id, 100.0, current_file='✅ Completed')
        duration = time.time() - start_time
        add_job_log(job_id, f'🎉 Job completed in {duration:.1f}s', 'success')
            
    except Exception as e:
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")
        db.update_job_status(job_id, JobStatus.FAILED, error_message=str(e))
        db.update_job_phase(job_id, phase="failed")
        logger.error(f"AllDebrid error: {e}", exc_info=True)


def transfer_to_nas_standalone(source_dir: str, nas_name: str, category: str, log_func, job_info: dict, filter_language: str) -> bool:
    """Transfer files to NAS using smbclient with smart category detection."""
    import subprocess
    import time
    
    nas_name_lower = nas_name.lower()
    
    # Get NAS config
    if nas_name in NAS_CONFIGS:
        config = NAS_CONFIGS[nas_name]
    elif 'lharmony' in nas_name_lower:
        config = NAS_CONFIGS.get('Lharmony')
    elif 'streamwave' in nas_name_lower:
        config = NAS_CONFIGS.get('Streamwave')
    else:
        log_func(f'❌ Unknown NAS: {nas_name}', 'error')
        return False
    
    if not config:
        log_func(f'❌ NAS {nas_name} not configured', 'error')
        return False
    
    host = config['host']
    username = config['username']
    password = config.get('password', '')
    share = config['share']
    media_path = config.get('media_path', 'media').strip('/')
    
    # Category mapping based on NAS type
    if 'lharmony' in nas_name_lower:
        category_map = {
            'malayalam movies': 'malayalam movies', 'movies': 'movies',
            'bollywood movies': 'bollywood movies', 'tv-shows': 'tv', 'tv': 'tv',
            'malayalam-tv-shows': 'malayalam tv shows', 'malayalam tv shows': 'malayalam tv shows',
        }
    else:  # Streamwave
        category_map = {
            'malayalam movies': 'Malayalam Movies', 'movies': 'movies',
            'bollywood movies': 'Bollywood Movies', 'tv-shows': 'tv-shows', 'tv': 'tv-shows',
            'malayalam-tv-shows': 'malayalam-tv-shows', 'malayalam tv shows': 'malayalam-tv-shows',
        }
    
    # Find media files
    source_path = Path(source_dir)
    media_files = []
    for ext in ['*.mkv', '*.mp4', '*.avi', '*.mov']:
        media_files.extend(source_path.rglob(ext))
    
    if not media_files:
        log_func('⚠️ No media files found', 'warning')
        return False
    
    log_func(f'📦 Found {len(media_files)} file(s) to transfer', 'info')
    
    success_count = 0
    for media_file in media_files:
        file_name = media_file.name
        
        # Smart detect category - pass metadata_found flag
        metadata_found = job_info.get('metadata_found', True)  # Default to True to avoid false Malayalam detection
        detected = detect_content_type_standalone(file_name, category, log_func, filter_language, metadata_found)
        job_info['detected_category'] = detected
        
        folder_name = category_map.get(detected.lower(), detected)
        remote_path = f"{media_path}/{folder_name}"
        
        is_tv = 'tv' in detected.lower()
        
        if is_tv:
            import re
            season_match = re.search(r'[Ss](\d{1,2})[Ee]\d{1,2}', file_name)
            if season_match:
                season_num = int(season_match.group(1))
                series_name = re.split(r'\s*-?\s*[Ss]\d{1,2}[Ee]\d{1,2}', file_name)[0].strip().rstrip(' -')
                target_folder = f"{series_name}/Season {season_num:02d}"
            else:
                target_folder = media_file.stem
        else:
            target_folder = media_file.stem
        
        log_func(f'📤 Uploading to {folder_name}/{target_folder}: {file_name}...', 'info')
        
        # Check for .nfo files (for Plex IMDB matching - movies only)
        nfo_file = media_file.with_suffix('.nfo')
        nfo_imdb_file = media_file.parent / (media_file.stem + '-imdb.nfo')
        has_nfo = nfo_file.exists()
        has_nfo_imdb = nfo_imdb_file.exists()
        
        # Build smbclient command - upload media file and .nfo files if exist
        if is_tv and '/' in target_folder:
            series_folder = target_folder.split('/')[0]
            smb_cmd = f'mkdir "{remote_path}/{series_folder}"; mkdir "{remote_path}/{target_folder}"; cd "{remote_path}/{target_folder}"; put "{media_file}" "{file_name}"'
        else:
            smb_cmd = f'mkdir "{remote_path}/{target_folder}"; cd "{remote_path}/{target_folder}"; put "{media_file}" "{file_name}"'
            # Add .nfo files for movies
            if has_nfo:
                smb_cmd += f'; put "{nfo_file}" "{nfo_file.name}"'
            if has_nfo_imdb:
                smb_cmd += f'; put "{nfo_imdb_file}" "{nfo_imdb_file.name}"'
        
        cmd = ['smbclient', f'//{host}/{share}', '-U', f'{username}%{password}', '-c', smb_cmd]
        
        try:
            start = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            elapsed = time.time() - start
            size_mb = media_file.stat().st_size / (1024 * 1024)
            speed = size_mb / elapsed if elapsed > 0 else 0
            
            if result.returncode == 0 or 'NT_STATUS_OBJECT_NAME_COLLISION' in result.stderr:
                nfo_msg = ""
                if has_nfo or has_nfo_imdb:
                    nfo_count = sum([has_nfo, has_nfo_imdb])
                    nfo_msg = f" + {nfo_count} .nfo"
                log_func(f'✅ Uploaded in {elapsed:.1f}s ({speed:.1f} MB/s): {file_name}{nfo_msg}', 'success')
                success_count += 1
            else:
                log_func(f'⚠️ Upload issue: {result.stderr[:100]}', 'warning')
        except subprocess.TimeoutExpired:
            log_func(f'⏱️ Upload timeout: {file_name}', 'error')
        except Exception as e:
            log_func(f'❌ Upload error: {str(e)}', 'error')
    
    return success_count > 0


def detect_content_type_standalone(filename: str, default_category: str, log_func, filter_language: str, metadata_found: bool = True) -> str:
    """Smart detect Movie vs TV Show and language from filename.
    
    Args:
        filename: The media filename
        default_category: User-selected category
        log_func: Logging function
        filter_language: Audio filter language
        metadata_found: Whether IMDB/TMDB metadata was found for this file
    """
    import re
    
    filename_lower = filename.lower()
    
    # TV patterns
    tv_patterns = [r's\d{1,2}e\d{1,2}', r'season\s*\d+', r'episode\s*\d+', r'\d{1,2}x\d{1,2}', r'e\d{2,3}', r'ep\d{1,3}']
    is_tv = any(re.search(p, filename_lower) for p in tv_patterns)
    
    # Language detection from filename
    malayalam_kw = ['malayalam', ' mal ', '-mal-', '.mal.', 'mlm', '[mal]', '(mal)']
    hindi_kw = ['hindi', 'bollywood', ' hin ', '-hin-', '.hin.', '[hin]', '(hin)']
    
    is_malayalam = any(kw in filename_lower for kw in malayalam_kw)
    is_hindi = any(kw in filename_lower for kw in hindi_kw)
    
    # Only use filter language as fallback if:
    # 1. No language detected in filename AND
    # 2. No metadata was found (new movies without IMDB/TMDB data)
    if not is_malayalam and not is_hindi and not metadata_found:
        if filter_language and filter_language.lower() == 'malayalam':
            is_malayalam = True
            log_func(f'🎯 No metadata found, using filter language: Malayalam', 'info')
        elif filter_language and filter_language.lower() == 'hindi':
            is_hindi = True
            log_func(f'🎯 No metadata found, using filter language: Hindi', 'info')
    
    # Determine category
    if is_tv:
        if is_malayalam:
            detected = 'malayalam-tv-shows'
        elif is_hindi:
            detected = 'tv-shows'
        else:
            detected = 'tv-shows'
    else:
        if is_malayalam:
            detected = 'malayalam movies'
        elif is_hindi:
            detected = 'bollywood movies'
        else:
            detected = 'movies'
    
    if detected.lower() != default_category.lower().replace('-', ' ').replace('_', ' '):
        log_func(f'🔍 Auto-detected: {default_category} → {detected}', 'info')
    
    return detected


@app.post("/api/v1/alldebrid")
async def download_from_alldebrid(request: AllDebridRequest):
    """Download files from AllDebrid links, organize and filter audio."""
    db = get_db()
    
    if not request.links:
        raise HTTPException(status_code=400, detail="No links provided")
    
    if not ALLDEBRID_API_KEY:
        raise HTTPException(status_code=400, detail="AllDebrid API key not configured. Set ALLDEBRID_API_KEY environment variable.")
    
    # Create job
    job = db.create_job(
        job_type=JobType.BOTH,
        input_path=f"AllDebrid ({len(request.links)} links)",
        output_path=request.output_path or DEFAULT_MEDIA_PATH,
        language=request.language
    )
    
    db.update_job_status(job.id, JobStatus.IN_PROGRESS)
    add_job_log(job.id, f"Job #{job.id} created for AllDebrid download", "info")
    
    # Convert nas_destination to dict if present
    nas_dest_dict = None
    if request.nas_destination:
        nas_dest_dict = {
            'nas_name': request.nas_destination.nas_name,
            'category': request.nas_destination.category
        }
    
    # Start background thread with all parameters
    thread = threading.Thread(
        target=run_alldebrid_download,
        args=(
            job.id, 
            request.links, 
            request.output_path or DEFAULT_MEDIA_PATH, 
            request.language, 
            request.download_only,
            nas_dest_dict,
            request.auto_detect_language
        ),
        daemon=True
    )
    thread.start()
    
    return {
        "success": True,
        "message": f"🚀 AllDebrid download started! Job #{job.id} - {len(request.links)} links",
        "job_id": job.id
    }


@app.get("/api/v1/alldebrid/status")
async def get_alldebrid_status():
    """Check if AllDebrid is configured."""
    return {
        "configured": bool(ALLDEBRID_API_KEY),
        "api_key_set": bool(ALLDEBRID_API_KEY)
    }


@app.get("/api/v1/alldebrid/jobs/{job_id}")
async def get_alldebrid_job(job_id: int):
    """Get AllDebrid job status with enhanced progress tracking."""
    db = get_db()
    try:
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get logs
        logs = get_job_logs(job_id)
        
        return {
            "id": job.id,
            "status": job.status.value if hasattr(job.status, 'value') else job.status,
            "progress": job.progress or 0,
            "current_file": job.current_file,
            "logs": logs,
            "error": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processed_files": job.processed_files,
            "total_files": job.total_files,
            # Enhanced progress tracking fields
            "phase": getattr(job, 'phase', 'pending'),
            "renamed_files": getattr(job, 'renamed_files', 0),
            "filtered_files": getattr(job, 'filtered_files', 0),
            "nas_destination": getattr(job, 'nas_destination', None),
            "detected_category": getattr(job, 'detected_category', None),
            "metadata_found": getattr(job, 'metadata_found', 'unknown'),
            "plex_scan_status": getattr(job, 'plex_scan_status', None),
            "plex_library_name": getattr(job, 'plex_library_name', None),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/convert", response_model=VideoConversionResponse)
async def convert_videos(request: VideoConversionRequest):
    """Convert videos using GPU service"""
    try:
        if not request.directory_path:
            raise HTTPException(status_code=400, detail="Directory path is required")
        
        directory = Path(request.directory_path)
        if not directory.exists():
            raise HTTPException(status_code=404, detail="Source directory not found")
        
        # Determine output directory
        if request.output_path:
            output_dir = Path(request.output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = directory / "converted"
            output_dir.mkdir(exist_ok=True)
        
        logger.info(f"🎬 Starting conversion in: {directory}")
        logger.info(f"📁 Output to: {output_dir}")
        
        # Find video files
        video_extensions = ('.mkv', '.mp4', '.avi', '.mov')
        video_files = []
        for ext in video_extensions:
            video_files.extend(directory.glob(f"*{ext}"))
        
        if not video_files:
            raise HTTPException(
                status_code=404,
                detail=f"No video files found. Looking for: {', '.join(video_extensions)}"
            )
        
        logger.info(f"🎬 Found {len(video_files)} video files")
        
        # Submit jobs to GPU service
        jobs = []
        for video_file in video_files:
            # Clean filename
            clean_name = clean_filename(video_file.name)
            output_file = output_dir / f"{clean_name}.mkv"
            
            try:
                # Submit to GPU service
                response = requests.post(
                    f"{GPU_SERVICE_URL}/convert",
                    json={
                        'input_path': str(video_file),
                        'output_path': str(output_file),
                        'preset': 'hevc_videotoolbox'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    job_data = response.json()
                    jobs.append({
                        'job_id': job_data['job_id'],
                        'input_file': str(video_file.name),
                        'output_file': str(output_file)
                    })
                    logger.info(f"📥 Submitted: {video_file.name} -> Job {job_data['job_id']}")
                else:
                    logger.error(f"❌ Failed to submit {video_file.name}")
            except Exception as e:
                logger.error(f"❌ Error submitting {video_file.name}: {e}")
        
        # Return immediately with job IDs for real-time tracking
        if len(jobs) > 0:
            return VideoConversionResponse(
                success=True,
                message=f"🚀 Started conversion of {len(jobs)} file(s). Track progress in real-time above!",
                total_files=len(jobs),
                successful=0,
                failed=0,
                compression_ratio=0,
                errors=[],
                processed_files=[],
                jobs=jobs
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to submit any jobs to GPU service")
        
        # OLD CODE - Poll for completion (commented out for now, jobs tracked via WebSocket instead)
        """
        completed = []
        failed = []
        total_input_size = 0
        total_output_size = 0
        
        for job in jobs:
            job_id = job['job_id']
            logger.info(f"⏳ Waiting for job {job_id}...")
            
            # Poll status
            import time
            max_wait = 3600  # 1 hour
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    status_response = requests.get(
                        f"{GPU_SERVICE_URL}/status/{job_id}",
                        timeout=5
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status_val = status_data.get('status')
                        
                        if status_val == 'completed':
                            completed.append({
                                'original_name': job['input_file'].name,
                                'new_name': job['output_file'].name
                            })
                            total_input_size += status_data.get('input_size', 0)
                            total_output_size += status_data.get('output_size', 0)
                            logger.info(f"✅ Completed: {job['input_file'].name}")
                            break
                        elif status_val == 'failed':
                            failed.append(status_data.get('error', 'Unknown error'))
                            logger.error(f"❌ Failed: {job['input_file'].name}")
                            break
                        else:
                            # Still processing, log progress
                            progress = status_data.get('progress', 0)
                            eta = status_data.get('eta', 'Unknown')
                            logger.info(f"📊 {job['input_file'].name}: {progress}% | ETA: {eta}")
                            time.sleep(5)
                except Exception as e:
                    logger.error(f"Error polling job {job_id}: {e}")
                    time.sleep(5)
        
        # Calculate results
        compression_ratio = 0
        if total_input_size > 0:
            compression_ratio = (1 - total_output_size / total_input_size) * 100
        
        success = len(failed) == 0
        message = f"✅ Converted {len(completed)}/{len(jobs)} files successfully!"
        if compression_ratio > 0:
            message += f" Saved {compression_ratio:.1f}% space"
        
        return VideoConversionResponse(
            success=success,
            message=message,
            total_files=len(jobs),
            successful=len(completed),
            failed=len(failed),
            compression_ratio=compression_ratio,
            errors=failed,
            processed_files=completed
        )
        """
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/v1/ws/conversion/{job_id}")
async def websocket_conversion_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time conversion progress"""
    await websocket.accept()
    try:
        while True:
            try:
                # Get progress from GPU service
                response = requests.get(f"{GPU_SERVICE_URL}/status/{job_id}", timeout=2)
                if response.status_code == 200:
                    status_data = response.json()
                    await websocket.send_json(status_data)
                    
                    # Stop streaming if job is done
                    if status_data.get('status') in ['completed', 'failed']:
                        break
                else:
                    await websocket.send_json({
                        'status': 'error',
                        'message': 'Failed to fetch status'
                    })
                    break
            except Exception as e:
                logger.error(f"Error fetching status for {job_id}: {e}")
                break
            
            await asyncio.sleep(1)  # Update every second
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")


@lru_cache(maxsize=256)
def clean_filename(filename: str) -> str:
    """Clean filename with caching for repeated calls."""
    name = Path(filename).stem
    
    # Use pre-compiled patterns
    cleaned = name
    for pattern in _CLEAN_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    
    cleaned = cleaned.replace('.', ' ').replace('_', ' ')
    cleaned = _MULTI_SPACE.sub(' ', cleaned).strip()
    
    return cleaned.title()


# ============================================================================
# JOB HISTORY API ENDPOINTS
# ============================================================================

@app.get("/api/v1/jobs/stats")
async def get_job_stats():
    """Get job statistics"""
    try:
        db = get_db()
        stats = db.get_job_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error fetching job stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/active")
async def get_active_jobs():
    """Get all active (in-progress) jobs"""
    try:
        db = get_db()
        jobs = db.get_active_jobs()
        
        return {
            "success": True,
            "jobs": [job.to_dict() for job in jobs],
            "count": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error fetching active jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/recent")
async def get_recent_jobs(limit: int = Query(20, ge=1, le=100)):
    """Get recent jobs"""
    try:
        db = get_db()
        jobs = db.get_recent_jobs(limit=limit)
        
        return {
            "success": True,
            "jobs": [job.to_dict() for job in jobs],
            "count": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error fetching recent jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs")
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get all jobs with optional filtering"""
    try:
        db = get_db()
        
        status_enum = JobStatus(status) if status else None
        type_enum = JobType(job_type) if job_type else None
        
        jobs = db.get_all_jobs(
            status=status_enum,
            job_type=type_enum,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "jobs": [job.to_dict() for job in jobs],
            "count": len(jobs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: int):
    """Get specific job by ID"""
    try:
        db = get_db()
        job = db.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "success": True,
            "job": job.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}/logs")
async def get_job_logs_endpoint(job_id: int):
    """Get logs for a specific job"""
    return {
        "success": True,
        "job_id": job_id,
        "logs": get_job_logs(job_id)
    }


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: int):
    """Delete a specific job"""
    try:
        db = get_db()
        job = db.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Don't delete active jobs
        if job.status == JobStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Cannot delete active job")
        
        with db.get_session() as session:
            session.delete(job)
            session.commit()
        
        return {
            "success": True,
            "message": f"Job {job_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: int):
    """Cancel a pending or stuck job"""
    try:
        db = get_db()
        job = db.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if job.status == JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job already completed")
        
        db.update_job_status(job_id, JobStatus.CANCELLED, error_message="Cancelled by user")
        add_job_log(job_id, "Job cancelled by user", "warning")
        
        return {
            "success": True,
            "message": f"Job {job_id} cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jobs/cleanup-stale")
async def cleanup_stale_jobs():
    """Mark old pending jobs as failed (jobs pending for more than 5 minutes)"""
    try:
        db = get_db()
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        cleaned = 0
        
        with db.get_session() as session:
            stale_jobs = session.query(Job).filter(
                Job.status == JobStatus.PENDING,
                Job.created_at < cutoff
            ).all()
            
            for job in stale_jobs:
                job.status = JobStatus.FAILED
                job.error_message = "Job timed out (server restart or stale job)"
                job.completed_at = datetime.utcnow()
                cleaned += 1
                add_job_log(job.id, "Job marked as failed (stale/orphaned)", "error")
            
            session.commit()
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned} stale jobs",
            "cleaned": cleaned
        }
    except Exception as e:
        logger.error(f"Error cleaning stale jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MUSIC ORGANIZER API ENDPOINTS
# ============================================================================

class MusicProcessRequest(BaseModel):
    """Request model for music processing"""
    source_path: str
    output_path: Optional[str] = None
    preset: str = "surround_7_0"  # 7.0 surround upmix with timbre-matching
    output_format: str = "keep"  # keep, flac, mp3, m4a
    enhance_audio: bool = True
    lookup_metadata: bool = True


class MusicProcessResponse(BaseModel):
    """Response model for music processing"""
    success: bool
    message: str
    job_id: Optional[int] = None
    total: int = 0
    processed: int = 0
    failed: int = 0


# MusicBrainz credentials from environment
MUSICBRAINZ_CLIENT_ID = os.getenv("MUSICBRAINZ_CLIENT_ID", "")
MUSICBRAINZ_CLIENT_SECRET = os.getenv("MUSICBRAINZ_CLIENT_SECRET", "")
_music_path = os.getenv("MUSIC_OUTPUT_PATH", str(Path.home() / "Documents" / "Music"))
MUSIC_OUTPUT_PATH = str(Path(_music_path).expanduser().resolve())

# Discogs API token
DISCOGS_API_TOKEN = os.getenv("DISCOGS_API_TOKEN", "")


def process_music_background(job_id: int, request: MusicProcessRequest):
    """Background task for music processing"""
    from music_organizer import MusicLibraryOrganizer, AudioPreset
    
    db = get_db()
    
    try:
        # Only 7.0 surround preset available
        preset = AudioPreset.SURROUND_7_0
        
        # Output format - always FLAC for 7.0 surround (proper audio container)
        output_format = 'flac'
        
        add_job_log(job_id, f"Initializing Music Organizer (7.0 Surround)...", "info")
        
        # Initialize organizer
        organizer = MusicLibraryOrganizer(
            musicbrainz_client_id=MUSICBRAINZ_CLIENT_ID,
            musicbrainz_client_secret=MUSICBRAINZ_CLIENT_SECRET,
            use_musicbrainz=request.lookup_metadata
        )
        
        add_job_log(job_id, f"Processing music from: {request.source_path}", "info")
        add_job_log(job_id, f"Output: {request.output_path}", "info")
        add_job_log(job_id, f"Preset: {request.preset}, Format: {request.output_format}", "info")
        
        input_path = Path(request.source_path)
        
        if input_path.is_file():
            # Single file
            result = organizer.organize_file(
                str(input_path),
                request.output_path,
                enhance_audio=request.enhance_audio,
                audio_preset=preset,
                output_format=output_format,
                lookup_metadata=request.lookup_metadata
            )
            
            if result:
                db.update_job_status(job_id, status=JobStatus.COMPLETED)
                db.update_job_progress(job_id, progress=100, processed_files=1)
                add_job_log(job_id, f"✅ Organized: {result}", "success")
            else:
                db.update_job_status(job_id, status=JobStatus.FAILED, error_message="Failed to process file")
                add_job_log(job_id, "❌ Failed to process file", "error")
        else:
            # Directory
            db.update_job_status(job_id, status=JobStatus.IN_PROGRESS)
            add_job_log(job_id, f"🔍 Scanning directory for audio files...", "info")
            
            results = organizer.organize_directory(
                str(input_path),
                request.output_path,
                enhance_audio=request.enhance_audio,
                audio_preset=preset,
                output_format=output_format,
                lookup_metadata=request.lookup_metadata
            )
            
            db.update_job_status(job_id, status=JobStatus.COMPLETED if results['failed'] == 0 else JobStatus.COMPLETED)
            db.update_job_progress(job_id, progress=100, processed_files=results['success'])
            
            add_job_log(job_id, f"✅ Processed {results['success']}/{results['total']} files", "success")
            if results['errors']:
                for err in results['errors'][:5]:
                    add_job_log(job_id, f"⚠️ {err}", "warning")
                    
    except Exception as e:
        logger.error(f"Music processing error: {e}")
        db.update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")


@app.get("/api/v1/music/status")
async def get_music_status():
    """Check if Music Organizer is configured"""
    try:
        from music_organizer import MUSICBRAINZ_AVAILABLE, MUTAGEN_AVAILABLE, AI_EXTRACTION_AVAILABLE
        
        return {
            "configured": True,
            "musicbrainz_available": MUSICBRAINZ_AVAILABLE,
            "musicbrainz_configured": bool(MUSICBRAINZ_CLIENT_ID),
            "mutagen_available": MUTAGEN_AVAILABLE,
            "ai_extraction_available": AI_EXTRACTION_AVAILABLE,
            "default_output": MUSIC_OUTPUT_PATH
        }
    except ImportError:
        return {
            "configured": False,
            "musicbrainz_available": False,
            "musicbrainz_configured": False,
            "mutagen_available": False,
            "ai_extraction_available": False,
            "default_output": MUSIC_OUTPUT_PATH
        }


# ============================================================================
# AI METADATA EXTRACTION API ENDPOINTS
# ============================================================================

class AIExtractRequest(BaseModel):
    """Request model for AI metadata extraction"""
    filenames: List[str]
    media_type: str = "auto"  # auto, video, music
    use_ai_fallback: bool = True
    force_ai: bool = False


class VideoMetadataResponse(BaseModel):
    """Response model for video metadata"""
    title: str
    year: Optional[int] = None
    media_type: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    quality: Optional[str] = None
    source: Optional[str] = None
    codec: Optional[str] = None
    audio: Optional[str] = None
    language: Optional[str] = None
    release_group: Optional[str] = None
    confidence: float


class MusicMetadataResponse(BaseModel):
    """Response model for music metadata"""
    artist: str
    title: str
    album: Optional[str] = None
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    confidence: float


@app.get("/api/v1/ai/status")
async def get_ai_status():
    """Check if AI metadata extraction is available"""
    try:
        from core.ai_metadata_extractor import AIMetadataExtractor, OPENAI_AVAILABLE, VENICE_API_KEY
        
        ai_available = OPENAI_AVAILABLE and bool(VENICE_API_KEY)
        
        return {
            "available": ai_available,
            "openai_package": OPENAI_AVAILABLE,
            "api_key_configured": bool(VENICE_API_KEY),
            "model": "llama-3.2-3b",
            "provider": "Venice AI"
        }
    except ImportError:
        return {
            "available": False,
            "openai_package": False,
            "api_key_configured": False,
            "model": None,
            "provider": None
        }


@app.post("/api/v1/ai/extract")
async def extract_metadata(request: AIExtractRequest):
    """Extract metadata from filenames using AI-powered hybrid extraction"""
    try:
        from core.ai_metadata_extractor import AIMetadataExtractor, MediaType
        
        extractor = AIMetadataExtractor()
        results = []
        
        for filename in request.filenames:
            # Determine media type
            if request.media_type == "auto":
                # Auto-detect based on extension
                ext = Path(filename).suffix.lower()
                is_music = ext in {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.wma'}
                is_video = ext in {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
                media_type = "music" if is_music else "video" if is_video else "video"
            else:
                media_type = request.media_type
            
            if media_type == "music":
                meta = extractor.extract_music_metadata(
                    filename, 
                    use_ai_fallback=request.use_ai_fallback,
                    force_ai=request.force_ai
                )
                results.append({
                    "filename": filename,
                    "type": "music",
                    "metadata": {
                        "artist": meta.artist,
                        "title": meta.title,
                        "album": meta.album,
                        "track_number": meta.track_number,
                        "year": meta.year,
                        "genre": meta.genre,
                        "confidence": meta.confidence
                    }
                })
            else:
                meta = extractor.extract_video_metadata(
                    filename,
                    use_ai_fallback=request.use_ai_fallback,
                    force_ai=request.force_ai
                )
                results.append({
                    "filename": filename,
                    "type": "video",
                    "metadata": {
                        "title": meta.title,
                        "year": meta.year,
                        "media_type": meta.media_type.value,
                        "season": meta.season,
                        "episode": meta.episode,
                        "episode_title": meta.episode_title,
                        "quality": meta.quality,
                        "source": meta.source,
                        "codec": meta.codec,
                        "audio": meta.audio,
                        "language": meta.language,
                        "release_group": meta.release_group,
                        "confidence": meta.confidence
                    }
                })
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
        
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"AI extraction not available: {e}")
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ai/extract/video")
async def extract_video_metadata(filenames: List[str], force_ai: bool = False):
    """Extract video metadata from filenames"""
    try:
        from core.ai_metadata_extractor import AIMetadataExtractor
        
        extractor = AIMetadataExtractor()
        results = []
        
        for filename in filenames:
            meta = extractor.extract_video_metadata(filename, use_ai_fallback=True, force_ai=force_ai)
            results.append({
                "filename": filename,
                "title": meta.title,
                "year": meta.year,
                "media_type": meta.media_type.value,
                "season": meta.season,
                "episode": meta.episode,
                "quality": meta.quality,
                "language": meta.language,
                "confidence": meta.confidence
            })
        
        return {"success": True, "results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ai/extract/music")
async def extract_music_metadata(filenames: List[str], force_ai: bool = False):
    """Extract music metadata from filenames"""
    try:
        from core.ai_metadata_extractor import AIMetadataExtractor
        
        extractor = AIMetadataExtractor()
        results = []
        
        for filename in filenames:
            meta = extractor.extract_music_metadata(filename, use_ai_fallback=True, force_ai=force_ai)
            results.append({
                "filename": filename,
                "artist": meta.artist,
                "title": meta.title,
                "album": meta.album,
                "track_number": meta.track_number,
                "year": meta.year,
                "confidence": meta.confidence
            })
        
        return {"success": True, "results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DISCOGS API ENDPOINTS
# ============================================================================

@app.get("/api/v1/discogs/status")
async def get_discogs_status():
    """Check if Discogs API is configured"""
    try:
        from core.discogs_lookup import DISCOGS_AVAILABLE
        
        return {
            "available": DISCOGS_AVAILABLE,
            "configured": bool(DISCOGS_API_TOKEN),
            "api_token_set": bool(DISCOGS_API_TOKEN)
        }
    except ImportError:
        return {
            "available": False,
            "configured": False,
            "api_token_set": False
        }


@app.post("/api/v1/discogs/search/track")
async def discogs_search_track(title: str, artist: str = ""):
    """Search for a track on Discogs"""
    if not DISCOGS_API_TOKEN:
        raise HTTPException(status_code=400, detail="Discogs API token not configured")
    
    try:
        from core.discogs_lookup import DiscogsClient
        
        client = DiscogsClient(DISCOGS_API_TOKEN)
        track = client.search_track(title, artist)
        
        if track:
            return {
                "success": True,
                "track": {
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "year": track.year,
                    "track_number": track.track_number,
                    "genre": track.genre,
                    "style": track.style,
                    "label": track.label,
                    "discogs_release_id": track.discogs_release_id
                }
            }
        else:
            return {"success": False, "message": "Track not found"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/discogs/search/album")
async def discogs_search_album(album: str, artist: str = ""):
    """Search for an album on Discogs"""
    if not DISCOGS_API_TOKEN:
        raise HTTPException(status_code=400, detail="Discogs API token not configured")
    
    try:
        from core.discogs_lookup import DiscogsClient
        
        client = DiscogsClient(DISCOGS_API_TOKEN)
        result = client.search_album(album, artist)
        
        if result:
            return {
                "success": True,
                "album": {
                    "title": result.title,
                    "artist": result.artist,
                    "year": result.year,
                    "genres": result.genres,
                    "styles": result.styles,
                    "labels": result.labels,
                    "country": result.country,
                    "format": result.format,
                    "track_count": result.track_count,
                    "cover_url": result.cover_url,
                    "discogs_release_id": result.discogs_release_id
                }
            }
        else:
            return {"success": False, "message": "Album not found"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/music/presets")
async def get_music_presets():
    """Get available audio enhancement presets"""
    return {
        "presets": [
            {
                "id": "surround_7_0",
                "name": "7.0 Surround",
                "description": "Upmix to 7.0 with timbre-matching for Polk T50 + Sony surrounds",
                "recommended": True
            }
        ],
        "formats": [
            {"id": "flac", "name": "FLAC (7.0 Surround)", "description": "Multi-channel lossless audio"}
        ]
    }


@app.post("/api/v1/music/process", response_model=MusicProcessResponse)
async def process_music(request: MusicProcessRequest, background_tasks: BackgroundTasks):
    """Process music files - organize and enhance"""
    
    # Validate source path
    source_path = Path(request.source_path)
    if not source_path.exists():
        raise HTTPException(status_code=400, detail=f"Source path not found: {request.source_path}")
    
    # Create output directory
    output_path = Path(request.output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create job
    db = get_db()
    job = db.create_job(
        job_type=JobType.ORGANIZE,  # Reuse organize type for music
        input_path=request.source_path,
        output_path=request.output_path,
        language=request.preset  # Store preset in language field
    )
    
    # Start background processing
    background_tasks.add_task(process_music_background, job.id, request)
    
    return MusicProcessResponse(
        success=True,
        message=f"Music processing started (Job #{job.id})",
        job_id=job.id
    )


class MusicEnhanceRequest(BaseModel):
    """Request model for enhancing music files in-place (preserving folder structure)"""
    source_path: str
    output_path: str = ""  # If empty, enhance in-place
    preset: str = "optimal"
    output_format: str = "keep"


def enhance_music_background(job_id: int, request: MusicEnhanceRequest):
    """Background task for enhancing music files while preserving folder structure"""
    from music_organizer import AudioEnhancer, AudioPreset
    
    db = get_db()
    
    try:
        # Only 7.0 surround preset available
        preset = AudioPreset.SURROUND_7_0
        
        add_job_log(job_id, f"🔊 Initializing 7.0 Surround Upmixer...", "info")
        add_job_log(job_id, f"📁 Source: {request.source_path}", "info")
        add_job_log(job_id, f"🎛️ Timbre-matching for Polk T50 + Sony surrounds", "info")
        
        # Initialize enhancer
        enhancer = AudioEnhancer()
        
        source_path = Path(request.source_path)
        output_path = Path(request.output_path) if request.output_path else source_path
        
        # Determine if we're enhancing in-place or to a different location
        in_place = str(source_path) == str(output_path)
        
        if in_place:
            add_job_log(job_id, "⚠️ Enhancing in-place (original files will be replaced)", "warning")
        else:
            add_job_log(job_id, f"📂 Output: {output_path}", "info")
            output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all audio files
        audio_extensions = ['.flac', '.mp3', '.m4a', '.opus', '.ogg', '.wav', '.webm']
        audio_files = []
        
        if source_path.is_file():
            if source_path.suffix.lower() in audio_extensions:
                audio_files = [source_path]
        else:
            audio_files = [f for f in source_path.rglob('*') 
                          if f.is_file() and f.suffix.lower() in audio_extensions]
        
        total = len(audio_files)
        add_job_log(job_id, f"🔍 Found {total} audio files to enhance", "info")
        
        if total == 0:
            db.update_job_status(job_id, status=JobStatus.COMPLETED)
            add_job_log(job_id, "⚠️ No audio files found", "warning")
            return
        
        db.update_job_status(job_id, status=JobStatus.IN_PROGRESS)
        processed = 0
        errors = []
        
        for i, audio_file in enumerate(audio_files):
            try:
                # Calculate destination path (preserve folder structure)
                if in_place:
                    # Create temp file path (don't create the file yet - ffmpeg will create it)
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    temp_path = Path(temp_dir) / f"enhance_{audio_file.stem}_{i}{audio_file.suffix}"
                    dest_path = temp_path
                else:
                    rel_path = audio_file.relative_to(source_path) if source_path.is_dir() else audio_file.name
                    dest_path = output_path / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                add_job_log(job_id, f"🎵 Enhancing ({i+1}/{total}): {audio_file.name}", "info")
                
                # Enhance the audio
                success = enhancer.enhance_audio(str(audio_file), str(dest_path), preset=preset)
                
                if success and dest_path.exists() and dest_path.stat().st_size > 0:
                    # If in-place, replace original with enhanced version
                    if in_place:
                        import shutil
                        shutil.move(str(dest_path), str(audio_file))
                    processed += 1
                else:
                    # Enhancement failed
                    add_job_log(job_id, f"⚠️ Enhancement failed for {audio_file.name}, keeping original", "warning")
                    # Clean up temp file if it exists
                    if in_place and dest_path.exists():
                        dest_path.unlink()
                    errors.append(f"Enhancement failed: {audio_file.name}")
                
                # Update progress
                progress = ((i + 1) / total) * 100
                db.update_job_progress(job_id, progress=progress, processed_files=processed)
                
            except Exception as e:
                error_msg = f"Error enhancing {audio_file.name}: {e}"
                add_job_log(job_id, f"⚠️ {error_msg}", "warning")
                errors.append(error_msg)
                # Clean up temp file if it exists
                if in_place and 'dest_path' in locals() and dest_path.exists():
                    try:
                        dest_path.unlink()
                    except:
                        pass
        
        # Complete
        db.update_job_status(job_id, status=JobStatus.COMPLETED)
        db.update_job_progress(job_id, progress=100, processed_files=processed)
        
        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                job.total_files = total
                session.commit()
        
        add_job_log(job_id, f"✅ Enhanced {processed}/{total} files (preset: {request.preset})", "success")
        
        if errors:
            add_job_log(job_id, f"⚠️ {len(errors)} files had errors", "warning")
            
    except Exception as e:
        logger.error(f"Music enhancement error: {e}")
        db.update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")


@app.post("/api/v1/music/enhance")
async def enhance_music(request: MusicEnhanceRequest, background_tasks: BackgroundTasks):
    """Enhance audio files while preserving folder structure (no reorganization)"""
    
    # Validate source path
    source_path = Path(request.source_path)
    if not source_path.exists():
        raise HTTPException(status_code=400, detail=f"Source path not found: {request.source_path}")
    
    # Create job
    db = get_db()
    output = request.output_path or request.source_path
    job = db.create_job(
        job_type=JobType.ORGANIZE,
        input_path=request.source_path,
        output_path=output,
        language=request.preset
    )
    
    # Start background processing
    background_tasks.add_task(enhance_music_background, job.id, request)
    
    return {
        "success": True,
        "message": f"Audio enhancement started (Job #{job.id})",
        "job_id": job.id,
        "preset": request.preset,
        "in_place": not request.output_path or request.output_path == request.source_path
    }


class MusicAllDebridRequest(BaseModel):
    """Request model for music AllDebrid download"""
    links: List[str]
    preset: str = "optimal"
    output_format: str = "flac"


def process_music_alldebrid_background(job_id: int, links: List[str], preset: str, output_format: str):
    """Background task for AllDebrid music download and processing"""
    import tempfile
    from alldebrid_downloader import AllDebridDownloader
    from music_organizer import MusicLibraryOrganizer, AudioPreset
    
    db = get_db()
    
    # Mark job as running immediately
    db.update_job_status(job_id, status=JobStatus.IN_PROGRESS)
    db.update_job_progress(job_id, progress=0, current_file="Initializing...")
    
    try:
        add_job_log(job_id, f"Starting AllDebrid download of {len(links)} music files...", "info")
        logger.info(f"[Job {job_id}] Starting music AllDebrid download of {len(links)} links")
        
        # Create temp directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create downloader with temp directory and progress callback
            def progress_callback(msg: str, level: str = "info"):
                add_job_log(job_id, msg, level)
                logger.info(f"[Job {job_id}] {msg}")
            
            downloader = AllDebridDownloader(
                ALLDEBRID_API_KEY, 
                download_dir=temp_dir,
                progress_callback=progress_callback
            )
            
            # Download all files at once using the proper method
            db.update_job_progress(job_id, progress=5, current_file=f"Downloading {len(links)} files...")
            add_job_log(job_id, f"Unlocking and downloading {len(links)} links...", "info")
            
            downloaded_files = downloader.download_links(links)
            downloaded_count = len(downloaded_files)
            
            add_job_log(job_id, f"Downloads complete ({downloaded_count}/{len(links)}). Processing music files...", "info")
            logger.info(f"[Job {job_id}] Downloads complete. Processing music files...")
            db.update_job_progress(job_id, progress=50, current_file="Processing music files...")
            
            # Only 7.0 surround preset available
            audio_preset = AudioPreset.SURROUND_7_0
            
            # Output format - always FLAC for 7.0 surround (proper audio container)
            out_format = 'flac'
            
            # Initialize organizer
            organizer = MusicLibraryOrganizer(
                musicbrainz_client_id=MUSICBRAINZ_CLIENT_ID,
                musicbrainz_client_secret=MUSICBRAINZ_CLIENT_SECRET,
                use_musicbrainz=True
            )
            
            # Process downloaded files
            results = organizer.organize_directory(
                temp_dir,
                MUSIC_OUTPUT_PATH,
                enhance_audio=True,
                audio_preset=audio_preset,
                output_format=out_format,
                lookup_metadata=True
            )
            
            db.update_job_status(job_id, status=JobStatus.COMPLETED)
            db.update_job_progress(
                job_id,
                progress=100,
                processed_files=results['success']
            )
            # Update total files separately
            with db.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.total_files = results['total']
                    session.commit()
            
            add_job_log(job_id, f"✅ Processed {results['success']}/{results['total']} music files", "success")
            
    except Exception as e:
        logger.error(f"Music AllDebrid error: {e}")
        db.update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")


@app.post("/api/v1/music/alldebrid")
async def download_music_from_alldebrid(request: MusicAllDebridRequest, background_tasks: BackgroundTasks):
    """Download music from AllDebrid, organize and enhance"""
    
    if not request.links:
        raise HTTPException(status_code=400, detail="No links provided")
    
    if not ALLDEBRID_API_KEY:
        raise HTTPException(status_code=400, detail="AllDebrid API key not configured")
    
    # Create job
    db = get_db()
    job = db.create_job(
        job_type=JobType.ORGANIZE,
        input_path=f"AllDebrid ({len(request.links)} links)",
        output_path=MUSIC_OUTPUT_PATH,
        language=request.preset
    )
    
    # Start background processing
    background_tasks.add_task(
        process_music_alldebrid_background,
        job.id,
        request.links,
        request.preset,
        request.output_format
    )
    
    return {
        "success": True,
        "message": f"Music download started (Job #{job.id})",
        "job_id": job.id
    }


# ============================================================================
# MULTI-SOURCE MUSIC DOWNLOADER API ENDPOINTS
# ============================================================================

class MusicDownloadRequest(BaseModel):
    """Request model for multi-source music download"""
    urls: List[str]
    source: str = "auto"  # auto, youtube_music, spotify, alldebrid
    audio_format: str = "original"  # original, flac, mp3, m4a, opus
    preset: str = "optimal"  # Audio enhancement preset
    enhance_audio: bool = True
    lookup_metadata: bool = True


def process_music_download_background(
    job_id: int, 
    urls: List[str], 
    source: str, 
    audio_format: str,
    preset: str,
    enhance_audio: bool,
    lookup_metadata: bool
):
    """Background task for multi-source music download and processing"""
    import tempfile
    import shutil
    import re
    from pathlib import Path
    from music_downloader import MusicDownloader, DownloadSource
    from music_organizer import MusicLibraryOrganizer, AudioPreset, AudioEnhancer
    
    db = get_db()
    
    # Mark job as running
    db.update_job_status(job_id, status=JobStatus.IN_PROGRESS)
    db.update_job_progress(job_id, progress=0, current_file="Initializing...")
    
    # Track download progress
    download_state = {"current_track": 0, "total_tracks": 0, "current_file": "", "last_update": 0, "current_progress": 5}
    
    try:
        add_job_log(job_id, f"Starting multi-source download of {len(urls)} URLs...", "info")
        logger.info(f"[Job {job_id}] Starting music download of {len(urls)} URLs")
        
        # Check if this is a playlist URL (YouTube or Spotify)
        is_playlist = any(
            'list=' in url or 
            'playlist' in url.lower() or
            'RDCLAK' in url  # YouTube Music radio/playlist
            for url in urls
        )
        
        add_job_log(job_id, f"🔍 Playlist detection: is_playlist={is_playlist}", "info")
        
        # Create temp directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Enhanced progress callback that updates job progress
            def progress_callback(msg: str, level: str = "info"):
                import time
                add_job_log(job_id, msg, level)
                logger.info(f"[Job {job_id}] {msg}")
                
                # Rate limit progress updates to avoid database spam
                current_time = time.time()
                if current_time - download_state["last_update"] < 0.5:
                    return
                download_state["last_update"] = current_time
                
                # Parse spotdl output patterns:
                # "Downloaded "Song Name": /path/to/file.flac"
                # "Processing: Song Name"
                # "Skipping Song Name (file already exists)"
                # "Found 50 songs in playlist"
                
                # Detect total tracks from playlist info
                total_match = re.search(r'Found (\d+) songs? in', msg, re.IGNORECASE)
                if total_match:
                    download_state["total_tracks"] = int(total_match.group(1))
                    db.update_job_progress(job_id, progress=8, current_file=f"Found {download_state['total_tracks']} tracks")
                    return
                
                # Track downloaded/skipped songs
                if 'Downloaded' in msg or 'Skipping' in msg:
                    download_state["current_track"] += 1
                    # Extract song name
                    song_match = re.search(r'(?:Downloaded|Skipping)\s+"?([^":]+)"?', msg)
                    if song_match:
                        download_state["current_file"] = song_match.group(1).strip()[:50]
                    
                    # Calculate progress (download phase is 5-50%)
                    total = download_state["total_tracks"] or 50  # Default estimate
                    progress = 5 + (download_state["current_track"] / total) * 45
                    progress = min(progress, 50)
                    
                    db.update_job_progress(
                        job_id, 
                        progress=progress, 
                        current_file=f"🎵 {download_state['current_track']}/{total}: {download_state['current_file']}",
                        processed_files=download_state["current_track"]
                    )
                    return
                
                # Parse yt-dlp style output (for YouTube Music)
                # "[download] Destination: /path/to/file.mp3"
                if 'Destination:' in msg or '[ExtractAudio]' in msg:
                    # Extract track number from filename pattern "XX - "
                    match = re.search(r'/(\d+)\s*-\s*[^/]+\.(flac|mp3|m4a|opus|webm)$', msg, re.IGNORECASE)
                    if match:
                        track_num = int(match.group(1))
                        if track_num > download_state["current_track"]:
                            download_state["current_track"] = track_num
                            filename_match = re.search(r'/([^/]+)\.(flac|mp3|m4a|opus|webm)$', msg, re.IGNORECASE)
                            if filename_match:
                                download_state["current_file"] = filename_match.group(1)[:50]
                            
                            total = download_state["total_tracks"] or max(track_num * 2, 50)
                            progress = 5 + (track_num / total) * 45
                            progress = min(progress, 50)
                            download_state["current_progress"] = progress
                            
                            db.update_job_progress(
                                job_id, 
                                progress=progress, 
                                current_file=f"⬇️ Track {track_num}: {download_state['current_file']}",
                                processed_files=track_num
                            )
                    return
                
                # Handle rate limit messages
                if 'rate limit' in msg.lower() or '429' in msg:
                    current_prog = download_state.get("current_progress", 10)
                    db.update_job_progress(job_id, progress=current_prog, current_file="⏳ Rate limited, waiting...")
                    return
                
                # Handle processing messages
                if 'Processing' in msg:
                    song_match = re.search(r'Processing:?\s*(.+)', msg)
                    if song_match:
                        current_prog = download_state.get("current_progress", 10)
                        db.update_job_progress(job_id, progress=current_prog, current_file=f"🔄 {song_match.group(1)[:50]}...")
            
            # Initialize downloader
            downloader = MusicDownloader(
                output_dir=temp_dir,
                alldebrid_api_key=ALLDEBRID_API_KEY,
                progress_callback=progress_callback
            )
            
            # Map source string to enum
            source_map = {
                'auto': DownloadSource.AUTO,
                'youtube_music': DownloadSource.YOUTUBE_MUSIC,
                'spotify': DownloadSource.SPOTIFY,
                'alldebrid': DownloadSource.ALLDEBRID,
            }
            download_source = source_map.get(source, DownloadSource.AUTO)
            
            db.update_job_progress(job_id, progress=5, current_file=f"Downloading from {source}...")
            add_job_log(job_id, f"Source: {source}, Format: {audio_format}", "info")
            
            # Download
            result = downloader.download(
                urls=urls,
                source=download_source,
                audio_format=audio_format
            )
            
            if not result.success and not result.files:
                raise Exception(f"Download failed: {', '.join(result.errors)}")
            
            add_job_log(job_id, f"Download complete. {result.message}", "info")
            db.update_job_progress(job_id, progress=50, current_file="Organizing music files...")
            
            detected_source = result.source if result.source != DownloadSource.AUTO else download_source
            add_job_log(job_id, f"🔍 Source: {detected_source.value}", "info")
            
            # For Spotify/YouTube downloads, files already have embedded metadata
            # Use that metadata to organize into Plex/Jellyfin structure
            # No need for external API lookups!
            
            # Only 7.0 surround preset available
            audio_preset = AudioPreset.SURROUND_7_0
            
            # Find all audio files
            audio_extensions = ['.flac', '.mp3', '.m4a', '.opus', '.ogg', '.wav', '.webm']
            audio_files = [f for f in Path(temp_dir).rglob('*') if f.is_file() and f.suffix.lower() in audio_extensions]
            
            add_job_log(job_id, f"📁 Found {len(audio_files)} audio files", "info")
            
            # Initialize enhancer for 7.0 surround upmix
            enhancer = None
            if enhance_audio:
                try:
                    enhancer = AudioEnhancer()
                    add_job_log(job_id, f"🔊 7.0 Surround upmix enabled (Polk T50 + Sony timbre-matching)", "info")
                except Exception as e:
                    add_job_log(job_id, f"⚠️ Audio enhancement unavailable: {e}", "warning")
            
            output_base = Path(MUSIC_OUTPUT_PATH)
            output_base.mkdir(parents=True, exist_ok=True)
            
            processed = 0
            total = len(audio_files)
            processed_files_list = []
            
            for idx, audio_file in enumerate(audio_files, 1):
                try:
                    # Preserve folder structure from spotdl (playlist/album name)
                    rel_path = audio_file.relative_to(temp_dir)
                    
                    # Output as .flac for 7.0 surround
                    if enhance_audio and enhancer:
                        output_path = output_base / rel_path.with_suffix('.flac')
                    else:
                        output_path = output_base / rel_path
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Get display name from filename
                    display_name = audio_file.stem
                    
                    # Process file (7.0 surround upmix or copy)
                    if enhance_audio and enhancer:
                        add_job_log(job_id, f"🔊 ({idx}/{total}) Upmixing to 7.0: {display_name}", "info")
                        success = enhancer.enhance_audio(str(audio_file), str(output_path), preset=audio_preset)
                        if not success or not output_path.exists() or output_path.stat().st_size == 0:
                            add_job_log(job_id, f"⚠️ Upmix failed, copying original FLAC", "warning")
                            output_path = output_base / rel_path  # Keep original extension
                            shutil.copy2(str(audio_file), str(output_path))
                    else:
                        add_job_log(job_id, f"📁 ({idx}/{total}) {display_name}", "info")
                        shutil.copy2(str(audio_file), str(output_path))
                    
                    processed_files_list.append(output_path)
                    processed += 1
                    
                    # Update progress (50-80% for processing)
                    progress = 50 + (idx / total) * 30
                    db.update_job_progress(job_id, progress=progress, current_file=display_name, processed_files=processed)
                    
                except Exception as e:
                    add_job_log(job_id, f"❌ Error processing {audio_file.name}: {e}", "error")
            
            # Transfer to NAS if configured (Lharmony for music)
            nas_transfer_success = False
            if LHARMONY_HOST and processed_files_list:
                add_job_log(job_id, f"📤 Transferring {len(processed_files_list)} files to NAS (Lharmony)...", "info")
                db.update_job_progress(job_id, progress=85, current_file="Transferring to NAS...")
                
                try:
                    from core.nas_transfer import NASTransfer
                    nas = NASTransfer()
                    
                    # Transfer each processed file to music folder
                    transferred = 0
                    for file_path in processed_files_list:
                        try:
                            rel_path = file_path.relative_to(output_base)
                            nas_dest = f"/music/{rel_path}"
                            
                            if nas.transfer_file(str(file_path), nas_dest, nas_name="lharmony"):
                                transferred += 1
                                add_job_log(job_id, f"✅ Transferred: {file_path.name}", "info")
                            else:
                                add_job_log(job_id, f"⚠️ Failed to transfer: {file_path.name}", "warning")
                        except Exception as e:
                            add_job_log(job_id, f"⚠️ Transfer error for {file_path.name}: {e}", "warning")
                    
                    nas_transfer_success = transferred > 0
                    add_job_log(job_id, f"📤 NAS transfer complete: {transferred}/{len(processed_files_list)} files", "info")
                    
                except Exception as e:
                    add_job_log(job_id, f"⚠️ NAS transfer failed: {e}", "warning")
            
            # Trigger Plex music library scan if transfer succeeded
            if nas_transfer_success and PLEX_ENABLED:
                add_job_log(job_id, f"🎬 Triggering Plex music library scan...", "info")
                db.update_job_progress(job_id, progress=95, current_file="Scanning Plex library...")
                
                try:
                    from core.plex_client import PlexClient
                    plex = PlexClient()
                    
                    # Scan music library
                    if plex.scan_library("Music"):
                        add_job_log(job_id, f"✅ Plex music library scan started", "success")
                    else:
                        add_job_log(job_id, f"⚠️ Plex scan may have failed", "warning")
                        
                except Exception as e:
                    add_job_log(job_id, f"⚠️ Plex scan error: {e}", "warning")
            
            # Complete
            db.update_job_status(job_id, status=JobStatus.COMPLETED)
            db.update_job_progress(job_id, progress=100, processed_files=processed)
            
            with db.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.total_files = total
                    session.commit()
            
            summary = f"✅ Processed {processed}/{total} files"
            if nas_transfer_success:
                summary += " → NAS (Lharmony)"
            add_job_log(job_id, summary, "success")
            
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Music download error: {e}\n{error_details}")
        db.update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")
        add_job_log(job_id, f"📋 Details: {error_details[:500]}", "error")


@app.post("/api/v1/music/download")
async def download_music(request: MusicDownloadRequest):
    """Download music from multiple sources (YouTube Music, Spotify, AllDebrid)"""
    
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    # Validate source-specific requirements
    if request.source == "alldebrid" and not ALLDEBRID_API_KEY:
        raise HTTPException(status_code=400, detail="AllDebrid API key not configured")
    
    # Create job
    db = get_db()
    source_label = request.source.replace('_', ' ').title()
    job = db.create_job(
        job_type=JobType.ORGANIZE,
        input_path=f"{source_label} ({len(request.urls)} URLs)",
        output_path=MUSIC_OUTPUT_PATH,
        language=request.preset
    )
    
    # Start background thread (not BackgroundTasks - those don't work well with blocking I/O)
    thread = threading.Thread(
        target=process_music_download_background,
        args=(
            job.id,
            request.urls,
            request.source,
            request.audio_format,
            request.preset,
            request.enhance_audio,
            request.lookup_metadata
        ),
        daemon=True
    )
    thread.start()
    
    return {
        "success": True,
        "message": f"Music download started (Job #{job.id})",
        "job_id": job.id,
        "source": request.source,
        "url_count": len(request.urls)
    }


@app.get("/api/v1/music/tools/status")
async def get_music_tools_status():
    """Check availability of music download tools"""
    try:
        from music_downloader import MusicDownloader
        
        downloader = MusicDownloader(
            output_dir="/tmp",
            alldebrid_api_key=ALLDEBRID_API_KEY
        )
        
        return {
            "success": True,
            "tools": {
                "yt-dlp": downloader.tools_available.get("yt-dlp", False),
                "spotdl": downloader.tools_available.get("spotdl", False),
                "ffmpeg": downloader.tools_available.get("ffmpeg", False),
            },
            "alldebrid_configured": bool(ALLDEBRID_API_KEY),
            "last_update": downloader.updater.last_update.isoformat() if downloader.updater.last_update else None
        }
    except Exception as e:
        logger.error(f"Error checking tools status: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools": {
                "yt-dlp": False,
                "spotdl": False,
                "ffmpeg": False,
            },
            "alldebrid_configured": bool(ALLDEBRID_API_KEY)
        }


@app.post("/api/v1/music/tools/update")
async def update_music_tools():
    """Manually trigger update of yt-dlp and spotdl"""
    try:
        from music_downloader import MusicDownloader
        
        downloader = MusicDownloader(
            output_dir="/tmp",
            alldebrid_api_key=ALLDEBRID_API_KEY
        )
        
        results = downloader.update_tools()
        
        return {
            "success": True,
            "message": "Tool update completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error updating tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NAS/SMB API ENDPOINTS
# ============================================================================

# NAS Configuration from environment
NAS_CONFIGS = {}

def init_nas_configs():
    """Initialize NAS configurations from environment variables or settings."""
    global NAS_CONFIGS
    
    # Helper to get config value from env or settings
    def get_config(env_key, settings_attr, default=""):
        val = os.getenv(env_key)
        if not val and USE_CONFIG and settings:
            val = getattr(settings, settings_attr, None)
        return val or default
    
    # Lharmony (Synology) - folder names: tv, malayalam tv shows
    lharmony_host = get_config("LHARMONY_HOST", "lharmony_host")
    if lharmony_host:
        lharmony_share = get_config("LHARMONY_SHARE", "lharmony_share", "data")
        NAS_CONFIGS["Lharmony"] = {
            "name": "Lharmony",
            "host": lharmony_host,
            "username": get_config("LHARMONY_USERNAME", "lharmony_username"),
            "password": get_config("LHARMONY_PASSWORD", "lharmony_password"),
            "share": lharmony_share,
            "media_path": get_config("LHARMONY_MEDIA_PATH", "lharmony_media_path", "/media"),
            "mount_point": f"/mnt/{lharmony_share}",
            "type": "synology",
            "categories": ["movies", "malayalam movies", "bollywood movies", "tv", "malayalam tv shows", "music"]
        }
    
    # Streamwave (Unraid) - folder names: tv-shows, malayalam-tv-shows
    streamwave_host = get_config("STREAMWAVE_HOST", "streamwave_host")
    if streamwave_host:
        streamwave_share = get_config("STREAMWAVE_SHARE", "streamwave_share", "Data-Streamwave")
        NAS_CONFIGS["Streamwave"] = {
            "name": "Streamwave",
            "host": streamwave_host,
            "username": get_config("STREAMWAVE_USERNAME", "streamwave_username"),
            "password": get_config("STREAMWAVE_PASSWORD", "streamwave_password"),
            "share": streamwave_share,
            "media_path": get_config("STREAMWAVE_MEDIA_PATH", "streamwave_media_path", "/media"),
            "mount_point": f"/mnt/{streamwave_share}",
            "type": "unraid",
            "categories": ["movies", "Malayalam Movies", "Bollywood Movies", "tv-shows", "malayalam-tv-shows"]
        }

# Initialize on module load
init_nas_configs()


class NASCopyRequest(BaseModel):
    nas_name: str
    source_path: str
    category: str
    move_file: bool = False


class NASTestRequest(BaseModel):
    nas_name: str


@app.get("/api/v1/nas/list")
async def list_nas():
    """List all configured NAS locations."""
    import subprocess
    
    nas_list = []
    
    for name, config in NAS_CONFIGS.items():
        # Check if NAS is reachable via ping
        is_connected = False
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", config["host"]],
                capture_output=True,
                timeout=5
            )
            is_connected = result.returncode == 0
        except Exception:
            pass
        
        nas_list.append({
            "name": config["name"],
            "host": config["host"],
            "type": config["type"],
            "mounted": is_connected,  # Use ping result
            "connected": is_connected,
            "status": "online" if is_connected else "offline",
            "mount_point": config["mount_point"],
            "categories": config["categories"]
        })
    
    return {
        "success": True,
        "nas_locations": nas_list,
        "count": len(nas_list)
    }


@app.get("/api/v1/nas/{nas_name}/status")
async def get_nas_status(nas_name: str):
    """Get status of a specific NAS."""
    import subprocess
    
    if nas_name not in NAS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"NAS not found: {nas_name}")
    
    config = NAS_CONFIGS[nas_name]
    
    # Check if NAS is reachable via ping
    is_connected = False
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", config["host"]],
            capture_output=True,
            timeout=5
        )
        is_connected = result.returncode == 0
    except Exception:
        pass
    
    # Build categories with status
    categories_status = {}
    for cat in config["categories"]:
        categories_status[cat] = {
            "path": f"{config['mount_point']}/{config['media_path'].lstrip('/')}/{cat}",
            "exists": is_connected  # Assume exists if connected
        }
    
    return {
        "success": True,
        "nas": {
            "name": config["name"],
            "host": config["host"],
            "type": config["type"],
            "mounted": is_connected,
            "connected": is_connected,
            "status": "online" if is_connected else "offline",
            "mount_point": config["mount_point"],
            "disk": None,
            "categories": categories_status,
            "categories_list": config["categories"]
        }
    }


@app.post("/api/v1/nas/test")
async def test_nas_connection(request: NASTestRequest):
    """Test NAS connection."""
    if request.nas_name not in NAS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"NAS not found: {request.nas_name}")
    
    config = NAS_CONFIGS[request.nas_name]
    mount_point = Path(config["mount_point"])
    
    # Check if mounted
    if not mount_point.exists() or not mount_point.is_mount():
        return {
            "success": False,
            "message": f"{request.nas_name} is not mounted. Mount it first using Finder or mount command.",
            "mounted": False
        }
    
    # Check media path
    media_base = mount_point / config["media_path"].lstrip('/')
    if not media_base.exists():
        return {
            "success": False,
            "message": f"Media path not found: {media_base}",
            "mounted": True
        }
    
    return {
        "success": True,
        "message": f"✅ {request.nas_name} is connected and ready!",
        "mounted": True,
        "media_path": str(media_base)
    }


@app.post("/api/v1/nas/copy")
async def copy_to_nas(request: NASCopyRequest, background_tasks: BackgroundTasks):
    """Copy a file to NAS."""
    if request.nas_name not in NAS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"NAS not found: {request.nas_name}")
    
    config = NAS_CONFIGS[request.nas_name]
    source_path = Path(request.source_path)
    
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Source file not found: {source_path}")
    
    # Check if NAS is mounted
    mount_point = Path(config["mount_point"])
    if not mount_point.exists() or not mount_point.is_mount():
        raise HTTPException(status_code=400, detail=f"{request.nas_name} is not mounted")
    
    # Validate category
    if request.category not in config["categories"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category '{request.category}' for {request.nas_name}. Valid: {config['categories']}"
        )
    
    # Build destination path
    media_base = mount_point / config["media_path"].lstrip('/')
    category_path = media_base / request.category
    
    # Create category folder if needed
    category_path.mkdir(parents=True, exist_ok=True)
    
    # For movies, create subfolder
    if "movie" in request.category.lower():
        folder_name = source_path.stem
        dest_folder = category_path / folder_name
        dest_folder.mkdir(exist_ok=True)
        dest_path = dest_folder / source_path.name
    else:
        dest_path = category_path / source_path.name
    
    try:
        if request.move_file:
            shutil.move(str(source_path), str(dest_path))
            action = "Moved"
        else:
            shutil.copy2(str(source_path), str(dest_path))
            action = "Copied"
        
        logger.info(f"✅ {action} {source_path.name} to {request.nas_name}/{request.category}")
        
        return {
            "success": True,
            "message": f"✅ {action} to {request.nas_name}/{request.category}",
            "destination": str(dest_path),
            "nas": request.nas_name,
            "category": request.category
        }
    except Exception as e:
        logger.error(f"❌ Copy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/nas/{nas_name}/categories")
async def get_nas_categories(nas_name: str):
    """Get available categories for a NAS."""
    if nas_name not in NAS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"NAS not found: {nas_name}")
    
    config = NAS_CONFIGS[nas_name]
    
    return {
        "success": True,
        "nas": nas_name,
        "categories": config["categories"]
    }


@app.get("/api/v1/nas/{nas_name}/browse/{category}")
async def browse_nas_category(nas_name: str, category: str, limit: int = Query(50, ge=1, le=200)):
    """Browse files in a NAS category."""
    if nas_name not in NAS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"NAS not found: {nas_name}")
    
    config = NAS_CONFIGS[nas_name]
    
    if category not in config["categories"]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    mount_point = Path(config["mount_point"])
    if not mount_point.exists() or not mount_point.is_mount():
        raise HTTPException(status_code=400, detail=f"{nas_name} is not mounted")
    
    category_path = mount_point / config["media_path"].lstrip('/') / category
    
    if not category_path.exists():
        return {
            "success": True,
            "nas": nas_name,
            "category": category,
            "path": str(category_path),
            "files": [],
            "count": 0
        }
    
    files = []
    for item in sorted(category_path.iterdir())[:limit]:
        if item.name.startswith('.'):
            continue
        
        file_info = {
            "name": item.name,
            "is_dir": item.is_dir(),
            "path": str(item)
        }
        
        if item.is_file():
            file_info["size_mb"] = round(item.stat().st_size / (1024 * 1024), 2)
        
        files.append(file_info)
    
    return {
        "success": True,
        "nas": nas_name,
        "category": category,
        "path": str(category_path),
        "files": files,
        "count": len(files)
    }


# ========== Plex Integration ==========

def get_plex_client():
    """Get Plex client instance if configured."""
    plex_url = os.environ.get('PLEX_SERVER_URL') or (settings.plex_server_url if USE_CONFIG and settings else None)
    plex_token = os.environ.get('PLEX_TOKEN') or (settings.plex_token if USE_CONFIG and settings else None)
    plex_enabled = os.environ.get('PLEX_ENABLED', '').lower() in ('true', '1', 'yes')
    
    if not plex_enabled and USE_CONFIG and settings:
        plex_enabled = getattr(settings, 'plex_enabled', False)
    
    if not plex_enabled or not plex_url or not plex_token:
        return None
    
    try:
        from core.plex_client import PlexClient
        return PlexClient(plex_url, plex_token)
    except ImportError as e:
        logger.warning(f"Plex client not available: {e}")
        return None


def get_tautulli_client():
    """Get Tautulli client instance if configured."""
    tautulli_url = os.environ.get('TAUTULLI_URL') or (settings.tautulli_url if USE_CONFIG and settings else None)
    tautulli_key = os.environ.get('TAUTULLI_API_KEY') or (settings.tautulli_api_key if USE_CONFIG and settings else None)
    tautulli_enabled = os.environ.get('TAUTULLI_ENABLED', '').lower() in ('true', '1', 'yes')
    
    if not tautulli_enabled and USE_CONFIG and settings:
        tautulli_enabled = getattr(settings, 'tautulli_enabled', False)
    
    if not tautulli_enabled or not tautulli_url or not tautulli_key:
        return None
    
    try:
        from core.tautulli_client import TautulliClient
        return TautulliClient(tautulli_url, tautulli_key)
    except ImportError as e:
        logger.warning(f"Tautulli client not available: {e}")
        return None


@app.get("/api/v1/plex/status")
async def get_plex_status():
    """Get Plex server status and connection info."""
    plex_url = os.environ.get('PLEX_SERVER_URL') or (settings.plex_server_url if USE_CONFIG and settings else None)
    plex_token = os.environ.get('PLEX_TOKEN') or (settings.plex_token if USE_CONFIG and settings else None)
    plex_enabled = os.environ.get('PLEX_ENABLED', '').lower() in ('true', '1', 'yes')
    if not plex_enabled and USE_CONFIG and settings:
        plex_enabled = getattr(settings, 'plex_enabled', False)
    
    plex = get_plex_client()
    if not plex:
        return {
            "success": False,
            "enabled": plex_enabled,
            "configured": bool(plex_url and plex_token),
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


@app.get("/api/v1/plex/libraries")
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
        logger.error(f"Failed to get libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/plex/scan/{library_key}")
async def scan_plex_library(library_key: str, path: str = None):
    """Trigger a Plex library scan."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        success = plex.scan_library(library_key, path)
        return {"success": success, "message": f"Scan triggered for library {library_key}"}
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/plex/recently-added")
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


# ========== Plex Poster/Art Upload ==========

class PosterUploadRequest(BaseModel):
    """Request model for poster upload"""
    rating_key: str
    poster_url: Optional[str] = None


class ArtUploadRequest(BaseModel):
    """Request model for background art upload"""
    rating_key: str
    art_url: Optional[str] = None


@app.post("/api/v1/plex/poster/url")
async def upload_poster_from_url(request: PosterUploadRequest):
    """Upload a custom poster from URL for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    if not request.poster_url:
        raise HTTPException(status_code=400, detail="poster_url is required")
    
    try:
        success = plex.upload_poster_from_url(request.rating_key, request.poster_url)
        if success:
            return {
                "success": True,
                "message": f"Poster uploaded successfully for item {request.rating_key}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload poster")
    except Exception as e:
        logger.error(f"Poster upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/plex/poster/upload/{rating_key}")
async def upload_poster_file(rating_key: str, file: UploadFile = File(...)):
    """Upload a custom poster file for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        # Read file content
        content = await file.read()
        
        success = plex.upload_poster(rating_key, content)
        if success:
            return {
                "success": True,
                "message": f"Poster uploaded successfully for item {rating_key}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload poster")
    except Exception as e:
        logger.error(f"Poster upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/plex/art/url")
async def upload_art_from_url(request: ArtUploadRequest):
    """Upload custom background art from URL for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    if not request.art_url:
        raise HTTPException(status_code=400, detail="art_url is required")
    
    try:
        success = plex.upload_art_from_url(request.rating_key, request.art_url)
        if success:
            return {
                "success": True,
                "message": f"Background art uploaded successfully for item {request.rating_key}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload art")
    except Exception as e:
        logger.error(f"Art upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/plex/art/upload/{rating_key}")
async def upload_art_file(rating_key: str, file: UploadFile = File(...)):
    """Upload custom background art file for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        content = await file.read()
        
        success = plex.upload_art(rating_key, content)
        if success:
            return {
                "success": True,
                "message": f"Background art uploaded successfully for item {rating_key}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload art")
    except Exception as e:
        logger.error(f"Art upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/plex/posters/{rating_key}")
async def get_plex_posters(rating_key: str):
    """Get available posters for a Plex item."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        posters = plex.get_posters(rating_key)
        return {
            "success": True,
            "posters": posters
        }
    except Exception as e:
        logger.error(f"Failed to get posters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/plex/scan/by-name/{library_name}")
async def scan_plex_library_by_name(library_name: str):
    """Trigger a Plex library scan by library name."""
    plex = get_plex_client()
    if not plex:
        raise HTTPException(status_code=503, detail="Plex not configured")
    
    try:
        success = plex.scan_library_by_name(library_name)
        if success:
            return {"success": True, "message": f"Scan triggered for library '{library_name}'"}
        else:
            raise HTTPException(status_code=404, detail=f"Library '{library_name}' not found")
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Tautulli Integration ==========

@app.get("/api/v1/tautulli/status")
async def get_tautulli_status():
    """Get Tautulli/Plex server status."""
    tautulli_url = os.environ.get('TAUTULLI_URL') or (settings.tautulli_url if USE_CONFIG and settings else None)
    tautulli_key = os.environ.get('TAUTULLI_API_KEY') or (settings.tautulli_api_key if USE_CONFIG and settings else None)
    tautulli_enabled = os.environ.get('TAUTULLI_ENABLED', '').lower() in ('true', '1', 'yes')
    if not tautulli_enabled and USE_CONFIG and settings:
        tautulli_enabled = getattr(settings, 'tautulli_enabled', False)
    
    tautulli = get_tautulli_client()
    if not tautulli:
        return {
            "success": False,
            "enabled": tautulli_enabled,
            "configured": bool(tautulli_url and tautulli_key),
            "message": "Tautulli not configured"
        }
    
    try:
        activity = tautulli.get_activity()
        return {
            "success": True,
            "enabled": True,
            "configured": True,
            "activity": activity
        }
    except Exception as e:
        logger.error(f"Tautulli status error: {e}")
        return {
            "success": False,
            "enabled": True,
            "configured": True,
            "error": str(e)
        }


@app.get("/api/v1/tautulli/libraries")
async def get_tautulli_libraries():
    """Get library statistics from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        libraries = tautulli.get_libraries()
        return {"success": True, "libraries": libraries}
    except Exception as e:
        logger.error(f"Failed to get Tautulli libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tautulli/stats/users")
async def get_tautulli_user_stats(days: int = 30):
    """Get user statistics from Tautulli."""
    tautulli = get_tautulli_client()
    if not tautulli:
        raise HTTPException(status_code=503, detail="Tautulli not configured")
    
    try:
        users = tautulli.get_user_stats(days=days)
        return {"success": True, "users": users}
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global tool updater instance for auto-updates
_tool_updater = None


def start_tool_auto_updates():
    """Start automatic tool updates on backend startup"""
    global _tool_updater
    try:
        from music_downloader import ToolUpdater
        _tool_updater = ToolUpdater()
        _tool_updater.start_auto_update()
        logger.info("🔄 Music tool auto-updater started (yt-dlp, spotdl)")
    except Exception as e:
        logger.warning(f"⚠️ Could not start tool auto-updater: {e}")


if __name__ == '__main__':
    # Use settings if available, otherwise use defaults
    if USE_CONFIG and settings:
        app_name = settings.app_name
        api_host = settings.api_host
        api_port = settings.api_port
        log_level = settings.log_level.lower()
        gpu_enabled = settings.gpu_service_enabled
    else:
        app_name = "Media Organizer Pro"
        api_host = "0.0.0.0"
        api_port = 8000
        log_level = "info"
        gpu_enabled = True
    
    logger.info(f"🚀 Starting {app_name} on http://{api_host}:{api_port}")
    logger.info(f"🎮 GPU Service: {GPU_SERVICE_URL}")
    logger.info(f"📁 Media path: {DEFAULT_MEDIA_PATH}")
    logger.info(f"🎵 Music path: {MUSIC_OUTPUT_PATH}")
    
    # Start music tool auto-updater (yt-dlp, spotdl)
    start_tool_auto_updates()
    
    # Check GPU service
    if gpu_enabled:
        try:
            gpu_check = requests.get(f"{GPU_SERVICE_URL}/health", timeout=2)
            if gpu_check.json().get('gpu_available'):
                logger.info("✅ GPU Service connected - VideoToolbox available")
            else:
                logger.warning("⚠️  GPU Service connected but VideoToolbox not available")
        except:
            logger.warning("⚠️  GPU Service not running - start it first!")
    
    uvicorn.run(
        app,
        host=api_host,
        port=api_port,
        log_level=log_level
    )
