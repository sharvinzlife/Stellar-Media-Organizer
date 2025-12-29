import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import { Cloud, Download, Loader2, Link2, CheckCircle, HardDrive, FolderOpen, Sparkles, Film, Filter, Upload, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';

interface AllDebridStatusResponse {
  configured: boolean;
}

interface AllDebridDownloadResponse {
  success: boolean;
  message?: string;
  detail?: string;
  job_id?: number;
}

interface NASLocation {
  name: string;
  host: string;
  type: string;
  mounted: boolean;
  categories: string[];
}

interface JobProgress {
  phase: string;
  renamed_files: number;
  filtered_files: number;
  nas_destination: string | null;
  detected_category: string | null;
  metadata_found: string;
  plex_scan_status: string | null;
  plex_library_name: string | null;
}

// Extend Window interface for global addLog function
declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

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

const PHASE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  'pending': { label: 'Pending', icon: '⏳', color: 'text-gray-400' },
  'downloading': { label: 'Downloading', icon: '⬇️', color: 'text-blue-400' },
  'filtering': { label: 'Filtering Audio', icon: '🎵', color: 'text-purple-400' },
  'organizing': { label: 'Organizing', icon: '📁', color: 'text-yellow-400' },
  'uploading': { label: 'Uploading to NAS', icon: '📤', color: 'text-emerald-400' },
  'scanning': { label: 'Plex Scanning', icon: '📺', color: 'text-orange-400' },
  'completed': { label: 'Completed', icon: '✅', color: 'text-green-400' },
  'failed': { label: 'Failed', icon: '❌', color: 'text-red-400' },
};

