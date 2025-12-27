import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Button from './ui/Button';
import {
  HardDrive,
  Server,
  Wifi,
  WifiOff,
  FolderOpen,
  Film,
  Tv,
  Music,
  Copy,
  MoveRight,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronDown,
  Database
} from 'lucide-react';
import api from '../lib/api';

interface NASLocation {
  name: string;
  host: string;
  type: string;
  mounted: boolean;
  mount_point: string;
  categories: string[];
}

interface NASStatus {
  name: string;
  host: string;
  type: string;
  mounted: boolean;
  mount_point: string;
  disk?: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    used_percent: number;
  };
  categories: Record<string, { path: string; exists: boolean }>;
}

interface NASPanelProps {
  mediaType?: 'video' | 'audio';
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  'movies': <Film className="h-4 w-4" />,
  'malayalam movies': <Film className="h-4 w-4 text-orange-400" />,
  'bollywood movies': <Film className="h-4 w-4 text-pink-400" />,
  'tv-shows': <Tv className="h-4 w-4" />,
  'tv': <Tv className="h-4 w-4" />,
  'malayalam-tv-shows': <Tv className="h-4 w-4 text-orange-400" />,
  'malayalam tv shows': <Tv className="h-4 w-4 text-orange-400" />,
  'music': <Music className="h-4 w-4 text-green-400" />,
};

const CATEGORY_LABELS: Record<string, string> = {
  'movies': 'Movies',
  'malayalam movies': 'Malayalam Movies',
  'bollywood movies': 'Bollywood Movies',
  'tv-shows': 'TV Shows',
  'tv': 'TV Shows',
  'malayalam-tv-shows': 'Malayalam TV Shows',
  'malayalam tv shows': 'Malayalam TV Shows',
  'music': 'Music',
};

const NASPanel: React.FC<NASPanelProps> = ({ mediaType = 'video' }) => {
  const [nasLocations, setNasLocations] = useState<NASLocation[]>([]);
  const [nasStatuses, setNasStatuses] = useState<Record<string, NASStatus>>({});
  const [loading, setLoading] = useState(false);
  const [testingNAS, setTestingNAS] = useState<string | null>(null);
  const [expandedNAS, setExpandedNAS] = useState<string | null>(null);

  useEffect(() => {
    fetchNASList();
  }, []);

  const fetchNASList = async () => {
    setLoading(true);
    try {
      const response = await api.get('/nas/list');
      const locations = response.data.nas_locations || [];
      setNasLocations(locations);
      
      // Fetch status for ALL NAS locations in parallel
      if (locations.length > 0) {
        await Promise.all(locations.map((nas: NASLocation) => fetchNASStatus(nas.name)));
      }
    } catch (error) {
      console.error('Failed to fetch NAS list:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchNASStatus = async (nasName: string) => {
    try {
      const response = await api.get(`/nas/${nasName}/status`);
      setNasStatuses(prev => ({
        ...prev,
        [nasName]: response.data.nas
      }));
    } catch (error) {
      console.error(`Failed to fetch NAS status for ${nasName}:`, error);
    }
  };

  const testConnection = async (nasName: string) => {
    setTestingNAS(nasName);
    try {
      const response = await api.post('/nas/test', { nas_name: nasName });
      if (response.data.success) {
        toast.success(response.data.message);
      } else {
        toast.error(response.data.message);
      }
      await fetchNASStatus(nasName);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Connection test failed');
    } finally {
      setTestingNAS(null);
    }
  };

  // Filter categories based on media type
  const getFilteredCategories = (categories: string[]) => {
    if (mediaType === 'audio') {
      return categories.filter(cat => cat === 'music');
    }
    return categories.filter(cat => cat !== 'music');
  };

  return (
    <Card variant="glass" className="border-cyan-500/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500">
            <Server className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-white">NAS Destinations</span>
            <p className="text-xs text-slate-400 font-normal mt-0.5">
              {mediaType === 'audio' ? 'Music storage on Lharmony' : 'Video storage locations'}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchNASList}
            className="ml-auto"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* NAS Cards */}
        {nasLocations.map((nas) => {
          const filteredCategories = getFilteredCategories(nas.categories);
          
          // Skip NAS if no categories for this media type
          if (filteredCategories.length === 0) return null;
          
          const isExpanded = expandedNAS === nas.name;
          const status = nasStatuses[nas.name];
          const isTesting = testingNAS === nas.name;
          
          return (
            <div
              key={nas.name}
              className={`
                rounded-xl border transition-all duration-300
                ${nas.mounted 
                  ? 'border-emerald-500/30 bg-emerald-500/5' 
                  : 'border-red-500/30 bg-red-500/5'
                }
              `}
            >
              {/* NAS Header */}
              <div
                className="p-4 cursor-pointer"
                onClick={() => setExpandedNAS(isExpanded ? null : nas.name)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`
                      p-2 rounded-lg
                      ${nas.mounted ? 'bg-emerald-500/20' : 'bg-red-500/20'}
                    `}>
                      <HardDrive className={`h-5 w-5 ${nas.mounted ? 'text-emerald-400' : 'text-red-400'}`} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-white flex items-center gap-2">
                        {nas.name}
                        {nas.mounted ? (
                          <Wifi className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <WifiOff className="h-3 w-3 text-red-400" />
                        )}
                      </h4>
                      <p className="text-xs text-slate-400">
                        {nas.host} • {nas.type}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        testConnection(nas.name);
                      }}
                      disabled={isTesting}
                    >
                      {isTesting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </Button>
                    <ChevronDown className={`
                      h-4 w-4 text-slate-400 transition-transform
                      ${isExpanded ? 'rotate-180' : ''}
                    `} />
                  </div>
                </div>
                
                {/* Disk Usage Bar */}
                {nas.mounted && status?.disk && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>{status.disk.used_gb} GB used</span>
                      <span>{status.disk.free_gb} GB free</span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          status.disk.used_percent > 90 
                            ? 'bg-red-500' 
                            : status.disk.used_percent > 70 
                              ? 'bg-yellow-500' 
                              : 'bg-emerald-500'
                        }`}
                        style={{ width: `${status.disk.used_percent}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
              
              {/* Expanded Categories */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-white/5 pt-3">
                  <p className="text-xs text-slate-500 mb-2">Available Categories:</p>
                  <div className="grid grid-cols-2 gap-2">
                    {filteredCategories.map((category) => (
                      <div
                        key={category}
                        className={`
                          flex items-center gap-2 p-2 rounded-lg text-sm
                          ${status?.categories?.[category]?.exists
                            ? 'bg-white/5 text-slate-300'
                            : 'bg-red-500/10 text-red-400'
                          }
                        `}
                      >
                        {CATEGORY_ICONS[category] || <FolderOpen className="h-4 w-4" />}
                        <span>{CATEGORY_LABELS[category] || category}</span>
                        {status?.categories?.[category]?.exists ? (
                          <CheckCircle className="h-3 w-3 text-emerald-400 ml-auto" />
                        ) : (
                          <XCircle className="h-3 w-3 text-red-400 ml-auto" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
        
        {/* Empty State */}
        {nasLocations.length === 0 && !loading && (
          <div className="text-center py-8 text-slate-400">
            <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No NAS locations configured</p>
            <p className="text-xs mt-1">Add NAS credentials to config.env</p>
          </div>
        )}
        
        {/* Loading State */}
        {loading && (
          <div className="text-center py-8">
            <Loader2 className="h-8 w-8 mx-auto animate-spin text-cyan-400" />
            <p className="text-slate-400 mt-2">Loading NAS locations...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default NASPanel;
