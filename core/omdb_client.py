#!/usr/bin/env python3
"""
OMDb API Client
Fetches movie/series data from OMDb (Open Movie Database).

OMDb provides IMDb data including ratings, plot, cast, and more.
Great for supplementing TMDB data or as a fallback.
"""

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)

# Environment variable
ENV_OMDB_API_KEY = "OMDB_API_KEY"

# Default API key (free tier)
DEFAULT_API_KEY = "8800e3b1"


@dataclass
class OMDbRating:
    """External rating from OMDb."""
    source: str
    value: str


@dataclass
class OMDbMovieInfo:
    """OMDb movie information."""
    title: str
    year: str
    imdb_id: str
    type: str  # "movie" or "series"
    rated: str | None = None
    released: str | None = None
    runtime: str | None = None
    genre: str | None = None
    director: str | None = None
    writer: str | None = None
    actors: str | None = None
    plot: str | None = None
    language: str | None = None
    country: str | None = None
    awards: str | None = None
    poster: str | None = None
    ratings: list[OMDbRating] = field(default_factory=list)
    metascore: str | None = None
    imdb_rating: str | None = None
    imdb_votes: str | None = None
    box_office: str | None = None


@dataclass
class OMDbSeriesInfo:
    """OMDb series information."""
    title: str
    year: str  # e.g., "2016–2025"
    imdb_id: str
    total_seasons: int | None = None
    rated: str | None = None
    released: str | None = None
    runtime: str | None = None
    genre: str | None = None
    director: str | None = None
    writer: str | None = None
    actors: str | None = None
    plot: str | None = None
    language: str | None = None
    country: str | None = None
    awards: str | None = None
    poster: str | None = None
    ratings: list[OMDbRating] = field(default_factory=list)
    metascore: str | None = None
    imdb_rating: str | None = None
    imdb_votes: str | None = None


@dataclass
class OMDbEpisodeInfo:
    """OMDb episode information."""
    title: str
    season: int
    episode: int
    imdb_id: str
    released: str | None = None
    runtime: str | None = None
    imdb_rating: str | None = None
    imdb_votes: str | None = None
    plot: str | None = None


class OMDbError(Exception):
    """Base OMDb error."""
    pass


class OMDbNotFoundError(OMDbError):
    """Resource not found."""
    pass


