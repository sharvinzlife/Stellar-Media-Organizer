"""
Discogs API Client for Music Metadata Lookup
Provides artist, album, track, and release information from Discogs database.
"""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from discogs_client import Client as DiscogsAPIClient
    DISCOGS_AVAILABLE = True
except ImportError:
    DISCOGS_AVAILABLE = False
    DiscogsAPIClient = None

logger = logging.getLogger(__name__)

# Discogs API Token from environment
DISCOGS_API_TOKEN = os.getenv("DISCOGS_API_TOKEN", "")


@dataclass
class DiscogsTrackInfo:
    """Track information from Discogs"""
    title: str
    artist: str
    album: str
    position: str  # Track position (e.g., "A1", "1", "1-1")
    track_number: int
    duration: str | None = None
    year: int | None = None
    genre: str | None = None
    style: str | None = None
    label: str | None = None
    discogs_release_id: int | None = None
    discogs_master_id: int | None = None


@dataclass
class DiscogsAlbumInfo:
    """Album/Release information from Discogs"""
    title: str
    artist: str
    year: int | None = None
    genres: list[str] = None
    styles: list[str] = None
    labels: list[str] = None
    country: str | None = None
    format: str | None = None  # Vinyl, CD, Digital, etc.
    track_count: int = 0
    discogs_release_id: int | None = None
    discogs_master_id: int | None = None
    cover_url: str | None = None

    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.styles is None:
            self.styles = []
        if self.labels is None:
            self.labels = []


@dataclass
class DiscogsArtistInfo:
    """Artist information from Discogs"""
    name: str
    discogs_id: int
    profile: str | None = None
    urls: list[str] = None
    members: list[str] = None  # For bands

    def __post_init__(self):
        if self.urls is None:
            self.urls = []
        if self.members is None:
            self.members = []


class DiscogsClient:
    """
    Discogs API client for music metadata lookup.
    Uses personal access token for authentication.
    """

    def __init__(self, api_token: str | None = None):
        """
        Initialize Discogs client.

        Args:
            api_token: Discogs API token. Get from https://www.discogs.com/settings/developers
        """
        if not DISCOGS_AVAILABLE:
            raise ImportError("discogs-client not installed. Run: pip install discogs-client")

        self.api_token = api_token or DISCOGS_API_TOKEN
        if not self.api_token:
            raise ValueError("Discogs API token required. Set DISCOGS_API_TOKEN environment variable.")

        self.client = DiscogsAPIClient(
            'StellarMediaOrganizer/1.0',
            user_token=self.api_token
        )
        logger.info("✅ Discogs client initialized")

    @lru_cache(maxsize=100)
    def search_track(self, title: str, artist: str = "") -> DiscogsTrackInfo | None:
        """
        Search for a track on Discogs.

        Args:
            title: Track title
            artist: Artist name (optional but recommended)

        Returns:
            DiscogsTrackInfo if found
        """
        try:
            # Build search query
            query = title
            if artist:
                query = f"{artist} - {title}"

            # Search for releases containing this track
            results = self.client.search(query, type='release')

            if not results or len(results) == 0:
                return None

            # Get first result
            release = results[0]

            # Find the matching track in the tracklist
            track_info = None
            track_num = 1

            for idx, track in enumerate(release.tracklist, 1):
                track_title_lower = track.title.lower()
                if title.lower() in track_title_lower or track_title_lower in title.lower():
                    track_info = track
                    track_num = idx
                    break

            # Get artist name
            artist_name = ""
            if release.artists:
                artist_name = release.artists[0].name

            # Get genre/style
            genre = release.genres[0] if release.genres else None
            style = release.styles[0] if release.styles else None

            # Get label
            label = None
            if release.labels:
                label = release.labels[0].name

            return DiscogsTrackInfo(
                title=track_info.title if track_info else title,
                artist=artist_name or artist,
                album=release.title,
                position=track_info.position if track_info else str(track_num),
                track_number=track_num,
                duration=track_info.duration if track_info else None,
                year=release.year if hasattr(release, 'year') else None,
                genre=genre,
                style=style,
                label=label,
                discogs_release_id=release.id,
                discogs_master_id=release.master.id if hasattr(release, 'master') and release.master else None
            )

        except Exception as e:
            logger.warning(f"Discogs track search error: {e}")
            return None

    @lru_cache(maxsize=100)
    def search_album(self, album: str, artist: str = "") -> DiscogsAlbumInfo | None:
        """
        Search for an album/release on Discogs.

        Args:
            album: Album title
            artist: Artist name (optional but recommended)

        Returns:
            DiscogsAlbumInfo if found
        """
        try:
            # Build search query
            query = album
            if artist:
                query = f"{artist} - {album}"

            results = self.client.search(query, type='release')

            if not results or len(results) == 0:
                # Try master release
                results = self.client.search(query, type='master')
                if not results or len(results) == 0:
                    return None

            release = results[0]

            # Get artist name
            artist_name = ""
            if release.artists:
                artist_name = release.artists[0].name

            # Get labels
            labels = []
            if hasattr(release, 'labels') and release.labels:
                labels = [l.name for l in release.labels]

            # Get cover image
            cover_url = None
            if hasattr(release, 'images') and release.images:
                cover_url = release.images[0].get('uri', None)

            # Get format
            format_str = None
            if hasattr(release, 'formats') and release.formats:
                format_str = release.formats[0].get('name', None)

            return DiscogsAlbumInfo(
                title=release.title,
                artist=artist_name or artist,
                year=release.year if hasattr(release, 'year') else None,
                genres=list(release.genres) if release.genres else [],
                styles=list(release.styles) if release.styles else [],
                labels=labels,
                country=release.country if hasattr(release, 'country') else None,
                format=format_str,
                track_count=len(release.tracklist) if hasattr(release, 'tracklist') else 0,
                discogs_release_id=release.id,
                discogs_master_id=release.master.id if hasattr(release, 'master') and release.master else None,
                cover_url=cover_url
            )

        except Exception as e:
            logger.warning(f"Discogs album search error: {e}")
            return None

    @lru_cache(maxsize=100)
    def search_artist(self, name: str) -> DiscogsArtistInfo | None:
        """
        Search for an artist on Discogs.

        Args:
            name: Artist name

        Returns:
            DiscogsArtistInfo if found
        """
        try:
            results = self.client.search(name, type='artist')

            if not results or len(results) == 0:
                return None

            artist = results[0]

            # Get members (for bands)
            members = []
            if hasattr(artist, 'members') and artist.members:
                members = [m.name for m in artist.members]

            # Get URLs
            urls = []
            if hasattr(artist, 'urls') and artist.urls:
                urls = list(artist.urls)

            return DiscogsArtistInfo(
                name=artist.name,
                discogs_id=artist.id,
                profile=artist.profile if hasattr(artist, 'profile') else None,
                urls=urls,
                members=members
            )

        except Exception as e:
            logger.warning(f"Discogs artist search error: {e}")
            return None

    def get_release_tracklist(self, release_id: int) -> list[DiscogsTrackInfo]:
        """
        Get full tracklist for a release.

        Args:
            release_id: Discogs release ID

        Returns:
            List of DiscogsTrackInfo
        """
        try:
            release = self.client.release(release_id)

            artist_name = ""
            if release.artists:
                artist_name = release.artists[0].name

            genre = release.genres[0] if release.genres else None
            style = release.styles[0] if release.styles else None
            label = release.labels[0].name if release.labels else None

            tracks = []
            for idx, track in enumerate(release.tracklist, 1):
                # Handle track artist (for compilations)
                track_artist = artist_name
                if hasattr(track, 'artists') and track.artists:
                    track_artist = track.artists[0].name

                tracks.append(DiscogsTrackInfo(
                    title=track.title,
                    artist=track_artist,
                    album=release.title,
                    position=track.position,
                    track_number=idx,
                    duration=track.duration if hasattr(track, 'duration') else None,
                    year=release.year if hasattr(release, 'year') else None,
                    genre=genre,
                    style=style,
                    label=label,
                    discogs_release_id=release.id,
                    discogs_master_id=release.master.id if hasattr(release, 'master') and release.master else None
                ))

            return tracks

        except Exception as e:
            logger.error(f"Discogs tracklist error: {e}")
            return []


