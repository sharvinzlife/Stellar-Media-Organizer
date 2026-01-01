#!/usr/bin/env python3
"""
AllDebrid Downloader
Downloads files from AllDebrid links using aria2c for multi-threaded downloads.
Automatically organizes and renames using TMDB metadata.

Features:
- Multi-threaded downloads via aria2c
- TMDB integration for accurate naming
- Plex/Jellyfin compatible folder structure
- Audio track filtering by language
"""

import logging
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# AllDebrid API
ALLDEBRID_API_BASE = "https://api.alldebrid.com/v4"

# TMDB Integration
try:
    from core.smart_renamer import FilenameParser, MediaType, SmartRenamer
    from core.tmdb_client import TMDBClient, get_tmdb_client
    TMDB_AVAILABLE = True
except ImportError:
    TMDB_AVAILABLE = False
    logger.warning("TMDB integration not available. Install with: pip install requests")


# Shared ANSI escape pattern for cleaning aria2c / terminal output
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\[\d+;\d+m|\[\d+m')


class AllDebridDownloader:
    """Downloads and organizes files from AllDebrid with IMDB/TMDB integration."""

    def __init__(
        self,
        api_key: str,
        download_dir: str | None = None,
        tmdb_token: str | None = None,
        tmdb_api_key: str | None = None,
        omdb_api_key: str | None = None,
        progress_callback: Callable[[str, str], None] | None = None
    ):
        self.api_key = api_key
        # Use provided dir, or temp directory as fallback
        if download_dir is None:
            download_dir = os.path.join(Path.home(), "Downloads", "AllDebrid")
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback or (lambda msg, level: None)

        # Initialize TMDB client
        self.tmdb_client: TMDBClient | None = None
        self.smart_renamer: SmartRenamer | None = None

        if TMDB_AVAILABLE:
            tmdb_token = tmdb_token or os.getenv("TMDB_ACCESS_TOKEN")
            tmdb_api_key = tmdb_api_key or os.getenv("TMDB_API_KEY")
            omdb_api_key = omdb_api_key or os.getenv("OMDB_API_KEY")

            if tmdb_token or tmdb_api_key:
                self.tmdb_client = TMDBClient(
                    access_token=tmdb_token,
                    api_key=tmdb_api_key
                )
                self.smart_renamer = SmartRenamer(
                    tmdb_client=self.tmdb_client,
                    omdb_api_key=omdb_api_key,
                    organize_folders=True,
                    include_episode_title=True
                )
                if omdb_api_key:
                    self._log("✅ IMDB (OMDB) + TMDB integration enabled")
                else:
                    self._log("✅ TMDB integration enabled (OMDB not configured)")
            else:
                self._log("⚠️ TMDB credentials not found. Set TMDB_ACCESS_TOKEN or TMDB_API_KEY", "warning")

        # Check aria2c is available
        if not self._check_aria2():
            raise RuntimeError("aria2c not found. Install with: brew install aria2")

    def _log(self, message: str, level: str = "info"):
        """Log message and call progress callback."""
        # Strip ANSI escape codes from aria2c/output so logs and callbacks are clean
        clean_message = ANSI_ESCAPE_RE.sub('', message)
        logger.info(clean_message)
        self.progress_callback(clean_message, level)

    def _check_aria2(self) -> bool:
        """Check if aria2c is installed."""
        try:
            subprocess.run(['aria2c', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def unlock_link(self, link: str) -> dict | None:
        """Unlock an AllDebrid link to get direct download URL."""
        try:
            self._log("🔓 Unlocking link via API...")
            response = requests.get(
                f"{ALLDEBRID_API_BASE}/link/unlock",
                params={
                    "agent": "MediaOrganizerPro",
                    "apikey": self.api_key,
                    "link": link
                },
                timeout=30
            )
            data = response.json()

            if data.get("status") == "success":
                result = data.get("data")
                self._log(f"   ✅ Unlocked: {result.get('filename', 'unknown')}")
                return result
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            self._log(f"❌ Failed to unlock: {error_msg}", "error")
            return None

        except Exception as e:
            self._log(f"❌ Error unlocking link: {e}", "error")
            return None

    def _run_aria2c_download(self, url: str, filename: str, connections: int) -> tuple[int, bool]:
        """
        Run aria2c download and return (exit_code, file_exists).
        
        Optimal aria2c settings based on research:
        - 8 connections is a good balance (16 can overwhelm some servers)
        - min-split-size=5M prevents too many small chunks
        - Longer timeouts for large files
        - auto-file-renaming=false to prevent duplicate files
        """
        output_path = self.download_dir / filename
        
        cmd = [
            'aria2c',
            f'--max-connection-per-server={connections}',
            f'--split={connections}',
            '--min-split-size=5M',  # Larger chunks = fewer connections needed
            '--file-allocation=none',
            '--continue=true',
            '--max-tries=5',  # Retry individual connections
            '--retry-wait=3',
            '--timeout=180',  # 3 minutes timeout for slow connections
            '--connect-timeout=60',
            '--max-file-not-found=3',
            '--max-resume-failure-tries=5',
            '--summary-interval=5',
            '--console-log-level=notice',
            '--auto-file-renaming=false',
            '--allow-overwrite=true',
            '-d', str(self.download_dir),
            '-o', filename,
            url
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Read output in real-time
            while True:
                retcode = process.poll()

                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            if '%' in line or 'ETA' in line or 'DL:' in line or 'NOTICE' in line:
                                percent_match = re.search(r'\((\d+)%\)', line)
                                if percent_match:
                                    percent = percent_match.group(1)
                                    self._log(f"   📊 {percent}% - {line[:80]}")
                                else:
                                    self._log(f"   {line[:100]}")
                            elif 'Download complete' in line or 'OK' in line:
                                self._log(f"   ✅ {line}", "success")

                if retcode is not None:
                    _remaining_out, remaining_err = process.communicate()
                    if remaining_err and 'error' in remaining_err.lower():
                        self._log(f"   ⚠️ {remaining_err[:200]}", "warning")
                    break

            return process.returncode, output_path.exists()

        except Exception as e:
            self._log(f"   ⚠️ aria2c exception: {e}", "warning")
            return -1, output_path.exists()

    def download_file(self, url: str, filename: str, file_num: int = 1, total_files: int = 1,
                      connections: int = 8, max_retries: int = 3) -> Path | None:
        """
        Download a file using aria2c with multiple connections and retry logic.
        
        Args:
            url: Direct download URL
            filename: Output filename
            file_num: Current file number (for logging)
            total_files: Total files to download (for logging)
            connections: Initial number of connections (default 8, reduced on retry)
            max_retries: Maximum download attempts (default 3)
        
        Returns:
            Path to downloaded file or None on failure
            
        Error codes from aria2c:
            9 = Not enough disk space (often false positive from server disconnect)
            22 = HTTP response header bad/unexpected (server issue)
            6 = Network problem
            2 = Timeout
        """
        output_path = self.download_dir / filename
        aria2_control = output_path.with_suffix(output_path.suffix + '.aria2')

        self._log(f"📥 [{file_num}/{total_files}] Downloading: {filename}")
        
        # Connection strategy: start with requested, reduce on each retry
        # Research shows 8 connections is optimal for most servers
        connection_schedule = [
            min(connections, 8),   # First try: 8 connections (balanced)
            6,                      # Second try: 6 connections (more conservative)
            4,                      # Third try: 4 connections (very conservative)
        ]
        
        for attempt in range(max_retries):
            current_connections = connection_schedule[min(attempt, len(connection_schedule) - 1)]
            
            if attempt > 0:
                self._log(f"   🔄 Retry {attempt}/{max_retries - 1} with {current_connections} connections...")
                # Small delay before retry
                import time
                time.sleep(2)
            else:
                self._log(f"   Using {current_connections} connections...")

            self._log(f"   🔧 Command: aria2c -x{current_connections} -d {self.download_dir} -o {filename}")

            exit_code, file_exists = self._run_aria2c_download(url, filename, current_connections)

            # Success!
            if exit_code == 0 and file_exists:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                self._log(f"✅ Downloaded: {filename} ({size_mb:.1f} MB)", "success")
                return output_path

            # Handle specific error codes
            error_msg = {
                2: "timeout",
                6: "network problem", 
                9: "disk space or server disconnect",
                22: "server error (HTTP)",
            }.get(exit_code, f"unknown error (code {exit_code})")
            
            self._log(f"   ⚠️ Attempt {attempt + 1} failed: {error_msg}", "warning")

            # Clean up partial file for fresh retry (but keep .aria2 for resume)
            # Only clean up on final attempt or if error suggests corruption
            if exit_code in [9, 22] or attempt == max_retries - 1:
                if output_path.exists():
                    try:
                        output_path.unlink()
                        self._log(f"   🧹 Cleaned up partial file for fresh retry", "info")
                    except Exception:
                        pass
                if aria2_control.exists():
                    try:
                        aria2_control.unlink()
                    except Exception:
                        pass

        # All retries exhausted
        self._log(f"❌ Download failed after {max_retries} attempts: {filename}", "error")
        
        # Final cleanup
        if output_path.exists():
            try:
                output_path.unlink()
                self._log(f"   🧹 Cleaned up partial file: {filename}", "info")
            except Exception as cleanup_err:
                self._log(f"   ⚠️ Could not clean up partial file: {cleanup_err}", "warning")
        if aria2_control.exists():
            try:
                aria2_control.unlink()
            except Exception:
                pass
                
        return None

    def download_links(self, links: list[str]) -> list[Path]:
        """Download multiple AllDebrid links."""
        downloaded_files = []
        total = len(links)

        for i, link in enumerate(links, 1):
            self._log(f"\n📦 Processing link {i}/{total}")

            # Unlock the link
            unlocked = self.unlock_link(link)
            if not unlocked:
                continue

            url = unlocked.get("link")
            filename = unlocked.get("filename", f"file_{i}.mkv")
            size = unlocked.get("filesize", 0)
            size_mb = size / (1024 * 1024) if size else 0

            self._log(f"   📄 File: {filename} ({size_mb:.1f} MB)")

            # Download
            downloaded = self.download_file(url, filename, i, total)
            if downloaded:
                downloaded_files.append(downloaded)

        return downloaded_files

    def smart_rename_file(self, file_path: Path, output_dir: Path) -> tuple[Path | None, bool, str | None]:
        """
        Rename a file using IMDB (OMDB) as primary, TMDB as fallback.
        Creates .nfo file with IMDB URL for Plex matching.

        Naming convention for movies with IMDB data:
            Sisu Road to Revenge (2025) {imdb-tt31844586}/
                Sisu Road to Revenge (2025) {imdb-tt31844586}.mkv

        Args:
            file_path: Path to the downloaded file
            output_dir: Output directory for organized files

        Returns:
            Tuple of (new_path, metadata_found)
            - new_path: New path if renamed, original path if metadata unavailable, None on error
            - metadata_found: True if IMDB/TMDB metadata was found
        """
        if not self.smart_renamer:
            self._log("⚠️ IMDB/TMDB not configured, skipping smart rename", "warning")
            return file_path, False

        self._log(f"🔍 Looking up metadata for: {file_path.name}")

        result = self.smart_renamer.rename_file(file_path, output_dir, dry_run=False)

        if not (result.success and result.new_path):
            self._log(f"   ⚠️ Rename failed: {result.error}", "warning")
            return file_path, False, None

        # Base logging about metadata lookup
        if result.new_name and result.original_name != result.new_name:
            self._log(f"   ✅ Renamed: {result.new_name}")
        else:
            self._log("   ℹ️ Already correctly named")

        if result.imdb_id:
            # IMDB is primary metadata source
            self._log(f"   🎬 IMDB: {result.imdb_id} - {result.tmdb_title}")
            self._log("   📄 Created .nfo files for Plex matching")
        elif result.tmdb_id:
            # TMDB fallback
            self._log(f"   📺 TMDB: {result.tmdb_title} (ID: {result.tmdb_id})")

        # Log detected primary language from metadata if available
        primary_language = getattr(result, "primary_language", None)
        if primary_language:
            self._log(f"   🌐 Language (metadata): {primary_language}", "info")

        # Track metadata status
        if not result.metadata_found:
            self._log("   ⚠️ No IMDB/TMDB metadata found - will use Malayalam library", "warning")

        # Enforce final naming convention for MOVIES ONLY that have IMDB metadata:
        # <Title> (<Year>) {imdb-<id>}/<Title> (<Year>) {imdb-<id>}.ext
        #
        # TV shows should NOT be renamed here - they already have proper naming
        # from SmartRenamer with episode info (S01E01) and folder has TMDB hint.
        #
        # We only touch the file/parent folder if we actually have an IMDB ID
        # AND it's NOT a TV show (no episode pattern in filename).
        new_path = result.new_path
        
        # Check if this is a TV show by looking for episode patterns in the new filename
        # Pattern matches S01E01, S1E1, S01E01-E04, etc.
        is_tv_show = bool(re.search(r'S\d{1,2}E\d{1,2}', result.new_name or ''))
        
        # Debug logging for TV show detection
        if result.imdb_id:
            self._log(f"   🔍 TV show check: new_name='{result.new_name}', is_tv_show={is_tv_show}")
        
        if result.imdb_id and new_path and new_path.exists() and not is_tv_show:
            ext = new_path.suffix
            stem = new_path.stem

            # Prefer TMDB title + year if available, otherwise keep existing stem
            title_part = result.tmdb_title or stem
            # Try to extract year from existing name to avoid losing it
            year_match = re.search(r'\((\d{4})\)', stem)
            year_part = year_match.group(1) if year_match else None

            base_name = f"{title_part} ({year_part})" if year_part else title_part

            imdb_tag = f"{{imdb-{result.imdb_id}}}"
            final_name = f"{base_name} {imdb_tag}{ext}"
            final_stem = f"{base_name} {imdb_tag}"

            parent = new_path.parent
            final_path = parent / final_name

            try:
                # Rename the media file itself
                if final_path != new_path:
                    new_path = new_path.rename(final_path)
                    self._log(f"   ✏️ IMDB-tagged name: {final_name}")

                # If the parent folder name matches the old stem, also align it
                # to keep the folder/file pattern consistent:
                #   Folder: Base {imdb-id}
                #   File:   Base {imdb-id}.ext
                if parent.name == stem:
                    target_folder = parent.parent / final_stem
                    if target_folder != parent:
                        parent = parent.rename(target_folder)
                        new_path = parent / final_name
                        self._log(f"   ✏️ Adjusted folder to: {target_folder.name}")
            except Exception as e:
                # If renaming fails for any reason, keep the successful SmartRenamer path
                self._log(f"   ⚠️ IMDB-tag rename skipped due to error: {e}", "warning")

        return new_path, result.metadata_found, getattr(result, "primary_language", None)

    def download_and_organize_smart(
        self,
        links: list[str],
        output_dir: str | None = None,
        language: str | None = None,
        filter_audio: bool = False
    ) -> dict:
        """
        Download links and organize using TMDB metadata.

        Args:
            links: List of AllDebrid links
            output_dir: Output directory for organized files
            language: Audio language to keep (if filter_audio is True)
            filter_audio: Whether to filter audio tracks

        Returns:
            Dict with download/organize results including metadata_found status and original filenames
        """
        results = {
            "downloaded": [],
            "renamed": [],
            "filtered": [],
            "errors": [],
            "metadata_found": False,   # Track if any file had metadata
            "original_filenames": {},  # Map: new_path -> original_filename (for category detection)
            "primary_languages": {}    # Map: new_path -> primary_language (from OMDB/TMDB)
        }

        if output_dir is None:
            output_dir = os.path.join(Path.home(), "Documents", "Processed")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Download all files and capture original filenames
        self._log("=" * 50)
        self._log("📥 STEP 1: Downloading files from AllDebrid")
        self._log("=" * 50)

        # Download with original filename tracking
        downloaded_files_with_originals = []
        total = len(links)

        for i, link in enumerate(links, 1):
            self._log(f"\n📦 Processing link {i}/{total}")

            # Unlock the link
            unlocked = self.unlock_link(link)
            if not unlocked:
                continue

            url = unlocked.get("link")
            original_filename = unlocked.get("filename", f"file_{i}.mkv")  # CAPTURE ORIGINAL
            size = unlocked.get("filesize", 0)
            size_mb = size / (1024 * 1024) if size else 0

            self._log(f"   📄 Original: {original_filename} ({size_mb:.1f} MB)")

            # Download
            downloaded = self.download_file(url, original_filename, i, total)
            if downloaded:
                downloaded_files_with_originals.append((downloaded, original_filename))
                results["downloaded"].append(str(downloaded))

        if not downloaded_files_with_originals:
            self._log("❌ No files downloaded!", "error")
            return results

        # Step 2: Smart rename using IMDB/TMDB
        self._log("=" * 50)
        self._log("🎬 STEP 2: Renaming with IMDB/TMDB metadata")
        self._log("=" * 50)

        renamed_files = []
        any_metadata_found = False
        for file_path, original_filename in downloaded_files_with_originals:
            new_path, metadata_found, primary_language = self.smart_rename_file(file_path, output_path)
            if metadata_found:
                any_metadata_found = True
            if new_path:
                renamed_files.append(new_path)
                new_path_str = str(new_path)
                results["renamed"].append(new_path_str)
                # Store mapping: new_path -> original_filename for category detection
                results["original_filenames"][new_path_str] = original_filename
                # Store primary language from metadata (if available)
                if primary_language:
                    results["primary_languages"][new_path_str] = primary_language
            else:
                results["errors"].append(f"Failed to rename: {file_path.name}")

        results["metadata_found"] = any_metadata_found

        # Step 3: Filter audio tracks (optional)
        if filter_audio and language:
            self._log("=" * 50)
            self._log(f"🎵 STEP 3: Filtering audio (keeping {language})")
            self._log("=" * 50)

            try:
                from media_organizer import AudioTrackFilter
                audio_filter = AudioTrackFilter()

                for file_path in renamed_files:
                    if file_path.suffix.lower() == '.mkv':
                        filtered = audio_filter.filter_audio(file_path, language)
                        if filtered:
                            results["filtered"].append(str(file_path))
                            self._log(f"   ✅ Filtered: {file_path.name}")
            except ImportError:
                self._log("⚠️ Audio filtering not available", "warning")

        # Summary
        self._log("=" * 50)
        self._log("🎉 COMPLETE!", "success")
        self._log(f"   Downloaded: {len(results['downloaded'])} files")
        self._log(f"   Renamed: {len(results['renamed'])} files")
        if filter_audio:
            self._log(f"   Filtered: {len(results['filtered'])} files")
        if results['errors']:
            self._log(f"   Errors: {len(results['errors'])}", "warning")
        self._log("=" * 50)

        return results

    def download_and_organize(self, links: list[str], output_dir: str | None = None,
                               language: str = "malayalam") -> dict:
        """Download links, organize files, and filter audio."""
        from media_organizer import AudioTrackFilter, MediaOrganizer

        if output_dir is None:
            output_dir = os.path.join(Path.home(), "Documents", "Processed")

        results = {
            "downloaded": [],
            "organized": [],
            "filtered": [],
            "errors": []
        }

        # Step 1: Download all files
        self._log("=" * 50)
        self._log("📥 STEP 1: Downloading files from AllDebrid")
        self._log("=" * 50)

        downloaded_files = self.download_links(links)
        results["downloaded"] = [str(f) for f in downloaded_files]

        if not downloaded_files:
            self._log("❌ No files downloaded!", "error")
            return results

        # Step 2: Organize files
        self._log("=" * 50)
        self._log("📁 STEP 2: Organizing files")
        self._log("=" * 50)

        organizer = MediaOrganizer()
        organized = organizer.organize_files(self.download_dir, Path(output_dir))
        results["organized"] = [str(f.path) for f in organized]

        for f in organized:
            self._log(f"   Moved: {f.path.name}")

        # Step 3: Filter audio tracks
        self._log("=" * 50)
        self._log(f"🎵 STEP 3: Filtering audio (keeping {language})")
        self._log("=" * 50)

        audio_filter = AudioTrackFilter()
        filtered = audio_filter.batch_filter(Path(output_dir), language)
        results["filtered"] = [str(f) for f in filtered]

        for f in filtered:
            self._log(f"   Filtered: {Path(f).name}")

        self._log("=" * 50)
        self._log("🎉 COMPLETE!", "success")
        self._log(f"   Downloaded: {len(results['downloaded'])} files")
        self._log(f"   Organized: {len(results['organized'])} files")
        self._log(f"   Filtered: {len(results['filtered'])} files")
        self._log("=" * 50)

        return results


def parse_links(text: str) -> list[str]:
    """Parse AllDebrid links from text (handles newlines, spaces, etc.)."""
    pattern = r'https://alldebrid\.com/f/[A-Za-z0-9_-]+'
    links = re.findall(pattern, text)
    return list(set(links))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AllDebrid Downloader with TMDB Integration")
    parser.add_argument('links', nargs='?', help='AllDebrid links (space or newline separated)')
    parser.add_argument('--api-key', '-k', help='AllDebrid API key (or set ALLDEBRID_API_KEY env var)')
    parser.add_argument('--tmdb-token', '-t', help='TMDB access token (or set TMDB_ACCESS_TOKEN env var)')
    parser.add_argument('--output', '-o', default=None, help='Output directory')
    parser.add_argument('--language', '-l', default='english', help='Audio language to keep')
    parser.add_argument('--filter-audio', '-f', action='store_true', help='Filter audio tracks by language')
    parser.add_argument('--download-only', action='store_true', help='Only download, skip organize/rename')
    parser.add_argument('--legacy', action='store_true', help='Use legacy organize method (no TMDB)')

    args = parser.parse_args()

    api_key = args.api_key or os.getenv('ALLDEBRID_API_KEY')
    if not api_key:
        print("❌ AllDebrid API key required!")
        print("   Set ALLDEBRID_API_KEY environment variable or use --api-key")
        return 1

    tmdb_token = args.tmdb_token or os.getenv('TMDB_ACCESS_TOKEN')
    tmdb_api_key = os.getenv('TMDB_API_KEY')

    if args.links:
        links_text = args.links
    else:
        print("Paste AllDebrid links (press Ctrl+D when done):")
        import sys
        links_text = sys.stdin.read()

    links = parse_links(links_text)

    if not links:
        print("❌ No valid AllDebrid links found!")
        return 1

    print(f"📋 Found {len(links)} links to download")

    downloader = AllDebridDownloader(
        api_key,
        tmdb_token=tmdb_token,
        tmdb_api_key=tmdb_api_key
    )

    if args.download_only:
        downloaded = downloader.download_links(links)
        print(f"\n✅ Downloaded {len(downloaded)} files to {downloader.download_dir}")
    elif args.legacy:
        # Use legacy organize method
        downloader.download_and_organize(links, args.output, args.language)
        print(f"\n✅ Complete! Files organized in {args.output}")
    else:
        # Use smart TMDB-based organize
        if not tmdb_token and not tmdb_api_key:
            print("⚠️ TMDB credentials not found. Using legacy organize method.")
            print("   Set TMDB_ACCESS_TOKEN for smart renaming with episode titles.")
            downloader.download_and_organize(links, args.output, args.language)
        else:
            downloader.download_and_organize_smart(
                links,
                args.output,
                language=args.language,
                filter_audio=args.filter_audio
            )
        print(f"\n✅ Complete! Files organized in {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
