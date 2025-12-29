#!/usr/bin/env python3
"""
Music Organizer Pro - Professional Music Library Management
Integrates MusicBrainz metadata lookup with FFmpeg audio enhancement
Outputs Plex/Jellyfin compatible folder structure
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Audio file handling
try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# MusicBrainz API
try:
    import musicbrainzngs
    MUSICBRAINZ_AVAILABLE = True
except ImportError:
    MUSICBRAINZ_AVAILABLE = False

# AI Metadata Extraction
try:
    from core.ai_metadata_extractor import AIMetadataExtractor, MusicMetadata as AIMusicMetadata
    AI_EXTRACTION_AVAILABLE = True
except ImportError:
    AI_EXTRACTION_AVAILABLE = False
    AIMetadataExtractor = None

# Discogs API
try:
    from core.discogs_lookup import DiscogsClient, lookup_track as discogs_lookup_track
    DISCOGS_AVAILABLE = True
except ImportError:
    DISCOGS_AVAILABLE = False
    DiscogsClient = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AudioPreset(Enum):
    """Audio enhancement presets"""
    SURROUND_7_0 = "surround_7_0"  # 7.0 Timbre-Matching for Polk T50 + Sony surrounds


@dataclass
class AudioSettings:
    """Audio enhancement settings for 7.0 surround upmix"""
    # 7.0 Surround Timbre-Matching Settings
    # Optimized for: Polk T50 fronts + Sony surround speakers + Denon AVR
    presence_boost: float = 3.0    # 3500Hz boost for Sony surrounds (dB)
    air_boost: float = 2.0         # 12000Hz boost for treble matching (dB)
    
    @classmethod
    def from_preset(cls, preset: AudioPreset) -> 'AudioSettings':
        """Create settings from a preset"""
        presets = {
            # SURROUND_7_0: Timbre-matching for Polk T50 + Sony surrounds
            # - Presence boost (3500Hz): Improves clarity on warmer Sony surrounds
            # - Air boost (12000Hz): Matches Polk tweeter detail
            AudioPreset.SURROUND_7_0: cls(
                presence_boost=3.0,
                air_boost=2.0
            ),
        }
        return presets.get(preset, cls())


@dataclass  
class MusicMetadata:
    """Music file metadata"""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    track_number: int = 0
    total_tracks: int = 0
    disc_number: int = 1
    total_discs: int = 1
    year: str = ""
    genre: str = ""
    musicbrainz_recording_id: str = ""
    musicbrainz_release_id: str = ""
    musicbrainz_artist_id: str = ""
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


class MusicBrainzClient:
    """MusicBrainz API client for metadata lookup"""
    
    def __init__(self, client_id: str = "", client_secret: str = ""):
        if not MUSICBRAINZ_AVAILABLE:
            raise ImportError("musicbrainzngs not installed. Run: pip install musicbrainzngs")
        
        musicbrainzngs.set_useragent(
            "MediaOrganizerPro",
            "1.0",
            "https://github.com/media-organizer-pro"
        )
        
        # OAuth credentials (optional, for higher rate limits)
        self.client_id = client_id
        self.client_secret = client_secret
    
    def search_recording(self, title: str, artist: str = "", album: str = "") -> Optional[Dict]:
        """Search for a recording by title, artist, album"""
        try:
            query_parts = [f'recording:"{title}"']
            if artist:
                query_parts.append(f'artist:"{artist}"')
            if album:
                query_parts.append(f'release:"{album}"')
            
            query = " AND ".join(query_parts)
            result = musicbrainzngs.search_recordings(query=query, limit=5)
            
            if result.get('recording-list'):
                # Return best match (first result)
                return result['recording-list'][0]
            return None
        except Exception as e:
            logger.error(f"MusicBrainz search error: {e}")
            return None
    
    def get_release_info(self, release_id: str) -> Optional[Dict]:
        """Get detailed release (album) information"""
        try:
            result = musicbrainzngs.get_release_by_id(
                release_id,
                includes=['artists', 'recordings', 'release-groups']
            )
            return result.get('release')
        except Exception as e:
            logger.error(f"MusicBrainz release lookup error: {e}")
            return None
    
    def lookup_metadata(self, title: str, artist: str = "", album: str = "") -> Optional[MusicMetadata]:
        """Lookup and return structured metadata"""
        recording = self.search_recording(title, artist, album)
        if not recording:
            return None
        
        metadata = MusicMetadata()
        metadata.title = recording.get('title', title)
        metadata.musicbrainz_recording_id = recording.get('id', '')
        
        # Get artist info
        if recording.get('artist-credit'):
            artists = recording['artist-credit']
            if artists:
                first_artist = artists[0].get('artist', {})
                metadata.artist = first_artist.get('name', '')
                metadata.musicbrainz_artist_id = first_artist.get('id', '')
        
        # Get release (album) info
        if recording.get('release-list'):
            # Prefer official album releases
            releases = recording['release-list']
            best_release = None
            for rel in releases:
                status = rel.get('status', '').lower()
                if status == 'official':
                    best_release = rel
                    break
            if not best_release:
                best_release = releases[0]
            
            metadata.album = best_release.get('title', '')
            metadata.musicbrainz_release_id = best_release.get('id', '')
            metadata.year = best_release.get('date', '')[:4] if best_release.get('date') else ''
            
            # Get track number from medium-list
            if best_release.get('medium-list'):
                for medium in best_release['medium-list']:
                    if medium.get('track-list'):
                        for track in medium['track-list']:
                            if track.get('recording', {}).get('id') == recording.get('id'):
                                metadata.track_number = int(track.get('number', 0))
                                metadata.disc_number = int(medium.get('position', 1))
                                break
        
        return metadata


class AudioEnhancer:
    """
    FFmpeg-based 7.0 Surround Upmixer with Timbre-Matching
    
    Optimized for: Polk T50 front towers + Sony surround speakers + Denon AVR
    
    This processor:
    1. Upmixes stereo to 7.0 surround
    2. Applies presence boost (3500Hz) to surrounds for Sony speaker clarity
    3. Applies air boost (12000Hz) to match Polk tweeter detail
    4. Outputs lossless FLAC in MKV container for Plex Direct Play
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.wma'}
    
    def __init__(self):
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Verify FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg not found. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
    
    def _fix_va_metadata(self, file_path: str) -> bool:
        """
        Fix V.A./Various Artists in ALBUMARTIST tag.
        Plex uses ALBUMARTIST for grouping - we replace V.A. with album name.
        Also ensures TRACKNUMBER is properly set.
        """
        try:
            if not MUTAGEN_AVAILABLE:
                return False
            
            audio = mutagen.File(file_path, easy=True)
            if audio is None:
                return False
            
            album_artist = str(audio.get('albumartist', [''])[0])
            album = str(audio.get('album', [''])[0])
            
            modified = False
            
            # Check if album_artist is V.A. or similar
            va_patterns = ['v.a.', 'va', 'various artists', 'various']
            if album_artist.lower().strip() in va_patterns:
                # Replace with album name
                if album:
                    audio['albumartist'] = album
                    logger.debug(f"Fixed ALBUMARTIST: V.A. -> {album}")
                    modified = True
            
            # Ensure TRACKNUMBER is set (sometimes gets lost in processing)
            if 'tracknumber' not in audio or not audio['tracknumber']:
                # Try to extract from filename (e.g., "01 - Artist - Title.flac")
                import re
                filename = Path(file_path).stem
                track_match = re.match(r'^(\d+)\s*-', filename)
                if track_match:
                    track_num = track_match.group(1)
                    audio['tracknumber'] = track_num
                    logger.debug(f"Fixed TRACKNUMBER: {track_num}")
                    modified = True
            
            if modified:
                audio.save()
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Could not fix V.A. metadata: {e}")
            return False
    
    def _build_7_0_surround_filter(self, settings: AudioSettings) -> str:
        """
        Build FFmpeg filter for 7.0 surround upmix with timbre-matching EQ
        
        What this does for your specific gear:
        - Presence Boost (3500Hz): Sony surround speakers often have a "warmer" or 
          "muffled" mid-range compared to Polk T50s. We boost 3.5kHz to improve 
          clarity and dialogue definition in the surround field.
        - Brightness/Air (12000Hz): Adds boost to highest frequencies to match 
          the detailed tweeter response of your front Polk speakers.
        - Multi-Channel Mapping: Treats Side and Back channels independently from 
          Fronts, so Polk T50s remain untouched while only Sony speakers are "brightened".
        
        7.0 Channel Layout: FL FR FC LFE BL BR SL SR (but 7.0 has no LFE, so: FL FR FC BL BR SL SR)
        We apply EQ to: SL, SR, BL, BR (surround channels for Sony speakers)
        We leave untouched: FL, FR, FC (front channels for Polk T50s)
        """
        presence_boost = settings.presence_boost  # 3500Hz boost (dB)
        air_boost = settings.air_boost            # 12000Hz boost (dB)
        
        # 7.0 Timbre-Matching Surround Filter
        # Step 1: Upmix stereo to 7.0 surround
        # Step 2: Split into individual channels
        # Step 3: Apply EQ only to surround channels (SL, SR, BL, BR)
        # Step 4: Recombine into 7.0 output
        #
        # 7.0 layout: FL FR FC BL BR SL SR (7 channels)
        # Channels 0-2 (FL, FR, FC) = Polk T50 fronts - no EQ
        # Channels 3-6 (BL, BR, SL, SR) = Sony surrounds - apply timbre-matching EQ
        filter_complex = (
            # Upmix to 7.0 surround
            f"[0:a]surround=chl_out=7.0[7ch];"
            # Split into individual mono channels
            f"[7ch]channelsplit=channel_layout=7.0[FL][FR][FC][BL][BR][SL][SR];"
            # Apply timbre-matching EQ to surround channels (Sony speakers)
            f"[SL]equalizer=f=3500:t=q:w=1:g={presence_boost},equalizer=f=12000:t=q:w=1:g={air_boost}[SL_eq];"
            f"[SR]equalizer=f=3500:t=q:w=1:g={presence_boost},equalizer=f=12000:t=q:w=1:g={air_boost}[SR_eq];"
            f"[BL]equalizer=f=3500:t=q:w=1:g={presence_boost},equalizer=f=12000:t=q:w=1:g={air_boost}[BL_eq];"
            f"[BR]equalizer=f=3500:t=q:w=1:g={presence_boost},equalizer=f=12000:t=q:w=1:g={air_boost}[BR_eq];"
            # Recombine into 7.0 output (FL FR FC BL BR SL SR)
            f"[FL][FR][FC][BL_eq][BR_eq][SL_eq][SR_eq]join=inputs=7:channel_layout=7.0[out]"
        )
        
        return filter_complex
    
    def enhance_audio(
        self,
        input_path: str,
        output_path: str,
        settings: Optional[AudioSettings] = None,
        preset: AudioPreset = AudioPreset.SURROUND_7_0,
        preserve_metadata: bool = True,
        output_format: Optional[str] = None
    ) -> bool:
        """
        Upmix stereo audio to 7.0 surround with timbre-matching EQ
        
        Args:
            input_path: Source audio file (stereo)
            output_path: Destination path (will be .flac with 7.0 audio)
            settings: Custom AudioSettings (overrides preset)
            preset: Audio enhancement preset (SURROUND_7_0)
            preserve_metadata: Copy metadata to output
            output_format: Ignored - always outputs multi-channel FLAC
        
        Returns:
            True if successful
        
        Hardware Calibration Tips (Denon AVR):
        - Channel Levels: Sony surrounds are often less efficient than Polk towers.
          Go to Setup > Speakers > Manual Setup > Levels and increase Surround 
          and Surround Back channels by +1.5dB or +2.0dB.
        - Crossover: Since you have no sub, ensure Front Speakers are set to "Large" 
          so Polk T50s handle all the bass for the whole system.
        - Plex Playback: Ensure you are using "Direct Play" for best quality.
        """
        if settings is None:
            settings = AudioSettings.from_preset(preset)
        
        # Build 7.0 surround filter with timbre-matching
        filter_complex = self._build_7_0_surround_filter(settings)
        
        # Output to FLAC (supports multi-channel audio natively)
        if not output_path.endswith('.flac'):
            output_path = str(Path(output_path).with_suffix('.flac'))
        
        # Build FFmpeg command for 7.0 surround upmix
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map_metadata', '0',      # Copy all metadata from input
            '-c:a', 'flac',           # Lossless FLAC codec
            '-sample_fmt', 's32',      # 32-bit for quality
            output_path
        ]
        
        try:
            logger.info(f"🔊 Upmixing to 7.0 surround: {Path(input_path).name}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                check=True, 
                encoding='utf-8', 
                errors='replace'
            )
            
            # Verify output file exists and has content
            output_file = Path(output_path)
            if output_file.exists() and output_file.stat().st_size > 0:
                logger.info(f"✅ 7.0 Surround FLAC: {input_path} -> {output_path}")
                
                # Fix V.A./Various Artists in ALBUMARTIST tag for Plex
                self._fix_va_metadata(output_path)
                
                return True
            else:
                logger.error(f"FFmpeg produced empty output for: {input_path}")
                if output_file.exists():
                    output_file.unlink()
                return False
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr[:500] if e.stderr else 'No error message'
            logger.error(f"FFmpeg error for {input_path}: {error_msg}")
            # Clean up any partial output
            output_file = Path(output_path)
            if output_file.exists():
                output_file.unlink()
            return False
    
    def batch_enhance(
        self,
        input_dir: str,
        output_dir: str,
        preset: AudioPreset = AudioPreset.SURROUND_7_0,
        output_format: str = "flac"
    ) -> Tuple[int, int]:
        """
        Batch upmix all audio files in directory to 7.0 surround
        
        Returns:
            Tuple of (successful, failed) counts
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        success = 0
        failed = 0
        
        for file in input_path.rglob('*'):
            if file.suffix.lower() in self.SUPPORTED_FORMATS:
                # Preserve relative path structure, output as .flac
                rel_path = file.relative_to(input_path)
                out_file = output_path / rel_path.with_suffix('.flac')
                out_file.parent.mkdir(parents=True, exist_ok=True)
                
                if self.enhance_audio(str(file), str(out_file), preset=preset):
                    success += 1
                else:
                    failed += 1
        
        return success, failed


class MusicLibraryOrganizer:
    """
    Organize music files for Plex/Jellyfin/Emby
    
    Output structure:
    /Music
      /Artist Name
        /Album Name (Year)
          01 - Track Title.flac
          02 - Track Title.flac
          cover.jpg
    """
    
    AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.wma', '.alac'}
    
    def __init__(
        self,
        musicbrainz_client_id: str = "",
        musicbrainz_client_secret: str = "",
        use_musicbrainz: bool = True,
        use_ai_extraction: bool = True,
        use_discogs: bool = True,
        discogs_api_token: str = ""
    ):
        self.use_musicbrainz = use_musicbrainz and MUSICBRAINZ_AVAILABLE
        self.use_ai_extraction = use_ai_extraction and AI_EXTRACTION_AVAILABLE
        self.use_discogs = use_discogs and DISCOGS_AVAILABLE
        self.mb_client = None
        self.ai_extractor = None
        self.discogs_client = None
        
        if self.use_musicbrainz:
            try:
                self.mb_client = MusicBrainzClient(musicbrainz_client_id, musicbrainz_client_secret)
            except ImportError:
                logger.warning("MusicBrainz not available, using embedded metadata only")
                self.use_musicbrainz = False
        
        if self.use_ai_extraction:
            try:
                self.ai_extractor = AIMetadataExtractor()
                logger.info("✅ AI metadata extraction enabled")
            except Exception as e:
                logger.warning(f"AI extraction not available: {e}")
                self.use_ai_extraction = False
        
        if self.use_discogs:
            try:
                token = discogs_api_token or os.getenv("DISCOGS_API_TOKEN", "")
                if token:
                    self.discogs_client = DiscogsClient(token)
                    logger.info("✅ Discogs metadata lookup enabled")
                else:
                    self.use_discogs = False
                    logger.info("Discogs API token not configured")
            except Exception as e:
                logger.warning(f"Discogs not available: {e}")
                self.use_discogs = False
        
        self.enhancer = AudioEnhancer()
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename"""
        # Remove characters not allowed in filenames
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        # Replace multiple spaces with single space
        name = re.sub(r'\s+', ' ', name).strip()
        # Limit length
        return name[:200] if len(name) > 200 else name
    
    def _extract_metadata_from_filename(self, file_path: str) -> Optional[MusicMetadata]:
        """Extract metadata from filename using AI extraction."""
        if not self.use_ai_extraction or not self.ai_extractor:
            return None
        
        try:
            filename = Path(file_path).name
            ai_result = self.ai_extractor.extract_music_metadata(filename, use_ai_fallback=True)
            
            if ai_result and ai_result.confidence >= 0.7:
                metadata = MusicMetadata()
                metadata.title = ai_result.title or ""
                metadata.artist = ai_result.artist or ""
                metadata.album = ai_result.album or ""
                metadata.track_number = ai_result.track_number or 0
                metadata.year = str(ai_result.year) if ai_result.year else ""
                metadata.genre = ai_result.genre or ""
                logger.debug(f"AI extracted from filename: {ai_result.artist} - {ai_result.title}")
                return metadata
        except Exception as e:
            logger.debug(f"AI filename extraction failed: {e}")
        
        return None
    
    def _read_embedded_metadata(self, file_path: str) -> MusicMetadata:
        """Read metadata from audio file tags"""
        if not MUTAGEN_AVAILABLE:
            return MusicMetadata()
        
        metadata = MusicMetadata()
        
        try:
            audio = mutagen.File(file_path, easy=True)
            if audio is None:
                return metadata
            
            # Common tag mappings
            metadata.title = str(audio.get('title', [''])[0])
            metadata.artist = str(audio.get('artist', [''])[0])
            metadata.album = str(audio.get('album', [''])[0])
            metadata.album_artist = str(audio.get('albumartist', audio.get('artist', ['']))[0])
            metadata.genre = str(audio.get('genre', [''])[0])
            metadata.year = str(audio.get('date', audio.get('year', ['']))[0])[:4]
            
            # Track number (handle "1/12" format)
            track_str = str(audio.get('tracknumber', ['0'])[0])
            if '/' in track_str:
                parts = track_str.split('/')
                metadata.track_number = int(parts[0]) if parts[0].isdigit() else 0
                metadata.total_tracks = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            else:
                metadata.track_number = int(track_str) if track_str.isdigit() else 0
            
            # Disc number
            disc_str = str(audio.get('discnumber', ['1'])[0])
            if '/' in disc_str:
                parts = disc_str.split('/')
                metadata.disc_number = int(parts[0]) if parts[0].isdigit() else 1
                metadata.total_discs = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            else:
                metadata.disc_number = int(disc_str) if disc_str.isdigit() else 1
            
            # Duration
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                metadata.duration = audio.info.length
            
        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")
        
        # If embedded metadata is missing key fields, try AI extraction from filename
        if not metadata.title or not metadata.artist:
            ai_metadata = self._extract_metadata_from_filename(file_path)
            if ai_metadata:
                # Fill in missing fields from AI extraction
                if not metadata.title and ai_metadata.title:
                    metadata.title = ai_metadata.title
                if not metadata.artist and ai_metadata.artist:
                    metadata.artist = ai_metadata.artist
                if not metadata.album and ai_metadata.album:
                    metadata.album = ai_metadata.album
                if not metadata.track_number and ai_metadata.track_number:
                    metadata.track_number = ai_metadata.track_number
                if not metadata.year and ai_metadata.year:
                    metadata.year = ai_metadata.year
                logger.info(f"Filled missing metadata from filename: {metadata.artist} - {metadata.title}")
        
        return metadata
    
    def _write_metadata(self, file_path: str, metadata: MusicMetadata) -> bool:
        """Write metadata to audio file tags"""
        if not MUTAGEN_AVAILABLE:
            return False
        
        try:
            audio = mutagen.File(file_path, easy=True)
            if audio is None:
                return False
            
            # For compilation albums, set album_artist to album name (not V.A.)
            album_artist = metadata.album_artist or metadata.artist or ""
            if self._is_various_artists(album_artist):
                # Use album name as album artist for compilations
                album_artist = metadata.album or "Compilation"
            
            if metadata.title:
                audio['title'] = metadata.title
            if metadata.artist:
                audio['artist'] = metadata.artist  # Keep individual track artist
            if metadata.album:
                audio['album'] = metadata.album
            if album_artist:
                audio['albumartist'] = album_artist  # Album name for compilations
            if metadata.genre:
                audio['genre'] = metadata.genre
            if metadata.year:
                audio['date'] = metadata.year
            if metadata.track_number:
                if metadata.total_tracks:
                    audio['tracknumber'] = f"{metadata.track_number}/{metadata.total_tracks}"
                else:
                    audio['tracknumber'] = str(metadata.track_number)
            if metadata.disc_number:
                if metadata.total_discs > 1:
                    audio['discnumber'] = f"{metadata.disc_number}/{metadata.total_discs}"
                else:
                    audio['discnumber'] = str(metadata.disc_number)
            
            audio.save()
            return True
        except Exception as e:
            logger.error(f"Error writing metadata to {file_path}: {e}")
            return False
    
    def _lookup_metadata(self, file_path: str, existing: MusicMetadata) -> MusicMetadata:
        """Enhance metadata using MusicBrainz lookup, with Discogs fallback"""
        # Only lookup if we have at least a title
        if not existing.title:
            return existing
        
        # Try MusicBrainz first
        if self.use_musicbrainz and self.mb_client:
            mb_metadata = self.mb_client.lookup_metadata(
                title=existing.title,
                artist=existing.artist,
                album=existing.album
            )
            
            if mb_metadata:
                # Merge: prefer MusicBrainz data but keep existing if MB is empty
                if mb_metadata.title:
                    existing.title = mb_metadata.title
                if mb_metadata.artist:
                    existing.artist = mb_metadata.artist
                if mb_metadata.album:
                    existing.album = mb_metadata.album
                if mb_metadata.year:
                    existing.year = mb_metadata.year
                if mb_metadata.track_number:
                    existing.track_number = mb_metadata.track_number
                if mb_metadata.musicbrainz_recording_id:
                    existing.musicbrainz_recording_id = mb_metadata.musicbrainz_recording_id
                if mb_metadata.musicbrainz_release_id:
                    existing.musicbrainz_release_id = mb_metadata.musicbrainz_release_id
                if mb_metadata.musicbrainz_artist_id:
                    existing.musicbrainz_artist_id = mb_metadata.musicbrainz_artist_id
                return existing
        
        # Fallback to Discogs if MusicBrainz didn't find anything
        if self.use_discogs and self.discogs_client:
            try:
                discogs_track = self.discogs_client.search_track(
                    title=existing.title,
                    artist=existing.artist
                )
                
                if discogs_track:
                    logger.info(f"Discogs found: {discogs_track.artist} - {discogs_track.title}")
                    # Merge Discogs data
                    if discogs_track.title:
                        existing.title = discogs_track.title
                    if discogs_track.artist:
                        existing.artist = discogs_track.artist
                    if discogs_track.album:
                        existing.album = discogs_track.album
                    if discogs_track.year:
                        existing.year = str(discogs_track.year)
                    if discogs_track.track_number:
                        existing.track_number = discogs_track.track_number
                    if discogs_track.genre:
                        existing.genre = discogs_track.genre
            except Exception as e:
                logger.debug(f"Discogs lookup failed: {e}")
        
        return existing
    
    def _is_various_artists(self, artist: str) -> bool:
        """Check if artist name indicates a compilation/various artists album"""
        if not artist:
            return False
        va_patterns = [
            'various artists', 'v.a.', 'va', 'various', 'compilation',
            'soundtrack', 'ost', 'original soundtrack', 'mixed by',
            'various artist', 'varios artistas', 'diverse', 'v. a.'
        ]
        artist_lower = artist.lower().strip()
        return any(pattern in artist_lower or artist_lower == pattern for pattern in va_patterns)
    
    def _extract_album_from_folder(self, folder_path: str) -> Optional[Dict[str, str]]:
        """
        Extract album metadata from folder name like:
        'V.A. - Music That Makes Me Want To Dance (2025 Dance) [Flac 16-44]'
        
        Returns dict with: album, year, artist (cleaned)
        """
        folder_name = Path(folder_path).name
        
        # Pattern: "Artist - Album Name (Year Info) [Quality]"
        # We want to extract album name and year, skip V.A./Various Artists
        
        # Remove quality tags like [Flac 16-44], [MP3 320], etc.
        folder_clean = re.sub(r'\s*\[.*?\]\s*$', '', folder_name).strip()
        
        # Check for "Artist - Album" pattern
        if ' - ' in folder_clean:
            parts = folder_clean.split(' - ', 1)
            artist_part = parts[0].strip()
            album_part = parts[1].strip() if len(parts) > 1 else folder_clean
            
            # If artist is V.A. or Various Artists, use album name as album_artist
            if self._is_various_artists(artist_part):
                # Extract year from album part if present
                year_match = re.search(r'\((\d{4})\s*[^)]*\)', album_part)
                year = year_match.group(1) if year_match else ""
                
                # Clean album name - keep the descriptive part
                # "Music That Makes Me Want To Dance (2025 Dance)" -> keep as is for album
                album_name = album_part
                
                return {
                    'album': album_name,
                    'album_artist': album_name,  # Use album name as album_artist
                    'year': year,
                    'is_compilation': True
                }
        
        # No "Artist - Album" pattern, just use folder name
        year_match = re.search(r'\((\d{4})\)', folder_clean)
        year = year_match.group(1) if year_match else ""
        
        return {
            'album': folder_clean,
            'album_artist': folder_clean,
            'year': year,
            'is_compilation': False
        }
    
    def _generate_output_path(
        self,
        output_dir: str,
        metadata: MusicMetadata,
        original_ext: str,
        source_folder: str = ""
    ) -> Path:
        """
        Generate output path for music files.
        
        For compilations (V.A., Various Artists):
        - Uses album name as folder: /Album Name (Year)/01 - Track.mkv
        - NEVER uses "V.A." or "Various Artists" in folder names
        
        For regular albums:
        - Uses artist/album structure: /Artist/Album (Year)/01 - Track.mkv
        """
        # Try to extract album info from source folder if available
        folder_info = None
        if source_folder:
            folder_info = self._extract_album_from_folder(source_folder)
        
        # Determine album and album_artist
        album_artist = metadata.album_artist or metadata.artist or ""
        album = metadata.album or ""
        year = metadata.year or ""
        
        # If folder info available and it's a compilation, use that
        if folder_info and folder_info.get('is_compilation'):
            album = folder_info.get('album', album) or album
            album_artist = folder_info.get('album_artist', album) or album  # Use album name
            year = folder_info.get('year', year) or year
        
        # ALWAYS skip V.A./Various Artists - use album name instead
        if self._is_various_artists(album_artist) or not album_artist:
            album_artist = album or "Unknown Album"
        
        # Sanitize names
        album = self._sanitize_filename(album or "Unknown Album")
        album_artist = self._sanitize_filename(album_artist)
        
        # For compilations, use single folder: /Album Name (Year)/
        # For regular albums, use: /Artist/Album (Year)/
        is_compilation = self._is_various_artists(metadata.album_artist or metadata.artist or "")
        
        if is_compilation or folder_info and folder_info.get('is_compilation'):
            # Compilation: /Album Name (Year)/01 - Track.mkv
            if year:
                folder = f"{album} ({year})"
            else:
                folder = album
            
            # Track filename
            track_num = str(metadata.track_number).zfill(2) if metadata.track_number else "00"
            title = self._sanitize_filename(metadata.title or "Unknown Track")
            
            if metadata.total_discs > 1:
                filename = f"{metadata.disc_number}-{track_num} - {title}{original_ext}"
            else:
                filename = f"{track_num} - {title}{original_ext}"
            
            return Path(output_dir) / folder / filename
        else:
            # Regular album: /Artist/Album (Year)/01 - Track.mkv
            artist_folder = album_artist
            
            if year:
                album_folder = f"{album} ({year})"
            else:
                album_folder = album
            
            track_num = str(metadata.track_number).zfill(2) if metadata.track_number else "00"
            title = self._sanitize_filename(metadata.title or "Unknown Track")
            
            if metadata.total_discs > 1:
                filename = f"{metadata.disc_number}-{track_num} - {title}{original_ext}"
            else:
                filename = f"{track_num} - {title}{original_ext}"
            
            return Path(output_dir) / artist_folder / album_folder / filename
    
    def organize_file(
        self,
        input_path: str,
        output_dir: str,
        enhance_audio: bool = True,
        audio_preset: AudioPreset = AudioPreset.SURROUND_7_0,
        output_format: Optional[str] = None,
        lookup_metadata: bool = True
    ) -> Optional[str]:
        """
        Organize a single music file with 7.0 surround upmix
        
        Args:
            input_path: Source file path
            output_dir: Base output directory
            enhance_audio: Apply 7.0 surround upmix with timbre-matching
            audio_preset: Enhancement preset (SURROUND_7_0)
            output_format: Output format (None = MKV with FLAC for 7.0)
            lookup_metadata: Use MusicBrainz for metadata
        
        Returns:
            Output file path if successful, None otherwise
        """
        input_file = Path(input_path)
        
        if input_file.suffix.lower() not in self.AUDIO_EXTENSIONS:
            logger.warning(f"Unsupported format: {input_path}")
            return None
        
        # Get source folder for album detection
        source_folder = str(input_file.parent)
        
        # Read existing metadata
        metadata = self._read_embedded_metadata(input_path)
        
        # Try to extract album info from folder name (for V.A. compilations)
        folder_info = self._extract_album_from_folder(source_folder)
        if folder_info:
            # If folder indicates compilation, update metadata
            if folder_info.get('is_compilation'):
                if not metadata.album:
                    metadata.album = folder_info.get('album', '')
                if not metadata.album_artist or self._is_various_artists(metadata.album_artist):
                    metadata.album_artist = folder_info.get('album_artist', metadata.album)
                if not metadata.year:
                    metadata.year = folder_info.get('year', '')
                logger.info(f"📀 Compilation detected: {metadata.album}")
        
        # Enhance with MusicBrainz/Discogs lookup
        if lookup_metadata:
            metadata = self._lookup_metadata(input_path, metadata)
        
        # Determine output format - always FLAC for 7.0 surround (proper audio container)
        out_ext = ".flac" if enhance_audio else (f".{output_format}" if output_format else input_file.suffix)
        
        # Generate output path (passes source folder for V.A. detection)
        output_path = self._generate_output_path(output_dir, metadata, out_ext, source_folder)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Process file
        if enhance_audio:
            success = self.enhancer.enhance_audio(
                input_path,
                str(output_path),
                preset=audio_preset,
                output_format=output_format or input_file.suffix.lstrip('.')
            )
            if not success:
                return None
        else:
            # Just copy the file
            shutil.copy2(input_path, output_path)
        
        # Update metadata in output file
        self._write_metadata(str(output_path), metadata)
        
        logger.info(f"Organized: {input_path} -> {output_path}")
        return str(output_path)
    
    def organize_directory(
        self,
        input_dir: str,
        output_dir: str,
        enhance_audio: bool = True,
        audio_preset: AudioPreset = AudioPreset.SURROUND_7_0,
        output_format: Optional[str] = None,
        lookup_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Organize all music files in a directory with 7.0 surround upmix
        
        Returns:
            Summary dict with counts and any errors
        """
        input_path = Path(input_dir)
        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        for file in input_path.rglob('*'):
            if file.suffix.lower() in self.AUDIO_EXTENSIONS:
                results['total'] += 1
                
                try:
                    output = self.organize_file(
                        str(file),
                        output_dir,
                        enhance_audio=enhance_audio,
                        audio_preset=audio_preset,
                        output_format=output_format,
                        lookup_metadata=lookup_metadata
                    )
                    
                    if output:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to process: {file}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"{file}: {str(e)}")
        
        return results


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Music Organizer Pro - 7.0 Surround Upmix with Timbre-Matching"
    )
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('-o', '--output', default=str(Path.home() / "Documents" / "Music"),
                       help='Output directory')
    parser.add_argument('--no-enhance', action='store_true',
                       help='Skip 7.0 surround upmix (just organize)')
    parser.add_argument('--no-lookup', action='store_true',
                       help='Skip MusicBrainz metadata lookup')
    parser.add_argument('--mb-client-id', default='',
                       help='MusicBrainz OAuth client ID')
    parser.add_argument('--mb-client-secret', default='',
                       help='MusicBrainz OAuth client secret')
    
    args = parser.parse_args()
    
    # Always use SURROUND_7_0 preset
    preset = AudioPreset.SURROUND_7_0
    
    # Output format is always FLAC for 7.0 surround (proper audio container)
    output_format = 'flac'
    
    # Initialize organizer
    organizer = MusicLibraryOrganizer(
        musicbrainz_client_id=args.mb_client_id or os.getenv('MUSICBRAINZ_CLIENT_ID', ''),
        musicbrainz_client_secret=args.mb_client_secret or os.getenv('MUSICBRAINZ_CLIENT_SECRET', ''),
        use_musicbrainz=not args.no_lookup
    )
    
    input_path = Path(args.input)
    
    print("🔊 7.0 Surround Timbre-Matching Mode")
    print("   Optimized for: Polk T50 fronts + Sony surrounds + Denon AVR")
    print("   Output: Multi-channel FLAC for Plex Direct Play")
    print()
    
    if input_path.is_file():
        result = organizer.organize_file(
            str(input_path),
            args.output,
            enhance_audio=not args.no_enhance,
            audio_preset=preset,
            output_format=output_format,
            lookup_metadata=not args.no_lookup
        )
        if result:
            print(f"✅ Organized: {result}")
            print()
            print("📺 Denon AVR Calibration Tips:")
            print("   • Channel Levels: Increase Surround/Back by +1.5dB to +2.0dB")
            print("   • Crossover: Set Front Speakers to 'Large' (no sub)")
            print("   • Plex: Use 'Direct Play' for best quality")
        else:
            print("❌ Failed to organize file")
    elif input_path.is_dir():
        results = organizer.organize_directory(
            str(input_path),
            args.output,
            enhance_audio=not args.no_enhance,
            audio_preset=preset,
            output_format=output_format,
            lookup_metadata=not args.no_lookup
        )
        print(f"\n📊 Results:")
        print(f"   Total: {results['total']}")
        print(f"   ✅ Success: {results['success']}")
        print(f"   ❌ Failed: {results['failed']}")
        if results['errors']:
            print(f"\n⚠️  Errors:")
            for err in results['errors'][:10]:
                print(f"   - {err}")
        print()
        print("📺 Denon AVR Calibration Tips:")
        print("   • Channel Levels: Increase Surround/Back by +1.5dB to +2.0dB")
        print("   • Crossover: Set Front Speakers to 'Large' (no sub)")
        print("   • Plex: Use 'Direct Play' for best quality")
    else:
        print(f"❌ Path not found: {args.input}")
