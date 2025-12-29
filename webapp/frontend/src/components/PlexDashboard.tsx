import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Button from './ui/Button';
import {
  Tv,
  Film,
  Music,
  Users,
  Activity,
  RefreshCw,
  Clock,
  Wifi,
  WifiOff,
  Sparkles,
  Eye,
  BarChart3,
  Library,
  Scan,
  Loader2,
  ChevronDown,
  ChevronUp,
  Globe,
  Server,
  MonitorPlay,
  Star,
  Image,
} from 'lucide-react';
import { toast } from 'sonner';
import PosterUploadModal from './PosterUploadModal';

// Types
interface PlexLibrary {
  key: string;
  title: string;
  type: string;
  agent: string;
  locations: string[];
  updated_at: number;
  scanned_at: number;
}

interface TautulliLibrary {
  section_id: number;
  name: string;
  type: string;
  count: number;
  parent_count: number;
  child_count: number;
  is_active: boolean;
}

interface UserStats {
  user_id: number;
  username: string;
  friendly_name: string;
  total_plays: number;
  total_duration: number;
  total_duration_formatted: string;
  last_seen: number;
  last_played: string;
}

interface RecentItem {
  rating_key: string;
  title: string;
  type: string;
  year: number;
  imdb_id: string;
  tmdb_id: string;
  added_at: number;
  library: string;
}

