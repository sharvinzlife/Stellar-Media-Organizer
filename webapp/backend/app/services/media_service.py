"""
Media processing service - adapted from original media_organizer.py
"""
import os
import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class MediaFile:
    """Represents a media file with its metadata."""
    path: str
    original_name: str
    cleaned_name: Optional[str] = None
    format_detected: Optional[str] = None
    is_series: bool = False
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None
    audio_tracks: Optional[List[Dict]] = None
    video_tracks: Optional[List[Dict]] = None
    subtitle_tracks: Optional[List[Dict]] = None
    
    def to_dict(self):
        return asdict(self)


class SeriesDetector:
    """Detects TV series and extracts season/episode information."""
    
    @staticmethod
    def detect_series(filename: str) -> Tuple[bool, Optional[str], Optional[int], Optional[int], Optional[int]]:
        """
        Detect if filename is a TV series and extract information.
        Returns: (is_series, series_name, season, episode, year)
        """
        patterns = [
            r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?[Ss](\d{1,2})[Ee](\d{1,2})',
            r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?Season[.\s]+(\d{1,2})[.\s]+Episode[.\s]+(\d{1,2})',
            r'^(.+?)[.\s]+(?:\((\d{4})\)[.\s]+)?(\d{1,2})[x×](\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                groups = match.groups()
                series_name = groups[0].strip()
                year = int(groups[1]) if groups[1] else None
                season = int(groups[2])
                episode = int(groups[3])
                
                series_name = re.sub(r'[.\-_]+', ' ', series_name).strip()
                series_name = re.sub(r'\s+', ' ', series_name)
                
                return True, series_name, season, episode, year
        
        return False, None, None, None, None
    
    @staticmethod
    def create_series_folder_structure(base_path: Path, series_name: str, year: Optional[int] = None) -> Path:
        """Create proper series folder structure for media servers."""
        if year:
            series_folder_name = f"{series_name} ({year})"
        else:
            series_folder_name = series_name
        
        series_folder_name = re.sub(r'[<>:"|*?]', '_', series_folder_name)
        series_folder_name = series_folder_name.strip()
        
        series_path = base_path / series_folder_name
        series_path.mkdir(exist_ok=True)
        
        return series_path
    
    @staticmethod
    def create_episode_filename(series_name: str, season: int, episode: int, year: Optional[int], extension: str) -> str:
        """Create properly formatted episode filename."""
        if year:
            base_name = f"{series_name} ({year})"
        else:
            base_name = series_name
        
        episode_name = f"{base_name} - S{season:02d}E{episode:02d}{extension}"
        episode_name = re.sub(r'[<>:"|*?]', '_', episode_name)
        
        return episode_name


class FormatCleaner(ABC):
    """Abstract base class for format-specific cleaners."""
    
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
    """Cleaner for 5MovieRulz format files."""
    
    def can_clean(self, filename: str) -> bool:
        return bool(re.search(r'^(www\.)?[0-9]+[Mm]ovie[Rr]ul[zs]\.[a-zA-Z]+ - ', filename))
    
    def clean(self, filename: str) -> str:
        cleaned = re.sub(r'^(www\.)?[0-9]+[Mm]ovie[Rr]ul[zs]\.[a-zA-Z]+ - ', '', filename)
        match = re.match(r'^(.+?)\((\d{4})\)\s+.*$', cleaned)
        if match:
            title = match.group(1).strip()
            year = match.group(2)
            return f"{title} ({year})"
        return cleaned
    
    def get_format_name(self) -> str:
        return "MovieRulz"


class TamilMVCleaner(FormatCleaner):
    """Cleaner for TamilMV format files - handles all variations."""
    
    # Updated pattern: case-insensitive, optional numbers, optional letters after TamilMV
    pattern = re.compile(r'^(www\.)?[0-9]*tamilmv[a-z]*\.[a-z]+ - ', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        return bool(self.pattern.search(filename))
    
    def clean(self, filename: str) -> str:
        return self.pattern.sub('', filename)
    
    def get_format_name(self) -> str:
        return "TamilMV"


class SanetCleaner(FormatCleaner):
    """Cleaner for Sanet.st format files."""
    
    def can_clean(self, filename: str) -> bool:
        return bool(re.search(r'^[Ss]anet\.st\.', filename))
    
    def clean(self, filename: str) -> str:
        cleaned = re.sub(r'^[Ss]anet\.st\.', '', filename)
        cleaned = re.sub(r'\.(19[0-9][0-9]|20[0-9][0-9])\..*$', r'.\1', cleaned)
        
        match = re.match(r'^(.+)\.([0-9]{4})$', cleaned)
        if match:
            title = match.group(1).replace('.', ' ')
            year = match.group(2)
            return f"{title} ({year})"
        
        return cleaned.replace('.', ' ')
    
    def get_format_name(self) -> str:
        return "Sanet.st"


class StandardReleaseCleaner(FormatCleaner):
    """Cleaner for standard scene/P2P release format."""
    
    def can_clean(self, filename: str) -> bool:
        dot_pattern = r'^[A-Za-z0-9]+\.(19[0-9][0-9]|20[0-9][0-9])\.[0-9]+p\b'
        underscore_pattern = r'^.+?_(19[0-9][0-9]|20[0-9][0-9])_[0-9]+p'
        return bool(re.search(dot_pattern, filename) or re.search(underscore_pattern, filename))
    
    def clean(self, filename: str) -> str:
        match = re.match(r'^([A-Za-z0-9\.\-_]+?)\.(19[0-9][0-9]|20[0-9][0-9])\.[0-9]+p.*$', filename, re.IGNORECASE)
        
        if match:
            title = match.group(1)
            year = match.group(2)
            title = re.sub(r'[\.\-_]+', ' ', title)
            title = re.sub(r'\s+', ' ', title).strip()
            return f"{title} ({year})"
        
        match = re.match(r'^(.+?)_(19[0-9][0-9]|20[0-9][0-9])_[0-9]+p.*$', filename, re.IGNORECASE)
        
        if match:
            title = match.group(1)
            year = match.group(2)
            title = re.sub(r'_+', ' ', title)
            title = re.sub(r'\s+', ' ', title).strip()
            return f"{title} ({year})"
        
        return filename
    
    def get_format_name(self) -> str:
        return "Standard Release"


class MediaOrganizer:
    """Main class for organizing media files."""
    
    def __init__(self):
        self.cleaners: List[FormatCleaner] = [
            MovieRulzCleaner(),
            TamilMVCleaner(),
            SanetCleaner(),
            StandardReleaseCleaner(),
        ]
        self.series_detector = SeriesDetector()
    
    def clean_filename(self, filename: str) -> Tuple[str, Optional[str]]:
        """Clean filename using appropriate cleaner."""
        for cleaner in self.cleaners:
            if cleaner.can_clean(filename):
                cleaned = cleaner.clean(filename)
                return cleaned, cleaner.get_format_name()
        return filename, None
    
    def analyze_media_file(self, file_path: Path) -> MediaFile:
        """Analyze a media file and extract metadata."""
        media_file = MediaFile(path=str(file_path), original_name=file_path.name)
        
        cleaned_name, format_detected = self.clean_filename(file_path.name)
        media_file.cleaned_name = cleaned_name
        media_file.format_detected = format_detected
        
        is_series, series_name, season, episode, year = self.series_detector.detect_series(cleaned_name)
        media_file.is_series = is_series
        media_file.series_name = series_name
        media_file.season = season
        media_file.episode = episode
        media_file.year = year
        
        return media_file
    
    def ensure_extension(self, new_name: str, original_name: str) -> str:
        """Ensure the cleaned name has the correct extension."""
        original_ext = Path(original_name).suffix
        if original_ext and not new_name.endswith(original_ext):
            return new_name + original_ext
        return new_name
    
    def organize_files(self, directory: Union[str, Path]) -> List[MediaFile]:
        """Organize files in the given directory."""
        directory = Path(directory)
        processed_files = []
        
        logger.info(f"Starting organization in {directory}")
        
        # Process loose files
        self._process_loose_files(directory, processed_files)
        
        # Process directories
        self._process_directories(directory, processed_files)
        
        return processed_files
    
    def _process_loose_files(self, directory: Path, processed_files: List[MediaFile]):
        """Process loose files in the directory."""
        series_groups = {}
        movie_files = []
        
        for file_path in directory.iterdir():
            if file_path.is_dir() or file_path.suffix.lower() not in ['.mkv', '.mp4', '.avi'] or file_path.name.startswith('.'):
                continue
            
            media_file = self.analyze_media_file(file_path)
            
            if media_file.is_series:
                series_key = (media_file.series_name, media_file.year)
                if series_key not in series_groups:
                    series_groups[series_key] = []
                series_groups[series_key].append(media_file)
            else:
                movie_files.append(media_file)
            
            processed_files.append(media_file)
        
        # Process series files
        for (series_name, year), episodes in series_groups.items():
            self._organize_series_files(directory, series_name, year, episodes)
        
        # Process movie files
        for media_file in movie_files:
            self._organize_movie_file(directory, media_file)
    
    def _organize_series_files(self, base_dir: Path, series_name: str, year: Optional[int], episodes: List[MediaFile]):
        """Organize series files into proper folder structure."""
        series_folder = self.series_detector.create_series_folder_structure(base_dir, series_name, year)
        
        logger.info(f"Organizing series: {series_name}" + (f" ({year})" if year else ""))
        
        for media_file in episodes:
            if media_file.season and media_file.episode:
                new_filename = self.series_detector.create_episode_filename(
                    series_name, media_file.season, media_file.episode, year, Path(media_file.path).suffix
                )
                
                target_path = series_folder / new_filename
                Path(media_file.path).rename(target_path)
                media_file.path = str(target_path)
    
    def _organize_movie_file(self, base_dir: Path, media_file: MediaFile):
        """Organize a movie file."""
        if media_file.cleaned_name and media_file.cleaned_name != media_file.original_name:
            final_name = self.ensure_extension(media_file.cleaned_name, media_file.original_name)
            folder_name = Path(final_name).stem
            folder_name = re.sub(r'[<>:"|*?]', '_', folder_name).strip()
            
            target_folder = base_dir / folder_name
            target_folder.mkdir(exist_ok=True)
            target_path = target_folder / final_name
            
            Path(media_file.path).rename(target_path)
            media_file.path = str(target_path)
    
    def _process_directories(self, directory: Path, processed_files: List[MediaFile]):
        """Process directories that need renaming."""
        for dir_path in directory.iterdir():
            if not dir_path.is_dir():
                continue
            
            cleaned_name, format_detected = self.clean_filename(dir_path.name)
            
            if cleaned_name != dir_path.name:
                new_dir_path = directory / cleaned_name
                if not new_dir_path.exists():
                    dir_path.rename(new_dir_path)
                    dir_path = new_dir_path
            
            # Process files inside directory
            for file_path in dir_path.iterdir():
                if not file_path.is_file():
                    continue
                
                media_file = self.analyze_media_file(file_path)
                
                if media_file.cleaned_name and media_file.cleaned_name != media_file.original_name:
                    final_name = self.ensure_extension(media_file.cleaned_name, media_file.original_name)
                    target_path = dir_path / final_name
                    
                    if not target_path.exists():
                        file_path.rename(target_path)
                        media_file.path = str(target_path)
                
                processed_files.append(media_file)


class AudioTrackFilter:
    """Class for filtering audio tracks in MKV files."""
    
    def __init__(self):
        self.language_keywords = {
            'malayalam': ['malayalam', 'mal', 'ml', 'മലയാളം'],
            'tamil': ['tamil', 'tam', 'ta', 'தமிழ்'],
            'telugu': ['telugu', 'tel', 'te', 'తెలుగు'],
            'hindi': ['hindi', 'hin', 'hi', 'हिन्दी'],
            'english': ['english', 'eng', 'en'],
            'kannada': ['kannada', 'kan', 'kn', 'ಕನ್ನಡ'],
            'bengali': ['bengali', 'ben', 'bn', 'বাংলা']
        }
    
    def check_mkvtoolnix_available(self) -> bool:
        """Check if MKVToolNix is installed."""
        try:
            subprocess.run(['mkvmerge', '--version'], capture_output=True, check=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("MKVToolNix not found")
            return False
    
    def check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is installed."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg not found")
            return False
    
    def get_track_info(self, file_path: Path) -> Dict:
        """Get track information from MKV file using mkvmerge."""
        try:
            cmd = ['mkvmerge', '-J', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            track_data = json.loads(result.stdout)
            
            info = {
                'audio_tracks': [],
                'video_tracks': [],
                'subtitle_tracks': []
            }
            
            for track in track_data.get('tracks', []):
                track_info = {
                    'id': track['id'],
                    'type': track['type'],
                    'language': track['properties'].get('language', 'und'),
                    'track_name': track['properties'].get('track_name', ''),
                    'codec': track['codec']
                }
                
                if track['type'] == 'audio':
                    info['audio_tracks'].append(track_info)
                elif track['type'] == 'video':
                    info['video_tracks'].append(track_info)
                elif track['type'] == 'subtitles':
                    info['subtitle_tracks'].append(track_info)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting track info for {file_path}: {e}")
            return {}
    
    def is_language_track(self, track: Dict, target_language: str) -> bool:
        """Check if a track matches the target language."""
        if target_language.lower() not in self.language_keywords:
            return False
            
        keywords = self.language_keywords[target_language.lower()]
        
        lang = track.get('language', '').lower()
        if lang in keywords:
            return True
        
        if lang == 'und':
            name = track.get('track_name', '').lower()
            return any(keyword in name for keyword in keywords)
        
        return False
    
    def filter_language_audio(self, file_path: Path, target_language: str = 'malayalam', 
                             output_path: Optional[Path] = None, volume_boost: float = 1.0) -> bool:
        """Filter MKV file to keep only specified language audio tracks."""
        if not self.check_mkvtoolnix_available():
            return False
        
        try:
            track_info = self.get_track_info(file_path)
            if not track_info:
                return False
            
            target_tracks = [
                track for track in track_info['audio_tracks'] 
                if self.is_language_track(track, target_language)
            ]
            
            if not target_tracks:
                logger.warning(f"No {target_language} audio tracks found in {file_path}")
                return False
            
            if output_path is None:
                suffix = f"_{target_language}"
                output_path = file_path.parent / f"{file_path.stem}{suffix}{file_path.suffix}"
            
            # Build mkvmerge command
            cmd = ['mkvmerge', '-o', str(output_path)]
            
            video_ids = [str(track['id']) for track in track_info['video_tracks']]
            if video_ids:
                cmd.extend(['--video-tracks', ','.join(video_ids)])
            else:
                cmd.extend(['--no-video'])
            
            target_ids = [str(track['id']) for track in target_tracks]
            cmd.extend(['--audio-tracks', ','.join(target_ids)])
            
            if track_info['subtitle_tracks']:
                subtitle_ids = [str(track['id']) for track in track_info['subtitle_tracks']]
                cmd.extend(['--subtitle-tracks', ','.join(subtitle_ids)])
            else:
                cmd.extend(['--no-subtitles'])
            
            cmd.append(str(file_path))
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Apply volume boost if requested
            if volume_boost != 1.0 and self.check_ffmpeg_available():
                self._apply_volume_boost(output_path, volume_boost)
            
            logger.info(f"Filtered audio: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error filtering {file_path}: {e}")
            return False
    
    def _apply_volume_boost(self, file_path: Path, volume_boost: float) -> bool:
        """Apply volume boost using ffmpeg."""
        try:
            temp_output = file_path.parent / f"{file_path.stem}_temp_boost{file_path.suffix}"
            
            cmd = [
                'ffmpeg', '-i', str(file_path),
                '-af', f'volume={volume_boost}',
                '-c:v', 'copy',
                '-c:s', 'copy',
                '-y',
                str(temp_output)
            ]
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Replace original with boosted version
            file_path.unlink()
            temp_output.rename(file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying volume boost: {e}")
            return False
    
    def batch_filter_directory(self, directory: Union[str, Path], target_language: str = 'malayalam', 
                               volume_boost: float = 1.0) -> List[Path]:
        """Filter all MKV files in directory."""
        directory = Path(directory)
        processed_files = []
        
        mkv_files = list(directory.rglob("*.mkv"))
        mkv_files = [f for f in mkv_files if f'_{target_language}' not in f.name and '_vol' not in f.name]
        
        for mkv_file in mkv_files:
            if self.filter_language_audio(mkv_file, target_language, volume_boost=volume_boost):
                processed_files.append(mkv_file)
        
        return processed_files
