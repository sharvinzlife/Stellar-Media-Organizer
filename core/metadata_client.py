#!/usr/bin/env python3
"""
Unified Metadata Client
Combines TMDB and OMDb for comprehensive media metadata.

Strategy:
- TMDB: Primary source for episode titles, accurate naming, year ranges
- OMDb: Supplement with IMDb ratings, Rotten Tomatoes, plot details
"""

import logging
from dataclasses import dataclass, field

from .omdb_client import OMDbClient, OMDbMovieInfo, OMDbSeriesInfo, get_omdb_client
from .tmdb_client import TMDBClient, TMDBEpisodeInfo, TMDBMovieInfo, TMDBSeriesInfo, get_tmdb_client

logger = logging.getLogger(__name__)


@dataclass
class EnrichedSeriesInfo:
    """Series info enriched with data from both TMDB and OMDb."""
    # Core info (from TMDB)
    title: str
    tmdb_id: int
    year_range: str
    start_year: int | None = None
    end_year: int | None = None
    is_ongoing: bool = False
    total_seasons: int = 0
    total_episodes: int = 0

    # TMDB specific
    genres: list[str] = field(default_factory=list)
    tmdb_rating: float | None = None
    overview: str | None = None
    poster_path: str | None = None
    networks: list[str] = field(default_factory=list)

    # OMDb specific (IMDb data)
    imdb_id: str | None = None
    imdb_rating: str | None = None
    imdb_votes: str | None = None
    rated: str | None = None  # PG-13, R, etc.
    runtime: str | None = None
    director: str | None = None
    actors: str | None = None
    awards: str | None = None

    # External ratings
    rotten_tomatoes: str | None = None
    metacritic: str | None = None


@dataclass
class EnrichedMovieInfo:
    """Movie info enriched with data from both TMDB and OMDb."""
    # Core info (from TMDB)
    title: str
    tmdb_id: int
    year: int | None = None

    # TMDB specific
    genres: list[str] = field(default_factory=list)
    tmdb_rating: float | None = None
    overview: str | None = None
    poster_path: str | None = None
    runtime: int | None = None
    tagline: str | None = None

    # OMDb specific (IMDb data)
    imdb_id: str | None = None
    imdb_rating: str | None = None
    imdb_votes: str | None = None
    rated: str | None = None
    director: str | None = None
    actors: str | None = None
    awards: str | None = None
    box_office: str | None = None

    # External ratings
    rotten_tomatoes: str | None = None
    metacritic: str | None = None