const AllDebridPanel: React.FC = () => {
  const [links, setLinks] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [configured, setConfigured] = useState<boolean>(false);
  const [language, setLanguage] = useState<string>('auto');
  
  // NAS destination
  const [destinationType, setDestinationType] = useState<'local' | 'nas'>('nas');
  const [nasLocations, setNasLocations] = useState<NASLocation[]>([]);
  const [selectedNAS, setSelectedNAS] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [localPath, setLocalPath] = useState<string>('');
  
  // Enhanced progress tracking
  const [detectedCategory, setDetectedCategory] = useState<string | null>(null);
  const [, setCurrentJobId] = useState<number | null>(null);
  const [jobProgress, setJobProgress] = useState<JobProgress | null>(null);
  const [progressPercent, setProgressPercent] = useState<number>(0);

  useEffect(() => {
    checkStatus();
    loadNASLocations();
  }, []);

  const checkStatus = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/alldebrid/status');
      const data: AllDebridStatusResponse = await response.json();
      setConfigured(data.configured);
    } catch (error) {
      console.error('Failed to check AllDebrid status:', error);
    }
  };

  const loadNASLocations = async (): Promise<void> => {
    try {
      const response = await api.get('/nas/list');
      const locations = response.data.nas_locations || [];
      // Filter to only video categories (exclude music)
      const videoNAS = locations.map((nas: NASLocation) => ({
        ...nas,
        categories: nas.categories.filter((cat: string) => cat !== 'music')
      })).filter((nas: NASLocation) => nas.categories.length > 0);
      
      setNasLocations(videoNAS);
      if (videoNAS.length > 0) {
        setSelectedNAS(videoNAS[0].name);
        if (videoNAS[0].categories.length > 0) {
          // Default to malayalam movies if available
          const defaultCat = videoNAS[0].categories.find((c: string) => c.includes('malayalam')) || videoNAS[0].categories[0];
          setSelectedCategory(defaultCat);
        }
      }
    } catch {
      // NAS not configured
    }
  };

  const parseLinks = (text: string): string[] => {
    const pattern = /https:\/\/alldebrid\.com\/f\/[A-Za-z0-9_-]+/g;
    const matches = text.match(pattern) || [];
    return [...new Set(matches)];
  };

  const handleDownload = async (): Promise<void> => {
    const parsedLinks = parseLinks(links);

    if (parsedLinks.length === 0) {
      toast.error('No valid AllDebrid links found');
      return;
    }

    if (destinationType === 'nas' && (!selectedNAS || !selectedCategory)) {
      toast.error('Please select a NAS destination and category');
      return;
    }

    setLoading(true);
    const dest = destinationType === 'nas' ? `${selectedNAS} → ${CATEGORY_LABELS[selectedCategory] || selectedCategory}` : localPath;
    const langLabel = language === 'auto' ? 'Auto-detect' : language;
    window.addLog?.(`🚀 Starting AllDebrid download of ${parsedLinks.length} links...`, 'info');
    window.addLog?.(`   Language: ${langLabel}, Destination: ${dest}`, 'info');

    try {
      const response = await fetch('/api/v1/alldebrid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          links: parsedLinks,
          language: language,
          auto_detect_language: language === 'auto',
          download_only: false,
          output_path: destinationType === 'local' ? localPath : undefined,
          nas_destination: destinationType === 'nas' ? {
            nas_name: selectedNAS,
            category: selectedCategory,
          } : undefined,
        }),
      });

      const data: AllDebridDownloadResponse = await response.json();

      if (data.success) {
        toast.success(data.message || 'Download started');
        window.addLog?.(`✅ ${data.message}`, 'success');
        setLinks('');
        
        // Poll for job status if job_id returned
        if (data.job_id) {
          pollJobStatus(data.job_id);
        }
      } else {
        toast.error(data.detail || 'Download failed');
        window.addLog?.(`❌ ${data.detail}`, 'error');
        setLoading(false);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to start download');
      window.addLog?.(`❌ Error: ${errorMessage}`, 'error');
      setLoading(false);
    }
  };

  const pollJobStatus = async (jobId: number): Promise<void> => {
    let lastLogCount = 0;
    setCurrentJobId(jobId);
    setDetectedCategory(null);
    setJobProgress(null);
    setProgressPercent(0);
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/alldebrid/jobs/${jobId}`);
        const data = await response.json();
        
        // Update progress percent
        if (data.progress) {
          setProgressPercent(data.progress);
        }
        
        // Update enhanced progress tracking
        const progress: JobProgress = {
          phase: data.phase || 'pending',
          renamed_files: data.renamed_files || 0,
          filtered_files: data.filtered_files || 0,
          nas_destination: data.nas_destination,
          detected_category: data.detected_category,
          metadata_found: data.metadata_found || 'unknown',
          plex_scan_status: data.plex_scan_status,
          plex_library_name: data.plex_library_name,
        };
        setJobProgress(progress);
        
        // Update detected category if changed
        if (progress.detected_category && progress.detected_category !== detectedCategory) {
          setDetectedCategory(progress.detected_category);
          // Show notification for auto-detected category
          toast.info(`🔍 Auto-detected: ${CATEGORY_LABELS[progress.detected_category] || progress.detected_category}`);
        }
        
        // Show notification for no metadata found (defaulting to Malayalam)
        if (progress.metadata_found === 'no' && progress.phase === 'organizing') {
          toast.warning('⚠️ No IMDB/TMDB data found - defaulting to Malayalam library');
        }
        
        // Show Plex scan notification
        if (progress.plex_scan_status === 'scanning' && progress.plex_library_name) {
          toast.info(`📺 Scanning Plex library: ${progress.plex_library_name}`);
        }
        
        // Add new logs since last poll
        if (data.logs && data.logs.length > lastLogCount) {
          const newLogs = data.logs.slice(lastLogCount);
          newLogs.forEach((log: { message: string; level: string }) => {
            window.addLog?.(log.message, log.level);
          });
          lastLogCount = data.logs.length;
        }
        
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          toast.success('Download completed!');
          if (progress.plex_library_name) {
            toast.success(`📺 Plex scan triggered for ${progress.plex_library_name}`);
          }
          setLoading(false);
          setCurrentJobId(null);
          // Keep progress visible for a moment
          setTimeout(() => {
            setJobProgress(null);
            setDetectedCategory(null);
          }, 15000);
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          toast.error(data.error || 'Download failed');
          setLoading(false);
          setCurrentJobId(null);
          setJobProgress(null);
          setDetectedCategory(null);
        }
      } catch {
        // Continue polling
      }
    }, 2000);
    
    // Stop polling after 30 minutes max
    setTimeout(() => {
      clearInterval(pollInterval);
      setLoading(false);
      setCurrentJobId(null);
    }, 30 * 60 * 1000);
  };

  const linkCount = parseLinks(links).length;

  if (!configured) {
    return (
      <Card variant="glass" className="border-warning/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-warning/20 border border-warning/20">
              <Cloud className="h-5 w-5 text-warning" />
            </div>
            AllDebrid Downloads
          </CardTitle>
          <CardDescription>
            ⚠️ AllDebrid API key not configured. Set ALLDEBRID_API_KEY environment variable.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card variant="glass">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/20">
            <Cloud className="h-5 w-5 text-blue-500" />
          </div>
          AllDebrid Downloads
        </CardTitle>
        <CardDescription>
          Download, auto-detect language, organize, and push to NAS automatically
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Links Input */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            AllDebrid Links
          </label>
          <textarea
            value={links}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setLinks(e.target.value)}
            placeholder="Paste AllDebrid links here (one per line or all together)..."
            className="w-full h-24 px-4 py-3 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
          />
          {linkCount > 0 && (
            <p className="text-xs text-success flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              Found {linkCount} valid link{linkCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        {/* Audio Language */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-yellow-400" />
            Audio Language
          </label>
          <select
            value={language}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)}
            className="w-full h-11 px-4 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="auto">✨ Auto-detect (Malayalam → English → Hindi)</option>
            <option value="malayalam">🇮🇳 Malayalam</option>
            <option value="tamil">🇮🇳 Tamil</option>
            <option value="telugu">🇮🇳 Telugu</option>
            <option value="hindi">🇮🇳 Hindi</option>
            <option value="english">🇬🇧 English</option>
            <option value="kannada">🇮🇳 Kannada</option>
          </select>
          {language === 'auto' && (
            <p className="text-xs text-yellow-400/70 bg-yellow-500/10 p-2 rounded-lg">
              🔍 Will scan file and pick: Malayalam if available, else English, else Hindi
            </p>
          )}
        </div>

        {/* Destination */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-emerald-400" />
            Destination
          </label>
          
          {/* Toggle */}
          <div className="flex items-center gap-2 p-1 bg-base-content/5 rounded-xl">
            <button
              onClick={() => setDestinationType('local')}
              className={`
                flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-all text-sm
                ${destinationType === 'local' 
                  ? 'bg-primary text-primary-content shadow-lg' 
                  : 'text-base-content/60 hover:text-base-content hover:bg-base-content/10'
                }
              `}
            >
              <FolderOpen className="h-4 w-4" />
              Local
            </button>
            <button
              onClick={() => setDestinationType('nas')}
              disabled={nasLocations.length === 0}
              className={`
                flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-all text-sm
                ${destinationType === 'nas' 
                  ? 'bg-emerald-500 text-white shadow-lg' 
                  : 'text-base-content/60 hover:text-base-content hover:bg-base-content/10'
                }
                ${nasLocations.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <HardDrive className="h-4 w-4" />
              NAS
            </button>
          </div>

          {/* Local Path */}
          {destinationType === 'local' && (
            <input
              type="text"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="/path/to/downloads"
              className="w-full h-10 px-4 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 text-base-content text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          )}

          {/* NAS Selection */}
          {destinationType === 'nas' && (
            <div className="space-y-2">
              <select
                value={selectedNAS}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                  setSelectedNAS(e.target.value);
                  const nas = nasLocations.find(n => n.name === e.target.value);
                  if (nas && nas.categories.length > 0) {
                    const defaultCat = nas.categories.find(c => c.includes('malayalam')) || nas.categories[0];
                    setSelectedCategory(defaultCat);
                  }
                }}
                className="w-full h-10 px-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 text-base-content text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              >
                {nasLocations.map((nas) => (
                  <option key={nas.name} value={nas.name}>
                    {nas.name} ({nas.host})
                  </option>
                ))}
              </select>

              <select
                value={selectedCategory}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedCategory(e.target.value)}
                className="w-full h-10 px-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 text-base-content text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              >
                {nasLocations
                  .find(n => n.name === selectedNAS)
                  ?.categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {CATEGORY_LABELS[cat] || cat}
                    </option>
                  ))}
              </select>

              <p className="text-xs text-emerald-400/70 bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
                {detectedCategory ? (
                  <>
                    <span className="text-yellow-400">🔍 Auto-detected:</span>{' '}
                    <span className="font-semibold text-emerald-300">
                      {selectedNAS} → {CATEGORY_LABELS[detectedCategory] || detectedCategory}
                    </span>
                  </>
                ) : (
                  <>📁 Files → {selectedNAS} → {CATEGORY_LABELS[selectedCategory] || selectedCategory}</>
                )}
              </p>
            </div>
          )}
        </div>

        {/* Enhanced Progress Display */}
        {loading && jobProgress && (
          <div className="space-y-3 p-4 rounded-xl bg-slate-900/50 border border-slate-700/50">
            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className={PHASE_LABELS[jobProgress.phase]?.color || 'text-gray-400'}>
                  {PHASE_LABELS[jobProgress.phase]?.icon} {PHASE_LABELS[jobProgress.phase]?.label || jobProgress.phase}
                </span>
                <span className="text-slate-400">{Math.round(progressPercent)}%</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Progress Details */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              {jobProgress.renamed_files > 0 && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                  <Film className="h-3.5 w-3.5 text-yellow-400" />
                  <span className="text-yellow-300">Renamed: {jobProgress.renamed_files}</span>
                </div>
              )}
              {jobProgress.filtered_files > 0 && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <Filter className="h-3.5 w-3.5 text-purple-400" />
                  <span className="text-purple-300">Filtered: {jobProgress.filtered_files}</span>
                </div>
              )}
              {jobProgress.nas_destination && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 col-span-2">
                  <Upload className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-emerald-300">→ {jobProgress.nas_destination}</span>
                </div>
              )}
              {jobProgress.plex_scan_status === 'scanning' && jobProgress.plex_library_name && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-orange-500/10 border border-orange-500/20 col-span-2">
                  <RefreshCw className="h-3.5 w-3.5 text-orange-400 animate-spin" />
                  <span className="text-orange-300">Plex scanning: {jobProgress.plex_library_name}</span>
                </div>
              )}
              {jobProgress.metadata_found === 'no' && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 col-span-2">
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                  <span className="text-amber-300">No IMDB/TMDB data → Malayalam library</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Download Button */}
        <Button
          onClick={handleDownload}
          disabled={loading || linkCount === 0}
          size="lg"
          className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              <Download className="h-5 w-5" />
              Download & Organize ({linkCount} link{linkCount !== 1 ? 's' : ''})
            </>
          )}
        </Button>

        <p className="text-xs text-base-content/50 text-center">
          Downloads with aria2c → {language === 'auto' ? 'Auto-detects language' : `Filters ${language} audio`} → Organizes → {destinationType === 'nas' ? 'Pushes to NAS' : 'Saves locally'}
        </p>
      </CardContent>
    </Card>
  );
};

export default AllDebridPanel;
