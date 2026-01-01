#!/usr/bin/env python3
"""
IMDB Lookup Module
Fetches accurate series/movie data from IMDB for proper naming.
"""

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)


@dataclass
class IMDBSeriesInfo:
    """IMDB series information."""
    title: str
    imdb_id: str
    year_range: str  # e.g., "2016–2025"
    start_year: int
    end_year: int | None
    is_ongoing: bool
    total_seasons: int
    genres: list[str]
    rating: float | None


@dataclass
class IMDBEpisodeInfo:
    """IMDB episode information."""
    title: str
    season: int
    episode: int
    imdb_id: str
    air_date: str | None
    rating: float | None


class IMDBLookup:
    """
    Lookup series and episode information from IMDB.
    Uses the unofficial IMDB API endpoints.
    """

    # IMDB suggestion API (used by search bar)
    SUGGEST_API = "https://v2.sg.media-imdb.com/suggestion/{letter}/{query}.json"

    # Alternative: OMDb API (requires free API key from omdbapi.com)
    OMDB_API = "http://www.omdbapi.com/"

    def __init__(self, omdb_api_key: str | None = None):
        """
        Initialize IMDB lookup.

        Args:
            omdb_api_key: Optional OMDb API key for more detailed lookups.
                         Get free key at: https://www.omdbapi.com/apikey.aspx
        """
        self.omdb_api_key = omdb_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    @lru_cache(maxsize=100)
    def search_series(self, query: str) -> IMDBSeriesInfo | None:
        """
        Search for a TV series on IMDB and return its info.
        Results are cached for performance.

        Args:
            query: Series name to search for (e.g., "Stranger Things")

        Returns:
            IMDBSeriesInfo if found, None otherwise
        """
        # Clean the query
        query_clean = re.sub(r'[^\w\s]', '', query).strip().lower()

        # Try OMDb API first if we have a key (more reliable)
        if self.omdb_api_key:
            result = self._search_omdb(query_clean)
            if result:
                return result

        # Fall back to IMDB suggestion API
        return self._search_imdb_suggest(query_clean)

    def _search_omdb(self, query: str) -> IMDBSeriesInfo | None:
        """Search using OMDb API."""
        try:
            response = self.session.get(
                self.OMDB_API,
                params={
                    'apikey': self.omdb_api_key,
                    't': query,
                    'type': 'series'
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('Response') == 'True':
                    return self._parse_omdb_series(data)

        except Exception as e:
            logger.warning(f"OMDb API error: {e}")

        return None

    def _parse_omdb_series(self, data: dict) -> IMDBSeriesInfo:
        """Parse OMDb API response into IMDBSeriesInfo."""
        year_str = data.get('Year', '')

        # Parse year range (e.g., "2016–2025" or "2016–")
        start_year = None
        end_year = None
        is_ongoing = False

        if '–' in year_str:
            parts = year_str.split('–')
            start_year = int(parts[0]) if parts[0].isdigit() else None
            if len(parts) > 1 and parts[1].isdigit():
                end_year = int(parts[1])
            else:
                is_ongoing = True
        elif year_str.isdigit():
            start_year = int(year_str)
            is_ongoing = True
            year_str = f"{year_str}–"

        # Get rating
        rating = None
        if data.get('imdbRating') and data['imdbRating'] != 'N/A':
            rating = float(data['imdbRating'])

        # Get total seasons
        total_seasons = 1
        if data.get('totalSeasons') and data['totalSeasons'].isdigit():
            total_seasons = int(data['totalSeasons'])

        return IMDBSeriesInfo(
            title=data.get('Title', ''),
            imdb_id=data.get('imdbID', ''),
            year_range=year_str,
            start_year=start_year,
            end_year=end_year,
            is_ongoing=is_ongoing,
            total_seasons=total_seasons,
            genres=data.get('Genre', '').split(', ') if data.get('Genre') else [],
            rating=rating
        )

    def _search_imdb_suggest(self, query: str) -> IMDBSeriesInfo | None:
        """Search using IMDB's suggestion API."""
        try:
            # IMDB suggestion API uses first letter for URL path
            first_letter = query[0].lower() if query else 'a'
            url = self.SUGGEST_API.format(letter=first_letter, query=query.replace(' ', '_'))

            response = self.session.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                # Find first TV series result
                for item in data.get('d', []):
                    # 'qid' indicates type: tvSeries, movie, etc.
                    if item.get('qid') == 'tvSeries':
                        return self._parse_imdb_suggest_item(item)

        except Exception as e:
            logger.warning(f"IMDB suggest API error: {e}")

        return None

    def _parse_imdb_suggest_item(self, item: dict) -> IMDBSeriesInfo:
        """Parse IMDB suggestion API item."""
        # Year info comes as "y" (start year) and "yr" (year range string)
        start_year = item.get('y')
        year_range = item.get('yr', str(start_year) if start_year else '')

        # Determine if ongoing
        is_ongoing = year_range.endswith('–') or year_range.endswith('-')

        # Parse end year
        end_year = None
        if '–' in year_range or '-' in year_range:
            parts = re.split(r'[–-]', year_range)
            if len(parts) > 1 and parts[1].isdigit():
                end_year = int(parts[1])

        return IMDBSeriesInfo(
            title=item.get('l', ''),
            imdb_id=item.get('id', ''),
            year_range=year_range.replace('-', '–'),  # Normalize to en-dash
            start_year=start_year,
            end_year=end_year,
            is_ongoing=is_ongoing,
            total_seasons=0,  # Not available from suggest API
            genres=[],
            rating=None
        )

    def get_episode_info(self, imdb_id: str, season: int, episode: int) -> IMDBEpisodeInfo | None:
        """
        Get episode information from IMDB.
        Requires OMDb API key.

        Args:
            imdb_id: IMDB ID of the series (e.g., "tt4574334")
            season: Season number
            episode: Episode number

        Returns:
            IMDBEpisodeInfo if found, None otherwise
        """
        if not self.omdb_api_key:
            logger.warning("OMDb API key required for episode lookup")
            return None

        try:
            response = self.session.get(
                self.OMDB_API,
                params={
                    'apikey': self.omdb_api_key,
                    'i': imdb_id,
                    'Season': season,
                    'Episode': episode
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('Response') == 'True':
                    rating = None
                    if data.get('imdbRating') and data['imdbRating'] != 'N/A':
                        rating = float(data['imdbRating'])

                    return IMDBEpisodeInfo(
                        title=data.get('Title', ''),
                        season=season,
                        episode=episode,
                        imdb_id=data.get('imdbID', ''),
                        air_date=data.get('Released'),
                        rating=rating
                    )

        except Exception as e:
            logger.warning(f"Episode lookup error: {e}")

        return None

    def get_series_with_episodes(self, query: str, season: int | None = None) -> tuple[IMDBSeriesInfo | None, dict[int, IMDBEpisodeInfo]]:
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

        if series and season and self.omdb_api_key:
            # Get all episodes for the season
            try:
                response = self.session.get(
                    self.OMDB_API,
                    params={
                        'apikey': self.omdb_api_key,
                        'i': series.imdb_id,
                        'Season': season
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('Response') == 'True':
                        for ep in data.get('Episodes', []):
                            ep_num = int(ep.get('Episode', 0))
                            rating = None
                            if ep.get('imdbRating') and ep['imdbRating'] != 'N/A':
                                rating = float(ep['imdbRating'])

                            episodes[ep_num] = IMDBEpisodeInfo(
                                title=ep.get('Title', ''),
                                season=season,
                                episode=ep_num,
                                imdb_id=ep.get('imdbID', ''),
                                air_date=ep.get('Released'),
                                rating=rating
                            )

            except Exception as e:
                logger.warning(f"Season episodes lookup error: {e}")

        return series, episodes


# Singleton instance for easy access
_imdb_lookup: IMDBLookup | None = None


# Default OMDb API key
DEFAULT_OMDB_API_KEY = "8800e3b1"


def get_imdb_lookup(omdb_api_key: str | None = None) -> IMDBLookup:
    """Get or create the IMDB lookup singleton."""
    global _imdb_lookup
    key = omdb_api_key or DEFAULT_OMDB_API_KEY
    if _imdb_lookup is None or (key and _imdb_lookup.omdb_api_key != key):
        _imdb_lookup = IMDBLookup(key)
    return _imdb_lookup


def lookup_series(name: str, omdb_api_key: str | None = None) -> IMDBSeriesInfo | None:
    """
    Convenience function to look up a series.

    Args:
        name: Series name to search
        omdb_api_key: Optional OMDb API key

    Returns:
        IMDBSeriesInfo if found
    """
    return get_imdb_lookup(omdb_api_key).search_series(name)


if __name__ == '__main__':
    # Test the lookup
    import sys

    api_key = sys.argv[1] if len(sys.argv) > 1 else None

    lookup = IMDBLookup(api_key)

    # Test series lookup
    test_series = ['Stranger Things', 'Game of Thrones', 'The Bear', 'Wednesday']

    for name in test_series:
        print(f"\n🔍 Searching: {name}")
        info = lookup.search_series(name)
        if info:
            print(f"   ✅ {info.title} ({info.year_range})")
            print(f"   📺 IMDB: {info.imdb_id}")
            if info.rating:
                print(f"   ⭐ Rating: {info.rating}")
        else:
            print("   ❌ Not found")