class UnifiedMetadataClient:
    """
    Unified client that combines TMDB and OMDb data.

    Usage:
        client = UnifiedMetadataClient()

        # Get enriched series info
        series, episodes = client.get_series_with_episodes("Stranger Things", 5)
        print(f"{series.title} - IMDb: {series.imdb_rating}, RT: {series.rotten_tomatoes}")

        # Get enriched movie info
        movie = client.get_movie("Inception", 2010)
        print(f"{movie.title} - IMDb: {movie.imdb_rating}, RT: {movie.rotten_tomatoes}")
    """

    def __init__(
        self,
        tmdb_client: TMDBClient | None = None,
        omdb_client: OMDbClient | None = None,
        tmdb_token: str | None = None,
        tmdb_api_key: str | None = None,
        omdb_api_key: str | None = None
    ):
        """
        Initialize unified client.

        Args:
            tmdb_client: Existing TMDB client
            omdb_client: Existing OMDb client
            tmdb_token: TMDB access token
            tmdb_api_key: TMDB API key
            omdb_api_key: OMDb API key
        """
        if tmdb_client:
            self.tmdb = tmdb_client
        elif tmdb_token or tmdb_api_key:
            self.tmdb = TMDBClient(access_token=tmdb_token, api_key=tmdb_api_key)
        else:
            self.tmdb = get_tmdb_client()

        if omdb_client:
            self.omdb = omdb_client
        elif omdb_api_key:
            self.omdb = OMDbClient(api_key=omdb_api_key)
        else:
            self.omdb = get_omdb_client()

    @classmethod
    def from_env(cls) -> "UnifiedMetadataClient":
        """Create client from environment variables."""
        return cls(
            tmdb_client=get_tmdb_client(),
            omdb_client=get_omdb_client()
        )

    def _enrich_series(
        self,
        tmdb_series: TMDBSeriesInfo,
        omdb_series: OMDbSeriesInfo | None = None
    ) -> EnrichedSeriesInfo:
        """Combine TMDB and OMDb series data."""
        enriched = EnrichedSeriesInfo(
            title=tmdb_series.title,
            tmdb_id=tmdb_series.tmdb_id,
            year_range=tmdb_series.year_range,
            start_year=tmdb_series.start_year,
            end_year=tmdb_series.end_year,
            is_ongoing=tmdb_series.is_ongoing,
            total_seasons=tmdb_series.total_seasons,
            total_episodes=tmdb_series.total_episodes,
            genres=tmdb_series.genres,
            tmdb_rating=tmdb_series.rating,
            overview=tmdb_series.overview,
            poster_path=tmdb_series.poster_path,
            networks=tmdb_series.networks
        )

        # Add OMDb data if available
        if omdb_series:
            enriched.imdb_id = omdb_series.imdb_id
            enriched.imdb_rating = omdb_series.imdb_rating
            enriched.imdb_votes = omdb_series.imdb_votes
            enriched.rated = omdb_series.rated
            enriched.runtime = omdb_series.runtime
            enriched.director = omdb_series.director
            enriched.actors = omdb_series.actors
            enriched.awards = omdb_series.awards

            # Extract external ratings
            for rating in omdb_series.ratings:
                if "Rotten Tomatoes" in rating.source:
                    enriched.rotten_tomatoes = rating.value
                elif "Metacritic" in rating.source:
                    enriched.metacritic = rating.value

        return enriched

    def _enrich_movie(
        self,
        tmdb_movie: TMDBMovieInfo,
        omdb_movie: OMDbMovieInfo | None = None
    ) -> EnrichedMovieInfo:
        """Combine TMDB and OMDb movie data."""
        enriched = EnrichedMovieInfo(
            title=tmdb_movie.title,
            tmdb_id=tmdb_movie.tmdb_id,
            year=tmdb_movie.year,
            genres=tmdb_movie.genres,
            tmdb_rating=tmdb_movie.rating,
            overview=tmdb_movie.overview,
            poster_path=tmdb_movie.poster_path,
            runtime=tmdb_movie.runtime,
            tagline=tmdb_movie.tagline
        )

        # Add OMDb data if available
        if omdb_movie:
            enriched.imdb_id = omdb_movie.imdb_id
            enriched.imdb_rating = omdb_movie.imdb_rating
            enriched.imdb_votes = omdb_movie.imdb_votes
            enriched.rated = omdb_movie.rated
            enriched.director = omdb_movie.director
            enriched.actors = omdb_movie.actors
            enriched.awards = omdb_movie.awards
            enriched.box_office = omdb_movie.box_office

            # Extract external ratings
            for rating in omdb_movie.ratings:
                if "Rotten Tomatoes" in rating.source:
                    enriched.rotten_tomatoes = rating.value
                elif "Metacritic" in rating.source:
                    enriched.metacritic = rating.value

        return enriched

    def get_series(self, title: str) -> EnrichedSeriesInfo | None:
        """
        Get enriched series information.

        Args:
            title: Series name

        Returns:
            EnrichedSeriesInfo with data from both sources
        """
        # Get TMDB data (primary)
        tmdb_series = self.tmdb.search_series(title)
        if not tmdb_series:
            logger.warning(f"Series not found on TMDB: {title}")
            return None

        # Try to get OMDb data (supplement)
        omdb_series = None
        try:
            omdb_series = self.omdb.search_series(title)
        except Exception as e:
            logger.debug(f"OMDb lookup failed: {e}")

        return self._enrich_series(tmdb_series, omdb_series)

    def get_movie(self, title: str, year: int | None = None) -> EnrichedMovieInfo | None:
        """
        Get enriched movie information.

        Args:
            title: Movie title
            year: Optional year

        Returns:
            EnrichedMovieInfo with data from both sources
        """
        # Get TMDB data (primary)
        tmdb_movie = self.tmdb.search_movie_single(title, year)
        if not tmdb_movie:
            logger.warning(f"Movie not found on TMDB: {title}")
            return None

        # Try to get OMDb data (supplement)
        omdb_movie = None
        try:
            omdb_movie = self.omdb.search_movie(title, year)
        except Exception as e:
            logger.debug(f"OMDb lookup failed: {e}")

        return self._enrich_movie(tmdb_movie, omdb_movie)

    def get_series_with_episodes(
        self,
        title: str,
        season: int
    ) -> tuple[EnrichedSeriesInfo | None, dict[int, TMDBEpisodeInfo]]:
        """
        Get series info and episodes.

        Args:
            title: Series name
            season: Season number

        Returns:
            Tuple of (enriched_series_info, {episode_num: episode_info})
        """
        # Get TMDB data (has episode titles)
        tmdb_series, episodes = self.tmdb.get_series_with_episodes(title, season)
        if not tmdb_series:
            return None, {}

        # Enrich with OMDb
        omdb_series = None
        try:
            omdb_series = self.omdb.search_series(title)
        except Exception as e:
            logger.debug(f"OMDb lookup failed: {e}")

        enriched = self._enrich_series(tmdb_series, omdb_series)

        return enriched, episodes

    def test_connection(self) -> dict[str, bool]:
        """Test both API connections."""
        return {
            "tmdb": self.tmdb.test_connection(),
            "omdb": self.omdb.test_connection()
        }


