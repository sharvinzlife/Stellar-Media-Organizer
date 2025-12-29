#!/usr/bin/env python3
"""
Plex Media Server API Client
Handles library scanning, metadata matching, and media management
"""
import re
import time
import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)


@dataclass
class PlexLibrary:
    """Represents a Plex library section"""
    key: str
    title: str
    type: str  # 'movie', 'show', 'artist'
    agent: str
    scanner: str
    language: str
    locations: List[str]
    updated_at: Optional[int] = None
    scanned_at: Optional[int] = None


@dataclass
class PlexMediaItem:
    """Represents a media item in Plex"""
    rating_key: str
    title: str
    type: str
    year: Optional[int] = None
    summary: Optional[str] = None
    guid: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    added_at: Optional[int] = None
    duration: Optional[int] = None
    library_section_id: Optional[int] = None
    library_section_title: Optional[str] = None


@dataclass 
class PlexSession:
    """Represents an active Plex session"""
    session_key: str
    title: str
    type: str
    user: str
    player: str
    platform: str
    state: str  # 'playing', 'paused', 'buffering'
    progress: int  # percentage
    duration: int
    grandparent_title: Optional[str] = None  # For TV shows
    parent_title: Optional[str] = None  # Season for TV shows


class PlexClient:
    """Plex Media Server API Client"""
    
    def __init__(self, server_url: str, token: str, timeout: int = 30):
        """
        Initialize Plex client.
        
        Args:
            server_url: Plex server URL (e.g., http://192.168.1.100:32400)
            token: Plex authentication token
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'X-Plex-Token': token,
            'Accept': 'application/json',
            'X-Plex-Client-Identifier': 'stellar-media-organizer',
            'X-Plex-Product': 'Stellar Media Organizer',
            'X-Plex-Version': '1.0.0',
        })
    
    def _request(self, method: str, endpoint: str, params: Dict = None, **kwargs) -> Dict:
        """Make an API request to Plex server."""
        url = f"{self.server_url}{endpoint}"
        try:
            response = self.session.request(
                method, url, params=params, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            
            # Plex returns JSON when Accept header is set
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Plex API request failed: {e}")
            raise
    
    def get_server_identity(self) -> Dict[str, Any]:
        """Get Plex server identity and status."""
        try:
            data = self._request('GET', '/')
            container = data.get('MediaContainer', {})
            return {
                'friendly_name': container.get('friendlyName'),
                'machine_identifier': container.get('machineIdentifier'),
                'version': container.get('version'),
                'platform': container.get('platform'),
                'platform_version': container.get('platformVersion'),
                'my_plex': container.get('myPlex'),
                'my_plex_subscription': container.get('myPlexSubscription'),
                'transcode_active_sessions': container.get('transcoderActiveVideoSessions', 0),
            }
        except Exception as e:
            logger.error(f"Failed to get server identity: {e}")
            return {}
    
    def get_libraries(self) -> List[PlexLibrary]:
        """Get all library sections."""
        try:
            data = self._request('GET', '/library/sections')
            libraries = []
            
            for section in data.get('MediaContainer', {}).get('Directory', []):
                locations = [loc.get('path') for loc in section.get('Location', [])]
                libraries.append(PlexLibrary(
                    key=section.get('key'),
                    title=section.get('title'),
                    type=section.get('type'),
                    agent=section.get('agent'),
                    scanner=section.get('scanner'),
                    language=section.get('language'),
                    locations=locations,
                    updated_at=section.get('updatedAt'),
                    scanned_at=section.get('scannedAt'),
                ))
            
            return libraries
        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []
    
    def get_library_by_path(self, path: str) -> Optional[PlexLibrary]:
        """Find library that contains the given path."""
        libraries = self.get_libraries()
        for lib in libraries:
            for location in lib.locations:
                if path.startswith(location) or location in path:
                    return lib
        return None
    
    def get_library_by_name(self, name: str) -> Optional[PlexLibrary]:
        """Find library by name (case-insensitive)."""
        libraries = self.get_libraries()
        name_lower = name.lower()
        for lib in libraries:
            if lib.title.lower() == name_lower:
                return lib
        return None

    def scan_library(self, library_key: str, path: str = None) -> bool:
        """
        Trigger a library scan.
        
        Args:
            library_key: Library section key
            path: Optional specific path to scan (for partial scans)
        
        Returns:
            True if scan was triggered successfully
        """
        try:
            endpoint = f'/library/sections/{library_key}/refresh'
            params = {}
            if path:
                params['path'] = path
            
            self._request('GET', endpoint, params=params)
            logger.info(f"Triggered library scan for section {library_key}" + 
                       (f" path: {path}" if path else ""))
            return True
        except Exception as e:
            logger.error(f"Failed to trigger library scan: {e}")
            return False
    
    def scan_library_by_name(self, library_name: str, path: str = None) -> bool:
        """Trigger a library scan by library name."""
        library = self.get_library_by_name(library_name)
        if library:
            return self.scan_library(library.key, path)
        logger.warning(f"Library not found: {library_name}")
        return False
    
    def search(self, query: str, limit: int = 10) -> List[PlexMediaItem]:
        """Search for media across all libraries."""
        try:
            data = self._request('GET', '/search', params={'query': query})
            items = []
            
            for item in data.get('MediaContainer', {}).get('Metadata', [])[:limit]:
                items.append(self._parse_media_item(item))
            
            return items
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_recently_added(self, library_key: str = None, limit: int = 20) -> List[PlexMediaItem]:
        """Get recently added items."""
        try:
            if library_key:
                endpoint = f'/library/sections/{library_key}/recentlyAdded'
            else:
                endpoint = '/library/recentlyAdded'
            
            data = self._request('GET', endpoint, params={
                'X-Plex-Container-Start': 0,
                'X-Plex-Container-Size': limit
            })
            
            items = []
            for item in data.get('MediaContainer', {}).get('Metadata', []):
                items.append(self._parse_media_item(item))
            
            return items
        except Exception as e:
            logger.error(f"Failed to get recently added: {e}")
            return []
    
    def get_item_by_rating_key(self, rating_key: str) -> Optional[PlexMediaItem]:
        """Get a specific media item by rating key."""
        try:
            data = self._request('GET', f'/library/metadata/{rating_key}')
            items = data.get('MediaContainer', {}).get('Metadata', [])
            if items:
                return self._parse_media_item(items[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get item {rating_key}: {e}")
            return None
    
    def get_active_sessions(self) -> List[PlexSession]:
        """Get currently active streaming sessions."""
        try:
            data = self._request('GET', '/status/sessions')
            sessions = []
            
            for item in data.get('MediaContainer', {}).get('Metadata', []):
                user = item.get('User', {})
                player = item.get('Player', {})
                
                sessions.append(PlexSession(
                    session_key=item.get('sessionKey'),
                    title=item.get('title'),
                    type=item.get('type'),
                    user=user.get('title', 'Unknown'),
                    player=player.get('title', 'Unknown'),
                    platform=player.get('platform', 'Unknown'),
                    state=player.get('state', 'unknown'),
                    progress=int(item.get('viewOffset', 0) / max(item.get('duration', 1), 1) * 100),
                    duration=item.get('duration', 0),
                    grandparent_title=item.get('grandparentTitle'),
                    parent_title=item.get('parentTitle'),
                ))
            
            return sessions
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def _parse_media_item(self, item: Dict) -> PlexMediaItem:
        """Parse a media item from API response."""
        # Extract IMDB/TMDB IDs from GUID
        guid = item.get('guid', '')
        imdb_id = None
        tmdb_id = None
        
        # Check Guid array for external IDs
        for g in item.get('Guid', []):
            gid = g.get('id', '')
            if 'imdb://' in gid:
                imdb_id = gid.replace('imdb://', '')
            elif 'tmdb://' in gid:
                tmdb_id = gid.replace('tmdb://', '')
        
        return PlexMediaItem(
            rating_key=item.get('ratingKey'),
            title=item.get('title'),
            type=item.get('type'),
            year=item.get('year'),
            summary=item.get('summary'),
            guid=guid,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            added_at=item.get('addedAt'),
            duration=item.get('duration'),
            library_section_id=item.get('librarySectionID'),
            library_section_title=item.get('librarySectionTitle'),
        )
    
    # ========== Metadata Matching ==========
    
    def get_matches(self, rating_key: str, title: str = None, year: str = None) -> List[Dict]:
        """
        Get potential metadata matches for an item.
        
        Args:
            rating_key: The item's rating key
            title: Optional title to search for
            year: Optional year to filter by
        
        Returns:
            List of potential matches with their GUIDs
        """
        try:
            endpoint = f'/library/metadata/{rating_key}/matches'
            params = {'manual': '1'}
            if title:
                params['title'] = title
            if year:
                params['year'] = year
            
            # Plex returns XML for matches endpoint
            url = f"{self.server_url}{endpoint}?{urlencode(params)}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse XML response for matches
            matches = []
            content = response.text
            
            # Extract SearchResult elements
            import re
            pattern = r'<SearchResult[^>]*guid="([^"]+)"[^>]*name="([^"]+)"[^>]*year="([^"]*)"[^>]*score="([^"]*)"'
            for match in re.finditer(pattern, content):
                matches.append({
                    'guid': match.group(1),
                    'name': match.group(2),
                    'year': match.group(3),
                    'score': match.group(4),
                })
            
            return matches
        except Exception as e:
            logger.error(f"Failed to get matches: {e}")
            return []
    
    def match_item(self, rating_key: str, guid: str, name: str = None, year: str = None) -> bool:
        """
        Match an item with a specific GUID (IMDB/TMDB).
        
        Args:
            rating_key: The item's rating key
            guid: The GUID to match with (e.g., 'plex://movie/...', 'imdb://tt1234567')
            name: Optional name for the match
            year: Optional year for the match
        
        Returns:
            True if match was successful
        """
        try:
            endpoint = f'/library/metadata/{rating_key}/match'
            params = {'guid': guid}
            if name:
                params['name'] = name
            if year:
                params['year'] = year
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.put(url, timeout=self.timeout)
            
            logger.info(f"Matched item {rating_key} with GUID {guid}")
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to match item: {e}")
            return False
    
    def match_with_imdb(self, rating_key: str, imdb_id: str, title: str = None, year: str = None) -> bool:
        """
        Match an item with an IMDB ID.
        
        This searches for the Plex GUID using the IMDB ID, then matches.
        """
        try:
            # First, search for matches using IMDB ID
            matches = self.get_matches(rating_key, title=imdb_id)
            
            plex_guid = None
            for match in matches:
                if match.get('guid', '').startswith('plex://'):
                    plex_guid = match['guid']
                    break
            
            # If no Plex GUID found, try title search
            if not plex_guid and title:
                matches = self.get_matches(rating_key, title=title, year=year)
                for match in matches:
                    if match.get('guid', '').startswith('plex://'):
                        plex_guid = match['guid']
                        break
            
            # Fallback to imdb:// format
            if not plex_guid:
                plex_guid = f"imdb://{imdb_id}"
            
            # Match with the GUID
            success = self.match_item(rating_key, plex_guid, name=title, year=year)
            
            if success:
                # Refresh metadata after matching
                time.sleep(1)
                self.refresh_item(rating_key)
            
            return success
        except Exception as e:
            logger.error(f"Failed to match with IMDB: {e}")
            return False
    
    def refresh_item(self, rating_key: str, force: bool = True) -> bool:
        """Refresh metadata for a specific item."""
        try:
            endpoint = f'/library/metadata/{rating_key}/refresh'
            params = {}
            if force:
                params['force'] = '1'
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.put(url, timeout=self.timeout)
            
            logger.info(f"Refreshed metadata for item {rating_key}")
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to refresh item: {e}")
            return False
    
    def set_rating(self, rating_key: str, rating: float) -> bool:
        """
        Set user rating for an item.
        
        Args:
            rating_key: The item's rating key
            rating: Rating value (1-10 scale)
        
        Returns:
            True if rating was set successfully
        """
        try:
            endpoint = '/:/rate'
            params = {
                'key': rating_key,
                'identifier': 'com.plexapp.plugins.library',
                'rating': str(rating),
            }
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.put(url, timeout=self.timeout)
            
            logger.info(f"Set rating {rating} for item {rating_key}")
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to set rating: {e}")
            return False
    
    def wait_for_item(self, title: str, max_wait: int = 120, check_interval: int = 5) -> Optional[PlexMediaItem]:
        """
        Wait for a newly added item to appear in Plex.
        
        Args:
            title: Title to search for
            max_wait: Maximum wait time in seconds
            check_interval: Time between checks in seconds
        
        Returns:
            The found item or None if not found within max_wait
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            items = self.search(title, limit=5)
            for item in items:
                if title.lower() in item.title.lower():
                    logger.info(f"Found item in Plex: {item.title} (key: {item.rating_key})")
                    return item
            
            logger.debug(f"Item not found yet, waiting... ({int(time.time() - start_time)}s)")
            time.sleep(check_interval)
        
        logger.warning(f"Item not found in Plex after {max_wait}s: {title}")
        return None
    
    # ========== Poster/Art Management ==========
    
    def upload_poster(self, rating_key: str, poster_data: bytes) -> bool:
        """
        Upload a custom poster for an item.
        
        Args:
            rating_key: The item's rating key
            poster_data: Raw image bytes (JPEG/PNG)
        
        Returns:
            True if upload was successful
        """
        try:
            endpoint = f'/library/metadata/{rating_key}/posters'
            url = f"{self.server_url}{endpoint}?X-Plex-Token={self.token}"
            
            response = self.session.post(
                url,
                data=poster_data,
                headers={'Content-Type': 'image/jpeg'},
                timeout=self.timeout
            )
            
            logger.info(f"Uploaded poster for item {rating_key}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to upload poster: {e}")
            return False
    
    def upload_poster_from_url(self, rating_key: str, poster_url: str) -> bool:
        """
        Set poster from a URL.
        
        Args:
            rating_key: The item's rating key
            poster_url: URL of the poster image
        
        Returns:
            True if successful
        """
        try:
            # Plex can accept poster URLs directly
            endpoint = f'/library/metadata/{rating_key}/posters'
            params = {'url': poster_url}
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.post(url, timeout=self.timeout)
            
            logger.info(f"Set poster from URL for item {rating_key}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to set poster from URL: {e}")
            return False
    
    def upload_art(self, rating_key: str, art_data: bytes) -> bool:
        """
        Upload custom background art for an item.
        
        Args:
            rating_key: The item's rating key
            art_data: Raw image bytes (JPEG/PNG)
        
        Returns:
            True if upload was successful
        """
        try:
            endpoint = f'/library/metadata/{rating_key}/arts'
            url = f"{self.server_url}{endpoint}?X-Plex-Token={self.token}"
            
            response = self.session.post(
                url,
                data=art_data,
                headers={'Content-Type': 'image/jpeg'},
                timeout=self.timeout
            )
            
            logger.info(f"Uploaded art for item {rating_key}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to upload art: {e}")
            return False
    
    def upload_art_from_url(self, rating_key: str, art_url: str) -> bool:
        """
        Set background art from a URL.
        
        Args:
            rating_key: The item's rating key
            art_url: URL of the background image
        
        Returns:
            True if successful
        """
        try:
            endpoint = f'/library/metadata/{rating_key}/arts'
            params = {'url': art_url}
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.post(url, timeout=self.timeout)
            
            logger.info(f"Set art from URL for item {rating_key}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to set art from URL: {e}")
            return False
    
    def get_posters(self, rating_key: str) -> List[Dict]:
        """Get available posters for an item."""
        try:
            endpoint = f'/library/metadata/{rating_key}/posters'
            data = self._request('GET', endpoint)
            
            posters = []
            for item in data.get('MediaContainer', {}).get('Metadata', []):
                posters.append({
                    'key': item.get('key'),
                    'ratingKey': item.get('ratingKey'),
                    'selected': item.get('selected', False),
                    'thumb': item.get('thumb'),
                    'provider': item.get('provider'),
                })
            return posters
        except Exception as e:
            logger.error(f"Failed to get posters: {e}")
            return []
    
    def select_poster(self, rating_key: str, poster_key: str) -> bool:
        """Select a specific poster for an item."""
        try:
            endpoint = f'/library/metadata/{rating_key}/poster'
            params = {'url': poster_key}
            
            url = f"{self.server_url}{endpoint}?{urlencode(params)}&X-Plex-Token={self.token}"
            response = self.session.put(url, timeout=self.timeout)
            
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to select poster: {e}")
            return False
    
    def is_library_scanning(self, library_key: str) -> bool:
        """Check if a library is currently scanning."""
        try:
            libraries = self.get_libraries()
            for lib in libraries:
                if lib.key == library_key:
                    # Check if scanned_at is recent (within last 60 seconds)
                    if lib.scanned_at:
                        return time.time() - lib.scanned_at < 60
            return False
        except Exception as e:
            logger.error(f"Failed to check scan status: {e}")
            return False