const PlexDashboard: React.FC = () => {
  // State
  const [plexStatus, setPlexStatus] = useState<any>(null);
  const [tautulliStatus, setTautulliStatus] = useState<any>(null);
  const [libraries, setLibraries] = useState<PlexLibrary[]>([]);
  const [tautulliLibraries, setTautulliLibraries] = useState<TautulliLibrary[]>([]);
  const [userStats, setUserStats] = useState<UserStats[]>([]);
  const [recentItems, setRecentItems] = useState<RecentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scanningLibrary, setScanningLibrary] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState({
    server: true,
    libraries: true,
    activity: true,
    users: false,
    recent: false,
  });
  
  // Poster upload modal state
  const [posterModalOpen, setPosterModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<RecentItem | null>(null);

  // Fetch all data
  const fetchData = useCallback(async (showToast = false) => {
    try {
      setRefreshing(true);
      
      // Fetch Plex status
      const plexRes = await fetch('/api/v1/plex/status');
      const plexData = await plexRes.json();
      setPlexStatus(plexData);
      
      // Fetch Tautulli status
      const tautulliRes = await fetch('/api/v1/tautulli/status');
      const tautulliData = await tautulliRes.json();
      setTautulliStatus(tautulliData);
      
      // Fetch libraries if Plex is connected
      if (plexData.success) {
        const libRes = await fetch('/api/v1/plex/libraries');
        const libData = await libRes.json();
        if (libData.success) {
          setLibraries(libData.libraries);
        }
        
        // Fetch recently added
        const recentRes = await fetch('/api/v1/plex/recently-added?limit=10');
        const recentData = await recentRes.json();
        if (recentData.success) {
          setRecentItems(recentData.items);
        }
      }
      
      // Fetch Tautulli libraries and stats
      if (tautulliData.success) {
        const tLibRes = await fetch('/api/v1/tautulli/libraries');
        const tLibData = await tLibRes.json();
        if (tLibData.success) {
          setTautulliLibraries(tLibData.libraries);
        }
        
        const statsRes = await fetch('/api/v1/tautulli/stats/users?days=30');
        const statsData = await statsRes.json();
        if (statsData.success) {
          setUserStats(statsData.users);
        }
      }
      
      if (showToast) {
        toast.success('📺 Plex data refreshed!');
      }
    } catch (error) {
      console.error('Failed to fetch Plex data:', error);
      if (showToast) {
        toast.error('Failed to refresh Plex data');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => fetchData(false), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Scan library
  const handleScanLibrary = async (libraryKey: string, libraryName: string) => {
    setScanningLibrary(libraryKey);
    try {
      const res = await fetch(`/api/v1/plex/scan/${libraryKey}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        toast.success(`🔍 Scanning ${libraryName}...`);
      } else {
        toast.error(`Failed to scan ${libraryName}`);
      }
    } catch (error) {
      toast.error('Scan failed');
    } finally {
      setTimeout(() => setScanningLibrary(null), 2000);
    }
  };

  // Toggle section
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Format timestamp
  const formatTime = (timestamp: number) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp * 1000).toLocaleString();
  };

  // Get library icon
  const getLibraryIcon = (type: string) => {
    switch (type) {
      case 'movie': return <Film className="w-5 h-5" />;
      case 'show': return <Tv className="w-5 h-5" />;
      case 'artist': return <Music className="w-5 h-5" />;
      default: return <Library className="w-5 h-5" />;
    }
  };

  // Get library gradient
  const getLibraryGradient = (type: string) => {
    switch (type) {
      case 'movie': return 'from-amber-500 to-orange-600';
      case 'show': return 'from-purple-500 to-indigo-600';
      case 'artist': return 'from-pink-500 to-rose-600';
      default: return 'from-cyan-500 to-blue-600';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-yellow-500 animate-spin-slow opacity-20 blur-xl absolute inset-0" />
            <Loader2 className="w-16 h-16 text-amber-500 animate-spin mx-auto relative" />
          </div>
          <p className="mt-4 text-slate-400 animate-pulse">Connecting to Plex...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Plex branding */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-yellow-500/10 border border-amber-500/20 p-6">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAzMHYySDI0di0yaDEyek0zNiAyNnYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
        
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute -inset-2 bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl blur-lg opacity-40 animate-pulse" />
              <div className="relative p-4 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/30">
                <MonitorPlay className="w-8 h-8 text-white" />
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                📺 Plex Command Center
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  LIVE
                </span>
              </h2>
              <p className="text-slate-400 text-sm">Monitor, manage & control your media empire</p>
            </div>
          </div>
          
          <Button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-400"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Server Status Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Plex Server Card */}
        <Card variant="glass" className="overflow-hidden">
          <div className={`h-1 ${plexStatus?.success ? 'bg-gradient-to-r from-green-500 to-emerald-500' : 'bg-gradient-to-r from-red-500 to-rose-500'}`} />
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl ${plexStatus?.success ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                  <Server className={`w-5 h-5 ${plexStatus?.success ? 'text-green-400' : 'text-red-400'}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Plex Media Server</h3>
                  <p className="text-xs text-slate-500">
                    {plexStatus?.server?.name || 'Not connected'}
                  </p>
                </div>
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                plexStatus?.success 
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {plexStatus?.success ? (
                  <>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
                    </span>
                    Connected
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3" />
                    Offline
                  </>
                )}
              </div>
            </div>
            
            {plexStatus?.success && plexStatus?.server && (
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Version</p>
                  <p className="text-sm font-medium text-white">{plexStatus.server.version}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Platform</p>
                  <p className="text-sm font-medium text-white">{plexStatus.server.platform}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Active Streams</p>
                  <p className="text-sm font-medium text-amber-400 flex items-center gap-1">
                    <Activity className="w-4 h-4" />
                    {plexStatus.active_sessions || 0}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Plex Pass</p>
                  <p className="text-sm font-medium flex items-center gap-1">
                    {plexStatus.server.plex_pass ? (
                      <span className="text-amber-400 flex items-center gap-1">
                        <Star className="w-4 h-4 fill-amber-400" /> Active
                      </span>
                    ) : (
                      <span className="text-slate-400">No</span>
                    )}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tautulli Card */}
        <Card variant="glass" className="overflow-hidden">
          <div className={`h-1 ${tautulliStatus?.success ? 'bg-gradient-to-r from-purple-500 to-indigo-500' : 'bg-gradient-to-r from-red-500 to-rose-500'}`} />
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl ${tautulliStatus?.success ? 'bg-purple-500/20' : 'bg-red-500/20'}`}>
                  <BarChart3 className={`w-5 h-5 ${tautulliStatus?.success ? 'text-purple-400' : 'text-red-400'}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Tautulli</h3>
                  <p className="text-xs text-slate-500">Statistics & Monitoring</p>
                </div>
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                tautulliStatus?.success 
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' 
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {tautulliStatus?.success ? (
                  <>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-400" />
                    </span>
                    Connected
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3" />
                    Offline
                  </>
                )}
              </div>
            </div>
            
            {tautulliStatus?.success && tautulliStatus?.activity && (
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Current Streams</p>
                  <p className="text-sm font-medium text-purple-400 flex items-center gap-1">
                    <Eye className="w-4 h-4" />
                    {tautulliStatus.activity.stream_count || 0}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Total Bandwidth</p>
                  <p className="text-sm font-medium text-cyan-400">
                    {((tautulliStatus.activity.total_bandwidth || 0) / 1000).toFixed(1)} Mbps
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">WAN</p>
                  <p className="text-sm font-medium text-amber-400 flex items-center gap-1">
                    <Globe className="w-4 h-4" />
                    {((tautulliStatus.activity.wan_bandwidth || 0) / 1000).toFixed(1)} Mbps
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">LAN</p>
                  <p className="text-sm font-medium text-green-400 flex items-center gap-1">
                    <Wifi className="w-4 h-4" />
                    {((tautulliStatus.activity.lan_bandwidth || 0) / 1000).toFixed(1)} Mbps
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Libraries Section */}
      <Card variant="glass" className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-amber-500 via-orange-500 to-yellow-500" />
        <CardHeader className="pb-2">
          <button 
            onClick={() => toggleSection('libraries')}
            className="w-full flex items-center justify-between"
          >
            <CardTitle className="flex items-center gap-2 text-lg">
              <Library className="w-5 h-5 text-amber-400" />
              📚 Media Libraries
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                {libraries.length}
              </span>
            </CardTitle>
            {expandedSections.libraries ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
          </button>
        </CardHeader>
        {expandedSections.libraries && (
          <CardContent className="pt-2">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {libraries.map((lib) => {
                const tautulliLib = tautulliLibraries.find(t => t.section_id === parseInt(lib.key));
                return (
                  <div 
                    key={lib.key}
                    className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${getLibraryGradient(lib.type)} p-[1px]`}
                  >
                    <div className="bg-slate-900/95 rounded-xl p-4 h-full">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={`p-2 rounded-lg bg-gradient-to-br ${getLibraryGradient(lib.type)}`}>
                            {getLibraryIcon(lib.type)}
                          </div>
                          <div>
                            <h4 className="font-semibold text-white">{lib.title}</h4>
                            <p className="text-xs text-slate-500 capitalize">{lib.type}</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleScanLibrary(lib.key, lib.title)}
                          disabled={scanningLibrary === lib.key}
                          className="bg-white/10 hover:bg-white/20 border-0 h-8 w-8 p-0"
                        >
                          {scanningLibrary === lib.key ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Scan className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                      
                      {tautulliLib && (
                        <div className="grid grid-cols-3 gap-2 text-center">
                          <div className="p-2 rounded-lg bg-white/5">
                            <p className="text-lg font-bold text-white">{tautulliLib.count}</p>
                            <p className="text-[10px] text-slate-500">Items</p>
                          </div>
                          {tautulliLib.parent_count > 0 && (
                            <div className="p-2 rounded-lg bg-white/5">
                              <p className="text-lg font-bold text-purple-400">{tautulliLib.parent_count}</p>
                              <p className="text-[10px] text-slate-500">Shows</p>
                            </div>
                          )}
                          {tautulliLib.child_count > 0 && (
                            <div className="p-2 rounded-lg bg-white/5">
                              <p className="text-lg font-bold text-cyan-400">{tautulliLib.child_count}</p>
                              <p className="text-[10px] text-slate-500">Episodes</p>
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(lib.scanned_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        )}
      </Card>

      {/* User Statistics Section */}
      <Card variant="glass" className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-purple-500 via-pink-500 to-rose-500" />
        <CardHeader className="pb-2">
          <button 
            onClick={() => toggleSection('users')}
            className="w-full flex items-center justify-between"
          >
            <CardTitle className="flex items-center gap-2 text-lg">
              <Users className="w-5 h-5 text-purple-400" />
              👥 User Statistics
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
                Last 30 days
              </span>
            </CardTitle>
            {expandedSections.users ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
          </button>
        </CardHeader>
        {expandedSections.users && (
          <CardContent className="pt-2">
            {userStats.length > 0 ? (
              <div className="space-y-3">
                {userStats.map((user, idx) => (
                  <div 
                    key={user.user_id}
                    className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                      idx === 0 ? 'bg-gradient-to-br from-amber-400 to-orange-500' :
                      idx === 1 ? 'bg-gradient-to-br from-slate-300 to-slate-400' :
                      idx === 2 ? 'bg-gradient-to-br from-amber-600 to-amber-700' :
                      'bg-gradient-to-br from-purple-500 to-indigo-500'
                    }`}>
                      {idx < 3 ? ['🥇', '🥈', '🥉'][idx] : user.friendly_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-white">{user.friendly_name}</h4>
                      <p className="text-xs text-slate-500">
                        Last: {user.last_played || 'Unknown'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-purple-400">{user.total_plays}</p>
                      <p className="text-xs text-slate-500">plays</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-cyan-400">{user.total_duration_formatted}</p>
                      <p className="text-xs text-slate-500">watch time</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No user statistics available</p>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Recently Added Section */}
      <Card variant="glass" className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />
        <CardHeader className="pb-2">
          <button 
            onClick={() => toggleSection('recent')}
            className="w-full flex items-center justify-between"
          >
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              ✨ Recently Added
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                {recentItems.length} items
              </span>
            </CardTitle>
            {expandedSections.recent ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
          </button>
        </CardHeader>
        {expandedSections.recent && (
          <CardContent className="pt-2">
            {recentItems.length > 0 ? (
              <div className="grid md:grid-cols-2 gap-3">
                {recentItems.map((item) => (
                  <div 
                    key={item.rating_key}
                    className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all hover:scale-[1.02]"
                  >
                    <div className={`p-2.5 rounded-lg ${
                      item.type === 'movie' ? 'bg-amber-500/20' : 
                      item.type === 'episode' ? 'bg-purple-500/20' : 
                      'bg-pink-500/20'
                    }`}>
                      {item.type === 'movie' ? <Film className="w-5 h-5 text-amber-400" /> :
                       item.type === 'episode' ? <Tv className="w-5 h-5 text-purple-400" /> :
                       <Music className="w-5 h-5 text-pink-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-white truncate">{item.title}</h4>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="capitalize">{item.type}</span>
                        {item.year && <span>• {item.year}</span>}
                        <span>• {item.library}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {item.imdb_id && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-400 font-medium">
                          IMDb
                        </span>
                      )}
                      {item.tmdb_id && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-400 font-medium">
                          TMDb
                        </span>
                      )}
                      {/* Show upload button for items without metadata */}
                      {!item.imdb_id && !item.tmdb_id && (
                        <button
                          onClick={() => {
                            setSelectedItem(item);
                            setPosterModalOpen(true);
                          }}
                          className="p-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 transition-colors"
                          title="Upload custom artwork"
                        >
                          <Image className="w-3.5 h-3.5 text-amber-400" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                <Sparkles className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No recently added items</p>
              </div>
            )}
          </CardContent>
        )}
      </Card>
      
      {/* Poster Upload Modal */}
      {selectedItem && (
        <PosterUploadModal
          isOpen={posterModalOpen}
          onClose={() => {
            setPosterModalOpen(false);
            setSelectedItem(null);
          }}
          ratingKey={selectedItem.rating_key}
          title={selectedItem.title}
        />
      )}
    </div>
  );
};

export default PlexDashboard;
