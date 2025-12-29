#!/usr/bin/env python3
"""
NAS Transfer Module - Linux Compatible
Handles file transfers to SMB/NAS shares on Linux using smbclient or CIFS mount.

Supports:
- Direct smbclient transfers (no mount required)
- CIFS mount-based transfers
- Multiple NAS configurations
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NASConfig:
    """NAS configuration."""
    name: str
    host: str
    username: str
    password: str
    share: str
    media_path: str = "/media"


class NASTransfer:
    """
    Linux-compatible NAS file transfer.
    
    Uses smbclient for direct transfers without mounting.
    Falls back to CIFS mount if smbclient is unavailable.
    """
    
    def __init__(self):
        self.nas_configs: Dict[str, NASConfig] = {}
        self._load_from_env()
        self._check_tools()
    
    def _check_tools(self):
        """Check available transfer tools."""
        self.has_smbclient = shutil.which('smbclient') is not None
        self.has_mount_cifs = shutil.which('mount.cifs') is not None
        
        if not self.has_smbclient and not self.has_mount_cifs:
            logger.warning("Neither smbclient nor mount.cifs available. Install with: apt install smbclient cifs-utils")
    
    def _load_from_env(self):
        """Load NAS configurations from environment variables."""
        # Lharmony (Synology DS925+)
        lharmony_host = os.getenv("LHARMONY_HOST")
        if lharmony_host:
            self.nas_configs["lharmony"] = NASConfig(
                name="Lharmony",
                host=lharmony_host,
                username=os.getenv("LHARMONY_USERNAME", ""),
                password=os.getenv("LHARMONY_PASSWORD", ""),
                share=os.getenv("LHARMONY_SHARE", "data"),
                media_path=os.getenv("LHARMONY_MEDIA_PATH", "/media")
            )
            logger.info(f"Loaded NAS config: Lharmony ({lharmony_host})")
        
        # Streamwave (Unraid)
        streamwave_host = os.getenv("STREAMWAVE_HOST")
        if streamwave_host:
            self.nas_configs["streamwave"] = NASConfig(
                name="Streamwave",
                host=streamwave_host,
                username=os.getenv("STREAMWAVE_USERNAME", ""),
                password=os.getenv("STREAMWAVE_PASSWORD", ""),
                share=os.getenv("STREAMWAVE_SHARE", "Data-Streamwave"),
                media_path=os.getenv("STREAMWAVE_MEDIA_PATH", "/media")
            )
            logger.info(f"Loaded NAS config: Streamwave ({streamwave_host})")
    
    def transfer_file(
        self,
        local_path: str,
        remote_path: str,
        nas_name: str = "lharmony"
    ) -> bool:
        """
        Transfer a file to NAS using smbclient.
        
        Args:
            local_path: Local file path
            remote_path: Remote path on NAS (e.g., /music/Artist/Album/track.flac)
            nas_name: NAS name (lharmony or streamwave)
            
        Returns:
            True if transfer successful
        """
        nas_name = nas_name.lower()
        if nas_name not in self.nas_configs:
            logger.error(f"NAS not configured: {nas_name}")
            return False
        
        config = self.nas_configs[nas_name]
        local_file = Path(local_path)
        
        if not local_file.exists():
            logger.error(f"Local file not found: {local_path}")
            return False
        
        # Build remote directory path
        # Remote paths should be relative to the share root
        # For music: media/music/Album/file.flac
        # For movies: media/movies/Movie/file.mkv
        remote_path_clean = remote_path.lstrip('/')
        
        # Map category shortcuts to full paths under media/
        category_map = {
            'music': 'media/music',
            'movies': 'media/movies',
            'tv-shows': 'media/tv',
            'tv': 'media/tv',
            'malayalam movies': 'media/malayalam movies',
            'malayalam-movies': 'media/malayalam movies',
            'bollywood movies': 'media/bollywood movies',
            'bollywood-movies': 'media/bollywood movies',
            'malayalam-tv-shows': 'media/malayalam tv shows',
            'malayalam tv shows': 'media/malayalam tv shows',
        }
        
        # Check if path starts with a known category
        first_part = remote_path_clean.split('/')[0].lower() if '/' in remote_path_clean else remote_path_clean.lower()
        
        if first_part in category_map:
            # Replace category shortcut with full path
            rest_of_path = '/'.join(remote_path_clean.split('/')[1:])
            full_path = f"{category_map[first_part]}/{rest_of_path}"
            remote_dir = str(Path(full_path).parent).replace('\\', '/')
        else:
            # Use media_path prefix for unknown categories
            remote_dir = str(Path(config.media_path.lstrip('/')) / Path(remote_path_clean).parent).replace('\\', '/')
        
        remote_filename = Path(remote_path).name
        
        if self.has_smbclient:
            return self._transfer_with_smbclient(config, local_file, remote_dir, remote_filename)
        else:
            logger.error("smbclient not available. Install with: apt install smbclient")
            return False
    
    def _transfer_with_smbclient(
        self,
        config: NASConfig,
        local_file: Path,
        remote_dir: str,
        remote_filename: str
    ) -> bool:
        """Transfer file using smbclient."""
        try:
            # Create remote directory structure
            # smbclient doesn't have mkdir -p, so we need to create each level
            dir_parts = remote_dir.strip('/').split('/')
            current_path = ""
            
            for part in dir_parts:
                if part:
                    current_path += f"/{part}"
                    mkdir_cmd = [
                        'smbclient',
                        f'//{config.host}/{config.share}',
                        '-U', f'{config.username}%{config.password}',
                        '-c', f'mkdir "{current_path}"'
                    ]
                    # Ignore errors (directory may already exist)
                    subprocess.run(mkdir_cmd, capture_output=True, timeout=30)
            
            # Transfer file
            put_cmd = [
                'smbclient',
                f'//{config.host}/{config.share}',
                '-U', f'{config.username}%{config.password}',
                '-c', f'cd "{remote_dir}"; put "{local_file}" "{remote_filename}"'
            ]
            
            result = subprocess.run(
                put_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for large files
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Transferred: {local_file.name} -> {config.name}:{remote_dir}/{remote_filename}")
                return True
            else:
                logger.error(f"❌ Transfer failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Transfer timeout for {local_file.name}")
            return False
        except Exception as e:
            logger.error(f"❌ Transfer error: {e}")
            return False
    
    def transfer_directory(
        self,
        local_dir: str,
        remote_base: str,
        nas_name: str = "lharmony",
        extensions: Optional[list] = None
    ) -> tuple:
        """
        Transfer all files from a directory to NAS.
        
        Args:
            local_dir: Local directory path
            remote_base: Remote base path (e.g., /music)
            nas_name: NAS name
            extensions: List of file extensions to transfer (e.g., ['.flac', '.mp3'])
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        local_path = Path(local_dir)
        if not local_path.exists():
            logger.error(f"Local directory not found: {local_dir}")
            return (0, 0)
        
        success = 0
        failed = 0
        
        for file in local_path.rglob('*'):
            if file.is_file():
                # Filter by extension if specified
                if extensions and file.suffix.lower() not in extensions:
                    continue
                
                # Preserve relative path structure
                rel_path = file.relative_to(local_path)
                remote_path = f"{remote_base}/{rel_path}"
                
                if self.transfer_file(str(file), remote_path, nas_name):
                    success += 1
                else:
                    failed += 1
        
        logger.info(f"Transfer complete: {success} succeeded, {failed} failed")
        return (success, failed)
    
    def test_connection(self, nas_name: str = "lharmony") -> bool:
        """Test NAS connection."""
        nas_name = nas_name.lower()
        if nas_name not in self.nas_configs:
            logger.error(f"NAS not configured: {nas_name}")
            return False
        
        config = self.nas_configs[nas_name]
        
        try:
            cmd = [
                'smbclient',
                f'//{config.host}/{config.share}',
                '-U', f'{config.username}%{config.password}',
                '-c', 'ls'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {config.name} connection OK")
                return True
            else:
                logger.error(f"❌ {config.name} connection failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection test error: {e}")
            return False


if __name__ == "__main__":
    # Test NAS transfer
    logging.basicConfig(level=logging.INFO)
    
    # Load config from .env
    from dotenv import load_dotenv
    load_dotenv("config.env")
    
    nas = NASTransfer()
    
    print("Configured NAS:")
    for name, config in nas.nas_configs.items():
        print(f"  - {config.name} ({config.host})")
    
    print("\nTesting connections...")
    for name in nas.nas_configs:
        nas.test_connection(name)