# Singleton instance
_discogs_client: DiscogsClient | None = None


def get_discogs_client(api_token: str | None = None) -> DiscogsClient | None:
    """Get or create Discogs client singleton."""
    global _discogs_client

    token = api_token or DISCOGS_API_TOKEN
    if not token:
        return None

    if _discogs_client is None:
        try:
            _discogs_client = DiscogsClient(token)
        except Exception as e:
            logger.warning(f"Failed to initialize Discogs client: {e}")
            return None

    return _discogs_client


def lookup_track(title: str, artist: str = "", api_token: str | None = None) -> DiscogsTrackInfo | None:
    """Convenience function to look up a track."""
    client = get_discogs_client(api_token)
    if client:
        return client.search_track(title, artist)
    return None


def lookup_album(album: str, artist: str = "", api_token: str | None = None) -> DiscogsAlbumInfo | None:
    """Convenience function to look up an album."""
    client = get_discogs_client(api_token)
    if client:
        return client.search_album(album, artist)
    return None


if __name__ == "__main__":
    # Test the client
    import sys

    token = sys.argv[1] if len(sys.argv) > 1 else DISCOGS_API_TOKEN

    if not token:
        print("❌ DISCOGS_API_TOKEN not set")
        sys.exit(1)

    client = DiscogsClient(token)

    # Test track search
    print("\n🔍 Searching track: 'Get Lucky' by 'Daft Punk'")
    track = client.search_track("Get Lucky", "Daft Punk")
    if track:
        print(f"   ✅ {track.artist} - {track.title}")
        print(f"   💿 Album: {track.album} ({track.year})")
        print(f"   🎵 Genre: {track.genre}, Style: {track.style}")
    else:
        print("   ❌ Not found")

    # Test album search
    print("\n🔍 Searching album: 'Random Access Memories' by 'Daft Punk'")
    album = client.search_album("Random Access Memories", "Daft Punk")
    if album:
        print(f"   ✅ {album.artist} - {album.title} ({album.year})")
        print(f"   🎵 Genres: {', '.join(album.genres)}")
        print(f"   📀 Format: {album.format}, Tracks: {album.track_count}")
    else:
        print("   ❌ Not found")

    # Test artist search
    print("\n🔍 Searching artist: 'Daft Punk'")
    artist = client.search_artist("Daft Punk")
    if artist:
        print(f"   ✅ {artist.name} (ID: {artist.discogs_id})")
        if artist.members:
            print(f"   👥 Members: {', '.join(artist.members)}")
    else:
        print("   ❌ Not found")
