#!/usr/bin/env python3
"""
Media Organizer Pro v6.0
A high-performance tool for organizing media files with IMDB integration.

Performance optimizations applied:
- Sets for O(1) membership testing
- __slots__ for memory efficiency  
- Pre-compiled regex patterns
- Local function caching
- Minimal object copying
- Efficient itertools usage

Requirements:
    pip install pymkv2 rich requests
    brew install mkvtoolnix ffmpeg
"""

import os
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Set
from abc import ABC, abstractmethod
from functools import lru_cache
import bisect

# IMDB lookup
try:
    from imdb_lookup import lookup_series, IMDBSeriesInfo
    IMDB_AVAILABLE = True
except ImportError:
    IMDB_AVAILABLE = False
    IMDBSeriesInfo = None

# MKV support
try:
    from pymkv import MKVFile
    PYMKV_AVAILABLE = True
except ImportError:
    PYMKV_AVAILABLE = False

# Rich console
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, FloatPrompt
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# PRE-COMPILED REGEX PATTERNS (Hack #10: Avoid repeated function calls)
# =============================================================================
class Patterns:
    """Pre-compiled regex patterns for performance."""
    __slots__ = ()  # No instance attributes needed
    
    # Scene release: Show.Name.S01E01.Episode.Title.1080p...
    SCENE_SERIES = re.compile(
        r'^(.+?)[.\s][Ss](\d{1,2})[Ee](\d{1,2})[.\s](.+?)\.(\d{3,4}p)',
        re.IGNORECASE
    )
    
    # Standard series patterns
    SERIES_PATTERNS = [
        re.compile(r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?[Ss](\d{1,2})[Ee](\d{1,2})', re.IGNORECASE),
        re.compile(r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?Season[.\s]+(\d{1,2})[.\s]+Episode[.\s]+(\d{1,2})', re.IGNORECASE),
        re.compile(r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?(\d{1,2})[x×](\d{1,2})', re.IGNORECASE),
    ]
    
    # Cleaner patterns (case-insensitive for better matching)
    MOVIERULZ = re.compile(r'^(www\.)?[0-9]*movierulz?\.[a-z.]+ - ', re.IGNORECASE)
    TAMILMV = re.compile(r'^(www\.)?[0-9]*tamilmv[a-z]*\.[a-z.]+ - ', re.IGNORECASE)
    SANET = re.compile(r'^sanet\.st\.', re.IGNORECASE)
    GENERIC = re.compile(r'^[^_]+_[0-9]{4}_.*$')
    RARBG = re.compile(r'^RARBG\.to\.')
    YTS = re.compile(r'^YTS\.[A-Z]+\.')
    SCENE_QUALITY = re.compile(r'^.+?[.\s][Ss]\d{1,2}[Ee]\d{1,2}.*\d{3,4}p')
    STANDARD_DOT = re.compile(r'^[A-Za-z0-9]+\.(19[0-9][0-9]|20[0-9][0-9])\.[0-9]+p\b')
    STANDARD_UNDERSCORE = re.compile(r'^.+?_(19[0-9][0-9]|20[0-9][0-9])_[0-9]+p')
    
    # Utility patterns
    YEAR_QUALITY = re.compile(r'\.(19[0-9][0-9]|20[0-9][0-9])\..*$')
    MOVIE_YEAR = re.compile(r'^(.+?)\((\d{4})\)\s+.*$')
    TITLE_YEAR = re.compile(r'^(.+)\.([0-9]{4})$')
    CLEAN_SEPARATORS = re.compile(r'[.\-_]+')
    MULTI_SPACE = re.compile(r'\s+')
    INVALID_CHARS = re.compile(r'[<>:"|*?]')


# =============================================================================
# DATA CLASSES WITH __slots__ (Hack #3: Memory efficiency)
# =============================================================================
class MediaFile:
    """Represents a media file with metadata. Uses __slots__ for memory efficiency."""
    __slots__ = ('path', 'original_name', 'cleaned_name', 'format_detected',
                 'is_series', 'series_name', 'season', 'episode', 'year',
                 'episode_title', 'audio_tracks', 'video_tracks', 'subtitle_tracks')
    
    def __init__(self, path: Path, original_name: str):
        self.path = path
        self.original_name = original_name
        self.cleaned_name: Optional[str] = None
        self.format_detected: Optional[str] = None
        self.is_series: bool = False
        self.series_name: Optional[str] = None
        self.season: Optional[int] = None
        self.episode: Optional[int] = None
        self.year: Optional[Union[int, str]] = None
        self.episode_title: Optional[str] = None
        self.audio_tracks: Optional[List[Dict]] = None
        self.video_tracks: Optional[List[Dict]] = None
        self.subtitle_tracks: Optional[List[Dict]] = None


# =============================================================================
# SERIES DETECTOR WITH CACHING (Hack #10: Cache repeated lookups)
# =============================================================================
class SeriesDetector:
    """Detects TV series with IMDB integration and caching."""
    
    # Use set for O(1) lookups (Hack #1)
    _imdb_cache: Dict[str, 'IMDBSeriesInfo'] = {}
    _failed_lookups: Set[str] = set()  # Track failed lookups to avoid retrying
    
    # Fallback years (used if IMDB unavailable)
    KNOWN_SERIES: Dict[str, str] = {
        'stranger things': '2016–2025',
        'game of thrones': '2011–2019',
        'house of the dragon': '2022–',
        'the witcher': '2019–',
        'the mandalorian': '2019–',
        'wednesday': '2022–',
        'squid game': '2021–',
        'the last of us': '2023–',
        'breaking bad': '2008–2013',
        'better call saul': '2015–2022',
        'the boys': '2019–',
        'succession': '2018–2023',
        'severance': '2022–',
        'the bear': '2022–',
    }
    
    @classmethod
    @lru_cache(maxsize=256)  # Cache lookups
    def lookup_imdb(cls, series_name: str) -> Optional['IMDBSeriesInfo']:
        """Look up series on IMDB with caching."""
        if not IMDB_AVAILABLE:
            return None
        
        cache_key = series_name.lower().strip()
        
        # Skip if previously failed (Hack #1: Set for O(1) check)
        if cache_key in cls._failed_lookups:
            return None
        
        if cache_key in cls._imdb_cache:
            return cls._imdb_cache[cache_key]
        
        try:
            info = lookup_series(series_name)
            if info:
                cls._imdb_cache[cache_key] = info
                logger.info(f"IMDB: Found '{info.title}' ({info.year_range})")
                return info
            cls._failed_lookups.add(cache_key)
        except Exception as e:
            cls._failed_lookups.add(cache_key)
            logger.debug(f"IMDB lookup failed: {e}")
        
        return None
    
    @classmethod
    def get_series_info(cls, series_name: str) -> Tuple[str, Optional[str]]:
        """Get series title and year. Returns (title, year_range)."""
        imdb_info = cls.lookup_imdb(series_name)
        if imdb_info:
            return imdb_info.title, imdb_info.year_range
        
        # Fallback to known series
        key = series_name.lower()
        if key in cls.KNOWN_SERIES:
            return series_name.title(), cls.KNOWN_SERIES[key]
        
        return series_name.title(), None
    
    @staticmethod
    def detect_series(filename: str) -> Tuple[bool, Optional[str], Optional[int], Optional[int], Optional[str], Optional[str]]:
        """
        Detect if filename is a TV series.
        Returns: (is_series, series_name, season, episode, year, episode_title)
        """
        # Try scene release pattern first (most common)
        match = Patterns.SCENE_SERIES.search(filename)
        if match:
            series_raw = match.group(1).strip()
            season = int(match.group(2))
            episode = int(match.group(3))
            episode_title = match.group(4).strip()
            
            # Clean names using pre-compiled patterns
            series_clean = Patterns.CLEAN_SEPARATORS.sub(' ', series_raw).strip()
            series_clean = Patterns.MULTI_SPACE.sub(' ', series_clean)
            episode_title = Patterns.CLEAN_SEPARATORS.sub(' ', episode_title).strip()
            episode_title = Patterns.MULTI_SPACE.sub(' ', episode_title)
            
            # Get IMDB info
            title, year = SeriesDetector.get_series_info(series_clean)
            
            return True, title, season, episode, year, episode_title
        
        # Try other patterns
        for pattern in Patterns.SERIES_PATTERNS:
            match = pattern.search(filename)
            if match:
                groups = match.groups()
                series_name = Patterns.CLEAN_SEPARATORS.sub(' ', groups[0]).strip()
                series_name = Patterns.MULTI_SPACE.sub(' ', series_name)
                year = groups[1] if groups[1] else None
                season = int(groups[2])
                episode = int(groups[3])
                
                title, imdb_year = SeriesDetector.get_series_info(series_name)
                year = imdb_year or year
                
                return True, title, season, episode, year, None
        
        return False, None, None, None, None, None
    
    @staticmethod
    def create_folder_name(series_name: str, year: Optional[str]) -> str:
        """Create sanitized folder name."""
        if year:
            name = f"{series_name} ({year})"
        else:
            name = series_name
        return Patterns.INVALID_CHARS.sub('_', name).strip()
    
    @staticmethod
    def create_episode_filename(series_name: str, season: int, episode: int, 
                                 year: Optional[str], extension: str,
                                 episode_title: Optional[str] = None) -> str:
        """Create properly formatted episode filename (Plex/Jellyfin style).
        
        Format: Show Name (Year) - s01e01 - Episode Title.ext
        """
        base = f"{series_name} ({year})" if year else series_name
        
        if episode_title:
            name = f"{base} - s{season:02d}e{episode:02d} - {episode_title}{extension}"
        else:
            name = f"{base} - s{season:02d}e{episode:02d}{extension}"
        
        return Patterns.INVALID_CHARS.sub('_', name)


# =============================================================================
# FORMAT CLEANERS (Optimized with pre-compiled patterns)
# =============================================================================
class FormatCleaner(ABC):
    """Abstract base for format cleaners."""
    __slots__ = ()
    
    @abstractmethod
    def can_clean(self, filename: str) -> bool:
        pass
    
    @abstractmethod
    def clean(self, filename: str) -> str:
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        pass


class MovieRulzCleaner(FormatCleaner):
    __slots__ = ()
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.MOVIERULZ.search(filename))
    
    def clean(self, filename: str) -> str:
        cleaned = Patterns.MOVIERULZ.sub('', filename)
        match = Patterns.MOVIE_YEAR.match(cleaned)
        if match:
            return f"{match.group(1).strip()} ({match.group(2)})"
        return cleaned
    
    def get_format_name(self) -> str:
        return "MovieRulz"


class TamilMVCleaner(FormatCleaner):
    __slots__ = ()
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.TAMILMV.search(filename))
    
    def clean(self, filename: str) -> str:
        return Patterns.TAMILMV.sub('', filename)
    
    def get_format_name(self) -> str:
        return "TamilMV"


class SanetCleaner(FormatCleaner):
    __slots__ = ()
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.SANET.search(filename))
    
    def clean(self, filename: str) -> str:
        cleaned = Patterns.SANET.sub('', filename)
        cleaned = Patterns.YEAR_QUALITY.sub(r'.\1', cleaned)
        match = Patterns.TITLE_YEAR.match(cleaned)
        if match:
            return f"{match.group(1).replace('.', ' ')} ({match.group(2)})"
        return cleaned.replace('.', ' ')
    
    def get_format_name(self) -> str:
        return "Sanet.st"


