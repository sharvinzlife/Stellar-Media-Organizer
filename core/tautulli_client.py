#!/usr/bin/env python3
"""
Tautulli API Client
Handles Plex statistics, monitoring, and watch history
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class TautulliLibrary:
    """Represents a Plex library in Tautulli"""
    section_id: int
    section_name: str
    section_type: str
    count: int
    parent_count: int = 0
    child_count: int = 0
    is_active: bool = True


@dataclass
class TautulliUserStats:
    """Represents user statistics"""
    user_id: int
    username: str
    friendly_name: str
    total_plays: int
    total_duration: int  # seconds
    last_seen: int | None = None
    last_played: str | None = None


@dataclass
class TautulliHistoryItem:
    """Represents a watch history entry"""
    date: int  # Unix timestamp
    duration: int  # seconds watched
    friendly_name: str
    full_title: str
    media_type: str
    platform: str
    player: str
    title: str
    user: str
    year: int | None = None
    watched_status: float = 0.0
    percent_complete: int = 0
    grandparent_title: str | None = None  # Series name for TV
    parent_media_index: int | None = None  # Season number
    media_index: int | None = None  # Episode number


@dataclass
class TautulliServerStatus:
    """Represents Plex server status from Tautulli"""
    connected: bool
    sessions: int
    remote_access: str  # 'up' or 'down'
    version: str
    platform: str


class TautulliClient:
    """Tautulli API Client for Plex monitoring and statistics"""

    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize Tautulli client.

        Args:
            base_url: Tautulli server URL (e.g., http://192.168.1.100:8181)
            api_key: Tautulli API key
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, cmd: str, params: dict | None = None) -> dict:
        """Make an API request to Tautulli."""
        url = f"{self.base_url}/api/v2"

        request_params = {
            'apikey': self.api_key,
            'cmd': cmd,
        }
        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get('response', {}).get('result') != 'success':
                error_msg = data.get('response', {}).get('message', 'Unknown error')
                raise Exception(f"Tautulli API error: {error_msg}")

            return data.get('response', {}).get('data', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Tautulli API request failed: {e}")
            raise

    def get_server_status(self) -> TautulliServerStatus | None:
        """Get Plex server status including remote access."""
        try:
            data = self._request('get_server_status')
            return TautulliServerStatus(
                connected=data.get('connected', False),
                sessions=data.get('sessions', 0),
                remote_access=data.get('remote_access', 'unknown'),
                version=data.get('version', ''),
                platform=data.get('platform', ''),
            )
        except Exception as e:
            logger.error(f"Failed to get server status: {e}")
            return None

    def get_libraries(self) -> list[TautulliLibrary]:
        """Get all Plex libraries."""
        try:
            data = self._request('get_libraries')
            libraries = []

            for lib in data:
                libraries.append(TautulliLibrary(
                    section_id=int(lib.get('section_id', 0)),
                    section_name=lib.get('section_name', ''),
                    section_type=lib.get('section_type', ''),
                    count=int(lib.get('count', 0)),
                    parent_count=int(lib.get('parent_count', 0)),
                    child_count=int(lib.get('child_count', 0)),
                    is_active=lib.get('is_active', 1) == 1,
                ))

            return libraries
        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []

    def get_library_by_name(self, name: str) -> TautulliLibrary | None:
        """Find library by name (case-insensitive)."""
        libraries = self.get_libraries()
        name_lower = name.lower()
        for lib in libraries:
            if lib.section_name.lower() == name_lower:
                return lib
        return None

    def get_activity(self) -> dict[str, Any]:
        """Get current server activity (active streams)."""
        try:
            data = self._request('get_activity')
            return {
                'stream_count': data.get('stream_count', 0),
                'sessions': data.get('sessions', []),
                'total_bandwidth': data.get('total_bandwidth', 0),
                'wan_bandwidth': data.get('wan_bandwidth', 0),
                'lan_bandwidth': data.get('lan_bandwidth', 0),
            }
        except Exception as e:
            logger.error(f"Failed to get activity: {e}")
            return {'stream_count': 0, 'sessions': []}

    def get_home_stats(self, stat_id: str = 'top_users', time_range: int = 30,
                       stats_count: int = 10) -> list[dict]:
        """
        Get home statistics.

        Args:
            stat_id: Type of stats ('top_users', 'popular_movies', 'popular_tv', etc.)
            time_range: Number of days to include
            stats_count: Number of results to return
        """
        try:
            data = self._request('get_home_stats', {
                'stat_id': stat_id,
                'time_range': time_range,
                'stats_count': stats_count,
            })
            return data.get('rows', []) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"Failed to get home stats: {e}")
            return []

    def get_user_stats(self, days: int = 30) -> list[TautulliUserStats]:
        """Get user statistics for the specified time period."""
        try:
            data = self.get_home_stats('top_users', time_range=days, stats_count=25)

            users = []
            for row in data:
                users.append(TautulliUserStats(
                    user_id=row.get('user_id', 0),
                    username=row.get('user', ''),
                    friendly_name=row.get('friendly_name', ''),
                    total_plays=row.get('total_plays', 0),
                    total_duration=row.get('total_duration', 0),
                    last_seen=row.get('last_play'),
                    last_played=row.get('title'),
                ))

            return users
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return []

    def get_history(self, user: str | None = None, section_id: int | None = None,
                    length: int = 25, days: int | None = None) -> list[TautulliHistoryItem]:
        """
        Get watch history.

        Args:
            user: Filter by username
            section_id: Filter by library section ID
            length: Number of results
            days: Filter to last N days
        """
        try:
            params = {
                'length': length,
                'order_column': 'date',
                'order_dir': 'desc',
            }
            if user:
                params['user'] = user
            if section_id:
                params['section_id'] = section_id

            data = self._request('get_history', params)
            history_data = data.get('data', []) if isinstance(data, dict) else data

            items = []
            cutoff_time = None
            if days:
                cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()

            for item in history_data:
                date = item.get('date', 0)
                if cutoff_time and date < cutoff_time:
                    continue

                items.append(TautulliHistoryItem(
                    date=date,
                    duration=item.get('duration', 0),
                    friendly_name=item.get('friendly_name', ''),
                    full_title=item.get('full_title', ''),
                    media_type=item.get('media_type', ''),
                    platform=item.get('platform', ''),
                    player=item.get('player', ''),
                    title=item.get('title', ''),
                    user=item.get('user', ''),
                    year=item.get('year'),
                    watched_status=item.get('watched_status', 0),
                    percent_complete=item.get('percent_complete', 0),
                    grandparent_title=item.get('grandparent_title'),
                    parent_media_index=item.get('parent_media_index'),
                    media_index=item.get('media_index'),
                ))

            return items
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def get_library_watch_time_stats(self, section_id: int, days: int = 30) -> dict:
        """Get watch time statistics for a library."""
        try:
            data = self._request('get_library_watch_time_stats', {
                'section_id': section_id,
                'query_days': days,
                'grouping': 1,
            })
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to get library watch time stats: {e}")
            return {}

    def get_library_user_stats(self, section_id: int, days: int = 30) -> list[dict]:
        """Get user statistics for a specific library."""
        try:
            data = self._request('get_library_user_stats', {
                'section_id': section_id,
                'query_days': days,
            })
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get library user stats: {e}")
            return []

    def get_popular_movies(self, days: int = 30, count: int = 10) -> list[dict]:
        """Get most popular movies."""
        return self.get_home_stats('popular_movies', time_range=days, stats_count=count)

    def get_popular_tv(self, days: int = 30, count: int = 10) -> list[dict]:
        """Get most popular TV shows."""
        return self.get_home_stats('popular_tv', time_range=days, stats_count=count)

    def get_most_watched(self, days: int = 30, count: int = 10) -> list[dict]:
        """Get most watched content."""
        return self.get_home_stats('most_watched', time_range=days, stats_count=count)

    def notify(self, notifier_id: int, subject: str, body: str) -> bool:
        """
        Send a notification through Tautulli.

        Args:
            notifier_id: The notifier agent ID
            subject: Notification subject
            body: Notification body
        """
        try:
            self._request('notify', {
                'notifier_id': notifier_id,
                'subject': subject,
                'body': body,
            })
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def refresh_libraries_list(self) -> bool:
        """Refresh the libraries list in Tautulli."""
        try:
            self._request('refresh_libraries_list')
            return True
        except Exception as e:
            logger.error(f"Failed to refresh libraries list: {e}")
            return False


# ========== Utility Functions ==========

def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_bytes(bytes_val: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"
