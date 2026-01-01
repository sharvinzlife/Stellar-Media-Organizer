#!/usr/bin/env python3
"""
Fix metadata for files on NAS
- Replace "Various Artists" with album name in ALBUMARTIST
- Fix track numbers from filenames
"""

import re
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv

load_dotenv("config.env")

try:
    import mutagen
    from mutagen.flac import FLAC
except ImportError:
    print("❌ mutagen not installed. Install with: pip install mutagen")
    sys.exit(1)

from core.nas_transfer import NASTransfer


def fix_file_metadata(local_path: Path, force_album: str | None = None) -> bool:
    """Fix metadata in a single file"""
    try:
        audio = mutagen.File(str(local_path), easy=True)
        if audio is None:
            return False

        album_artist = str(audio.get('albumartist', [''])[0])
        album = str(audio.get('album', [''])[0])

        modified = False

        # Force album name for playlist compilations
        if force_album and album != force_album:
            audio['album'] = force_album
            print(f"  ✓ ALBUM: {album} → {force_album}")
            modified = True

        # Set ALBUMARTIST to playlist name for compilations
        if force_album and album_artist != force_album:
            audio['albumartist'] = force_album
            print(f"  ✓ ALBUMARTIST: {album_artist} → {force_album}")
            modified = True

        # Fix Various Artists (legacy)
        va_patterns = ['v.a.', 'va', 'various artists', 'various']
        if album_artist.lower().strip() in va_patterns:
            target = force_album if force_album else album
            if target:
                audio['albumartist'] = target
                print(f"  ✓ ALBUMARTIST: Various Artists → {target}")
                modified = True

        # Fix track number from filename
        if 'tracknumber' not in audio or not audio['tracknumber'] or audio['tracknumber'][0] == '1':
            filename = local_path.stem
            track_match = re.match(r'^(\d+)\s*-', filename)
            if track_match:
                track_num = track_match.group(1)
                audio['tracknumber'] = track_num
                print(f"  ✓ TRACKNUMBER: {track_num}")
                modified = True

        if modified:
            audio.save()
            return True

        return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    playlist_name = "Hot Hits USA"  # Force all tracks to this album name

    print(f"🔧 Fixing metadata on NAS: {playlist_name}")
    print("=" * 60)
    print(f"Setting ALBUM and ALBUMARTIST to: {playlist_name}")
    print("=" * 60)

    # Initialize NAS transfer
    nas = NASTransfer()

    if 'lharmony' not in nas.nas_configs:
        print("❌ Lharmony NAS not configured")
        return 1

    config = nas.nas_configs['lharmony']

    # Create temp directory for downloading files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # List files on NAS using smbclient
        print("\n📥 Listing files on NAS...")

        import subprocess

        # Build smbclient command to list files
        smb_path = f"//{config.host}/{config.share}"
        list_cmd = [
            'smbclient',
            smb_path,
            '-U', f'{config.username}%{config.password}',
            '-c', 'cd "media/music/Hot Hits USA"; ls'
        ]

        try:
            result = subprocess.run(list_cmd, check=False, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"❌ Failed to list files: {result.stderr}")
                return 1

            # Parse file list
            files = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if '.flac' in line.lower() and not line.startswith('.'):
                    # smbclient format: "  filename.flac      N size date"
                    # Extract filename - it's before the file type indicator (N, A, D, etc.)
                    match = re.search(r'^\s*(.+\.flac)\s+[NAD]', line, re.IGNORECASE)
                    if match:
                        filename = match.group(1).strip()
                        files.append(filename)

            print(f"Found {len(files)} FLAC files")

            if not files:
                print("❌ No FLAC files found")
                return 1

            # Process each file
            fixed_count = 0
            for idx, filename in enumerate(sorted(files), 1):
                print(f"\n[{idx}/{len(files)}] {filename}")

                # Download file from NAS
                local_file = temp_path / filename
                download_cmd = [
                    'smbclient',
                    smb_path,
                    '-U', f'{config.username}%{config.password}',
                    '-c', f'cd "media/music/Hot Hits USA"; get "{filename}" "{local_file}"'
                ]

                result = subprocess.run(download_cmd, check=False, capture_output=True, timeout=120)
                if result.returncode != 0:
                    print("  ❌ Download failed")
                    continue

                # Fix metadata
                if fix_file_metadata(local_file, force_album=playlist_name):
                    # Upload back to NAS
                    upload_cmd = [
                        'smbclient',
                        smb_path,
                        '-U', f'{config.username}%{config.password}',
                        '-c', f'cd "media/music/Hot Hits USA"; put "{local_file}" "{filename}"'
                    ]

                    result = subprocess.run(upload_cmd, check=False, capture_output=True, timeout=120)
                    if result.returncode == 0:
                        print("  ✅ Updated on NAS")
                        fixed_count += 1
                    else:
                        print("  ❌ Upload failed")
                else:
                    print("  ⏭️  No changes needed")

                # Clean up temp file
                if local_file.exists():
                    local_file.unlink()

            print("\n" + "=" * 60)
            print(f"✅ Fixed {fixed_count}/{len(files)} files")
            print("\n🎬 Triggering Plex music library scan...")

            # Trigger Plex scan
            try:
                from core.plex_client import PlexClient
                plex = PlexClient()
                if plex.scan_music_library():
                    print("✅ Plex scan triggered")
                else:
                    print("⚠️  Plex scan failed")
            except Exception as e:
                print(f"⚠️  Could not trigger Plex scan: {e}")

            return 0

        except Exception as e:
            print(f"❌ Error: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