class GenericMovieCleaner(FormatCleaner):
    __slots__ = ()
    _pattern = re.compile(r'^([^_]+)_([0-9]{4})_.*$')
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.GENERIC.match(filename))
    
    def clean(self, filename: str) -> str:
        match = self._pattern.match(filename)
        if match:
            return f"{match.group(1).replace('_', ' ')} ({match.group(2)})"
        return filename
    
    def get_format_name(self) -> str:
        return "Generic Movie"


class RARBGCleaner(FormatCleaner):
    __slots__ = ()
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.RARBG.search(filename))
    
    def clean(self, filename: str) -> str:
        cleaned = Patterns.RARBG.sub('', filename)
        cleaned = Patterns.YEAR_QUALITY.sub(r'.\1', cleaned)
        match = Patterns.TITLE_YEAR.match(cleaned)
        if match:
            return f"{match.group(1).replace('.', ' ')} ({match.group(2)})"
        return cleaned.replace('.', ' ')
    
    def get_format_name(self) -> str:
        return "RARBG"


class YTSCleaner(FormatCleaner):
    __slots__ = ()
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.YTS.search(filename))
    
    def clean(self, filename: str) -> str:
        cleaned = Patterns.YTS.sub('', filename)
        cleaned = Patterns.YEAR_QUALITY.sub(r'.\1', cleaned)
        match = Patterns.TITLE_YEAR.match(cleaned)
        if match:
            return f"{match.group(1).replace('.', ' ')} ({match.group(2)})"
        return cleaned.replace('.', ' ')
    
    def get_format_name(self) -> str:
        return "YTS"


