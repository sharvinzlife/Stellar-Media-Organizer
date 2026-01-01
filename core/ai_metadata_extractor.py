"""
AI-powered metadata extraction using Venice AI (OpenAI-compatible API)
Uses structured outputs for reliable IMDB/MusicBrainz matching
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Venice AI Configuration
VENICE_API_KEY = os.getenv("VENICE_API_KEY", "")
VENICE_BASE_URL = "https://api.venice.ai/api/v1"
VENICE_MODEL = "llama-3.2-3b"  # Fast and cheap, supports response schema

# Common release site prefixes to strip
RELEASE_SITE_PREFIXES = [
    r'^MovieRulz[\.\s\-_]*',
    r'^TamilMV[\.\s\-_]*',
    r'^TamilRockers[\.\s\-_]*',
    r'^Sanet\.st[\.\s\-_]*',
    r'^YTS[\.\s\-_]*',
    r'^YIFY[\.\s\-_]*',
    r'^RARBG[\.\s\-_]*',
    r'^1337x[\.\s\-_]*',
    r'^Torrent[\.\s\-_]*',
    r'^www\.[^\.]+\.[\w]+[\.\s\-_]*',
]

# Common suffixes to strip from music titles
MUSIC_SUFFIXES_TO_STRIP = [
    r'\s*\(Official\s*(Music\s*)?Video\)',
    r'\s*\(Official\s*Audio\)',
    r'\s*\(Lyric\s*Video\)',
    r'\s*\(Lyrics\)',
    r'\s*\(Audio\)',
    r'\s*\(Visualizer\)',
    r'\s*\[Official\s*(Music\s*)?Video\]',
    r'\s*\[Official\s*Audio\]',
    r'\s*\[Lyric\s*Video\]',
    r'\s*\[Lyrics\]',
    r'\s*\[Audio\]',
    r'\s*ft\.?\s+.+$',  # Remove featuring artists from title
    r'\s*feat\.?\s+.+$',
]


class MediaType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"
    MUSIC = "music"
    UNKNOWN = "unknown"


@dataclass
class VideoMetadata:
    """Extracted video metadata for IMDB matching"""
    title: str
    year: int | None = None
    media_type: MediaType = MediaType.UNKNOWN
    season: int | None = None
    episode: int | None = None
    episode_title: str | None = None
    quality: str | None = None  # 1080p, 4K, etc.
    source: str | None = None   # BluRay, WEB-DL, HDRip
    codec: str | None = None    # x264, x265, HEVC
    audio: str | None = None    # DTS, AAC, etc.
    language: str | None = None
    release_group: str | None = None
    confidence: float = 0.0


@dataclass
class MusicMetadata:
    """Extracted music metadata for MusicBrainz matching"""
    artist: str
    title: str
    album: str | None = None
    track_number: int | None = None
    year: int | None = None
    genre: str | None = None
    confidence: float = 0.0


class AIMetadataExtractor:
    """
    Hybrid metadata extractor that uses regex first, then AI for complex cases.
    Uses Venice AI (OpenAI-compatible) for structured extraction.
    """

    # Confidence threshold for AI fallback (lowered to trigger AI more often)
    CONFIDENCE_THRESHOLD = 0.75

    def __init__(self, api_key: str | None = None, confidence_threshold: float = 0.75):
        self.api_key = api_key or VENICE_API_KEY
        self.client = None
        self.confidence_threshold = confidence_threshold

        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=VENICE_BASE_URL
            )
            logger.info("✅ Venice AI client initialized")
        else:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ openai package not installed. Run: pip install openai")
            if not self.api_key:
                logger.warning("⚠️ VENICE_API_KEY not set. AI extraction disabled.")

    def _strip_release_prefixes(self, name: str) -> str:
        """Strip common release site prefixes from filename"""
        for pattern in RELEASE_SITE_PREFIXES:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        return name.strip()

    def _clean_music_title(self, title: str) -> str:
        """Clean music title by removing common suffixes"""
        for pattern in MUSIC_SUFFIXES_TO_STRIP:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        return title.strip()

    def _regex_extract_video(self, filename: str) -> VideoMetadata | None:
        """Try regex-based extraction first (fast, free)"""
        # Clean filename
        name = Path(filename).stem
        name = self._strip_release_prefixes(name)

        # Common patterns
        patterns = {
            # Movie: Title (Year) or Title.Year
            'movie_year': r'^(.+?)[\.\s\-_]*\(?(\d{4})\)?',
            # Series: Title S01E01 or Title 1x01
            'series_sxxexx': r'^(.+?)[\.\s\-_]*[Ss](\d{1,2})[Ee](\d{1,2})',
            'series_xbyy': r'^(.+?)[\.\s\-_]*(\d{1,2})x(\d{1,2})',
            # Quality
            'quality': r'(2160p|1080p|720p|480p|4K|UHD)',
            # Source
            'source': r'(BluRay|BDRip|WEB-?DL|WEBRip|HDRip|DVDRip|HDTV|CAM|TS)',
            # Codec
            'codec': r'(x264|x265|HEVC|H\.?264|H\.?265|AV1|VP9)',
            # Audio
            'audio': r'(DTS|DD5\.?1|AAC|AC3|FLAC|TrueHD|Atmos)',
            # Release group (usually at end after -)
            'release_group': r'-([A-Za-z0-9]+)$'
        }

        result = VideoMetadata(title="", media_type=MediaType.UNKNOWN)

        # Try series pattern first
        series_match = re.search(patterns['series_sxxexx'], name, re.IGNORECASE)
        if not series_match:
            series_match = re.search(patterns['series_xbyy'], name, re.IGNORECASE)

        if series_match:
            result.title = series_match.group(1).replace('.', ' ').replace('_', ' ').strip()
            result.season = int(series_match.group(2))
            result.episode = int(series_match.group(3))
            result.media_type = MediaType.SERIES
            result.confidence = 0.8
        else:
            # Try movie pattern
            movie_match = re.search(patterns['movie_year'], name, re.IGNORECASE)
            if movie_match:
                result.title = movie_match.group(1).replace('.', ' ').replace('_', ' ').strip()
                result.year = int(movie_match.group(2))
                result.media_type = MediaType.MOVIE
                result.confidence = 0.7

        # Extract additional info
        for key in ['quality', 'source', 'codec', 'audio', 'release_group']:
            match = re.search(patterns[key], name, re.IGNORECASE)
            if match:
                setattr(result, key, match.group(1))

        # Detect language from common patterns
        lang_patterns = {
            'Malayalam': r'\b(Malayalam|Mal)\b',
            'Tamil': r'\b(Tamil|Tam)\b',
            'Hindi': r'\b(Hindi|Hin)\b',
            'Telugu': r'\b(Telugu|Tel)\b',
            'Kannada': r'\b(Kannada|Kan)\b',
            'English': r'\b(English|Eng)\b',
        }
        for lang, pattern in lang_patterns.items():
            if re.search(pattern, name, re.IGNORECASE):
                result.language = lang
                break

        # If we got a title, return it
        if result.title:
            return result

        return None

    def _regex_extract_music(self, filename: str) -> MusicMetadata | None:
        """Try regex-based extraction for music files"""
        name = Path(filename).stem

        # YouTube playlist format: "Playlist Name - ### - Artist - Title"
        # e.g., "Dance Party Hits - 003 - Pitbull - Give Me Everything"
        playlist_pattern = r'^(.+?)\s*-\s*(\d{3})\s*-\s*(.+?)\s*-\s*(.+)$'
        match = re.match(playlist_pattern, name)
        if match:
            album = match.group(1).strip()
            track_num = int(match.group(2))
            artist = match.group(3).strip()
            title = self._clean_music_title(match.group(4).strip())
            return MusicMetadata(
                artist=artist,
                title=title,
                album=album,
                track_number=track_num,
                confidence=0.85
            )

        # Track# - Artist - Title (e.g., "01 - Daft Punk - Get Lucky")
        track_artist_title = r'^(\d{1,3})\s*[-\.]\s*(.+?)\s*-\s*(.+)$'
        match = re.match(track_artist_title, name)
        if match:
            return MusicMetadata(
                track_number=int(match.group(1)),
                artist=match.group(2).strip(),
                title=self._clean_music_title(match.group(3).strip()),
                confidence=0.8
            )

        # Artist - Title (e.g., "Calvin Harris - Summer")
        artist_title = r'^(.+?)\s*-\s*(.+)$'
        match = re.match(artist_title, name)
        if match:
            artist = match.group(1).strip()
            title = self._clean_music_title(match.group(2).strip())
            # Check if artist looks like a track number
            if re.match(r'^\d{1,3}$', artist):
                return None  # Let AI handle this
            return MusicMetadata(
                artist=artist,
                title=title,
                confidence=0.7
            )

        return None

    def _ai_extract_video(self, filename: str) -> VideoMetadata | None:
        """Use AI for complex filename extraction"""
        if not self.client:
            return None

        try:
            response = self.client.chat.completions.create(
                model=VENICE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a media filename parser. Extract metadata from video filenames for IMDB matching.
Strip release site names like MovieRulz, TamilMV, YTS, etc. from the title.
Always respond with valid JSON only, no other text. Use this exact format:
{"title": "string", "year": number or null, "media_type": "movie" or "series", "season": number or null, "episode": number or null, "quality": "string or null", "source": "string or null", "language": "string or null"}"""
                    },
                    {
                        "role": "user",
                        "content": f"Parse this filename: {filename}"
                    }
                ],
                temperature=0.1,
                max_tokens=300
            )

            content = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            if content.startswith('{'):
                data = json.loads(content)
            else:
                # Try to find JSON in response
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    logger.error(f"No JSON found in AI response: {content[:100]}")
                    return None

            return VideoMetadata(
                title=data.get("title", ""),
                year=data.get("year"),
                media_type=MediaType(data.get("media_type", "unknown")),
                season=data.get("season"),
                episode=data.get("episode"),
                episode_title=data.get("episode_title"),
                quality=data.get("quality"),
                source=data.get("source"),
                codec=data.get("codec"),
                audio=data.get("audio"),
                language=data.get("language"),
                release_group=data.get("release_group"),
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return None

    def _ai_extract_music(self, filename: str) -> MusicMetadata | None:
        """Use AI for complex music filename extraction"""
        if not self.client:
            return None

        try:
            response = self.client.chat.completions.create(
                model=VENICE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a music filename parser. Extract metadata from audio filenames for MusicBrainz matching.
Remove suffixes like "(Official Video)", "(Audio)", "(Lyrics)" from the title.
Always respond with valid JSON only, no other text. Use this exact format:
{"artist": "string", "title": "string", "album": "string or null", "track_number": number or null, "year": number or null}"""
                    },
                    {
                        "role": "user",
                        "content": f"Parse this filename: {filename}"
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            if content.startswith('{'):
                data = json.loads(content)
            else:
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    return None

            return MusicMetadata(
                artist=data.get("artist", ""),
                title=data.get("title", ""),
                album=data.get("album"),
                track_number=data.get("track_number"),
                year=data.get("year"),
                genre=data.get("genre"),
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"AI music extraction failed: {e}")
            return None

    def extract_video_metadata(self, filename: str, use_ai_fallback: bool = True, force_ai: bool = False) -> VideoMetadata:
        """
        Extract video metadata using hybrid approach:
        1. Try regex first (fast, free)
        2. Fall back to AI if regex fails or confidence is low

        Args:
            filename: Video filename to parse
            use_ai_fallback: Whether to use AI if regex confidence is low
            force_ai: Force AI extraction regardless of regex confidence
        """
        # Force AI if requested
        if force_ai and self.client:
            logger.info(f"Force AI extraction for: {filename}")
            ai_result = self._ai_extract_video(filename)
            if ai_result:
                return ai_result

        # Try regex first
        result = self._regex_extract_video(filename)

        if result and result.confidence >= self.confidence_threshold:
            logger.debug(f"Regex extracted: {result.title} (confidence: {result.confidence})")
            return result

        # Fall back to AI
        if use_ai_fallback and self.client:
            logger.info(f"Using AI for: {filename} (regex confidence: {result.confidence if result else 0})")
            ai_result = self._ai_extract_video(filename)
            if ai_result:
                return ai_result

        # Return regex result even if low confidence, or empty result
        return result or VideoMetadata(title=Path(filename).stem, media_type=MediaType.UNKNOWN, confidence=0.1)

    def extract_music_metadata(self, filename: str, use_ai_fallback: bool = True, force_ai: bool = False) -> MusicMetadata:
        """
        Extract music metadata using hybrid approach

        Args:
            filename: Music filename to parse
            use_ai_fallback: Whether to use AI if regex confidence is low
            force_ai: Force AI extraction regardless of regex confidence
        """
        # Force AI if requested
        if force_ai and self.client:
            logger.info(f"Force AI extraction for music: {filename}")
            ai_result = self._ai_extract_music(filename)
            if ai_result:
                return ai_result

        # Try regex first
        result = self._regex_extract_music(filename)

        if result and result.confidence >= self.confidence_threshold:
            logger.debug(f"Regex extracted: {result.artist} - {result.title}")
            return result

        # Fall back to AI
        if use_ai_fallback and self.client:
            logger.info(f"Using AI for music: {filename} (regex confidence: {result.confidence if result else 0})")
            ai_result = self._ai_extract_music(filename)
            if ai_result:
                return ai_result

        # Return regex result or empty
        return result or MusicMetadata(artist="Unknown", title=Path(filename).stem, confidence=0.1)

    def batch_extract_video(self, filenames: list[str], use_ai_fallback: bool = True) -> list[VideoMetadata]:
        """Extract metadata from multiple video files"""
        return [self.extract_video_metadata(f, use_ai_fallback) for f in filenames]

    def batch_extract_music(self, filenames: list[str], use_ai_fallback: bool = True) -> list[MusicMetadata]:
        """Extract metadata from multiple music files"""
        return [self.extract_music_metadata(f, use_ai_fallback) for f in filenames]


# Convenience functions
def extract_video_metadata(filename: str, api_key: str | None = None) -> VideoMetadata:
    """Quick function to extract video metadata"""
    extractor = AIMetadataExtractor(api_key)
    return extractor.extract_video_metadata(filename)


def extract_music_metadata(filename: str, api_key: str | None = None) -> MusicMetadata:
    """Quick function to extract music metadata"""
    extractor = AIMetadataExtractor(api_key)
    return extractor.extract_music_metadata(filename)


if __name__ == "__main__":
    # Test examples
    test_videos = [
        "The.Matrix.1999.1080p.BluRay.x264-SPARKS.mkv",
        "Breaking.Bad.S05E16.Felina.1080p.WEB-DL.DD5.1.H.264-NTb.mkv",
        "Inception (2010) [2160p] [4K] [BluRay] [5.1] [YTS.MX].mkv",
        "MovieRulz.Manjummel.Boys.2024.Malayalam.1080p.WEB-DL.mkv",
        "TamilMV.Aavesham.2024.Malayalam.TRUE.WEB-DL.4K.SDR.HEVC.AAC-Telly.mkv",
    ]

    test_music = [
        "01 - Daft Punk - Get Lucky.flac",
        "Calvin Harris - Summer (Official Video).opus",
        "Dance Party Hits - 003 - Pitbull - Give Me Everything.opus",
        "100 - Spinnin' Records - Imanbek & BYOR - Belly Dancer (Official Music Video).opus",
    ]

    extractor = AIMetadataExtractor()

    print("\n=== Video Metadata (Regex Only) ===")
    for f in test_videos:
        meta = extractor.extract_video_metadata(f, use_ai_fallback=False)
        print(f"\n{f}")
        print(f"  → Title: {meta.title}")
        print(f"  → Year: {meta.year}, Type: {meta.media_type.value}, Lang: {meta.language}")
        print(f"  → Confidence: {meta.confidence}")

    print("\n=== Music Metadata (Regex Only) ===")
    for f in test_music:
        meta = extractor.extract_music_metadata(f, use_ai_fallback=False)
        print(f"\n{f}")
        print(f"  → Artist: {meta.artist}")
        print(f"  → Title: {meta.title}")
        print(f"  → Album: {meta.album}, Track: {meta.track_number}")
        print(f"  → Confidence: {meta.confidence}")
