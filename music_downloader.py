#!/usr/bin/env python3
"""
Multi-Source Music Downloader
Supports: AllDebrid, YouTube Music (yt-dlp), Spotify (spotdl)
Auto-updates yt-dlp and spotdl on startup and every 6 hours
"""

import os
import re
import subprocess
import logging
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DownloadSource(Enum):
    """Supported download sources"""
    ALLDEBRID = "alldebrid"
    YOUTUBE_MUSIC = "youtube_music"
    SPOTIFY = "spotify"
    AUTO = "auto"  # Auto-detect from URL


@dataclass
class DownloadResult:
    """Result of a download operation"""
    success: bool
    source: DownloadSource
    files: List[str]
    message: str
    errors: List[str]


class ToolUpdater:
    """Manages auto-updates for yt-dlp and spotdl"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.last_update = None
        self.update_interval = timedelta(hours=6)
        self._update_thread = None
        self._stop_event = threading.Event()
    
    def check_and_update(self, force: bool = False) -> Dict[str, bool]:
        """Check and update tools if needed"""
        results = {"yt-dlp": False, "spotdl": False}
        
        now = datetime.now()
        if not force and self.last_update and (now - self.last_update) < self.update_interval:
            logger.info("Tools recently updated, skipping...")
            return results
        
        logger.info("🔄 Checking for tool updates...")
        
        # Update yt-dlp
        try:
            result = subprocess.run(
                ['pip', 'install', '--upgrade', 'yt-dlp'],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                results["yt-dlp"] = True
                logger.info("✅ yt-dlp updated successfully")
            else:
                logger.warning(f"⚠️ yt-dlp update failed: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ yt-dlp update error: {e}")
        
        # Update spotdl
        try:
            result = subprocess.run(
                ['pip', 'install', '--upgrade', 'spotdl'],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                results["spotdl"] = True
                logger.info("✅ spotdl updated successfully")
            else:
                logger.warning(f"⚠️ spotdl update failed: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ spotdl update error: {e}")
        
        self.last_update = now
        return results
    
    def start_auto_update(self):
        """Start background auto-update thread"""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
        self._update_thread.start()
        logger.info("🔄 Auto-update thread started (every 6 hours)")
    
    def stop_auto_update(self):
        """Stop background auto-update thread"""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=5)
    
    def _auto_update_loop(self):
        """Background loop for auto-updates"""
        # Initial update on start
        self.check_and_update(force=True)
        
        while not self._stop_event.is_set():
            # Wait for 6 hours or until stopped
            self._stop_event.wait(timeout=6 * 60 * 60)
            if not self._stop_event.is_set():
                self.check_and_update(force=True)


class MusicDownloader:
    """Multi-source music downloader"""
    
    # URL patterns for auto-detection
    YOUTUBE_PATTERNS = [
        r'youtube\.com/watch',
        r'youtube\.com/playlist',
        r'youtu\.be/',
        r'music\.youtube\.com/watch',
        r'music\.youtube\.com/playlist',
    ]
    
    SPOTIFY_PATTERNS = [
        r'open\.spotify\.com/track',
        r'open\.spotify\.com/album',
        r'open\.spotify\.com/playlist',
        r'spotify\.com/track',
        r'spotify\.com/album',
        r'spotify\.com/playlist',
    ]
    
    ALLDEBRID_PATTERNS = [
        r'alldebrid\.com/f/',
    ]
    
    def __init__(
        self,
        output_dir: str = "",
        alldebrid_api_key: str = "",
        progress_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.alldebrid_api_key = alldebrid_api_key or os.getenv('ALLDEBRID_API_KEY', '')
        self.progress_callback = progress_callback or (lambda msg, level: None)
        
        # Initialize tool updater
        self.updater = ToolUpdater()
        
        # Check tools availability
        self._check_tools()
    
    def _log(self, message: str, level: str = "info"):
        """Log message and call progress callback"""
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
        self.progress_callback(message, level)
    
    def _get_venv_bin_paths(self) -> List[Path]:
        """Get possible paths to virtual environment bin directories"""
        import sys
        paths = []
        
        # 1. Current Python executable's directory (if running in venv)
        python_path = Path(sys.executable)
        paths.append(python_path.parent)
        
        # 2. Project's .venv directory (relative to this file)
        project_root = Path(__file__).parent
        venv_bin = project_root / '.venv' / 'bin'
        if venv_bin.exists():
            paths.append(venv_bin)
        
        # 3. Check VIRTUAL_ENV environment variable
        virtual_env = os.environ.get('VIRTUAL_ENV')
        if virtual_env:
            venv_path = Path(virtual_env) / 'bin'
            if venv_path.exists():
                paths.append(venv_path)
        
        return paths
    
    def _check_tools(self):
        """Check if required tools are installed"""
        self.tools_available = {
            "yt-dlp": False,
            "spotdl": False,
            "ffmpeg": False,
        }
        
        # Get all possible venv bin paths
        venv_bins = self._get_venv_bin_paths()
        
        # Build list of paths to check for each tool
        yt_dlp_paths = []
        spotdl_paths = []
        for venv_bin in venv_bins:
            yt_dlp_paths.append(venv_bin / 'yt-dlp')
            spotdl_paths.append(venv_bin / 'spotdl')
        # Add system PATH as fallback
        yt_dlp_paths.append(Path('yt-dlp'))
        spotdl_paths.append(Path('spotdl'))
        
        # Check yt-dlp
        for yt_dlp_path in yt_dlp_paths:
            try:
                result = subprocess.run(
                    [str(yt_dlp_path), '--version'], 
                    capture_output=True, 
                    check=True,
                    timeout=10
                )
                self.tools_available["yt-dlp"] = True
                self._yt_dlp_path = str(yt_dlp_path)
                logger.info(f"✅ Found yt-dlp at: {yt_dlp_path}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not self.tools_available["yt-dlp"]:
            self._log("⚠️ yt-dlp not found. Install with: uv pip install yt-dlp", "warning")
            self._yt_dlp_path = 'yt-dlp'
        
        # Check spotdl
        for spotdl_path in spotdl_paths:
            try:
                result = subprocess.run(
                    [str(spotdl_path), '--version'], 
                    capture_output=True, 
                    check=True,
                    timeout=10
                )
                self.tools_available["spotdl"] = True
                self._spotdl_path = str(spotdl_path)
                logger.info(f"✅ Found spotdl at: {spotdl_path}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not self.tools_available["spotdl"]:
            self._log("⚠️ spotdl not found. Install with: uv pip install spotdl", "warning")
            self._spotdl_path = 'spotdl'
        
        # Check ffmpeg (system tool)
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=10)
            self.tools_available["ffmpeg"] = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._log("⚠️ ffmpeg not found. Install with: brew install ffmpeg", "warning")
    
    def detect_source(self, url: str) -> DownloadSource:
        """Auto-detect download source from URL"""
        url_lower = url.lower()
        
        for pattern in self.YOUTUBE_PATTERNS:
            if re.search(pattern, url_lower):
                return DownloadSource.YOUTUBE_MUSIC
        
        for pattern in self.SPOTIFY_PATTERNS:
            if re.search(pattern, url_lower):
                return DownloadSource.SPOTIFY
        
        for pattern in self.ALLDEBRID_PATTERNS:
            if re.search(pattern, url_lower):
                return DownloadSource.ALLDEBRID
        
        return DownloadSource.AUTO
    
    def start_auto_updates(self):
        """Start automatic tool updates"""
        self.updater.start_auto_update()
    
    def update_tools(self) -> Dict[str, bool]:
        """Manually trigger tool updates"""
        return self.updater.check_and_update(force=True)
    
    def download(
        self,
        urls: List[str],
        source: DownloadSource = DownloadSource.AUTO,
        audio_format: str = "flac",
        audio_quality: str = "0",  # Best quality
    ) -> DownloadResult:
        """
        Download music from URLs
        
        Args:
            urls: List of URLs to download
            source: Download source (auto-detect if AUTO)
            audio_format: Output format (flac, mp3, m4a)
            audio_quality: Quality setting
        
        Returns:
            DownloadResult with status and file list
        """
        if not urls:
            return DownloadResult(False, source, [], "No URLs provided", [])
        
        # Group URLs by source
        grouped = self._group_urls_by_source(urls, source)
        
        all_files = []
        all_errors = []
        
        # Process each source
        for src, src_urls in grouped.items():
            if not src_urls:
                continue
            
            self._log(f"📥 Processing {len(src_urls)} {src.value} URLs...")
            
            if src == DownloadSource.YOUTUBE_MUSIC:
                result = self._download_youtube(src_urls, audio_format, audio_quality)
            elif src == DownloadSource.SPOTIFY:
                result = self._download_spotify(src_urls, audio_format)
            elif src == DownloadSource.ALLDEBRID:
                result = self._download_alldebrid(src_urls)
            else:
                all_errors.append(f"Unknown source for URLs: {src_urls}")
                continue
            
            all_files.extend(result.files)
            all_errors.extend(result.errors)
        
        success = len(all_files) > 0
        message = f"Downloaded {len(all_files)} files" if success else "No files downloaded"
        
        return DownloadResult(
            success=success,
            source=source,
            files=all_files,
            message=message,
            errors=all_errors
        )
    
    def _group_urls_by_source(
        self,
        urls: List[str],
        default_source: DownloadSource
    ) -> Dict[DownloadSource, List[str]]:
        """Group URLs by their detected source"""
        grouped = {
            DownloadSource.YOUTUBE_MUSIC: [],
            DownloadSource.SPOTIFY: [],
            DownloadSource.ALLDEBRID: [],
        }
        
        for url in urls:
            if default_source != DownloadSource.AUTO:
                grouped[default_source].append(url)
            else:
                detected = self.detect_source(url)
                if detected in grouped:
                    grouped[detected].append(url)
                else:
                    self._log(f"⚠️ Could not detect source for: {url}", "warning")
        
        return grouped
    
    def _download_youtube(
        self,
        urls: List[str],
        audio_format: str = "flac",
        audio_quality: str = "0"
    ) -> DownloadResult:
        """Download from YouTube/YouTube Music using yt-dlp"""
        if not self.tools_available["yt-dlp"]:
            return DownloadResult(False, DownloadSource.YOUTUBE_MUSIC, [], 
                                "yt-dlp not installed", ["Install with: pip install yt-dlp"])
        
        files = []
        errors = []
        
        # Log the output directory being used
        self._log(f"📂 Output directory: {self.output_dir}")
        
        for url in urls:
            self._log(f"🎵 Downloading from YouTube: {url[:60]}...")
            
            # Check if it's a playlist URL
            is_playlist = 'list=' in url or 'playlist' in url.lower()
            self._log(f"   Is playlist: {is_playlist}")
            
            if is_playlist:
                # For playlists: ALL tracks go in ONE folder named after the playlist
                # Format: PlaylistName/001 - Artist - Title.ext
                output_template = str(self.output_dir / "%(playlist_title)s" / "%(playlist_index)03d - %(artist,channel,uploader|Unknown)s - %(title)s.%(ext)s")
            else:
                # For single videos: just Artist - Title
                output_template = str(self.output_dir / "%(artist,channel,uploader|Unknown)s - %(title)s.%(ext)s")
            
            self._log(f"   Output template: {output_template}")
            
            # Build yt-dlp command (use venv path if available)
            cmd = [self._yt_dlp_path, '--extract-audio']
            
            # Audio format (skip if 'original' to keep best quality)
            if audio_format != 'original':
                cmd.extend(['--audio-format', audio_format])
            
            cmd.extend([
                '--audio-quality', audio_quality,
                '--embed-thumbnail',
                '--embed-metadata',
                '--add-metadata',
            ])
            
            # Playlist-specific options
            if is_playlist:
                cmd.extend([
                    # Set album = playlist title, album_artist = playlist title
                    '--parse-metadata', 'playlist_title:%(album)s',
                    '--parse-metadata', 'playlist_title:%(album_artist)s',
                    '--parse-metadata', 'playlist_index:%(track_number)s',
                    '--yes-playlist',
                ])
            else:
                cmd.append('--no-playlist')
            
            cmd.extend([
                '--output', output_template,
                '--progress',
                '--newline',  # Better progress parsing
                url
            ])
            
            self._log(f"   Command: {' '.join(cmd[:10])}...")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                playlist_dir = None
                downloaded_files = []
                
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Log progress
                    if '[download]' in line and '%' in line:
                        self._log(f"   {line}")
                    elif 'Destination:' in line:
                        self._log(f"   📁 {line}")
                        # Track the file path
                        import re
                        match = re.search(r'Destination:\s*(.+)', line)
                        if match:
                            file_path = Path(match.group(1).strip())
                            downloaded_files.append(str(file_path))
                            if is_playlist and not playlist_dir:
                                playlist_dir = file_path.parent
                    elif '[ExtractAudio]' in line:
                        self._log(f"   🎵 {line}")
                        # Also track extracted audio files
                        import re
                        match = re.search(r'Destination:\s*(.+)', line)
                        if match:
                            file_path = Path(match.group(1).strip())
                            downloaded_files.append(str(file_path))
                            if is_playlist and not playlist_dir:
                                playlist_dir = file_path.parent
                    elif 'error' in line.lower():
                        self._log(f"   ⚠️ {line}", "warning")
                
                process.wait()
                
                if process.returncode == 0:
                    self._log(f"✅ YouTube download complete: {url[:40]}...", "success")
                    
                    # Handle playlist cover image - download separately
                    if is_playlist and playlist_dir and playlist_dir.exists():
                        self._log(f"   📁 Playlist folder: {playlist_dir}")
                        cover_path = playlist_dir / 'cover.jpg'
                        
                        if not cover_path.exists():
                            # Try to download playlist thumbnail using yt-dlp
                            try:
                                self._log(f"   🖼️ Fetching playlist cover...")
                                # Get playlist info to extract thumbnail URL
                                info_cmd = [
                                    self._yt_dlp_path, '--flat-playlist', '--dump-single-json',
                                    '--no-download', url
                                ]
                                info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                                if info_result.returncode == 0:
                                    import json
                                    playlist_info = json.loads(info_result.stdout)
                                    
                                    # Get thumbnail URL (try multiple fields)
                                    thumb_url = None
                                    if 'thumbnails' in playlist_info and playlist_info['thumbnails']:
                                        # Get highest quality thumbnail
                                        thumbs = sorted(playlist_info['thumbnails'], 
                                                       key=lambda x: x.get('width', 0) * x.get('height', 0), 
                                                       reverse=True)
                                        thumb_url = thumbs[0].get('url')
                                    elif 'thumbnail' in playlist_info:
                                        thumb_url = playlist_info['thumbnail']
                                    
                                    if thumb_url:
                                        # Download the thumbnail
                                        import requests
                                        response = requests.get(thumb_url, timeout=15)
                                        if response.status_code == 200:
                                            with open(cover_path, 'wb') as f:
                                                f.write(response.content)
                                            self._log(f"   🖼️ Saved playlist cover: cover.jpg", "success")
                                        else:
                                            self._log(f"   ⚠️ Could not download cover (HTTP {response.status_code})", "warning")
                                    else:
                                        self._log(f"   ⚠️ No playlist thumbnail found", "warning")
                            except Exception as e:
                                self._log(f"   ⚠️ Could not fetch playlist cover: {e}", "warning")
                    
                    files.extend(downloaded_files)
                else:
                    error_msg = f"yt-dlp failed for {url} (exit code: {process.returncode})"
                    errors.append(error_msg)
                    self._log(f"❌ {error_msg}", "error")
                    
            except Exception as e:
                error_msg = f"YouTube download error: {str(e)}"
                errors.append(error_msg)
                self._log(f"❌ {error_msg}", "error")
        
        return DownloadResult(
            success=len(files) > 0,
            source=DownloadSource.YOUTUBE_MUSIC,
            files=files,
            message=f"Downloaded {len(files)} files from YouTube",
            errors=errors
        )
    
    def _download_spotify(
        self,
        urls: List[str],
        audio_format: str = "flac"
    ) -> DownloadResult:
        """Download from Spotify using spotdl (Python 3.12 venv)"""
        if not self.tools_available["spotdl"]:
            return DownloadResult(False, DownloadSource.SPOTIFY, [],
                                "spotdl not installed", ["Install with: pip install spotdl"])
        
        files = []
        errors = []
        
        # spotdl output format - use playlist structure:
        # {list-name} = playlist/album name  
        # {list-position} = position in playlist (1, 2, 3...)
        # {artists} = track artist(s)
        # {title} = track title
        # Result: "HITS 2025/1 - Billie Eilish - BIRDS OF A FEATHER.flac"
        output_format = "{list-name}/{list-position} - {artists} - {title}"
        
        # Handle 'original' format - spotdl defaults to mp3, use flac for best quality
        actual_format = 'flac' if audio_format == 'original' else audio_format
        
        # Use Python 3.12 venv for spotdl (asyncio compatibility)
        project_root = Path(__file__).parent
        spotdl_python = project_root / '.venv-spotdl' / 'bin' / 'python3'
        
        if not spotdl_python.exists():
            return DownloadResult(
                False, 
                DownloadSource.SPOTIFY, 
                [],
                "Python 3.12 venv for spotdl not found",
                [f"Create venv with: uv venv .venv-spotdl --python 3.12 && uv pip install --python .venv-spotdl spotdl"]
            )
        
        for url in urls:
            self._log(f"🎵 Downloading from Spotify: {url[:60]}...")
            
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Use Python 3.12 venv to run spotdl
            # spotdl --output expects: "/full/path/{template-vars}"
            # Build the full template path correctly
            output_template = f"{self.output_dir}/{output_format}"
            
            cmd = [
                str(spotdl_python), '-m', 'spotdl',
                'download', url,
                '--output', output_template,
                '--format', actual_format,
            ]
            
            self._log(f"   Using Python 3.12 venv: {spotdl_python}")
            self._log(f"   Output template: {output_template}")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(self.output_dir)
                )
                
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if line:
                        self._log(f"   {line}")
                        if 'Downloaded' in line or 'Skipping' in line:
                            files.append(line)
                
                process.wait()
                
                if process.returncode == 0:
                    self._log(f"✅ Spotify download complete: {url[:40]}...", "success")
                else:
                    errors.append(f"spotdl failed for {url}")
                    
            except Exception as e:
                errors.append(f"Spotify download error: {str(e)}")
                self._log(f"❌ Error: {e}", "error")
        
        return DownloadResult(
            success=len(errors) == 0,
            source=DownloadSource.SPOTIFY,
            files=files,
            message=f"Downloaded from Spotify",
            errors=errors
        )
    
    def _download_alldebrid(self, urls: List[str]) -> DownloadResult:
        """Download from AllDebrid"""
        if not self.alldebrid_api_key:
            return DownloadResult(False, DownloadSource.ALLDEBRID, [],
                                "AllDebrid API key not configured", [])
        
        try:
            from alldebrid_downloader import AllDebridDownloader
            
            downloader = AllDebridDownloader(
                self.alldebrid_api_key,
                download_dir=str(self.output_dir),
                progress_callback=self.progress_callback
            )
            
            downloaded = downloader.download_links(urls)
            
            return DownloadResult(
                success=len(downloaded) > 0,
                source=DownloadSource.ALLDEBRID,
                files=[str(f) for f in downloaded],
                message=f"Downloaded {len(downloaded)} files from AllDebrid",
                errors=[]
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                source=DownloadSource.ALLDEBRID,
                files=[],
                message="AllDebrid download failed",
                errors=[str(e)]
            )


def parse_urls(text: str) -> List[str]:
    """Parse URLs from text input"""
    # Match common URL patterns
    url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'\.,;:\)\]\}]'
    urls = re.findall(url_pattern, text)
    return list(set(urls))  # Remove duplicates


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Source Music Downloader")
    parser.add_argument('urls', nargs='*', help='URLs to download')
    parser.add_argument('-o', '--output', default=str(Path.home() / "Documents" / "Music"),
                       help='Output directory')
    parser.add_argument('-f', '--format', choices=['flac', 'mp3', 'm4a', 'opus'],
                       default='flac', help='Audio format')
    parser.add_argument('--update', action='store_true',
                       help='Update yt-dlp and spotdl')
    parser.add_argument('--alldebrid-key', help='AllDebrid API key')
    
    args = parser.parse_args()
    
    downloader = MusicDownloader(
        output_dir=args.output,
        alldebrid_api_key=args.alldebrid_key or os.getenv('ALLDEBRID_API_KEY', '')
    )
    
    if args.update:
        print("🔄 Updating tools...")
        results = downloader.update_tools()
        for tool, updated in results.items():
            status = "✅ Updated" if updated else "⚠️ Failed"
            print(f"   {tool}: {status}")
        exit(0)
    
    if args.urls:
        urls = args.urls
    else:
        print("Paste URLs (press Ctrl+D when done):")
        import sys
        text = sys.stdin.read()
        urls = parse_urls(text)
    
    if not urls:
        print("❌ No URLs provided")
        exit(1)
    
    print(f"📋 Found {len(urls)} URLs to download")
    
    result = downloader.download(urls, audio_format=args.format)
    
    print(f"\n{'✅' if result.success else '❌'} {result.message}")
    if result.errors:
        print("Errors:")
        for err in result.errors:
            print(f"  - {err}")