class OMDbClient:
    """
    OMDb API client for fetching IMDb data.

    Usage:
        client = OMDbClient(api_key="your_key")

        # Search by title
        movie = client.search_movie("Inception", year=2010)

        # Get by IMDb ID
        movie = client.get_by_imdb_id("tt1375666")

        # Get episode
        episode = client.get_episode("tt0944947", season=1, episode=1)
    """

    BASE_URL = "http://www.omdbapi.com/"

    def __init__(self, api_key: str | None = None, timeout: int = 10):
        """
        Initialize OMDb client.

        Args:
            api_key: OMDb API key (get from omdbapi.com)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv(ENV_OMDB_API_KEY) or DEFAULT_API_KEY
        self.timeout = timeout
        self.session = requests.Session()

    @classmethod
    def from_env(cls) -> "OMDbClient":
        """Create client from environment variables."""
        return cls(api_key=os.getenv(ENV_OMDB_API_KEY))

    def _request(self, params: dict) -> dict | None:
        """Make API request."""
        params["apikey"] = self.api_key

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("Response") == "True":
                    return data
                if data.get("Error"):
                    error = data["Error"]
                    if "not found" in error.lower():
                        raise OMDbNotFoundError(error)
                    raise OMDbError(error)
            else:
                logger.error(f"OMDb API error {response.status_code}")
                return None

        except (OMDbNotFoundError, OMDbError):
            raise
        except Exception as e:
            logger.error(f"OMDb request failed: {e}")
            return None

    def _parse_ratings(self, ratings_list: list[dict]) -> list[OMDbRating]:
        """Parse ratings list."""
        return [
            OMDbRating(source=r["Source"], value=r["Value"])
            for r in ratings_list
        ]

    def _parse_movie(self, data: dict) -> OMDbMovieInfo:
        """Parse movie data."""
        return OMDbMovieInfo(
            title=data.get("Title", ""),
            year=data.get("Year", ""),
            imdb_id=data.get("imdbID", ""),
            type=data.get("Type", "movie"),
            rated=data.get("Rated"),
            released=data.get("Released"),
            runtime=data.get("Runtime"),
            genre=data.get("Genre"),
            director=data.get("Director"),
            writer=data.get("Writer"),
            actors=data.get("Actors"),
            plot=data.get("Plot"),
            language=data.get("Language"),
            country=data.get("Country"),
            awards=data.get("Awards"),
            poster=data.get("Poster"),
            ratings=self._parse_ratings(data.get("Ratings", [])),
            metascore=data.get("Metascore"),
            imdb_rating=data.get("imdbRating"),
            imdb_votes=data.get("imdbVotes"),
            box_office=data.get("BoxOffice")
        )

    def _parse_series(self, data: dict) -> OMDbSeriesInfo:
        """Parse series data."""
        total_seasons = None
        if data.get("totalSeasons") and data["totalSeasons"].isdigit():
            total_seasons = int(data["totalSeasons"])

        return OMDbSeriesInfo(
            title=data.get("Title", ""),
            year=data.get("Year", ""),
            imdb_id=data.get("imdbID", ""),
            total_seasons=total_seasons,
            rated=data.get("Rated"),
            released=data.get("Released"),
            runtime=data.get("Runtime"),
            genre=data.get("Genre"),
            director=data.get("Director"),
            writer=data.get("Writer"),
            actors=data.get("Actors"),
            plot=data.get("Plot"),
            language=data.get("Language"),
            country=data.get("Country"),
            awards=data.get("Awards"),
            poster=data.get("Poster"),
            ratings=self._parse_ratings(data.get("Ratings", [])),
            metascore=data.get("Metascore"),
            imdb_rating=data.get("imdbRating"),
            imdb_votes=data.get("imdbVotes")
        )

    def _parse_episode(self, data: dict, season: int, episode: int) -> OMDbEpisodeInfo:
        """Parse episode data."""
        return OMDbEpisodeInfo(
            title=data.get("Title", ""),
            season=season,
            episode=episode,
            imdb_id=data.get("imdbID", ""),
            released=data.get("Released"),
            runtime=data.get("Runtime"),
            imdb_rating=data.get("imdbRating"),
            imdb_votes=data.get("imdbVotes"),
            plot=data.get("Plot")
        )

    @lru_cache(maxsize=200)
    def search_movie(self, title: str, year: int | None = None) -> OMDbMovieInfo | None:
        """
        Search for a movie by title.

        Args:
            title: Movie title
            year: Optional year to narrow search

        Returns:
            OMDbMovieInfo if found
        """
        params = {"t": title, "type": "movie"}
        if year:
            params["y"] = year

        try:
            data = self._request(params)
            if data:
                return self._parse_movie(data)
        except OMDbNotFoundError:
            logger.debug(f"Movie not found: {title}")

        return None

    @lru_cache(maxsize=200)
    def search_series(self, title: str) -> OMDbSeriesInfo | None:
        """
        Search for a TV series by title.

        Args:
            title: Series title

        Returns:
            OMDbSeriesInfo if found
        """
        params = {"t": title, "type": "series"}

        try:
            data = self._request(params)
            if data:
                return self._parse_series(data)
        except OMDbNotFoundError:
            logger.debug(f"Series not found: {title}")

        return None

    def get_by_imdb_id(self, imdb_id: str) -> OMDbMovieInfo | None:
        """
        Get movie/series by IMDb ID.

        Args:
            imdb_id: IMDb ID (e.g., "tt1375666")

        Returns:
            OMDbMovieInfo or OMDbSeriesInfo
        """
        params = {"i": imdb_id}

        try:
            data = self._request(params)
            if data:
                if data.get("Type") == "series":
                    return self._parse_series(data)
                return self._parse_movie(data)
        except OMDbNotFoundError:
            logger.debug(f"IMDb ID not found: {imdb_id}")

        return None

    def get_episode(
        self,
        series_imdb_id: str,
        season: int,
        episode: int
    ) -> OMDbEpisodeInfo | None:
        """
        Get episode information.

        Args:
            series_imdb_id: IMDb ID of the series
            season: Season number
            episode: Episode number

        Returns:
            OMDbEpisodeInfo if found
        """
        params = {
            "i": series_imdb_id,
            "Season": season,
            "Episode": episode
        }

        try:
            data = self._request(params)
            if data:
                return self._parse_episode(data, season, episode)
        except OMDbNotFoundError:
            logger.debug(f"Episode not found: {series_imdb_id} S{season}E{episode}")

        return None

    def test_connection(self) -> bool:
        """Test API connection."""
        try:
            result = self.get_by_imdb_id("tt0111161")  # Shawshank Redemption
            return result is not None
        except Exception:
            return False


# Singleton
_omdb_client: OMDbClient | None = None


def get_omdb_client(api_key: str | None = None) -> OMDbClient:
    """Get or create OMDb client singleton."""
    global _omdb_client
    if _omdb_client is None:
        _omdb_client = OMDbClient(api_key=api_key)
    return _omdb_client


if __name__ == "__main__":
    import sys

    api_key = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API_KEY
    client = OMDbClient(api_key=api_key)

    # Test connection
    print("Testing OMDb connection...")
    if not client.test_connection():
        print("❌ Connection failed!")
        sys.exit(1)
    print("✅ Connected to OMDb\n")

    # Test movie
    print("Testing movie lookup...")
    movie = client.search_movie("Inception", 2010)
    if movie:
        print(f"✅ {movie.title} ({movie.year})")
        print(f"   IMDb: {movie.imdb_rating}/10 ({movie.imdb_votes} votes)")
        print(f"   Genre: {movie.genre}")
        print("   Ratings:")
        for rating in movie.ratings:
            print(f"      {rating.source}: {rating.value}")

    print()

    # Test series
    print("Testing series lookup...")
    series = client.search_series("Stranger Things")
    if series:
        print(f"✅ {series.title} ({series.year})")
        print(f"   IMDb: {series.imdb_rating}/10")
        print(f"   Seasons: {series.total_seasons}")
        print(f"   Genre: {series.genre}")