# Singleton
_unified_client: UnifiedMetadataClient | None = None


def get_unified_client(**kwargs) -> UnifiedMetadataClient:
    """Get or create unified client singleton."""
    global _unified_client
    if _unified_client is None:
        _unified_client = UnifiedMetadataClient(**kwargs)
    return _unified_client


if __name__ == "__main__":

    # Test with environment variables
    client = UnifiedMetadataClient.from_env()

    # Test connections
    print("Testing API connections...")
    status = client.test_connection()
    print(f"   TMDB: {'✅' if status['tmdb'] else '❌'}")
    print(f"   OMDb: {'✅' if status['omdb'] else '❌'}")
    print()

    # Test series
    print("Testing series lookup...")
    series, episodes = client.get_series_with_episodes("Stranger Things", 5)
    if series:
        print(f"✅ {series.title} ({series.year_range})")
        print(f"   TMDB ID: {series.tmdb_id}")
        print(f"   IMDb: {series.imdb_rating}/10 ({series.imdb_votes} votes)")
        if series.rotten_tomatoes:
            print(f"   Rotten Tomatoes: {series.rotten_tomatoes}")
        if series.metacritic:
            print(f"   Metacritic: {series.metacritic}")
        print(f"   Rated: {series.rated}")
        print(f"   Seasons: {series.total_seasons}")
        print(f"\n   Season 5 Episodes ({len(episodes)}):")
        for ep_num in sorted(episodes.keys())[:5]:
            print(f"      E{ep_num:02d}: {episodes[ep_num].title}")
    print()

    # Test movie
    print("Testing movie lookup...")
    movie = client.get_movie("Inception", 2010)
    if movie:
        print(f"✅ {movie.title} ({movie.year})")
        print(f"   TMDB ID: {movie.tmdb_id}")
        print(f"   IMDb: {movie.imdb_rating}/10 ({movie.imdb_votes} votes)")
        if movie.rotten_tomatoes:
            print(f"   Rotten Tomatoes: {movie.rotten_tomatoes}")
        if movie.metacritic:
            print(f"   Metacritic: {movie.metacritic}")
        print(f"   Rated: {movie.rated}")
        print(f"   Box Office: {movie.box_office}")
