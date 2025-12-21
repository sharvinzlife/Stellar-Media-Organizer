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
        return env_path
    
    # Default to /Users/sharvin/Documents/Processed
    return "/Users/sharvin/Documents/Processed"


DEFAULT_MEDIA_PATH = get_default_media_path()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).parent / "uploads"))).expanduser().resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# AllDebrid API key (set via environment variable)
ALLDEBRID_API_KEY = os.getenv("ALLDEBRID_API_KEY", "")


# Pydantic Models
class VideoConversionRequest(BaseModel):
    directory_path: str
    output_path: Optional[str] = None
    preset: str = 'hevc_best'


class AllDebridRequest(BaseModel):
    links: List[str]
    output_path: Optional[str] = None
    language: Optional[str] = 'malayalam'
    download_only: Optional[bool] = False


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
    output_path: Optional[str] = '/Users/sharvin/Documents/Processed'
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


def run_alldebrid_download(job_id: int, links: List[str], output_path: str, language: str, download_only: bool):
    """Run AllDebrid download in background thread."""
    db = get_db()
    
    try:
        from alldebrid_downloader import AllDebridDownloader
        
        api_key = ALLDEBRID_API_KEY
        if not api_key:
            add_job_log(job_id, "❌ AllDebrid API key not configured!", "error")
            db.update_job_status(job_id, JobStatus.FAILED, error_message="API key not configured")
            return
        
        # Progress callback to update job logs in real-time
        def progress_callback(message: str, level: str = "info"):
            add_job_log(job_id, message, level)
        
        add_job_log(job_id, f"🚀 Starting AllDebrid download of {len(links)} links...", "info")
        db.update_job_progress(job_id, 5.0, current_file=f"Unlocking {len(links)} links...")
        
        downloader = AllDebridDownloader(api_key, progress_callback=progress_callback)
        
        if download_only:
            downloaded = downloader.download_links(links)
            add_job_log(job_id, f"✅ Downloaded {len(downloaded)} files", "success")
            db.update_job_status(job_id, JobStatus.COMPLETED)
            db.update_job_progress(job_id, 100.0, processed_files=len(downloaded))
        else:
            results = downloader.download_and_organize(links, output_path, language)
            add_job_log(job_id, f"✅ Complete! Downloaded: {len(results['downloaded'])}, Organized: {len(results['organized'])}, Filtered: {len(results['filtered'])}", "success")
            db.update_job_status(job_id, JobStatus.COMPLETED)
            db.update_job_progress(job_id, 100.0, processed_files=len(results['downloaded']))
            
    except Exception as e:
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")
        db.update_job_status(job_id, JobStatus.FAILED, error_message=str(e))


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
    
    # Start background thread
    thread = threading.Thread(
        target=run_alldebrid_download,
        args=(job.id, request.links, request.output_path or DEFAULT_MEDIA_PATH, request.language, request.download_only),
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
    output_path: str = "/Users/sharvin/Documents/Music"
    preset: str = "optimal"  # optimal, clarity, bass_boost, warm, bright, flat
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
MUSIC_OUTPUT_PATH = os.getenv("MUSIC_OUTPUT_PATH", "/Users/sharvin/Documents/Music")


def process_music_background(job_id: int, request: MusicProcessRequest):
    """Background task for music processing"""
    from music_organizer import MusicLibraryOrganizer, AudioPreset
    
    db = get_db()
    
    try:
        # Map preset string to enum
        preset_map = {
            'optimal': AudioPreset.OPTIMAL,
            'clarity': AudioPreset.CLARITY,
            'bass_boost': AudioPreset.BASS_BOOST,
            'warm': AudioPreset.WARM,
            'bright': AudioPreset.BRIGHT,
            'flat': AudioPreset.FLAT,
        }
        preset = preset_map.get(request.preset, AudioPreset.OPTIMAL)
        
        # Output format
        output_format = None if request.output_format == 'keep' else request.output_format
        
        add_job_log(job_id, f"Initializing Music Organizer...", "info")
        
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
                db.update_job(job_id, status=JobStatus.COMPLETED, progress=100, processed_files=1, total_files=1)
                add_job_log(job_id, f"✅ Organized: {result}", "success")
            else:
                db.update_job(job_id, status=JobStatus.FAILED, error_message="Failed to process file")
                add_job_log(job_id, "❌ Failed to process file", "error")
        else:
            # Directory
            results = organizer.organize_directory(
                str(input_path),
                request.output_path,
                enhance_audio=request.enhance_audio,
                audio_preset=preset,
                output_format=output_format,
                lookup_metadata=request.lookup_metadata
            )
            
            db.update_job(
                job_id,
                status=JobStatus.COMPLETED if results['failed'] == 0 else JobStatus.COMPLETED,
                progress=100,
                processed_files=results['success'],
                total_files=results['total']
            )
            
            add_job_log(job_id, f"✅ Processed {results['success']}/{results['total']} files", "success")
            if results['errors']:
                for err in results['errors'][:5]:
                    add_job_log(job_id, f"⚠️ {err}", "warning")
                    
    except Exception as e:
        logger.error(f"Music processing error: {e}")
        db.update_job(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")


@app.get("/api/v1/music/status")
async def get_music_status():
    """Check if Music Organizer is configured"""
    try:
        from music_organizer import MUSICBRAINZ_AVAILABLE, MUTAGEN_AVAILABLE
        
        return {
            "configured": True,
            "musicbrainz_available": MUSICBRAINZ_AVAILABLE,
            "musicbrainz_configured": bool(MUSICBRAINZ_CLIENT_ID),
            "mutagen_available": MUTAGEN_AVAILABLE,
            "default_output": MUSIC_OUTPUT_PATH
        }
    except ImportError:
        return {
            "configured": False,
            "musicbrainz_available": False,
            "musicbrainz_configured": False,
            "mutagen_available": False,
            "default_output": MUSIC_OUTPUT_PATH
        }


@app.get("/api/v1/music/presets")
async def get_music_presets():
    """Get available audio enhancement presets"""
    return {
        "presets": [
            {
                "id": "optimal",
                "name": "Optimal",
                "description": "Balanced enhancement - bass +2dB, treble +2.5dB, clarity boost",
                "recommended": True
            },
            {
                "id": "clarity",
                "name": "Clarity",
                "description": "Focus on vocals/instruments - high-mid boost, harmonic enhancement"
            },
            {
                "id": "bass_boost",
                "name": "Bass Boost",
                "description": "Enhanced low frequencies - +5dB bass"
            },
            {
                "id": "warm",
                "name": "Warm",
                "description": "Fuller, warmer sound profile"
            },
            {
                "id": "bright",
                "name": "Bright",
                "description": "Crisp, enhanced highs"
            },
            {
                "id": "flat",
                "name": "Flat",
                "description": "No EQ - just EBU R128 loudness normalization"
            }
        ],
        "formats": [
            {"id": "keep", "name": "Keep Original", "description": "Preserve original format"},
            {"id": "flac", "name": "FLAC", "description": "Lossless compression"},
            {"id": "mp3", "name": "MP3", "description": "VBR highest quality"},
            {"id": "m4a", "name": "M4A/AAC", "description": "320kbps AAC"}
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
            
            # Map preset string to enum
            preset_map = {
                'optimal': AudioPreset.OPTIMAL,
                'clarity': AudioPreset.CLARITY,
                'bass_boost': AudioPreset.BASS_BOOST,
                'warm': AudioPreset.WARM,
                'bright': AudioPreset.BRIGHT,
                'flat': AudioPreset.FLAT,
            }
            audio_preset = preset_map.get(preset, AudioPreset.OPTIMAL)
            
            # Output format
            out_format = None if output_format == 'keep' else output_format
            
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
    download_state = {"current_track": 0, "total_tracks": 0, "current_file": ""}
    
    try:
        add_job_log(job_id, f"Starting multi-source download of {len(urls)} URLs...", "info")
        logger.info(f"[Job {job_id}] Starting music download of {len(urls)} URLs")
        
        # Check if this is a playlist URL (YouTube or Spotify)
        is_playlist = any('list=' in url or 'playlist' in url.lower() for url in urls)
        
        # Create temp directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Enhanced progress callback that updates job progress
            def progress_callback(msg: str, level: str = "info"):
                add_job_log(job_id, msg, level)
                logger.info(f"[Job {job_id}] {msg}")
                
                # Parse track number from destination paths like "/path/PlaylistName/42 - Artist - Title.mp3"
                if 'Destination:' in msg or '[ExtractAudio]' in msg:
                    # Extract track number from filename pattern "XX - "
                    match = re.search(r'/(\d+)\s*-\s*[^/]+\.(flac|mp3|m4a|opus|webm)$', msg, re.IGNORECASE)
                    if match:
                        track_num = int(match.group(1))
                        if track_num > download_state["current_track"]:
                            download_state["current_track"] = track_num
                            # Extract filename
                            filename_match = re.search(r'/([^/]+)\.(flac|mp3|m4a|opus|webm)$', msg, re.IGNORECASE)
                            if filename_match:
                                download_state["current_file"] = filename_match.group(1)
                            
                            # Update progress (download phase is 5-50%)
                            # Estimate total tracks if we don't know yet
                            if download_state["total_tracks"] == 0:
                                download_state["total_tracks"] = max(track_num * 2, 50)  # Estimate
                            
                            progress = 5 + (track_num / download_state["total_tracks"]) * 45
                            progress = min(progress, 50)  # Cap at 50% for download phase
                            
                            db.update_job_progress(
                                job_id, 
                                progress=progress, 
                                current_file=f"Downloading track {track_num}: {download_state['current_file'][:50]}...",
                                processed_files=track_num
                            )
            
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
            db.update_job_progress(job_id, progress=50, current_file="Processing music files...")
            
            # For playlists from YouTube/Spotify: preserve folder structure, just enhance audio
            # For AllDebrid or single tracks: use full music organizer with MusicBrainz
            detected_source = result.source if result.source != DownloadSource.AUTO else download_source
            
            if is_playlist and detected_source in [DownloadSource.YOUTUBE_MUSIC, DownloadSource.SPOTIFY]:
                add_job_log(job_id, "📁 Playlist detected - preserving folder structure", "info")
                
                # Map preset string to enum
                preset_map = {
                    'optimal': AudioPreset.OPTIMAL,
                    'clarity': AudioPreset.CLARITY,
                    'bass_boost': AudioPreset.BASS_BOOST,
                    'warm': AudioPreset.WARM,
                    'bright': AudioPreset.BRIGHT,
                    'flat': AudioPreset.FLAT,
                }
                audio_preset = preset_map.get(preset, AudioPreset.OPTIMAL)
                
                # Process files while preserving structure
                output_base = Path(MUSIC_OUTPUT_PATH)
                output_base.mkdir(parents=True, exist_ok=True)
                
                processed = 0
                total = 0
                
                # Initialize audio enhancer if needed
                enhancer = AudioEnhancer() if enhance_audio else None
                
                for item in Path(temp_dir).rglob('*'):
                    if item.is_file() and item.suffix.lower() in ['.flac', '.mp3', '.m4a', '.opus', '.ogg', '.wav']:
                        total += 1
                        # Preserve relative path structure
                        rel_path = item.relative_to(temp_dir)
                        dest_path = output_base / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        try:
                            if enhance_audio and enhancer:
                                add_job_log(job_id, f"🎵 Enhancing: {item.name}", "info")
                                enhancer.enhance_audio(str(item), str(dest_path), audio_preset)
                            else:
                                shutil.copy2(str(item), str(dest_path))
                            processed += 1
                        except Exception as e:
                            add_job_log(job_id, f"⚠️ Error processing {item.name}: {e}", "warning")
                            # Still copy the file even if enhancement fails
                            shutil.copy2(str(item), str(dest_path))
                            processed += 1
                
                db.update_job_status(job_id, status=JobStatus.COMPLETED)
                db.update_job_progress(job_id, progress=100, processed_files=processed)
                
                with db.get_session() as session:
                    job = session.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.total_files = total
                        session.commit()
                
                add_job_log(job_id, f"✅ Processed {processed}/{total} music files (playlist structure preserved)", "success")
            
            elif enhance_audio or lookup_metadata:
                # Use full music organizer for AllDebrid or single tracks
                preset_map = {
                    'optimal': AudioPreset.OPTIMAL,
                    'clarity': AudioPreset.CLARITY,
                    'bass_boost': AudioPreset.BASS_BOOST,
                    'warm': AudioPreset.WARM,
                    'bright': AudioPreset.BRIGHT,
                    'flat': AudioPreset.FLAT,
                }
                audio_preset = preset_map.get(preset, AudioPreset.OPTIMAL)
                
                # Initialize organizer
                organizer = MusicLibraryOrganizer(
                    musicbrainz_client_id=MUSICBRAINZ_CLIENT_ID,
                    musicbrainz_client_secret=MUSICBRAINZ_CLIENT_SECRET,
                    use_musicbrainz=lookup_metadata
                )
                
                # Process downloaded files
                results = organizer.organize_directory(
                    temp_dir,
                    MUSIC_OUTPUT_PATH,
                    enhance_audio=enhance_audio,
                    audio_preset=audio_preset,
                    output_format=None,  # Keep format from download
                    lookup_metadata=lookup_metadata
                )
                
                db.update_job_status(job_id, status=JobStatus.COMPLETED)
                db.update_job_progress(job_id, progress=100, processed_files=results['success'])
                
                with db.get_session() as session:
                    job = session.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.total_files = results['total']
                        session.commit()
                
                add_job_log(job_id, f"✅ Processed {results['success']}/{results['total']} music files", "success")
            else:
                # Just move files to output
                
                output_path = Path(MUSIC_OUTPUT_PATH)
                output_path.mkdir(parents=True, exist_ok=True)
                
                moved = 0
                for item in Path(temp_dir).rglob('*'):
                    if item.is_file():
                        dest = output_path / item.name
                        shutil.move(str(item), str(dest))
                        moved += 1
                
                db.update_job_status(job_id, status=JobStatus.COMPLETED)
                db.update_job_progress(job_id, progress=100, processed_files=moved)
                add_job_log(job_id, f"✅ Moved {moved} files to {MUSIC_OUTPUT_PATH}", "success")
                
    except Exception as e:
        logger.error(f"Music download error: {e}")
        db.update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
        add_job_log(job_id, f"❌ Error: {str(e)}", "error")


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
