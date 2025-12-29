#!/usr/bin/env python3
"""
Smart Media Renamer
Automatically detects and renames media files using TMDB metadata.

Features:
- Regex-based filename parsing for series/movies
- TMDB integration for accurate metadata
- Plex/Jellyfin compatible naming
- Batch processing support
- Dry-run mode for preview
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum

from .tmdb_client import (
    TMDBClient,
    TMDBSeriesInfo,
    TMDBMovieInfo,
    TMDBEpisodeInfo,
    TMDBFilenameGenerator,
    get_tmdb_client
)

logger = logging.getLogger(__name__)


class MediaType(str, Enum):
    """Detected media type."""
    SERIES = "series"
    MOVIE = "movie"
    UNKNOWN = "unknown"


@dataclass
class ParsedFilename:
    """Result of filename parsing."""
    original: str
    media_type: MediaType
    title: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    quality: Optional[str] = None
    source: Optional[str] = None
    codec: Optional[str] = None
    release_group: Optional[str] = None
    confidence: float = 0.0


@dataclass
class RenameResult:
    """Result of a rename operation."""
    original_path: Path
    new_path: Optional[Path]
    original_name: str
    new_name: Optional[str]
    success: bool
    error: Optional[str] = None
    tmdb_title: Optional[str] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None  # IMDB ID for .nfo file creation
    metadata_found: bool = True  # Whether IMDB/TMDB metadata was found


class FilenameParser:
    """
    Parse media filenames to extract metadata.
    Handles various release formats (scene, P2P, streaming rips, etc.)
    """
    
    # Pre-compiled patterns for performance
    PATTERNS = {
        # Series patterns (ordered by specificity)
        'series_full': re.compile(
            r'^(?P<title>.+?)[.\s_-]+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,2})'
            r'(?:[.\s_-]+(?P<ep_title>[^.]+?))?'
            r'(?:[.\s_-]+(?P<quality>\d{3,4}p))?',
            re.IGNORECASE
        ),
        'series_x_format': re.compile(
            r'^(?P<title>.+?)[.\s_-]+(?P<season>\d{1,2})[xX](?P<episode>\d{1,2})',
            re.IGNORECASE
        ),
        'series_season_episode': re.compile(
            r'^(?P<title>.+?)[.\s_-]+Season[.\s_]+(?P<season>\d{1,2})[.\s_]+'
            r'Episode[.\s_]+(?P<episode>\d{1,2})',
            re.IGNORECASE
        ),
        
        # Movie patterns
        'movie_year': re.compile(
            r'^(?P<title>.+?)[.\s_-]+[\(\[]?(?P<year>(?:19|20)\d{2})[\)\]]?'
            r'(?:[.\s_-]+(?P<quality>\d{3,4}p))?',
            re.IGNORECASE
        ),
        'movie_quality': re.compile(
            r'^(?P<title>.+?)[.\s_-]+(?P<quality>\d{3,4}p)',
            re.IGNORECASE
        ),
    }
    
    # Quality indicators
    QUALITY_PATTERN = re.compile(r'(2160p|1080p|720p|480p|4K|UHD)', re.IGNORECASE)
    SOURCE_PATTERN = re.compile(
        r'(BluRay|BDRip|WEB-?DL|WEBRip|HDRip|DVDRip|HDTV|AMZN|NF|DSNP|HMAX|ATVP)',
        re.IGNORECASE
    )
    CODEC_PATTERN = re.compile(r'(x264|x265|HEVC|H\.?264|H\.?265|AV1|VP9)', re.IGNORECASE)
    RELEASE_GROUP_PATTERN = re.compile(r'-([A-Za-z0-9]+)(?:\.[a-z]{2,4})?$')
    
    # Site prefixes to strip
    # Using [^\s\(\)\[\]\{\},.]* to exclude common delimiters but still catch all variations
    # The pattern requires at least one dot (domain.tld) to avoid false positives
    SITE_PREFIXES = [
        # TamilMV - catches ANY prefix/subdomain before "tamilmv" and ANY TLD after
        # Examples: www.1TamilMV.kiwi, www.xyz123TamilMV.buzz, 1tamilmv.ws, tamilmvhd.com, etc.
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*tamilmv[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # MovieRulz - same flexible pattern
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*movierulz[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # TamilRockers - same flexible pattern
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*tamilrockers[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # TamilBlasters - same flexible pattern
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*tamilblasters[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # TamilYogi
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*tamilyogi[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Isaimini
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*isaimini[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Moviesda
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*moviesda[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Kuttymovies
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*kuttymovies[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # HDHub4u
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*hdhub4u[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Filmyzilla
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*filmyzilla[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Bracketed site tags like [TamilMV], [1TamilMV], etc.
        r'^\[(?:www\.)?[^\]]*tamilmv[^\]]*\]\s*',
        r'^\[(?:www\.)?[^\]]*movierulz[^\]]*\]\s*',
        r'^\[(?:www\.)?[^\]]*tamilrockers[^\]]*\]\s*',
        r'^\[(?:www\.)?[^\]]*tamilblasters[^\]]*\]\s*',
        
        # Other common sites
        r'^sanet\.st\s*[.\-]\s*',
        r'^YTS\.[A-Z]+\s*[.\-]\s*',
        r'^RARBG\.[a-z]+\s*[.\-]\s*',
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*1337x[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*torrentgalaxy[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        r'^(?:www\.)?[^\s\(\)\[\]\{\},]*eztv[^\s\(\)\[\]\{\},]*\.[a-z]{2,10}\s*-\s*',
        
        # Generic pattern: www.anything.tld - (catches any site prefix with dash separator)
        # Handles domains with hyphens like www.random-site.org -
        r'^(?:www\.)?[\w\d][\w\d-]*\.[a-z]{2,10}\s+-\s+',
        r'^(?:www\.)?[\w\d][\w\d-]*\.[a-z]{2,10}\s*-\s*',
    ]
    
    def __init__(self):
        self._site_patterns = [re.compile(p, re.IGNORECASE) for p in self.SITE_PREFIXES]
    
    def _strip_site_prefix(self, filename: str) -> str:
        """Remove common site prefixes from filename."""
        for pattern in self._site_patterns:
            filename = pattern.sub('', filename)
        return filename.strip()
    
    def _clean_title(self, title: str) -> str:
        """Clean up extracted title."""
        # Replace separators with spaces
        title = re.sub(r'[._]+', ' ', title)
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title)
        # Title case
        return title.strip().title()
    
    def _extract_extras(self, filename: str) -> Dict[str, Optional[str]]:
        """Extract quality, source, codec, release group."""
        extras = {}
        
        match = self.QUALITY_PATTERN.search(filename)
        extras['quality'] = match.group(1) if match else None
        
        match = self.SOURCE_PATTERN.search(filename)
        extras['source'] = match.group(1) if match else None
        
        match = self.CODEC_PATTERN.search(filename)
        extras['codec'] = match.group(1) if match else None
        
        match = self.RELEASE_GROUP_PATTERN.search(filename)
        extras['release_group'] = match.group(1) if match else None
        
        return extras
    
    def parse(self, filename: str) -> ParsedFilename:
        """
        Parse a media filename and extract metadata.
        
        Args:
            filename: Filename to parse (with or without extension)
            
        Returns:
            ParsedFilename with extracted metadata
        """
        # Remove extension
        name = Path(filename).stem
        original = name
        
        # Strip site prefixes
        name = self._strip_site_prefix(name)
        
        # Extract extras
        extras = self._extract_extras(name)
        
        # Try series patterns first
        for pattern_name in ['series_full', 'series_x_format', 'series_season_episode']:
            match = self.PATTERNS[pattern_name].search(name)
            if match:
                groups = match.groupdict()
                return ParsedFilename(
                    original=original,
                    media_type=MediaType.SERIES,
                    title=self._clean_title(groups['title']),
                    season=int(groups['season']),
                    episode=int(groups['episode']),
                    episode_title=groups.get('ep_title'),
                    quality=groups.get('quality') or extras['quality'],
                    source=extras['source'],
                    codec=extras['codec'],
                    release_group=extras['release_group'],
                    confidence=0.9 if pattern_name == 'series_full' else 0.8
                )
        
        # Try movie patterns
        for pattern_name in ['movie_year', 'movie_quality']:
            match = self.PATTERNS[pattern_name].search(name)
            if match:
                groups = match.groupdict()
                year = int(groups['year']) if groups.get('year') else None
                return ParsedFilename(
                    original=original,
                    media_type=MediaType.MOVIE,
                    title=self._clean_title(groups['title']),
                    year=year,
                    quality=groups.get('quality') or extras['quality'],
                    source=extras['source'],
                    codec=extras['codec'],
                    release_group=extras['release_group'],
                    confidence=0.8 if year else 0.6
                )
        
        # Fallback - just clean the name
        return ParsedFilename(
            original=original,
            media_type=MediaType.UNKNOWN,
            title=self._clean_title(name),
            confidence=0.3
        )


class SmartRenamer:
    """
    Smart media file renamer with IMDB (OMDB) as primary and TMDB as fallback.
    
    Usage:
        renamer = SmartRenamer(tmdb_token="your_token", omdb_api_key="your_key")
        
        # Preview renames
        results = renamer.preview_rename("/path/to/files")
        
        # Execute renames
        results = renamer.rename_files("/path/to/files")
        
        # Rename single file
        result = renamer.rename_file("/path/to/file.mkv")
    """
    
    MEDIA_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    def __init__(
        self,
        tmdb_client: Optional[TMDBClient] = None,
        tmdb_token: Optional[str] = None,
        tmdb_api_key: Optional[str] = None,
        omdb_api_key: Optional[str] = None,
        organize_folders: bool = True,
        include_episode_title: bool = True
    ):
        """
        Initialize smart renamer.
        
        Args:
            tmdb_client: Existing TMDB client instance
            tmdb_token: TMDB access token (creates new client)
            tmdb_api_key: TMDB API key (creates new client)
            omdb_api_key: OMDB API key for IMDB lookups (primary source)
            organize_folders: Create series/season folder structure
            include_episode_title: Include episode titles in filenames
        """
        # TMDB client (fallback)
        if tmdb_client:
            self.tmdb = tmdb_client
        elif tmdb_token or tmdb_api_key:
            self.tmdb = TMDBClient(access_token=tmdb_token, api_key=tmdb_api_key)
        else:
            self.tmdb = get_tmdb_client()
        
        # OMDB client (primary for IMDB data)
        self.omdb = None
        omdb_key = omdb_api_key or os.getenv("OMDB_API_KEY")
        if omdb_key:
            try:
                from .omdb_client import OMDbClient
                self.omdb = OMDbClient(api_key=omdb_key)
                logger.info("OMDB (IMDB) client initialized - using as primary source")
            except ImportError:
                logger.warning("OMDB client not available, using TMDB only")
        
        self.parser = FilenameParser()
        self.generator = TMDBFilenameGenerator(self.tmdb)
        self.organize_folders = organize_folders
        self.include_episode_title = include_episode_title
        
        # Cache for series lookups
        self._series_cache: Dict[str, Tuple[TMDBSeriesInfo, Dict[int, Dict[int, TMDBEpisodeInfo]]]] = {}
        self._omdb_cache: Dict[str, any] = {}
    
    def _lookup_omdb(self, title: str, year: Optional[int] = None, media_type: str = "movie"):
        """Lookup title in OMDB (IMDB) first."""
        if not self.omdb:
            return None
        
        cache_key = f"{media_type}:{title}:{year}"
        if cache_key in self._omdb_cache:
            return self._omdb_cache[cache_key]
        
        try:
            if media_type == "series":
                result = self.omdb.search_series(title)
            else:
                result = self.omdb.search_movie(title, year)
            
            self._omdb_cache[cache_key] = result
            return result
        except Exception as e:
            logger.debug(f"OMDB lookup failed for {title}: {e}")
            return None
    
    def _get_series_info(
        self,
        title: str,
        season: int
    ) -> Tuple[Optional[TMDBSeriesInfo], Dict[int, TMDBEpisodeInfo]]:
        """Get series info with caching."""
        cache_key = title.lower()
        
        if cache_key in self._series_cache:
            series, seasons = self._series_cache[cache_key]
            if season in seasons:
                return series, seasons[season]
        
        series, episodes = self.tmdb.get_series_with_episodes(title, season)
        
        if series:
            if cache_key not in self._series_cache:
                self._series_cache[cache_key] = (series, {})
            self._series_cache[cache_key][1][season] = episodes
        
        return series, episodes
    
    def generate_clean_fallback_name(
        self,
        parsed: ParsedFilename,
        extension: str
    ) -> str:
        """
        Generate a clean filename when metadata lookup fails.
        Strips site prefixes, cleans up title, keeps year if available.
        
        Args:
            parsed: Parsed filename info
            extension: File extension
            
        Returns:
            Clean filename (without metadata lookup)
        """
        title = parsed.title
        
        # Clean up the title further
        # Remove common technical terms that might remain
        tech_terms = [
            r'\b(WEB-?DL|WEBRip|BluRay|BDRip|HDRip|DVDRip|HDTV)\b',
            r'\b(x264|x265|HEVC|H\.?264|H\.?265|AV1|VP9)\b',
            r'\b(AAC|AC3|DTS|FLAC|MP3|EAC3|TrueHD|Atmos)\b',
            r'\b(2160p|1080p|720p|480p|4K|UHD)\b',
            r'\b(AMZN|NF|DSNP|HMAX|ATVP|PCOK|PMTP)\b',
            r'\b(PROPER|REPACK|INTERNAL|EXTENDED|UNRATED)\b',
            r'\b(ESub|ESubs|Eng|Hindi|Tamil|Telugu|Malayalam)\b',
            r'\b(Multi|Dual|Audio)\b',
            r'\[.*?\]',  # Remove bracketed content
            r'\((?!(?:19|20)\d{2}\))[^)]*\)',  # Remove parentheses except year
        ]
        
        for pattern in tech_terms:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'[._-]+$', '', title).strip()  # Remove trailing separators
        
        # Title case
        title = title.title()
        
        if parsed.media_type == MediaType.SERIES:
            # For series: Title (Year) - S01E01.ext or Title - S01E01.ext
            ep_code = f"S{parsed.season:02d}E{parsed.episode:02d}"
            if parsed.year:
                new_name = f"{title} ({parsed.year}) - {ep_code}{extension}"
            else:
                new_name = f"{title} - {ep_code}{extension}"
        elif parsed.media_type == MediaType.MOVIE:
            # For movies: Title (Year).ext or just Title.ext
            if parsed.year:
                new_name = f"{title} ({parsed.year}){extension}"
            else:
                new_name = f"{title}{extension}"
        else:
            # Unknown type - just clean the title
            if parsed.year:
                new_name = f"{title} ({parsed.year}){extension}"
            else:
                new_name = f"{title}{extension}"
        
        return self.generator.sanitize(new_name)
    
    def generate_new_name(
        self,
        parsed: ParsedFilename,
        extension: str
    ) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        """
        Generate new filename using IMDB (OMDB) as primary, TMDB as fallback.
        
        Follows Plex naming conventions:
        - Movies: Movie Name (Year) {imdb-tt1234567}.mkv
        - TV Shows: Show Name (Year) {tvdb-123456} or {tmdb-123456}
        
        Returns:
            Tuple of (new_filename, title, tmdb_id, imdb_id)
        """
        if parsed.media_type == MediaType.SERIES:
            # Try OMDB first for series
            omdb_series = self._lookup_omdb(parsed.title, media_type="series")
            
            if omdb_series:
                logger.info(f"Found series in IMDB: {omdb_series.title} ({omdb_series.imdb_id})")
                series_title = omdb_series.title
                year_str = omdb_series.year.split('–')[0] if omdb_series.year else None
                imdb_id = omdb_series.imdb_id
                
                # Get episode info from TMDB (OMDB episode lookup is limited)
                series, episodes = self._get_series_info(series_title, parsed.season)
                tmdb_id = series.tmdb_id if series else None
                
                # Build base name with Plex hint - prefer TVDB/TMDB for TV shows
                # Format: Show Name (Year) {tmdb-123456} or {tvdb-123456}
                if year_str:
                    if tmdb_id:
                        base = f"{series_title} ({year_str}) {{tmdb-{tmdb_id}}}"
                    else:
                        base = f"{series_title} ({year_str})"
                else:
                    if tmdb_id:
                        base = f"{series_title} {{tmdb-{tmdb_id}}}"
                    else:
                        base = series_title
                
                ep_code = f"S{parsed.season:02d}E{parsed.episode:02d}"
                
                # Try to get episode title from TMDB
                if self.include_episode_title and episodes and parsed.episode in episodes:
                    ep_title = self.generator.sanitize(episodes[parsed.episode].title)
                    new_name = f"{series_title} - {ep_code} - {ep_title}{extension}"
                else:
                    # Try OMDB for episode title
                    if self.omdb and self.include_episode_title:
                        try:
                            ep_info = self.omdb.get_episode(omdb_series.imdb_id, parsed.season, parsed.episode)
                            if ep_info and ep_info.title:
                                ep_title = self.generator.sanitize(ep_info.title)
                                new_name = f"{series_title} - {ep_code} - {ep_title}{extension}"
                            else:
                                new_name = f"{series_title} - {ep_code}{extension}"
                        except:
                            new_name = f"{series_title} - {ep_code}{extension}"
                    else:
                        new_name = f"{series_title} - {ep_code}{extension}"
                
                return self.generator.sanitize(new_name), base, tmdb_id, imdb_id
            
            # Fallback to TMDB
            series, episodes = self._get_series_info(parsed.title, parsed.season)
            
            if not series:
                logger.warning(f"Series not found in IMDB or TMDB: {parsed.title}")
                return None, None, None, None
            
            # Build base name with TMDB hint for Plex
            # Format: Show Name (Year) {tmdb-123456}
            if series.year_range:
                year_start = series.year_range.split('–')[0] if '–' in series.year_range else series.year_range
                base = f"{series.title} ({year_start}) {{tmdb-{series.tmdb_id}}}"
            else:
                base = f"{series.title} {{tmdb-{series.tmdb_id}}}"
            
            ep_code = f"S{parsed.season:02d}E{parsed.episode:02d}"
            
            if self.include_episode_title and parsed.episode in episodes:
                ep_title = self.generator.sanitize(episodes[parsed.episode].title)
                new_name = f"{series.title} - {ep_code} - {ep_title}{extension}"
            else:
                new_name = f"{series.title} - {ep_code}{extension}"
            
            return self.generator.sanitize(new_name), base, series.tmdb_id, None
        
        elif parsed.media_type == MediaType.MOVIE:
            # Try OMDB (IMDB) first for movies
            omdb_movie = self._lookup_omdb(parsed.title, parsed.year, media_type="movie")
            
            if omdb_movie:
                logger.info(f"Found movie in IMDB: {omdb_movie.title} ({omdb_movie.year}) - {omdb_movie.imdb_id}")
                year = omdb_movie.year
                imdb_id = omdb_movie.imdb_id
                
                # Plex movie naming: Movie Name (Year) {imdb-tt1234567}.mkv
                if year:
                    new_name = f"{omdb_movie.title} ({year}) {{imdb-{imdb_id}}}{extension}"
                else:
                    new_name = f"{omdb_movie.title} {{imdb-{imdb_id}}}{extension}"
                
                return self.generator.sanitize(new_name), omdb_movie.title, None, imdb_id
            
            # Fallback to TMDB
            movie = self.tmdb.search_movie_single(parsed.title, parsed.year)
            
            if not movie:
                logger.warning(f"Movie not found in IMDB or TMDB: {parsed.title}")
                return None, None, None, None
            
            # Plex movie naming with TMDB: Movie Name (Year) {tmdb-123456}.mkv
            if movie.year:
                new_name = f"{movie.title} ({movie.year}) {{tmdb-{movie.tmdb_id}}}{extension}"
            else:
                new_name = f"{movie.title} {{tmdb-{movie.tmdb_id}}}{extension}"
            
            return self.generator.sanitize(new_name), movie.title, movie.tmdb_id, None
        
        return None, None, None, None
    
    def _create_nfo_file(self, media_path: Path, imdb_id: str) -> bool:
        """
        Create a .nfo file with IMDB URL for Plex matching (MOVIES ONLY).
        
        Creates TWO variations for maximum Plex compatibility:
        1. Movie Name (Year).nfo - contains IMDB URL
        2. Movie Name (Year)-imdb.nfo - contains IMDB URL
        
        Format: http://www.imdb.com/title/tt1234567/
        
        Args:
            media_path: Path to the media file
            imdb_id: IMDB ID (e.g., tt1234567)
            
        Returns:
            True if .nfo files were created successfully
        """
        try:
            # Create IMDB URL
            imdb_url = f"http://www.imdb.com/title/{imdb_id}/"
            
            # Variation 1: Movie Name (Year).nfo
            nfo_name = media_path.stem + ".nfo"
            nfo_path = media_path.parent / nfo_name
            nfo_path.write_text(imdb_url, encoding='utf-8')
            
            # Variation 2: Movie Name (Year)-imdb.nfo
            nfo_imdb_name = media_path.stem + "-imdb.nfo"
            nfo_imdb_path = media_path.parent / nfo_imdb_name
            nfo_imdb_path.write_text(imdb_url, encoding='utf-8')
            
            logger.info(f"Created .nfo files: {nfo_name}, {nfo_imdb_name} -> {imdb_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to create .nfo file: {e}")
            return False
    
    def get_target_path(
        self,
        parsed: ParsedFilename,
        new_name: str,
        base_dir: Path,
        use_fallback: bool = False,
        folder_name: Optional[str] = None
    ) -> Path:
        """
        Get target path for renamed file.
        
        Args:
            parsed: Parsed filename info
            new_name: New filename
            base_dir: Base output directory
            use_fallback: If True, don't try to lookup series info (metadata lookup failed)
            folder_name: Optional folder name with Plex hints (e.g., "Show Name (2020) {tmdb-123456}")
            
        Returns:
            Full target path
        """
        if not self.organize_folders:
            return base_dir / new_name
        
        if parsed.media_type == MediaType.SERIES:
            if folder_name:
                # Use provided folder name with Plex hints
                series_folder = self.generator.sanitize(folder_name)
            elif not use_fallback:
                series, _ = self._get_series_info(parsed.title, parsed.season)
                
                if series:
                    # Add TMDB hint for Plex matching
                    if series.year_range:
                        year_start = series.year_range.split('–')[0] if '–' in series.year_range else series.year_range
                        series_folder = f"{series.title} ({year_start}) {{tmdb-{series.tmdb_id}}}"
                    else:
                        series_folder = f"{series.title} {{tmdb-{series.tmdb_id}}}"
                    series_folder = self.generator.sanitize(series_folder)
                else:
                    series_folder = self.generator.sanitize(parsed.title)
            else:
                # Fallback: use parsed title (already cleaned)
                if parsed.year:
                    series_folder = f"{parsed.title} ({parsed.year})"
                else:
                    series_folder = parsed.title
                series_folder = self.generator.sanitize(series_folder)
            
            season_folder = f"Season {parsed.season:02d}"
            return base_dir / series_folder / season_folder / new_name
        
        elif parsed.media_type == MediaType.MOVIE:
            # Movies go in their own folder - folder name same as file (with Plex hints)
            movie_folder = Path(new_name).stem
            return base_dir / movie_folder / new_name
        
        return base_dir / new_name
    
    def rename_file(
        self,
        file_path: Path,
        output_dir: Optional[Path] = None,
        dry_run: bool = False
    ) -> RenameResult:
        """
        Rename a single media file.
        
        Args:
            file_path: Path to the file
            output_dir: Output directory (defaults to same directory)
            dry_run: If True, don't actually rename
            
        Returns:
            RenameResult with operation details
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return RenameResult(
                original_path=file_path,
                new_path=None,
                original_name=file_path.name,
                new_name=None,
                success=False,
                error="File not found",
                metadata_found=False
            )
        
        if file_path.suffix.lower() not in self.MEDIA_EXTENSIONS:
            return RenameResult(
                original_path=file_path,
                new_path=None,
                original_name=file_path.name,
                new_name=None,
                success=False,
                error=f"Not a media file: {file_path.suffix}",
                metadata_found=False
            )
        
        # Parse filename
        parsed = self.parser.parse(file_path.name)
        
        # Generate new name - returns (new_name, folder_name, tmdb_id, imdb_id)
        # folder_name includes Plex hints like {tmdb-123456} for TV shows
        use_fallback = False
        new_name, folder_name, tmdb_id, imdb_id = None, None, None, None
        metadata_found = False
        
        if parsed.media_type != MediaType.UNKNOWN:
            new_name, folder_name, tmdb_id, imdb_id = self.generate_new_name(parsed, file_path.suffix)
            metadata_found = new_name is not None
        
        # If metadata lookup failed or media type unknown, use fallback cleaning
        if not new_name:
            logger.info(f"Metadata lookup failed, using fallback cleaning for: {file_path.name}")
            new_name = self.generate_clean_fallback_name(parsed, file_path.suffix)
            use_fallback = True
            metadata_found = False
            # Use parsed title as the folder name for consistency
            folder_name = parsed.title
            tmdb_id = None
            imdb_id = None
        
        # Get target path - pass folder_name for TV shows with Plex hints
        base_dir = output_dir or file_path.parent
        target_path = self.get_target_path(parsed, new_name, base_dir, use_fallback, folder_name)
        
        # Check if already named correctly
        if file_path == target_path:
            return RenameResult(
                original_path=file_path,
                new_path=target_path,
                original_name=file_path.name,
                new_name=new_name,
                success=True,
                tmdb_title=folder_name,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                metadata_found=metadata_found,
                error="Already correctly named"
            )
        
        if dry_run:
            return RenameResult(
                original_path=file_path,
                new_path=target_path,
                original_name=file_path.name,
                new_name=new_name,
                success=True,
                tmdb_title=folder_name,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                metadata_found=metadata_found
            )
        
        # Execute rename
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(target_path))
            
            logger.info(f"Renamed: {file_path.name} -> {new_name}")
            
            # Create .nfo file with IMDB URL for Plex matching (MOVIES ONLY)
            # TV shows use folder naming with {tvdb-xxx} or {tmdb-xxx} instead
            if imdb_id and parsed.media_type == MediaType.MOVIE:
                self._create_nfo_file(target_path, imdb_id)
            
            return RenameResult(
                original_path=file_path,
                new_path=target_path,
                original_name=file_path.name,
                new_name=new_name,
                success=True,
                tmdb_title=folder_name,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                metadata_found=metadata_found
            )
        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return RenameResult(
                original_path=file_path,
                new_path=target_path,
                original_name=file_path.name,
                new_name=new_name,
                success=False,
                error=str(e),
                tmdb_title=folder_name,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                metadata_found=metadata_found
            )
    
    def rename_files(
        self,
        directory: Path,
        output_dir: Optional[Path] = None,
        dry_run: bool = False,
        recursive: bool = False
    ) -> List[RenameResult]:
        """
        Rename all media files in a directory.
        
        Args:
            directory: Directory containing media files
            output_dir: Output directory (defaults to same directory)
            dry_run: If True, don't actually rename
            recursive: Process subdirectories
            
        Returns:
            List of RenameResult for each file
        """
        directory = Path(directory)
        results = []
        
        if recursive:
            files = list(directory.rglob("*"))
        else:
            files = list(directory.iterdir())
        
        media_files = [
            f for f in files
            if f.is_file() and f.suffix.lower() in self.MEDIA_EXTENSIONS
        ]
        
        logger.info(f"Found {len(media_files)} media files in {directory}")
        
        for file_path in sorted(media_files):
            result = self.rename_file(file_path, output_dir, dry_run)
            results.append(result)
        
        return results
    
    def preview_rename(
        self,
        directory: Path,
        output_dir: Optional[Path] = None,
        recursive: bool = False
    ) -> List[RenameResult]:
        """Preview renames without executing them."""
        return self.rename_files(directory, output_dir, dry_run=True, recursive=recursive)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart Media Renamer - Rename media files using TMDB metadata"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="File or directory to rename"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output directory (default: same as input)"
    )
    parser.add_argument(
        "-t", "--token",
        help="TMDB access token"
    )
    parser.add_argument(
        "-k", "--api-key",
        help="TMDB API key"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without renaming"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Process subdirectories"
    )
    parser.add_argument(
        "--no-folders",
        action="store_true",
        help="Don't organize into folders"
    )
    parser.add_argument(
        "--no-episode-title",
        action="store_true",
        help="Don't include episode titles"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    # Get TMDB credentials
    token = args.token or os.getenv("TMDB_ACCESS_TOKEN")
    api_key = args.api_key or os.getenv("TMDB_API_KEY")
    
    if not token and not api_key:
        print("Error: TMDB credentials required")
        print("Set TMDB_ACCESS_TOKEN or TMDB_API_KEY environment variable")
        print("Or use --token or --api-key argument")
        return 1
    
    # Create renamer
    renamer = SmartRenamer(
        tmdb_token=token,
        tmdb_api_key=api_key,
        organize_folders=not args.no_folders,
        include_episode_title=not args.no_episode_title
    )
    
    # Test TMDB connection
    if not renamer.tmdb.test_connection():
        print("Error: Could not connect to TMDB API")
        return 1
    
    path = args.path
    
    if path.is_file():
        results = [renamer.rename_file(path, args.output, args.dry_run)]
    elif path.is_dir():
        results = renamer.rename_files(path, args.output, args.dry_run, args.recursive)
    else:
        print(f"Error: Path not found: {path}")
        return 1
    
    # Print results
    print()
    if args.dry_run:
        print("=== PREVIEW (dry run) ===")
    else:
        print("=== RESULTS ===")
    print()
    
    success_count = 0
    for result in results:
        if result.success:
            success_count += 1
            if result.new_name and result.original_name != result.new_name:
                print(f"✓ {result.original_name}")
                print(f"  → {result.new_name}")
                if result.tmdb_title:
                    print(f"  TMDB: {result.tmdb_title} (ID: {result.tmdb_id})")
            else:
                print(f"- {result.original_name} (no change needed)")
        else:
            print(f"✗ {result.original_name}")
            print(f"  Error: {result.error}")
        print()
    
    print(f"Processed: {len(results)} files, {success_count} successful")
    
    return 0


if __name__ == "__main__":
    exit(main())