class SceneSeriesCleaner(FormatCleaner):
    __slots__ = ()
    _pattern = re.compile(r'^(.+?)\.\d{3,4}p\..*$', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.SCENE_QUALITY.search(filename))
    
    def clean(self, filename: str) -> str:
        match = self._pattern.match(filename)
        if match:
            cleaned = match.group(1).replace('.', ' ')
            return Patterns.MULTI_SPACE.sub(' ', cleaned).strip()
        return filename
    
    def get_format_name(self) -> str:
        return "Scene Series"




class StandardReleaseCleaner(FormatCleaner):
    __slots__ = ()
    _dot_pattern = re.compile(r'^([A-Za-z0-9.\-_]+?)\.(19[0-9][0-9]|20[0-9][0-9])\.[0-9]+p.*$', re.IGNORECASE)
    _underscore_pattern = re.compile(r'^(.+?)_(19[0-9][0-9]|20[0-9][0-9])_[0-9]+p.*$', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        return bool(Patterns.STANDARD_DOT.search(filename) or Patterns.STANDARD_UNDERSCORE.search(filename))
    
    def clean(self, filename: str) -> str:
        match = self._dot_pattern.match(filename)
        if match:
            title = Patterns.CLEAN_SEPARATORS.sub(' ', match.group(1)).strip()
            return f"{Patterns.MULTI_SPACE.sub(' ', title)} ({match.group(2)})"
        
        match = self._underscore_pattern.match(filename)
        if match:
            title = match.group(1).replace('_', ' ').strip()
            return f"{Patterns.MULTI_SPACE.sub(' ', title)} ({match.group(2)})"
        
        return filename
    
    def get_format_name(self) -> str:
        return "Standard Release"


class NeoNoirCleaner(FormatCleaner):
    __slots__ = ()
    _pattern = re.compile(r'^(.+?)\.(2024|2025)\.\d+p\..*?x265-NeoNoir', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        return 'NeoNoir' in filename and bool(self._pattern.search(filename))
    
    def clean(self, filename: str) -> str:
        match = self._pattern.match(filename)
        if match:
            title = match.group(1).replace('.', ' ').strip()
            return f"{title} ({match.group(2)})"
        return filename
    
    def get_format_name(self) -> str:
        return "NeoNoir Release"


class GeneralReleaseCleaner(FormatCleaner):
    """Cleans general release names with year in parentheses - strips quality info after year."""
    __slots__ = ()
    # Match: Title (Year) followed by quality/codec info
    _pattern = re.compile(r'^(.+?\s*\(\d{4}\))[\s\-]+.*(?:WEB|HDR|SDR|HEVC|x26|BluRay|BRRip)', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        # Has year in parentheses AND has quality indicators after
        return bool(re.search(r'\(\d{4}\)', filename)) and bool(
            re.search(r'WEB|HDR|SDR|HEVC|x26|BluRay|BRRip|\d{3,4}p', filename, re.IGNORECASE)
        )
    
    def clean(self, filename: str) -> str:
        # Extract "Title (Year)" and discard the rest
        match = re.match(r'^(.+?\s*\(\d{4}\))', filename)
        if match:
            return match.group(1).strip()
        return filename
    
    def get_format_name(self) -> str:
        return "General Release"


# =============================================================================
# MEDIA ORGANIZER (Main class)
# =============================================================================
class MediaOrganizer:
    """Main class for organizing media files."""
    
    # Pre-allocate cleaner list (Hack #5)
    __slots__ = ('cleaners', 'series_detector', '_media_extensions')
    
    def __init__(self):
        # Pre-allocate cleaners list
        self.cleaners: List[FormatCleaner] = [
            NeoNoirCleaner(),
            MovieRulzCleaner(),
            TamilMVCleaner(),
            SanetCleaner(),
            GenericMovieCleaner(),
            RARBGCleaner(),
            YTSCleaner(),
            SceneSeriesCleaner(),
            StandardReleaseCleaner(),
            GeneralReleaseCleaner(),  # Catch-all for "Title (Year) - quality info" format
        ]
        self.series_detector = SeriesDetector()
        # Use set for O(1) extension lookup (Hack #1)
        self._media_extensions: Set[str] = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    
    def clean_filename(self, filename: str) -> Tuple[str, Optional[str]]:
        """Clean filename using appropriate cleaner."""
        for cleaner in self.cleaners:
            if cleaner.can_clean(filename):
                return cleaner.clean(filename), cleaner.get_format_name()
        return filename, None
    
    def analyze_file(self, file_path: Path) -> MediaFile:
        """Analyze a media file and extract metadata."""
        media_file = MediaFile(path=file_path, original_name=file_path.name)
        
        # Clean filename
        cleaned, format_detected = self.clean_filename(file_path.name)
        media_file.cleaned_name = cleaned
        media_file.format_detected = format_detected
        
        # Detect series from original filename
        is_series, name, season, episode, year, ep_title = SeriesDetector.detect_series(file_path.name)
        media_file.is_series = is_series
        media_file.series_name = name
        media_file.season = season
        media_file.episode = episode
        media_file.year = year
        media_file.episode_title = ep_title
        
        return media_file
    
    def organize_files(self, directory: Union[str, Path] = '.', output_dir: Optional[Union[str, Path]] = None) -> List[MediaFile]:
        """Organize files from directory to output_dir (or in-place if output_dir is None)."""
        directory = Path(directory)
        
        # Default output to /Users/sharvin/Documents/Processed
        if output_dir is None:
            output_dir = Path("/Users/sharvin/Documents/Processed")
        else:
            output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        processed: List[MediaFile] = []
        
        if RICH_AVAILABLE:
            console.print(Panel.fit("Media Organizer Pro v6.0", style="bold green"))
        else:
            logger.info("Media Organizer Pro v6.0")
        
        logger.info(f"Source: {directory}")
        logger.info(f"Output: {output_dir}")
        
        # Group series files (Hack #1: Use dict for grouping)
        series_groups: Dict[Tuple[str, Optional[str]], List[MediaFile]] = {}
        movie_files: List[MediaFile] = []
        
        # Process loose files
        for file_path in directory.iterdir():
            if file_path.is_dir() or file_path.name.startswith('.'):
                continue
            
            # Use set for O(1) extension check (Hack #1)
            if file_path.suffix.lower() not in self._media_extensions:
                continue
            
            media_file = self.analyze_file(file_path)
            
            if media_file.is_series:
                key = (media_file.series_name, media_file.year)
                if key not in series_groups:
                    series_groups[key] = []
                series_groups[key].append(media_file)
            else:
                movie_files.append(media_file)
            
            processed.append(media_file)
        
        # Organize series - use output_dir as base
        for (series_name, year), episodes in series_groups.items():
            self._organize_series(output_dir, series_name, year, episodes)
        
        # Organize movies - use output_dir as base
        for media_file in movie_files:
            self._organize_movie(output_dir, media_file)
        
        logger.info(f"Organization complete! Processed {len(processed)} files.")
        return processed
    
    def _organize_series(self, base_dir: Path, series_name: str, year: Optional[str], episodes: List[MediaFile]):
        """Organize series files into Plex/Jellyfin folder structure.
        
        Structure: /Show Name (Year)/Season XX/Show Name (Year) - sXXeXX - Title.ext
        """
        import shutil
        
        folder_name = SeriesDetector.create_folder_name(series_name, year)
        series_folder = base_dir / folder_name
        series_folder.mkdir(exist_ok=True)
        
        if RICH_AVAILABLE:
            console.print(f"Organizing: {folder_name}", style="cyan")
        
        for media_file in episodes:
            if media_file.season and media_file.episode:
                # Create Season folder (Plex/Jellyfin style)
                season_folder = series_folder / f"Season {media_file.season:02d}"
                season_folder.mkdir(exist_ok=True)
                
                # Create proper episode filename
                new_name = SeriesDetector.create_episode_filename(
                    series_name, media_file.season, media_file.episode,
                    year, media_file.path.suffix, media_file.episode_title
                )
                target = season_folder / new_name
                
                # Move file (use shutil.move for cross-device moves)
                shutil.move(str(media_file.path), str(target))
                media_file.path = target
                
                if RICH_AVAILABLE:
                    console.print(f"  {media_file.original_name} -> Season {media_file.season:02d}/{new_name}", style="green")
                else:
                    logger.info(f"Moved: {media_file.original_name} -> {folder_name}/Season {media_file.season:02d}/{new_name}")
    
    def _organize_movie(self, base_dir: Path, media_file: MediaFile):
        """Organize a movie file into its own folder."""
        import shutil
        
        # Use cleaned name if available, otherwise use original
        name_to_use = media_file.cleaned_name if media_file.cleaned_name else media_file.original_name
        
        # Ensure extension
        ext = media_file.path.suffix
        final_name = name_to_use
        if ext and not final_name.endswith(ext):
            final_name += ext
        
        folder_name = Path(final_name).stem
        folder_name = Patterns.INVALID_CHARS.sub('_', folder_name).strip()
        
        target_folder = base_dir / folder_name
        target_folder.mkdir(exist_ok=True)
        target = target_folder / final_name
        
        # Move file (use shutil.move for cross-device moves)
        shutil.move(str(media_file.path), str(target))
        media_file.path = target
        
        if RICH_AVAILABLE:
            console.print(f"{media_file.original_name} -> {folder_name}/{final_name}", style="green")
        else:
            logger.info(f"Moved: {media_file.original_name} -> {folder_name}/{final_name}")


# =============================================================================
# AUDIO TRACK FILTER
# =============================================================================
class AudioTrackFilter:
    """Filter audio tracks in MKV files."""
    
    __slots__ = ('language_keywords',)
    
    def __init__(self):
        # Use frozenset for immutable, hashable keyword sets
        # Comprehensive language support with ISO 639-1/639-2 codes
        self.language_keywords: Dict[str, frozenset] = {
            # Indian languages
            'malayalam': frozenset(['malayalam', 'mal', 'ml', 'm', 'mala', 'malay', 'mlm', 'mym', 'മലയാളം']),
            'tamil': frozenset(['tamil', 'tam', 'ta', 't', 'tml', 'தமிழ்']),
            'telugu': frozenset(['telugu', 'tel', 'te', 'tlg', 'తెలుగు']),
            'hindi': frozenset(['hindi', 'hin', 'hi', 'h', 'hnd', 'हिन्दी', 'हिंदी']),
            'kannada': frozenset(['kannada', 'kan', 'kn', 'k', 'knd', 'ಕನ್ನಡ']),
            'bengali': frozenset(['bengali', 'ben', 'bn', 'b', 'bng', 'bangla', 'বাংলা']),
            'marathi': frozenset(['marathi', 'mar', 'mr', 'mrt', 'मराठी']),
            'gujarati': frozenset(['gujarati', 'guj', 'gu', 'guj', 'ગુજરાતી']),
            'punjabi': frozenset(['punjabi', 'pan', 'pa', 'pnb', 'ਪੰਜਾਬੀ', 'پنجابی']),
            'odia': frozenset(['odia', 'oriya', 'ori', 'or', 'ory', 'ଓଡ଼ିଆ']),
            # European languages
            'english': frozenset(['english', 'eng', 'en']),
            'spanish': frozenset(['spanish', 'spa', 'es', 'español']),
            'french': frozenset(['french', 'fra', 'fre', 'fr', 'français']),
            'german': frozenset(['german', 'deu', 'ger', 'de', 'deutsch']),
            'italian': frozenset(['italian', 'ita', 'it', 'italiano']),
            'portuguese': frozenset(['portuguese', 'por', 'pt', 'português']),
            'russian': frozenset(['russian', 'rus', 'ru', 'русский']),
            'polish': frozenset(['polish', 'pol', 'pl']),
            'dutch': frozenset(['dutch', 'nld', 'dut', 'nl']),
            'swedish': frozenset(['swedish', 'swe', 'sv']),
            'norwegian': frozenset(['norwegian', 'nor', 'no', 'nb', 'nn']),
            'danish': frozenset(['danish', 'dan', 'da']),
            'finnish': frozenset(['finnish', 'fin', 'fi']),
            'greek': frozenset(['greek', 'gre', 'ell', 'el']),
            'czech': frozenset(['czech', 'ces', 'cze', 'cs']),
            'hungarian': frozenset(['hungarian', 'hun', 'hu']),
            'romanian': frozenset(['romanian', 'ron', 'rum', 'ro']),
            'ukrainian': frozenset(['ukrainian', 'ukr', 'uk']),
            'turkish': frozenset(['turkish', 'tur', 'tr']),
            # Asian languages
            'japanese': frozenset(['japanese', 'jpn', 'ja', '日本語']),
            'korean': frozenset(['korean', 'kor', 'ko', '한국어']),
            'chinese': frozenset(['chinese', 'zho', 'chi', 'zh', 'cmn', 'mandarin', '中文']),
            'thai': frozenset(['thai', 'tha', 'th']),
            'vietnamese': frozenset(['vietnamese', 'vie', 'vi']),
            'indonesian': frozenset(['indonesian', 'ind', 'id']),
            'malay': frozenset(['malay', 'msa', 'may', 'ms']),
            # Middle Eastern
            'arabic': frozenset(['arabic', 'ara', 'ar', 'عربي']),
            'hebrew': frozenset(['hebrew', 'heb', 'he', 'עברית']),
        }
    
    def get_track_info(self, file_path: Path) -> Optional[Dict]:
        """Get track information from MKV file."""
        try:
            result = subprocess.run(
                ['mkvmerge', '-J', str(file_path)],
                capture_output=True, text=True, check=True, timeout=30
            )
            data = json.loads(result.stdout)
            
            # Pre-allocate lists (Hack #5)
            info = {
                'audio_tracks': [],
                'video_tracks': [],
                'subtitle_tracks': []
            }
            
            for track in data.get('tracks', []):
                track_info = {
                    'id': track['id'],
                    'type': track['type'],
                    'language': track['properties'].get('language', 'und'),
                    'track_name': track['properties'].get('track_name', ''),
                    'codec': track['codec']
                }
                
                # Use dict lookup instead of if-elif chain
                track_type = track['type']
                if track_type == 'audio':
                    info['audio_tracks'].append(track_info)
                elif track_type == 'video':
                    info['video_tracks'].append(track_info)
                elif track_type == 'subtitles':
                    info['subtitle_tracks'].append(track_info)
            
            return info
        except Exception as e:
            logger.error(f"Error getting track info: {e}")
            return None
    
    def is_language_track(self, track: Dict, target_language: str) -> bool:
        """Check if track matches target language."""
        keywords = self.language_keywords.get(target_language.lower())
        if not keywords:
            return False
        
        lang = track.get('language', '').lower()
        if lang in keywords:
            return True
        
        # Only check name if language is undefined
        if lang == 'und':
            name = track.get('track_name', '').lower()
            return any(kw in name for kw in keywords)
        
        return False
    
    def filter_audio(self, file_path: Path, target_language: str = 'malayalam',
                     output_path: Optional[Path] = None, volume_boost: float = 1.0,
                     subtitle_language: str = 'english', replace_original: bool = True) -> bool:
        """Filter MKV to keep only specified language audio and subtitles."""
        track_info = self.get_track_info(file_path)
        if not track_info:
            return False
        
        # Find target audio tracks
        target_tracks = [
            t for t in track_info['audio_tracks']
            if self.is_language_track(t, target_language)
        ]
        
        if not target_tracks:
            logger.warning(f"No {target_language} audio in: {file_path.name}")
            return False
        
        # Find target subtitle tracks (English by default)
        target_subs = [
            t for t in track_info['subtitle_tracks']
            if self.is_language_track(t, subtitle_language)
        ]
        
        # Use temp file if replacing original
        if output_path is None:
            if replace_original:
                output_path = file_path.parent / f"{file_path.stem}_temp_filtered{file_path.suffix}"
            else:
                output_path = file_path.parent / f"{file_path.stem}_{target_language}{file_path.suffix}"
        
        # Build mkvmerge command
        cmd = ['mkvmerge', '-o', str(output_path)]
        
        # Video tracks
        video_ids = [str(t['id']) for t in track_info['video_tracks']]
        if video_ids:
            cmd.extend(['--video-tracks', ','.join(video_ids)])
        else:
            cmd.append('--no-video')
        
        # Audio tracks - only target language
        cmd.extend(['--audio-tracks', ','.join(str(t['id']) for t in target_tracks)])
        
        # Subtitle tracks - only target subtitle language (English by default)
        if target_subs:
            cmd.extend(['--subtitle-tracks', ','.join(str(t['id']) for t in target_subs)])
        else:
            # If no English subs found, keep all subs
            if track_info['subtitle_tracks']:
                cmd.extend(['--subtitle-tracks', ','.join(str(t['id']) for t in track_info['subtitle_tracks'])])
            else:
                cmd.append('--no-subtitles')
        
        cmd.append(str(file_path))
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=3600)  # 1 hour timeout for large files
            
            # Apply volume boost if needed
            if volume_boost != 1.0:
                self._apply_volume_boost(output_path, volume_boost)
            
            # Replace original file if requested
            if replace_original:
                file_path.unlink()  # Delete original
                output_path.rename(file_path)  # Rename temp to original name
                logger.info(f"Filtered: {file_path.name} (replaced original)")
            else:
                logger.info(f"Filtered: {file_path.name} -> {output_path.name}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"MKVMerge error: {e}")
            return False
    
    def _apply_volume_boost(self, file_path: Path, boost: float) -> bool:
        """Apply volume boost using ffmpeg."""
        temp_path = file_path.parent / f"{file_path.stem}_boosted{file_path.suffix}"
        
        try:
            subprocess.run([
                'ffmpeg', '-i', str(file_path),
                '-af', f'volume={boost}',
                '-c:v', 'copy', '-c:s', 'copy', '-y',
                str(temp_path)
            ], capture_output=True, check=True, timeout=600)
            
            # Replace original with boosted version
            file_path.unlink()
            temp_path.rename(file_path)
            return True
        except Exception as e:
            logger.error(f"Volume boost failed: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def batch_filter(self, directory: Union[str, Path], target_language: str = 'malayalam',
                     volume_boost: float = 1.0, subtitle_language: str = 'english') -> List[Path]:
        """Filter all MKV files in directory."""
        directory = Path(directory)
        processed: List[Path] = []
        
        # Find all MKV files (skip temp files)
        mkv_files = [
            f for f in directory.rglob("*.mkv")
            if '_temp_filtered' not in f.name
        ]
        
        if RICH_AVAILABLE:
            console.print(f"Found {len(mkv_files)} MKV files", style="cyan")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Processing...", total=len(mkv_files))
                for mkv in mkv_files:
                    progress.update(task, description=f"Processing {mkv.name}")
                    if self.filter_audio(mkv, target_language, volume_boost=volume_boost, subtitle_language=subtitle_language, replace_original=True):
                        processed.append(mkv)
                    progress.advance(task)
        else:
            for i, mkv in enumerate(mkv_files, 1):
                logger.info(f"Processing {i}/{len(mkv_files)}: {mkv.name}")
                if self.filter_audio(mkv, target_language, volume_boost=volume_boost, subtitle_language=subtitle_language, replace_original=True):
                    processed.append(mkv)
        
        return processed


# =============================================================================
# CLI INTERFACE
# =============================================================================
def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Media Organizer Pro v6.0 - High-performance media file organizer"
    )
    parser.add_argument('action', nargs='?', choices=['organize', 'filter', 'both'],
                        help='Action to perform')
    parser.add_argument('directory', nargs='?', default='.', help='Source directory to process')
    parser.add_argument('--output', '-o', default='/Users/sharvin/Documents/Processed',
                        help='Output directory (default: /Users/sharvin/Documents/Processed)')
    parser.add_argument('--language', default='malayalam',
                        help='Language to keep when filtering audio (e.g., malayalam, tamil, english, spanish)')
    parser.add_argument('--subtitle-language', default='english',
                        help='Subtitle language to keep (default: english)')
    parser.add_argument('--volume-boost', type=float, default=1.0,
                        help='Volume boost multiplier (e.g., 1.5)')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1
    
    output_dir = Path(args.output)
    
    if args.action in ('organize', 'both', None):
        organizer = MediaOrganizer()
        organizer.organize_files(directory, output_dir)
    
    if args.action in ('filter', 'both'):
        audio_filter = AudioTrackFilter()
        # Filter in the output directory after organizing
        filter_dir = output_dir if args.action == 'both' else directory
        audio_filter.batch_filter(filter_dir, args.language, args.volume_boost, args.subtitle_language)
    
    if not args.action:
        # Interactive mode
        if RICH_AVAILABLE:
            console.print("\nUsage: python media_organizer.py [organize|filter|both] [directory]", style="yellow")
        else:
            print("\nUsage: python media_organizer.py [organize|filter|both] [directory]")
    
    return 0


if __name__ == "__main__":
    exit(main())
