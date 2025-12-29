#!/usr/bin/env python3
"""
Process Music Album with 7.0 Surround Upmix
Processes FLAC files, applies timbre-matching EQ, transfers to NAS, triggers Plex scan.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config.env")

from music_organizer import AudioEnhancer, AudioPreset, MusicMetadata
from core.nas_transfer import NASTransfer
from core.plex_client import PlexClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_album_info(folder_path: str) -> dict:
    """Extract album info from folder name, .nfo file, or first track metadata."""
    import re
    from pathlib import Path
    
    folder = Path(folder_path)
    folder_name = folder.name
    
    # Try to read from .nfo file first
    nfo_files = list(folder.glob('*.nfo'))
    if nfo_files:
        try:
            nfo_content = nfo_files[0].read_text(errors='ignore')
            
            # Extract album name from .nfo
            album_match = re.search(r'Album\.+:\s*(.+)', nfo_content)
            year_match = re.search(r'Year\.+:\s*(\d{4})', nfo_content)
            artist_match = re.search(r'Artist\.+:\s*(.+)', nfo_content)
            
            if album_match:
                album = album_match.group(1).strip()
                year = year_match.group(1) if year_match else ""
                artist = artist_match.group(1).strip() if artist_match else ""
                
                is_va = artist.lower() in ['v.a.', 'va', 'various artists', 'various']
                
                logger.info(f"📄 Found album info in .nfo: {album} ({year})")
                
                return {
                    'album': album,
                    'album_with_year': f"{album} ({year})" if year else album,
                    'year': year,
                    'is_va': is_va
                }
        except Exception as e:
            logger.debug(f"Could not read .nfo file: {e}")
    
    # Try to read from first FLAC file metadata
    flac_files = sorted(folder.glob('*.flac'))
    if flac_files:
        try:
            import mutagen
            audio = mutagen.File(str(flac_files[0]), easy=True)
            if audio:
                album = str(audio.get('album', [''])[0])
                year = str(audio.get('date', [''])[0])[:4]
                album_artist = str(audio.get('albumartist', audio.get('artist', ['']))[0])
                
                if album:
                    is_va = album_artist.lower() in ['v.a.', 'va', 'various artists', 'various']
                    
                    logger.info(f"🎵 Found album info in metadata: {album} ({year})")
                    
                    return {
                        'album': album,
                        'album_with_year': f"{album} ({year})" if year else album,
                        'year': year,
                        'is_va': is_va
                    }
        except Exception as e:
            logger.debug(f"Could not read FLAC metadata: {e}")
    
    # Fallback: parse folder name
    # Remove quality tags like [Flac 16-44], [MP3 320], etc.
    folder_clean = re.sub(r'\s*\[.*?\]\s*$', '', folder_name).strip()
    
    # Check for "Artist - Album" pattern
    if ' - ' in folder_clean:
        parts = folder_clean.split(' - ', 1)
        artist_part = parts[0].strip()
        album_part = parts[1].strip() if len(parts) > 1 else folder_clean
        
        # Extract year
        year_match = re.search(r'\((\d{4})', album_part)
        year = year_match.group(1) if year_match else ""
        
        # Clean album name (remove year suffix for folder)
        album_clean = re.sub(r'\s*\(\d{4}[^)]*\)\s*$', '', album_part).strip()
        
        return {
            'album': album_clean,
            'album_with_year': f"{album_clean} ({year})" if year else album_clean,
            'year': year,
            'is_va': artist_part.lower() in ['v.a.', 'va', 'various artists', 'various']
        }
    
    return {'album': folder_clean, 'album_with_year': folder_clean, 'year': '', 'is_va': False}


def process_album(
    source_dir: str,
    output_dir: str = "/tmp/music_processed",
    enhance: bool = True,
    transfer_to_nas: bool = True,
    trigger_plex: bool = True
):
    """
    Process an album with 7.0 surround upmix.
    
    Args:
        source_dir: Directory containing FLAC files
        output_dir: Local output directory for processed files
        enhance: Apply 7.0 surround upmix
        transfer_to_nas: Transfer to Lharmony NAS
        trigger_plex: Trigger Plex music library scan
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return
    
    # Extract album info from folder name
    album_info = extract_album_info(source_dir)
    logger.info(f"📀 Album: {album_info['album_with_year']}")
    logger.info(f"   V.A. Compilation: {album_info['is_va']}")
    
    # Create output folder structure: /Album Name (Year)/
    album_folder = output_path / album_info['album_with_year']
    album_folder.mkdir(parents=True, exist_ok=True)
    
    # Find all FLAC files
    flac_files = sorted(source_path.glob('*.flac'))
    logger.info(f"📁 Found {len(flac_files)} FLAC files")
    
    if not flac_files:
        logger.error("No FLAC files found!")
        return
    
    # Initialize enhancer
    enhancer = None
    if enhance:
        try:
            enhancer = AudioEnhancer()
            logger.info("🔊 7.0 Surround upmix enabled (Polk T50 + Sony timbre-matching)")
        except Exception as e:
            logger.error(f"Failed to initialize enhancer: {e}")
            enhance = False
    
    # Process each file
    processed_files = []
    for idx, flac_file in enumerate(flac_files, 1):
        try:
            # Output filename (keep original name, change extension if needed)
            output_file = album_folder / flac_file.name
            
            if enhance and enhancer:
                logger.info(f"🔊 ({idx}/{len(flac_files)}) Upmixing: {flac_file.name}")
                success = enhancer.enhance_audio(
                    str(flac_file),
                    str(output_file),
                    preset=AudioPreset.SURROUND_7_0
                )
                if success:
                    processed_files.append(output_file)
                else:
                    logger.warning(f"⚠️ Upmix failed, copying original")
                    import shutil
                    shutil.copy2(flac_file, output_file)
                    processed_files.append(output_file)
            else:
                logger.info(f"📁 ({idx}/{len(flac_files)}) Copying: {flac_file.name}")
                import shutil
                shutil.copy2(flac_file, output_file)
                processed_files.append(output_file)
                
        except Exception as e:
            logger.error(f"❌ Error processing {flac_file.name}: {e}")
    
    logger.info(f"✅ Processed {len(processed_files)}/{len(flac_files)} files")
    
    # Fix V.A./Various Artists in ALBUMARTIST tag - Plex uses this for grouping
    if album_info['is_va'] and processed_files:
        logger.info("🔧 Fixing V.A. metadata in ALBUMARTIST tags...")
        import shutil
        if shutil.which('metaflac'):
            for file_path in processed_files:
                if file_path.suffix.lower() == '.flac':
                    try:
                        subprocess.run([
                            'metaflac',
                            '--remove-tag=album_artist',
                            '--remove-tag=ALBUMARTIST',
                            str(file_path)
                        ], capture_output=True)
                        subprocess.run([
                            'metaflac',
                            f'--set-tag=ALBUMARTIST={album_info["album"]}',
                            str(file_path)
                        ], capture_output=True)
                    except Exception as e:
                        logger.warning(f"Could not fix metadata for {file_path.name}: {e}")
            logger.info(f"✅ Fixed ALBUMARTIST tag to: {album_info['album']}")
        else:
            logger.warning("⚠️ metaflac not installed - V.A. metadata not fixed. Install with: apt install flac")
    
    # Copy cover image if exists
    cover_sources = ['Cover.jpg', 'cover.jpg', 'Folder.jpg', 'folder.jpg', 'Front.jpg', 'front.jpg']
    for cover_name in cover_sources:
        cover_src = source_path / cover_name
        if cover_src.exists():
            cover_dst = album_folder / "cover.jpg"
            import shutil
            shutil.copy2(cover_src, cover_dst)
            logger.info(f"📷 Copied album cover: {cover_name} -> cover.jpg")
            break
    
    # Transfer to NAS
    if transfer_to_nas and processed_files:
        logger.info("📤 Transferring to NAS (Lharmony)...")
        
        try:
            nas = NASTransfer()
            
            if not nas.test_connection("lharmony"):
                logger.error("❌ NAS connection failed")
            else:
                transferred = 0
                for file_path in processed_files:
                    # Remote path: music/Album Name (Year)/filename.flac
                    # Note: Don't include leading slash - NAS transfer adds media_path prefix
                    remote_path = f"music/{album_info['album_with_year']}/{file_path.name}"
                    
                    if nas.transfer_file(str(file_path), remote_path, "lharmony"):
                        transferred += 1
                    else:
                        logger.warning(f"⚠️ Failed to transfer: {file_path.name}")
                
                # Transfer cover image if exists
                cover_file = album_folder / "cover.jpg"
                if cover_file.exists():
                    remote_cover = f"music/{album_info['album_with_year']}/cover.jpg"
                    if nas.transfer_file(str(cover_file), remote_cover, "lharmony"):
                        logger.info("✅ Transferred: cover.jpg")
                        transferred += 1
                
                logger.info(f"📤 Transferred {transferred}/{len(processed_files)} files to NAS")
                
        except Exception as e:
            logger.error(f"❌ NAS transfer error: {e}")
    
    # Trigger Plex scan
    if trigger_plex:
        logger.info("🎬 Triggering Plex music library scan...")
        
        try:
            import os
            plex_url = os.getenv("PLEX_SERVER_URL", "http://10.1.0.105:32400")
            plex_token = os.getenv("PLEX_TOKEN", "")
            
            if plex_token:
                plex = PlexClient(plex_url, plex_token)
                # Scan music library
                if plex.scan_library_by_name("Music"):
                    logger.info("✅ Plex music library scan triggered")
                else:
                    logger.warning("⚠️ Could not find Music library in Plex")
            else:
                logger.warning("⚠️ PLEX_TOKEN not configured")
        except Exception as e:
            logger.warning(f"⚠️ Plex scan failed: {e}")
    
    logger.info("🎉 Processing complete!")
    logger.info(f"   Output: {album_folder}")
    
    print("\n📺 Denon AVR Calibration Tips:")
    print("   • Channel Levels: Increase Surround/Back by +1.5dB to +2.0dB")
    print("   • Crossover: Set Front Speakers to 'Large' (no sub)")
    print("   • Plex: Use 'Direct Play' for best quality")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process music album with 7.0 surround upmix")
    parser.add_argument('source', help='Source directory containing FLAC files')
    parser.add_argument('-o', '--output', default='/tmp/music_processed', help='Output directory')
    parser.add_argument('--no-enhance', action='store_true', help='Skip 7.0 surround upmix')
    parser.add_argument('--no-transfer', action='store_true', help='Skip NAS transfer')
    parser.add_argument('--no-plex', action='store_true', help='Skip Plex scan')
    
    args = parser.parse_args()
    
    process_album(
        source_dir=args.source,
        output_dir=args.output,
        enhance=not args.no_enhance,
        transfer_to_nas=not args.no_transfer,
        trigger_plex=not args.no_plex
    )
