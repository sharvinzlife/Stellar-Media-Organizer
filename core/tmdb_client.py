#!/usr/bin/env python3
"""
TMDB (The Movie Database) Client
Robust client for fetching series/movie/episode data from TMDB.

Features:
- Bearer token and API key authentication
- LRU caching for performance
- Retry logic with exponential backoff
- Rate limiting awareness
- Comprehensive error handling
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)

# Environment variable names
ENV_TMDB_ACCESS_TOKEN = "TMDB_ACCESS_TOKEN"
ENV_TMDB_API_KEY = "TMDB_API_KEY"


class MediaType(str, Enum):
    """Media type enumeration."""
    MOVIE = "movie"
    TV = "tv"
    UNKNOWN = "unknown"


@dataclass
class TMDBSeriesInfo:
    """TMDB series information."""
    title: str
    tmdb_id: int
    year_range: str  # e.g., "2016–2025"
    start_year: int | None = None
    end_year: int | None = None
    is_ongoing: bool = False
    total_seasons: int = 0
    total_episodes: int = 0
    genres: list[str] = field(default_factory=list)
    rating: float | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    status: str | None = None
    networks: list[str] = field(default_factory=list)
    # Language signals from TMDB (for smarter routing / logging)
    original_language: str | None = None
    spoken_languages: list[str] = field(default_factory=list)


@dataclass
class TMDBMovieInfo:
    """TMDB movie information."""
    title: str
    tmdb_id: int
    year: int | None = None
    genres: list[str] = field(default_factory=list)
    rating: float | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    runtime: int | None = None
    tagline: str | None = None
    # Language signals from TMDB (for smarter routing / logging)
    original_language: str | None = None
    spoken_languages: list[str] = field(default_factory=list)


@dataclass
class TMDBEpisodeInfo:
    """TMDB episode information."""
    title: str
    season: int
    episode: int
    tmdb_id: int
    air_date: str | None = None
    rating: float | None = None
    overview: str | None = None
    still_path: str | None = None
    runtime: int | None = None


@dataclass
class TMDBSeasonInfo:
    """TMDB season information."""
    season_number: int
    name: str
    tmdb_id: int
    episode_count: int
    air_date: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    episodes: dict[int, TMDBEpisodeInfo] = field(default_factory=dict)


class TMDBError(Exception):
    """Base TMDB error."""
    pass


class TMDBAuthError(TMDBError):
    """Authentication error."""
    pass


class TMDBNotFoundError(TMDBError):
    """Resource not found."""
    pass


class TMDBRateLimitError(TMDBError):
    """Rate limit exceeded."""
    pass


class TMDBClient:
    """
    Robust TMDB API client with caching and retry logic.

    Usage:
        # With access token (preferred)
        client = TMDBClient(access_token="your_token")

        # With API key
        client = TMDBClient(api_key="your_api_key")

        # From environment variables
        client = TMDBClient.from_env()

        # Search and get episode info
        series, episodes = client.get_series_with_episodes("Stranger Things", season=5)
    """

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF = 2.0  # exponential backoff multiplier

    def __init__(
        self,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: int = 15,
        max_retries: int = 3
    ):
        """
        Initialize TMDB client.

        Args:
            api_key: TMDB API key (v3 auth)
            access_token: TMDB Read Access Token (Bearer auth, preferred)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        self._setup_session()

        # Cache for series lookups
        self._series_cache: dict[str, TMDBSeriesInfo] = {}
        self._movie_cache: dict[str, TMDBMovieInfo] = {}
        self._season_cache: dict[tuple[int, int], TMDBSeasonInfo] = {}

    @classmethod
    def from_env(cls) -> "TMDBClient":
        """Create client from environment variables."""
        access_token = os.getenv(ENV_TMDB_ACCESS_TOKEN)
        api_key = os.getenv(ENV_TMDB_API_KEY)

        if not access_token and not api_key:
            logger.warning(
                f"No TMDB credentials found. Set {ENV_TMDB_ACCESS_TOKEN} or {ENV_TMDB_API_KEY}"
            )

        return cls(api_key=api_key, access_token=access_token)

    def _setup_session(self):
        """Configure session headers."""
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        if self.access_token:
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"

    def _request(
        self,
        endpoint: str,
        params: dict | None = None,
        method: str = "GET"
    ) -> dict | None:
        """
        Make API request with retry logic.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            method: HTTP method

        Returns:
            JSON response or None on failure
        """
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}

        # Add API key if not using bearer token
        if not self.access_token and self.api_key:
            params["api_key"] = self.api_key

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout
                )

                # Handle response codes
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 401:
                    raise TMDBAuthError("Invalid API key or access token")
                if response.status_code == 404:
                    raise TMDBNotFoundError(f"Resource not found: {endpoint}")
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"TMDB API error: {last_error}")

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                logger.warning(f"TMDB request timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"TMDB connection error (attempt {attempt + 1})")
            except (TMDBAuthError, TMDBNotFoundError):
                raise
            except Exception as e:
                last_error = str(e)
                logger.error(f"TMDB request failed: {e}")

            # Exponential backoff
            if attempt < self.max_retries - 1:
                delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                time.sleep(delay)

        logger.error(f"TMDB request failed after {self.max_retries} attempts: {last_error}")
        return None

    def is_configured(self) -> bool:
        """Check if client has valid credentials."""
        return bool(self.access_token or self.api_key)

    def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            result = self._request("configuration")
            return result is not None
        except TMDBAuthError:
            return False
        except Exception:
            return False

    # =========================================================================
    # SEARCH METHODS
    # =========================================================================

    def search_tv(self, query: str, year: int | None = None) -> list[TMDBSeriesInfo]:
        """
        Search for TV series.

        Args:
            query: Search query (series name)
            year: Optional first air year to filter results

        Returns:
            List of matching series
        """
        query_clean = re.sub(r'[^\w\s]', '', query).strip()

        params = {"query": query_clean}
        if year:
            params["first_air_date_year"] = year

        data = self._request("search/tv", params)
        if not data or not data.get("results"):
            return []

        results = []
        for item in data["results"][:10]:  # Limit to top 10
            info = self._parse_series_basic(item)
            if info:
                results.append(info)

        return results

    def search_movie(
        self,
        query: str,
        year: int | None = None,
        language_hint: str | None = None
    ) -> list[TMDBMovieInfo]:
        """
        Search for movies.

        Args:
            query: Search query (movie title)
            year: Optional release year to filter results
            language_hint: Optional language hint (e.g., "malayalam", "hindi") to prioritize results

        Returns:
            List of matching movies
        """
        query_clean = re.sub(r'[^\w\s]', '', query).strip()

        params = {"query": query_clean}
        if year:
            params["year"] = year

        data = self._request("search/movie", params)
        if not data or not data.get("results"):
            return []

        results = []
        for item in data["results"][:10]:
            info = self._parse_movie_basic(item)
            if info:
                results.append(info)

        # If language hint provided, prioritize results matching that language
        if language_hint and results:
            # Map common language names to ISO 639-1 codes used by TMDB
            lang_code_map = {
                "malayalam": "ml",
                "hindi": "hi",
                "tamil": "ta",
                "telugu": "te",
                "kannada": "kn",
                "bengali": "bn",
                "marathi": "mr",
                "english": "en",
            }
            target_code = lang_code_map.get(language_hint.lower())

            if target_code:
                # Sort results: matching language first, then by original order
                def lang_priority(movie: TMDBMovieInfo) -> int:
                    if movie.original_language == target_code:
                        return 0  # Highest priority
                    return 1

                results.sort(key=lang_priority)
                logger.debug(f"Prioritized results for language: {language_hint} ({target_code})")

        return results

    @lru_cache(maxsize=200)
    def search_series(self, query: str) -> TMDBSeriesInfo | None:
        """
        Search for a TV series and return the best match with full details.
        Results are cached.

        Args:
            query: Series name to search for

        Returns:
            TMDBSeriesInfo if found, None otherwise
        """
        cache_key = query.lower().strip()

        if cache_key in self._series_cache:
            return self._series_cache[cache_key]

        results = self.search_tv(query)
        if not results:
            return None

        # Get full details for best match
        best_match = results[0]
        full_info = self.get_series_details(best_match.tmdb_id)

        if full_info:
            self._series_cache[cache_key] = full_info
            logger.info(f"TMDB: Found '{full_info.title}' ({full_info.year_range})")

        return full_info

    @lru_cache(maxsize=200)
    def search_movie_single(
        self,
        query: str,
        year: int | None = None,
        language_hint: str | None = None
    ) -> TMDBMovieInfo | None:
        """
        Search for a movie and return the best match with full details.
        Results are cached.

        Args:
            query: Movie title to search for
            year: Optional release year
            language_hint: Optional language hint to prioritize regional movies
        """
        results = self.search_movie(query, year, language_hint)
        if not results:
            return None

        # Get full details for best match
        best_match = results[0]
        return self.get_movie_details(best_match.tmdb_id)

    # =========================================================================
    # DETAIL METHODS
    # =========================================================================

    def get_series_details(self, series_id: int) -> TMDBSeriesInfo | None:
        """Get detailed series information."""
        data = self._request(f"tv/{series_id}")
        if not data:
            return None

        return self._parse_series_full(data)

    def get_movie_details(self, movie_id: int) -> TMDBMovieInfo | None:
        """Get detailed movie information."""
        data = self._request(f"movie/{movie_id}")
        if not data:
            return None

        return self._parse_movie_full(data)

    def get_season(self, series_id: int, season_number: int) -> TMDBSeasonInfo | None:
        """
        Get season information with all episodes.

        Args:
            series_id: TMDB series ID
            season_number: Season number

        Returns:
            TMDBSeasonInfo with episodes dict
        """
        cache_key = (series_id, season_number)

        if cache_key in self._season_cache:
            return self._season_cache[cache_key]

        data = self._request(f"tv/{series_id}/season/{season_number}")
        if not data:
            return None

        episodes = {}
        for ep in data.get("episodes", []):
            ep_num = ep.get("episode_number")
            if ep_num:
                episodes[ep_num] = TMDBEpisodeInfo(
                    title=ep.get("name", ""),
                    season=season_number,
                    episode=ep_num,
                    tmdb_id=ep.get("id", 0),
                    air_date=ep.get("air_date"),
                    rating=ep.get("vote_average"),
                    overview=ep.get("overview"),
                    still_path=ep.get("still_path"),
                    runtime=ep.get("runtime")
                )

        season_info = TMDBSeasonInfo(
            season_number=season_number,
            name=data.get("name", f"Season {season_number}"),
            tmdb_id=data.get("id", 0),
            episode_count=len(episodes),
            air_date=data.get("air_date"),
            overview=data.get("overview"),
            poster_path=data.get("poster_path"),
            episodes=episodes
        )

        self._season_cache[cache_key] = season_info
        return season_info

    def get_episode(
        self,
        series_id: int,
        season_number: int,
        episode_number: int
    ) -> TMDBEpisodeInfo | None:
        """Get single episode information."""
        # Try to get from cached season first
        season = self.get_season(series_id, season_number)
        if season and episode_number in season.episodes:
            return season.episodes[episode_number]

        # Fallback to direct API call
        data = self._request(
            f"tv/{series_id}/season/{season_number}/episode/{episode_number}"
        )
        if not data:
            return None

        return TMDBEpisodeInfo(
            title=data.get("name", ""),
            season=season_number,
            episode=episode_number,
            tmdb_id=data.get("id", 0),
            air_date=data.get("air_date"),
            rating=data.get("vote_average"),
            overview=data.get("overview"),
            still_path=data.get("still_path"),
            runtime=data.get("runtime")
        )

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def get_series_with_episodes(
        self,
        query: str,
        season: int
    ) -> tuple[TMDBSeriesInfo | None, dict[int, TMDBEpisodeInfo]]:
        """
        Get series info and all episode titles for a season.

        Args:
            query: Series name to search
            season: Season number to get episodes for

        Returns:
            Tuple of (series_info, {episode_num: episode_info})
        """
        series = self.search_series(query)
        episodes = {}

        if series:
            season_info = self.get_season(series.tmdb_id, season)
            if season_info:
                episodes = season_info.episodes

        return series, episodes

    def get_episode_title(
        self,
        series_name: str,
        season: int,
        episode: int
    ) -> str | None:
        """
        Quick lookup for episode title.

        Args:
            series_name: Name of the series
            season: Season number
            episode: Episode number

        Returns:
            Episode title or None
        """
        series = self.search_series(series_name)
        if not series:
            return None

        ep_info = self.get_episode(series.tmdb_id, season, episode)
        return ep_info.title if ep_info else None

    def get_image_url(self, path: str | None, size: str = "original") -> str | None:
        """
        Get full image URL from path.

        Args:
            path: Image path from TMDB (e.g., "/abc123.jpg")
            size: Image size (w92, w154, w185, w342, w500, w780, original)

        Returns:
            Full image URL or None
        """
        if not path:
            return None
        return f"{self.IMAGE_BASE_URL}/{size}{path}"

    # =========================================================================
    # PARSING HELPERS
    # =========================================================================

    def _parse_series_basic(self, data: dict) -> TMDBSeriesInfo | None:
        """Parse basic series info from search results."""
        if not data:
            return None

        first_air = data.get("first_air_date", "")
        start_year = int(first_air[:4]) if first_air and len(first_air) >= 4 else None

        return TMDBSeriesInfo(
            title=data.get("name", ""),
            tmdb_id=data.get("id", 0),
            year_range=str(start_year) if start_year else "",
            start_year=start_year,
            rating=data.get("vote_average"),
            overview=data.get("overview"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path")
        )

    def _parse_series_full(self, data: dict) -> TMDBSeriesInfo | None:
        """Parse full series info from details endpoint."""
        if not data:
            return None

        # Parse dates
        first_air = data.get("first_air_date", "")
        last_air = data.get("last_air_date", "")
        start_year = int(first_air[:4]) if first_air and len(first_air) >= 4 else None
        end_year = int(last_air[:4]) if last_air and len(last_air) >= 4 else None

        # Determine if ongoing
        status = data.get("status", "")
        is_ongoing = status in ["Returning Series", "In Production", "Planned"]

        # Build year range string
        if start_year:
            if is_ongoing:
                year_range = f"{start_year}–"
            elif end_year and end_year != start_year:
                year_range = f"{start_year}–{end_year}"
            else:
                year_range = str(start_year)
        else:
            year_range = ""

        # Extract networks
        networks = [n.get("name", "") for n in data.get("networks", []) if n.get("name")]

        # Language signals
        original_language = data.get("original_language")
        spoken_languages = [
            lang.get("iso_639_1", "")
            for lang in data.get("spoken_languages", [])
            if lang.get("iso_639_1")
        ]

        return TMDBSeriesInfo(
            title=data.get("name", ""),
            tmdb_id=data.get("id", 0),
            year_range=year_range,
            start_year=start_year,
            end_year=end_year,
            is_ongoing=is_ongoing,
            total_seasons=data.get("number_of_seasons", 0),
            total_episodes=data.get("number_of_episodes", 0),
            genres=[g.get("name", "") for g in data.get("genres", [])],
            rating=data.get("vote_average"),
            overview=data.get("overview"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            status=status,
            networks=networks,
            original_language=original_language,
            spoken_languages=spoken_languages,
        )

    def _parse_movie_basic(self, data: dict) -> TMDBMovieInfo | None:
        """Parse basic movie info from search results."""
        if not data:
            return None

        release_date = data.get("release_date", "")
        year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

        # Language signals (basic search payload includes original_language)
        original_language = data.get("original_language")

        return TMDBMovieInfo(
            title=data.get("title", ""),
            tmdb_id=data.get("id", 0),
            year=year,
            rating=data.get("vote_average"),
            overview=data.get("overview"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            original_language=original_language,
            spoken_languages=[],
        )

    def _parse_movie_full(self, data: dict) -> TMDBMovieInfo | None:
        """Parse full movie info from details endpoint."""
        if not data:
            return None

        release_date = data.get("release_date", "")
        year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

        original_language = data.get("original_language")
        spoken_languages = [
            lang.get("iso_639_1", "")
            for lang in data.get("spoken_languages", [])
            if lang.get("iso_639_1")
        ]

        return TMDBMovieInfo(
            title=data.get("title", ""),
            tmdb_id=data.get("id", 0),
            year=year,
            genres=[g.get("name", "") for g in data.get("genres", [])],
            rating=data.get("vote_average"),
            overview=data.get("overview"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            runtime=data.get("runtime"),
            tagline=data.get("tagline"),
            original_language=original_language,
            spoken_languages=spoken_languages,
        )

    def clear_cache(self):
        """Clear all caches."""
        self._series_cache.clear()
        self._movie_cache.clear()
        self._season_cache.clear()
        self.search_series.cache_clear()
        self.search_movie_single.cache_clear()


# =============================================================================
# FILENAME UTILITIES
# =============================================================================

class TMDBFilenameGenerator:
    """
    Generate Plex/Jellyfin compatible filenames using TMDB data.

    Naming conventions:
    - Series: "Show Name (Year) - S01E01 - Episode Title.ext"
    - Movie: "Movie Name (Year).ext"
    """

    # Characters not allowed in filenames
    INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')

    def __init__(self, client: TMDBClient):
        self.client = client

    def sanitize(self, name: str) -> str:
        """Remove invalid filename characters."""
        return self.INVALID_CHARS.sub('', name).strip()

    def generate_series_filename(
        self,
        series_name: str,
        season: int,
        episode: int,
        extension: str = ".mkv",
        include_episode_title: bool = True
    ) -> str | None:
        """
        Generate proper series episode filename.

        Args:
            series_name: Name of the series
            season: Season number
            episode: Episode number
            extension: File extension (with dot)
            include_episode_title: Whether to include episode title

        Returns:
            Formatted filename or None if lookup fails
        """
        series, episodes = self.client.get_series_with_episodes(series_name, season)

        if not series:
            logger.warning(f"Series not found: {series_name}")
            return None

        # Build base name
        base = f"{series.title} ({series.year_range})" if series.year_range else series.title

        # Add episode info
        ep_code = f"S{season:02d}E{episode:02d}"

        if include_episode_title and episode in episodes:
            ep_title = self.sanitize(episodes[episode].title)
            filename = f"{base} - {ep_code} - {ep_title}{extension}"
        else:
            filename = f"{base} - {ep_code}{extension}"

        return self.sanitize(filename)

    def generate_movie_filename(
        self,
        movie_name: str,
        year: int | None = None,
        extension: str = ".mkv"
    ) -> str | None:
        """
        Generate proper movie filename.

        Args:
            movie_name: Name of the movie
            year: Optional year hint for search
            extension: File extension (with dot)

        Returns:
            Formatted filename or None if lookup fails
        """
        movie = self.client.search_movie_single(movie_name, year)

        if not movie:
            logger.warning(f"Movie not found: {movie_name}")
            return None

        if movie.year:
            filename = f"{movie.title} ({movie.year}){extension}"
        else:
            filename = f"{movie.title}{extension}"

        return self.sanitize(filename)

    def generate_series_folder(self, series_name: str) -> str | None:
        """Generate series folder name."""
        series = self.client.search_series(series_name)

        if not series:
            return None

        if series.year_range:
            return self.sanitize(f"{series.title} ({series.year_range})")
        return self.sanitize(series.title)

    def generate_season_folder(self, season: int) -> str:
        """Generate season folder name."""
        return f"Season {season:02d}"


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_tmdb_client: TMDBClient | None = None


def get_tmdb_client(
    api_key: str | None = None,
    access_token: str | None = None
) -> TMDBClient:
    """Get or create TMDB client singleton."""
    global _tmdb_client

    if _tmdb_client is None:
        if api_key or access_token:
            _tmdb_client = TMDBClient(api_key=api_key, access_token=access_token)
        else:
            _tmdb_client = TMDBClient.from_env()

    return _tmdb_client


def lookup_series(name: str) -> TMDBSeriesInfo | None:
    """Convenience function to look up a series."""
    return get_tmdb_client().search_series(name)


def lookup_movie(name: str, year: int | None = None, language_hint: str | None = None) -> TMDBMovieInfo | None:
    """Convenience function to look up a movie."""
    return get_tmdb_client().search_movie_single(name, year, language_hint)


def get_episode_title(series: str, season: int, episode: int) -> str | None:
    """Convenience function to get episode title."""
    return get_tmdb_client().get_episode_title(series, season, episode)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import sys

    # Get token from args or env
    token = sys.argv[1] if len(sys.argv) > 1 else os.getenv(ENV_TMDB_ACCESS_TOKEN)
    api_key = os.getenv(ENV_TMDB_API_KEY)

    if not token and not api_key:
        print(f"Usage: python {sys.argv[0]} <TMDB_ACCESS_TOKEN>")
        print(f"Or set {ENV_TMDB_ACCESS_TOKEN} or {ENV_TMDB_API_KEY} environment variable")
        sys.exit(1)

    client = TMDBClient(access_token=token, api_key=api_key)

    # Test connection
    print("Testing TMDB connection...")
    if not client.test_connection():
        print("❌ Connection failed!")
        sys.exit(1)
    print("✅ Connected to TMDB\n")

    # Test series lookup
    test_series = ["Stranger Things", "Breaking Bad", "The Bear"]

    for name in test_series:
        print(f"🔍 Searching: {name}")
        series, episodes = client.get_series_with_episodes(name, 1)

        if series:
            print(f"   ✅ {series.title} ({series.year_range})")
            print(f"   📺 TMDB ID: {series.tmdb_id}")
            print(f"   📊 Seasons: {series.total_seasons}, Episodes: {series.total_episodes}")
            if series.rating:
                print(f"   ⭐ Rating: {series.rating:.1f}")
            print(f"   🎭 Genres: {', '.join(series.genres)}")
            if episodes:
                print(f"   📝 Season 1 Episodes ({len(episodes)}):")
                for ep_num in sorted(episodes.keys())[:5]:
                    print(f"      E{ep_num:02d}: {episodes[ep_num].title}")
                if len(episodes) > 5:
                    print(f"      ... and {len(episodes) - 5} more")
        else:
            print("   ❌ Not found")
        print()

    # Test filename generation
    print("=" * 50)
    print("Testing filename generation:")
    generator = TMDBFilenameGenerator(client)

    filename = generator.generate_series_filename("Stranger Things", 5, 1)
    print(f"   Series: {filename}")

    filename = generator.generate_movie_filename("Inception", 2010)
    print(f"   Movie: {filename}")
