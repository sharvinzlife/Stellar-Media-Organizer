#!/usr/bin/env python3
"""
AllDebrid Downloader
Downloads files from AllDebrid links using aria2c for multi-threaded downloads.
Automatically organizes and filters audio tracks.
"""

import os
import re
import subprocess
import logging
import requests
from pathlib import Path
from typing import List, Optional, Dict, Callable

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# AllDebrid API
ALLDEBRID_API_BASE = "https://api.alldebrid.com/v4"


class AllDebridDownloader:
    """Downloads and organizes files from AllDebrid."""
    
    def __init__(self, api_key: str, download_dir: str = "/Users/sharvin/Downloads/AllDebrid",
                 progress_callback: Optional[Callable[[str, str], None]] = None):
        self.api_key = api_key
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback or (lambda msg, level: None)
        
        # Check aria2c is available
        if not self._check_aria2():
            raise RuntimeError("aria2c not found. Install with: brew install aria2")
    
    def _log(self, message: str, level: str = "info"):
        """Log message and call progress callback."""
        logger.info(message)
        self.progress_callback(message, level)
    
    def _check_aria2(self) -> bool:
        """Check if aria2c is installed."""
        try:
            subprocess.run(['aria2c', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def unlock_link(self, link: str) -> Optional[Dict]:
        """Unlock an AllDebrid link to get direct download URL."""
        try:
            self._log(f"🔓 Unlocking link via API...")
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
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                self._log(f"❌ Failed to unlock: {error_msg}", "error")
                return None
                
        except Exception as e:
            self._log(f"❌ Error unlocking link: {e}", "error")
            return None
    
    def download_file(self, url: str, filename: str, file_num: int = 1, total_files: int = 1, 
                      connections: int = 16) -> Optional[Path]:
        """Download a file using aria2c with multiple connections."""
        output_path = self.download_dir / filename
        
        self._log(f"📥 [{file_num}/{total_files}] Downloading: {filename}")
        self._log(f"   Using {connections} connections...")
        
        cmd = [
            'aria2c',
            '--max-connection-per-server=' + str(connections),
            '--split=' + str(connections),
            '--min-split-size=1M',
            '--file-allocation=none',
            '--continue=true',
            '--max-tries=5',
            '--retry-wait=5',
            '--timeout=120',
            '--connect-timeout=60',
            '--summary-interval=5',
            '--console-log-level=notice',
            '-d', str(self.download_dir),
            '-o', filename,
            url
        ]
        
        self._log(f"   🔧 Command: aria2c -d {self.download_dir} -o {filename}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            # Read output in real-time
            while True:
                # Check if process has finished
                retcode = process.poll()
                
                # Read available output
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            # Parse aria2c progress output
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
                    # Process finished, read any remaining output
                    remaining_out, remaining_err = process.communicate()
                    if remaining_err:
                        self._log(f"   ⚠️ {remaining_err[:200]}", "warning")
                    break
            
            if process.returncode == 0 and output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                self._log(f"✅ Downloaded: {filename} ({size_mb:.1f} MB)", "success")
                return output_path
            else:
                self._log(f"❌ Download failed (code {process.returncode}): {filename}", "error")
                return None
                
        except Exception as e:
            self._log(f"❌ Download error: {e}", "error")
            return None
    
    def download_links(self, links: List[str]) -> List[Path]:
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
    
    def download_and_organize(self, links: List[str], output_dir: str = "/Users/sharvin/Documents/Processed",
                               language: str = "malayalam") -> Dict:
        """Download links, organize files, and filter audio."""
        from media_organizer import MediaOrganizer, AudioTrackFilter
        
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


def parse_links(text: str) -> List[str]:
    """Parse AllDebrid links from text (handles newlines, spaces, etc.)."""
    pattern = r'https://alldebrid\.com/f/[A-Za-z0-9_-]+'
    links = re.findall(pattern, text)
    return list(set(links))


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AllDebrid Downloader with Media Organization")
    parser.add_argument('links', nargs='?', help='AllDebrid links (space or newline separated)')
    parser.add_argument('--api-key', '-k', help='AllDebrid API key (or set ALLDEBRID_API_KEY env var)')
    parser.add_argument('--output', '-o', default='/Users/sharvin/Documents/Processed', help='Output directory')
    parser.add_argument('--language', '-l', default='malayalam', help='Audio language to keep')
    parser.add_argument('--download-only', action='store_true', help='Only download, skip organize/filter')
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv('ALLDEBRID_API_KEY')
    if not api_key:
        print("❌ AllDebrid API key required!")
        print("   Set ALLDEBRID_API_KEY environment variable or use --api-key")
        return 1
    
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
    
    downloader = AllDebridDownloader(api_key)
    
    if args.download_only:
        downloaded = downloader.download_links(links)
        print(f"\n✅ Downloaded {len(downloaded)} files to {downloader.download_dir}")
    else:
        results = downloader.download_and_organize(links, args.output, args.language)
        print(f"\n✅ Complete! Files organized in {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main())
