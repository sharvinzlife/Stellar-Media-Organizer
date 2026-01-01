#!/usr/bin/env python3
"""
SMB/NAS Manager
Handles mounting and file operations for SMB shares on macOS.

Supports:
- Auto-mounting SMB shares
- File copying to NAS locations
- Connection testing
- Multiple NAS configurations
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaCategory(str, Enum):
    """Media category for organization."""
    MOVIES = "movies"
    MALAYALAM_MOVIES = "malayalam movies"
    BOLLYWOOD_MOVIES = "bollywood movies"
    TV_SHOWS = "tv-shows"
    MALAYALAM_TV_SHOWS = "malayalam-tv-shows"
    MUSIC = "music"


@dataclass
class SMBConfig:
    """SMB share configuration."""
    name: str
    host: str
    username: str
    password: str
    share: str
    media_path: str = "/media"

    def get_smb_url(self) -> str:
        """Get SMB URL."""
        return f"smb://{self.username}@{self.host}/{self.share}"

    def get_mount_point(self) -> Path:
        """Get local mount point."""
        # macOS mounts SMB shares to /Volumes/<share_name>
        return Path(f"/Volumes/{self.share}")

    def get_media_path(self, category: MediaCategory) -> Path:
        """Get full path for media category."""
        mount = self.get_mount_point()
        return mount / self.media_path.lstrip('/') / category.value


class SMBManager:
    """
    Manages SMB connections and file operations.

    Usage:
        # Configure NAS
        lharmony = SMBConfig(
            name="Lharmony",
            host="10.1.0.122",
            username="user",
            password="pass",
            share="data"
        )

        manager = SMBManager()
        manager.add_nas(lharmony)

        # Mount and copy
        if manager.mount("Lharmony"):
            manager.copy_to_nas(
                "Lharmony",
                "/path/to/file.mkv",
                MediaCategory.MOVIES
            )
    """

    def __init__(self):
        self.nas_configs: dict[str, SMBConfig] = {}

    def add_nas(self, config: SMBConfig):
        """Add NAS configuration."""
        self.nas_configs[config.name] = config
        logger.info(f"Added NAS: {config.name} ({config.host})")

    def is_mounted(self, nas_name: str) -> bool:
        """Check if NAS is mounted."""
        if nas_name not in self.nas_configs:
            return False

        config = self.nas_configs[nas_name]
        mount_point = config.get_mount_point()
        return mount_point.exists() and mount_point.is_mount()

    def mount(self, nas_name: str, force: bool = False) -> bool:
        """
        Mount SMB share.

        Args:
            nas_name: Name of NAS to mount
            force: Force remount if already mounted

        Returns:
            True if mounted successfully
        """
        if nas_name not in self.nas_configs:
            logger.error(f"NAS not configured: {nas_name}")
            return False

        config = self.nas_configs[nas_name]
        mount_point = config.get_mount_point()

        # Check if already mounted
        if self.is_mounted(nas_name):
            if not force:
                logger.info(f"{nas_name} already mounted at {mount_point}")
                return True
            self.unmount(nas_name)

        # Mount using macOS mount_smbfs
        smb_url = f"//{config.username}:{config.password}@{config.host}/{config.share}"

        try:
            # Create mount point if needed
            mount_point.mkdir(parents=True, exist_ok=True)

            # Mount command
            cmd = ["mount", "-t", "smbfs", smb_url, str(mount_point)]

            result = subprocess.run(
                cmd,
                check=False, capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"✅ Mounted {nas_name} at {mount_point}")
                return True
            logger.error(f"❌ Mount failed: {result.stderr}")
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Mount timeout for {nas_name}")
            return False
        except Exception as e:
            logger.error(f"❌ Mount error: {e}")
            return False

    def unmount(self, nas_name: str) -> bool:
        """Unmount SMB share."""
        if nas_name not in self.nas_configs:
            return False

        config = self.nas_configs[nas_name]
        mount_point = config.get_mount_point()

        if not self.is_mounted(nas_name):
            logger.info(f"{nas_name} not mounted")
            return True

        try:
            subprocess.run(
                ["umount", str(mount_point)],
                check=False, capture_output=True,
                timeout=10
            )
            logger.info(f"Unmounted {nas_name}")
            return True
        except Exception as e:
            logger.error(f"Unmount error: {e}")
            return False

    def test_connection(self, nas_name: str) -> bool:
        """
        Test NAS connection.

        Args:
            nas_name: Name of NAS to test

        Returns:
            True if connection successful
        """
        if nas_name not in self.nas_configs:
            return False

        # Try to mount
        if self.mount(nas_name):
            config = self.nas_configs[nas_name]
            media_base = config.get_mount_point() / config.media_path.lstrip('/')

            # Check if media path exists
            if media_base.exists():
                logger.info(f"✅ {nas_name} connection OK")
                return True
            logger.warning(f"⚠️ {nas_name} mounted but media path not found: {media_base}")
            return False

        return False

    def copy_to_nas(
        self,
        nas_name: str,
        source_path: Path,
        category: MediaCategory,
        create_folder: bool = True
    ) -> Path | None:
        """
        Copy file to NAS.

        Args:
            nas_name: Target NAS name
            source_path: Source file path
            category: Media category
            create_folder: Create folder for movies

        Returns:
            Destination path if successful
        """
        if nas_name not in self.nas_configs:
            logger.error(f"NAS not configured: {nas_name}")
            return None

        source_path = Path(source_path)
        if not source_path.exists():
            logger.error(f"Source file not found: {source_path}")
            return None

        # Ensure mounted
        if not self.is_mounted(nas_name) and not self.mount(nas_name):
            logger.error(f"Failed to mount {nas_name}")
            return None

        config = self.nas_configs[nas_name]
        category_path = config.get_media_path(category)

        # Create category folder if needed
        category_path.mkdir(parents=True, exist_ok=True)

        # Determine destination
        if create_folder and category in [MediaCategory.MOVIES, MediaCategory.MALAYALAM_MOVIES, MediaCategory.BOLLYWOOD_MOVIES]:
            # Movies go in their own folder
            folder_name = source_path.stem
            dest_folder = category_path / folder_name
            dest_folder.mkdir(exist_ok=True)
            dest_path = dest_folder / source_path.name
        else:
            # TV shows and music go directly in category folder
            dest_path = category_path / source_path.name

        # Copy file
        try:
            logger.info(f"Copying {source_path.name} to {nas_name}/{category.value}...")
            shutil.copy2(source_path, dest_path)
            logger.info(f"✅ Copied to {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"❌ Copy failed: {e}")
            return None

    def move_to_nas(
        self,
        nas_name: str,
        source_path: Path,
        category: MediaCategory,
        create_folder: bool = True
    ) -> Path | None:
        """Move file to NAS (copy + delete source)."""
        dest_path = self.copy_to_nas(nas_name, source_path, category, create_folder)

        if dest_path:
            try:
                source_path.unlink()
                logger.info(f"Deleted source: {source_path}")
                return dest_path
            except Exception as e:
                logger.warning(f"Failed to delete source: {e}")
                return dest_path

        return None

    def get_available_categories(self, nas_name: str) -> list[MediaCategory]:
        """Get available media categories for a NAS."""
        if nas_name not in self.nas_configs:
            return []

        self.nas_configs[nas_name]

        # Lharmony has all categories
        if "lharmony" in nas_name.lower():
            return [
                MediaCategory.MOVIES,
                MediaCategory.MALAYALAM_MOVIES,
                MediaCategory.BOLLYWOOD_MOVIES,
                MediaCategory.TV_SHOWS,
                MediaCategory.MALAYALAM_TV_SHOWS,
                MediaCategory.MUSIC
            ]
        # Streamwave has video only
        if "streamwave" in nas_name.lower():
            return [
                MediaCategory.MOVIES,
                MediaCategory.MALAYALAM_MOVIES,
                MediaCategory.BOLLYWOOD_MOVIES,
                MediaCategory.TV_SHOWS,
                MediaCategory.MALAYALAM_TV_SHOWS
            ]

        # Default: all categories
        return list(MediaCategory)


# Factory function
def create_smb_manager_from_env() -> SMBManager:
    """Create SMB manager from environment variables."""
    manager = SMBManager()

    # Lharmony
    lharmony_host = os.getenv("LHARMONY_HOST")
    if lharmony_host:
        lharmony = SMBConfig(
            name="Lharmony",
            host=lharmony_host,
            username=os.getenv("LHARMONY_USERNAME", ""),
            password=os.getenv("LHARMONY_PASSWORD", ""),
            share=os.getenv("LHARMONY_SHARE", "data"),
            media_path=os.getenv("LHARMONY_MEDIA_PATH", "/media")
        )
        manager.add_nas(lharmony)

    # Streamwave
    streamwave_host = os.getenv("STREAMWAVE_HOST")
    if streamwave_host:
        streamwave = SMBConfig(
            name="Streamwave",
            host=streamwave_host,
            username=os.getenv("STREAMWAVE_USERNAME", ""),
            password=os.getenv("STREAMWAVE_PASSWORD", ""),
            share=os.getenv("STREAMWAVE_SHARE", "Data-Streamwave"),
            media_path=os.getenv("STREAMWAVE_MEDIA_PATH", "/media")
        )
        manager.add_nas(streamwave)

    return manager


if __name__ == "__main__":
    # Test SMB manager
    logging.basicConfig(level=logging.INFO)

    manager = create_smb_manager_from_env()

    print("Configured NAS:")
    for name in manager.nas_configs:
        print(f"  - {name}")

    print("\nTesting connections...")
    for name in manager.nas_configs:
        status = "✅" if manager.test_connection(name) else "❌"
        print(f"  {status} {name}")
