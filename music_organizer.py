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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AudioPreset(Enum):
    """Audio enhancement presets"""
    OPTIMAL = "optimal"           # Balanced enhancement - recommended default
    CLARITY = "clarity"           # Focus on vocal/instrument clarity
    BASS_BOOST = "bass_boost"     # Enhanced low frequencies
    WARM = "warm"                 # Warmer, fuller sound
    BRIGHT = "bright"             # Enhanced highs, crisp sound
    FLAT = "flat"                 # No enhancement, just normalization
    CUSTOM = "custom"             # User-defined settings


@dataclass
class AudioSettings:
    """Audio enhancement settings"""
    # EQ Settings (in dB, range -12 to +12)
    bass: float = 0.0            # 60-250 Hz
    low_mid: float = 0.0         # 250-500 Hz  
    mid: float = 0.0             # 500-2000 Hz
    high_mid: float = 0.0        # 2000-4000 Hz
    treble: float = 0.0          # 4000-16000 Hz
    presence: float = 0.0        # 5000-8000 Hz (vocal presence)
    air: float = 0.0             # 12000-16000 Hz (air/sparkle)
    
    # Dynamics
    normalize: bool = True        # EBU R128 loudness normalization
    target_loudness: float = -14.0  # LUFS target (-23 to -9)
    dynamic_range: bool = False   # Apply dynamic range compression
    use_limiter: bool = True      # Apply brick-wall limiter for loudness
    
    # Enhancement
    stereo_width: float = 1.0     # 0.5 to 2.0 (1.0 = no change)
    clarity_enhance: bool = False # Subtle harmonic enhancement
    exciter_amount: float = 2.0   # Harmonic exciter intensity (0-10)
    warmth: float = 0.0           # Analog warmth simulation
    
    @classmethod
    def from_preset(cls, preset: AudioPreset) -> 'AudioSettings':
        """Create settings from a preset"""
        presets = {
            # OPTIMAL: Rich, loud, professional sound - best for most music
            AudioPreset.OPTIMAL: cls(
                bass=3.0, low_mid=1.0, mid=0.5, high_mid=2.0, treble=2.5,
                presence=2.0, air=1.5,
                normalize=True, target_loudness=-11.0, use_limiter=True,
                stereo_width=1.15, clarity_enhance=True, exciter_amount=3.0,
                warmth=1.5
            ),
            # CLARITY: Crystal clear vocals and instruments
            AudioPreset.CLARITY: cls(
                bass=-0.5, low_mid=-1.0, mid=1.5, high_mid=3.0, treble=3.5,
                presence=3.5, air=2.5,
                normalize=True, target_loudness=-12.0, use_limiter=True,
                stereo_width=1.1, clarity_enhance=True, exciter_amount=4.0
            ),
            # BASS_BOOST: Deep, punchy bass with maintained clarity
            AudioPreset.BASS_BOOST: cls(
                bass=6.0, low_mid=4.0, mid=0.0, high_mid=1.0, treble=2.0,
                presence=1.0, air=1.0,
                normalize=True, target_loudness=-12.0, use_limiter=True,
                dynamic_range=True, stereo_width=1.2
            ),
            # WARM: Vintage analog warmth, fuller sound
            AudioPreset.WARM: cls(
                bass=4.0, low_mid=3.0, mid=1.5, high_mid=0.0, treble=-0.5,
                presence=0.5, air=0.0,
                normalize=True, target_loudness=-13.0, use_limiter=True,
                stereo_width=1.1, warmth=3.0
            ),
            # BRIGHT: Crisp, airy, sparkling highs
            AudioPreset.BRIGHT: cls(
                bass=0.0, low_mid=0.0, mid=1.0, high_mid=3.5, treble=4.5,
                presence=4.0, air=4.0,
                normalize=True, target_loudness=-12.0, use_limiter=True,
                stereo_width=1.2, clarity_enhance=True, exciter_amount=4.5
            ),
            # FLAT: Transparent, just loudness normalization
            AudioPreset.FLAT: cls(
                normalize=True, target_loudness=-14.0, use_limiter=True
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
    """FFmpeg-based audio enhancement processor"""
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.wma'}
    
    def __init__(self):
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Verify FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg not found. Install with: brew install ffmpeg")
    
    def _build_eq_filter(self, settings: AudioSettings) -> str:
        """Build FFmpeg equalizer filter chain with 7-band parametric EQ"""
        filters = []
        
        # 7-band parametric EQ using 'equalizer' filter
        # Format: equalizer=f=<freq>:t=h:w=<width>:g=<gain>
        eq_bands = [
            (80, settings.bass, 120),        # Sub-bass/Bass: 60-200 Hz
            (250, settings.low_mid, 150),    # Low-mid: 200-400 Hz
            (1000, settings.mid, 600),       # Mid: 500-1500 Hz
            (2500, settings.high_mid, 1000), # High-mid: 2000-3500 Hz
            (5000, getattr(settings, 'presence', 0), 1500),  # Presence: 4000-6000 Hz
            (8000, settings.treble, 3000),   # Treble: 6000-10000 Hz
            (14000, getattr(settings, 'air', 0), 4000),  # Air: 12000-16000 Hz
        ]
        
        for freq, gain, width in eq_bands:
            if gain != 0:
                filters.append(f"equalizer=f={freq}:t=h:w={width}:g={gain}")
        
        return ",".join(filters) if filters else ""
    
    def _build_filter_chain(self, settings: AudioSettings) -> str:
        """Build complete FFmpeg audio filter chain with professional mastering"""
        filters = []
        
        # 1. High-pass filter to remove sub-bass rumble (below 30Hz)
        filters.append("highpass=f=30")
        
        # 2. EQ filters (7-band parametric)
        eq_filter = self._build_eq_filter(settings)
        if eq_filter:
            filters.append(eq_filter)
        
        # 3. Analog warmth simulation (subtle saturation)
        warmth = getattr(settings, 'warmth', 0)
        if warmth > 0:
            # Use crystalizer for harmonic richness
            filters.append(f"crystalizer=i={warmth * 0.5}")
        
        # 4. Stereo width adjustment
        if settings.stereo_width != 1.0:
            # extrastereo filter: multiplier for stereo difference
            width = settings.stereo_width
            filters.append(f"extrastereo=m={width}")
        
        # 5. Clarity enhancement (harmonic exciter)
        if settings.clarity_enhance:
            exciter_amount = getattr(settings, 'exciter_amount', 2.0)
            # aexciter for harmonic enhancement - adds presence and sparkle
            filters.append(f"aexciter=level_in=1:level_out=1:amount={exciter_amount}:drive=5:blend=5:freq=3500")
        
        # 6. Dynamic range compression (multiband-style using compand)
        if settings.dynamic_range:
            # Gentle multiband-style compression for punch and consistency
            # compand: attack/decay | input/output points | soft-knee | gain | initial volume | delay
            filters.append("acompressor=threshold=-18dB:ratio=3:attack=10:release=150:makeup=2")
        
        # 7. Loudness normalization (EBU R128) - 2-pass style with measured parameters
        if settings.normalize:
            # More aggressive loudness target for richer, louder sound
            target = settings.target_loudness
            # LRA (Loudness Range) of 7-11 for consistent perceived loudness
            filters.append(f"loudnorm=I={target}:TP=-1.0:LRA=9:print_format=summary")
        
        # 8. Brick-wall limiter for final loudness maximization
        use_limiter = getattr(settings, 'use_limiter', True)
        if use_limiter:
            # alimiter: prevents clipping while maximizing loudness
            # level_in: input gain, level_out: output ceiling, limit: threshold
            filters.append("alimiter=level_in=1:level_out=0.99:limit=0.99:attack=5:release=50")
        
        # 9. Final DC offset removal and dithering for quality
        filters.append("aresample=resampler=soxr:precision=28:dither_method=triangular")
        
        return ",".join(filters) if filters else "anull"
    
    def analyze_audio(self, input_path: str) -> Dict[str, Any]:
        """Analyze audio file for loudness stats (for 2-pass normalization)"""
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse loudnorm output from stderr
        output = result.stderr
        try:
            # Find JSON block in output
            json_match = re.search(r'\{[^}]+\}', output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {}
    
    def enhance_audio(
        self,
        input_path: str,
        output_path: str,
        settings: Optional[AudioSettings] = None,
        preset: AudioPreset = AudioPreset.OPTIMAL,
        preserve_metadata: bool = True,
        output_format: Optional[str] = None
    ) -> bool:
        """
        Enhance audio file with EQ, normalization, and effects
        
        Args:
            input_path: Source audio file
            output_path: Destination path
            settings: Custom AudioSettings (overrides preset)
            preset: Audio enhancement preset
            preserve_metadata: Copy metadata to output
            output_format: Output format (flac, mp3, m4a, opus, or None to auto-detect)
        
        Returns:
            True if successful
        """
        if settings is None:
            settings = AudioSettings.from_preset(preset)
        
        filter_chain = self._build_filter_chain(settings)
        
        # Auto-detect output format from extension if not specified
        if output_format is None:
            output_format = Path(output_path).suffix.lstrip('.').lower()
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y', '-i', input_path]
        
        # Audio filter
        cmd.extend(['-af', filter_chain])
        
        # Formats that support embedded cover art as video stream
        formats_with_cover_art = {'flac', 'mp3', 'm4a', 'aac'}
        supports_cover = output_format in formats_with_cover_art
        
        # Output codec settings based on format
        if output_format == 'flac':
            cmd.extend(['-c:a', 'flac', '-compression_level', '8'])
        elif output_format == 'mp3':
            cmd.extend(['-c:a', 'libmp3lame', '-q:a', '0'])  # VBR highest quality
        elif output_format in ('m4a', 'aac'):
            cmd.extend(['-c:a', 'aac', '-b:a', '320k'])
        elif output_format == 'opus':
            cmd.extend(['-c:a', 'libopus', '-b:a', '256k'])
        elif output_format == 'ogg':
            cmd.extend(['-c:a', 'libvorbis', '-q:a', '10'])
        elif output_format == 'wav':
            cmd.extend(['-c:a', 'pcm_s24le'])
        else:
            # Default to FLAC for unknown formats (never use copy with filters!)
            cmd.extend(['-c:a', 'flac', '-compression_level', '8'])
            supports_cover = True
            # Update output path to .flac if needed
            if not output_path.endswith('.flac'):
                output_path = str(Path(output_path).with_suffix('.flac'))
        
        # Preserve metadata and cover art (only for formats that support it)
        if preserve_metadata:
            if supports_cover:
                # Map audio, optional video (cover art), copy video codec, preserve metadata
                cmd.extend(['-map', '0:a', '-map', '0:v?', '-c:v', 'copy', '-map_metadata', '0', '-disposition:v', 'attached_pic'])
            else:
                # For opus/ogg/wav - only map audio and metadata (no cover art support)
                cmd.extend(['-map', '0:a', '-map_metadata', '0'])
        
        cmd.append(output_path)
        
        try:
            # Use errors='replace' to handle non-UTF8 characters in FFmpeg output
            result = subprocess.run(cmd, capture_output=True, check=True, encoding='utf-8', errors='replace')
            # Verify output file exists and has content
            output_file = Path(output_path)
            if output_file.exists() and output_file.stat().st_size > 0:
                logger.info(f"Enhanced: {input_path} -> {output_path}")
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
        preset: AudioPreset = AudioPreset.OPTIMAL,
        output_format: str = "flac"
    ) -> Tuple[int, int]:
        """
        Batch enhance all audio files in directory
        
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
                # Preserve relative path structure
                rel_path = file.relative_to(input_path)
                out_file = output_path / rel_path.with_suffix(f'.{output_format}')
                out_file.parent.mkdir(parents=True, exist_ok=True)
                
                if self.enhance_audio(str(file), str(out_file), preset=preset, output_format=output_format):
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
        use_musicbrainz: bool = True
    ):
        self.use_musicbrainz = use_musicbrainz and MUSICBRAINZ_AVAILABLE
        self.mb_client = None
        
        if self.use_musicbrainz:
            try:
                self.mb_client = MusicBrainzClient(musicbrainz_client_id, musicbrainz_client_secret)
            except ImportError:
                logger.warning("MusicBrainz not available, using embedded metadata only")
                self.use_musicbrainz = False
        
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
        """Enhance metadata using MusicBrainz lookup"""
        if not self.use_musicbrainz or not self.mb_client:
            return existing
        
        # Only lookup if we have at least a title
        if not existing.title:
            return existing
        
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
    
    def _is_various_artists(self, artist: str) -> bool:
        """Check if artist name indicates a compilation/various artists album"""
        va_patterns = [
            'various artists', 'v.a.', 'va', 'various', 'compilation',
            'soundtrack', 'ost', 'original soundtrack', 'mixed by',
            'various artist', 'varios artistas', 'diverse'
        ]
        artist_lower = artist.lower().strip()
        return any(pattern in artist_lower or artist_lower == pattern for pattern in va_patterns)
    
    def _generate_output_path(
        self,
        output_dir: str,
        metadata: MusicMetadata,
        original_ext: str
    ) -> Path:
        """Generate Plex/Jellyfin compatible output path"""
        album_artist = metadata.album_artist or metadata.artist or ""
        album = self._sanitize_filename(metadata.album or "Unknown Album")
        
        # For compilation/various artists albums, use single folder with album name (year)
        # Structure: /Music/Album Name (Year)/01 - Track.flac
        if self._is_various_artists(album_artist) or not album_artist:
            # Single folder: Album Name (Year)
            if metadata.year:
                folder = f"{album} ({metadata.year})"
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
            # Regular artist album: /Artist/Album (Year)/Track.flac
            artist_folder = self._sanitize_filename(album_artist)
            
            if metadata.year:
                album_folder = f"{album} ({metadata.year})"
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
        audio_preset: AudioPreset = AudioPreset.OPTIMAL,
        output_format: Optional[str] = None,
        lookup_metadata: bool = True
    ) -> Optional[str]:
        """
        Organize a single music file
        
        Args:
            input_path: Source file path
            output_dir: Base output directory
            enhance_audio: Apply audio enhancement
            audio_preset: Enhancement preset
            output_format: Output format (None = keep original)
            lookup_metadata: Use MusicBrainz for metadata
        
        Returns:
            Output file path if successful, None otherwise
        """
        input_file = Path(input_path)
        
        if input_file.suffix.lower() not in self.AUDIO_EXTENSIONS:
            logger.warning(f"Unsupported format: {input_path}")
            return None
        
        # Read existing metadata
        metadata = self._read_embedded_metadata(input_path)
        
        # Enhance with MusicBrainz lookup
        if lookup_metadata:
            metadata = self._lookup_metadata(input_path, metadata)
        
        # Determine output format
        out_ext = f".{output_format}" if output_format else input_file.suffix
        
        # Generate output path
        output_path = self._generate_output_path(output_dir, metadata, out_ext)
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
        audio_preset: AudioPreset = AudioPreset.OPTIMAL,
        output_format: Optional[str] = None,
        lookup_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Organize all music files in a directory
        
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
        description="Music Organizer Pro - Organize and enhance your music library"
    )
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('-o', '--output', default='/Users/sharvin/Documents/Music',
                       help='Output directory')
    parser.add_argument('--preset', choices=['optimal', 'clarity', 'bass_boost', 'warm', 'bright', 'flat'],
                       default='optimal', help='Audio enhancement preset')
    parser.add_argument('--format', choices=['flac', 'mp3', 'm4a', 'keep'],
                       default='keep', help='Output format')
    parser.add_argument('--no-enhance', action='store_true',
                       help='Skip audio enhancement')
    parser.add_argument('--no-lookup', action='store_true',
                       help='Skip MusicBrainz metadata lookup')
    parser.add_argument('--mb-client-id', default='',
                       help='MusicBrainz OAuth client ID')
    parser.add_argument('--mb-client-secret', default='',
                       help='MusicBrainz OAuth client secret')
    
    args = parser.parse_args()
    
    # Map preset string to enum
    preset_map = {
        'optimal': AudioPreset.OPTIMAL,
        'clarity': AudioPreset.CLARITY,
        'bass_boost': AudioPreset.BASS_BOOST,
        'warm': AudioPreset.WARM,
        'bright': AudioPreset.BRIGHT,
        'flat': AudioPreset.FLAT,
    }
    preset = preset_map.get(args.preset, AudioPreset.OPTIMAL)
    
    # Output format
    output_format = None if args.format == 'keep' else args.format
    
    # Initialize organizer
    organizer = MusicLibraryOrganizer(
        musicbrainz_client_id=args.mb_client_id or os.getenv('MUSICBRAINZ_CLIENT_ID', ''),
        musicbrainz_client_secret=args.mb_client_secret or os.getenv('MUSICBRAINZ_CLIENT_SECRET', ''),
        use_musicbrainz=not args.no_lookup
    )
    
    input_path = Path(args.input)
    
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
    else:
        print(f"❌ Path not found: {args.input}")
