#!/usr/bin/env python3
"""
Fix metadata for files on NAS
- Replace "Various Artists" with album name in ALBUMARTIST
- Fix track numbers from filenames
"""

import sys
import re
import tempfile
import shutil
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


def fix_file_metadata(local_path: Path) -> bool:
    """Fix metadata in a single file"""
    try:
        audio = mutagen.File(str(local_path), easy=True)
        if audio is None:
            return False
        
        album_artist = str(audio.get('albumartist', [''])[0])
        album = str(audio.get('album', [''])[0])
        
        modified = False
        
        # Fix Various Artists
        va_patterns = ['v.a.', 'va', 'various artists', 'various']
        if album_artist.lower().strip() in va_patterns:
            if album:
                audio['albumartist'] = album
                print(f"  ✓ ALBUMARTIST: Various Artists → {album}")
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
    nas_path = "smb://lharmony-nas.local/data/media/music/Hot Hits USA/"
    
    print("🔧 Fixing metadata on NAS: Hot Hits USA")
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
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
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
                
                result = subprocess.run(download_cmd, capture_output=True, timeout=120)
                if result.returncode != 0:
                    print(f"  ❌ Download failed")
                    continue
                
                # Fix metadata
                if fix_file_metadata(local_file):
                    # Upload back to NAS
                    upload_cmd = [
                        'smbclient',
                        smb_path,
                        '-U', f'{config.username}%{config.password}',
                        '-c', f'cd "media/music/Hot Hits USA"; put "{local_file}" "{filename}"'
                    ]
                    
                    result = subprocess.run(upload_cmd, capture_output=True, timeout=120)
                    if result.returncode == 0:
                        print(f"  ✅ Updated on NAS")
                        fixed_count += 1
                    else:
                        print(f"  ❌ Upload failed")
                else:
                    print(f"  ⏭️  No changes needed")
                
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
