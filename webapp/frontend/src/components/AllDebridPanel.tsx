import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import { Cloud, Download, Loader2, Link2, CheckCircle, HardDrive, FolderOpen, Sparkles } from 'lucide-react';
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
  const [localPath, setLocalPath] = useState<string>('/Users/sharvin/Documents/Processed');

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
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/alldebrid/jobs/${jobId}`);
        const data = await response.json();
        const job = data.job;
        
        // Add new logs
        if (job.logs && job.logs.length > 0) {
          const lastLog = job.logs[job.logs.length - 1];
          window.addLog?.(lastLog.message, lastLog.level);
        }
        
        if (job.status === 'completed') {
          clearInterval(pollInterval);
          toast.success('Download completed!');
          setLoading(false);
        } else if (job.status === 'failed') {
          clearInterval(pollInterval);
          toast.error(job.error || 'Download failed');
          setLoading(false);
        }
      } catch {
        // Continue polling
      }
    }, 2000);
    
    // Stop polling after 30 minutes max
    setTimeout(() => {
      clearInterval(pollInterval);
      setLoading(false);
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
                📁 Files → {selectedNAS} → {CATEGORY_LABELS[selectedCategory] || selectedCategory}
              </p>
            </div>
          )}
        </div>

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
