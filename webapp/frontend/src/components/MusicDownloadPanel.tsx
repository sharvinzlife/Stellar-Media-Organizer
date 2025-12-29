import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import DownloadAnimation from './DownloadAnimation';
import {
  Cloud,
  Download,
  Loader2,
  Link2,
  CheckCircle,
  Music,
  Youtube,
  RefreshCw,
  AlertCircle,
  Settings,
} from 'lucide-react';
import { toast } from 'sonner';

interface ToolsStatus {
  success: boolean;
  tools: {
    'yt-dlp': boolean;
    spotdl: boolean;
    ffmpeg: boolean;
  };
  alldebrid_configured: boolean;
  last_update: string | null;
}

interface DownloadResponse {
  success: boolean;
  message?: string;
  detail?: string;
  job_id?: number;
}

interface Preset {
  id: string;
  name: string;
  desc: string;
}

declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

const MusicDownloadPanel: React.FC = () => {
  const [urls, setUrls] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [updatingTools, setUpdatingTools] = useState<boolean>(false);
  const [source, setSource] = useState<string>('auto');
  const [audioFormat, setAudioFormat] = useState<string>('flac');
  const [preset, setPreset] = useState<string>('surround_7_0');
  const [enhanceAudio, setEnhanceAudio] = useState<boolean>(true);
  const [lookupMetadata, setLookupMetadata] = useState<boolean>(true);
  const [toolsStatus, setToolsStatus] = useState<ToolsStatus | null>(null);

  const sources = [
    { id: 'auto', name: 'Auto Detect', icon: '🔍' },
    { id: 'youtube_music', name: 'YouTube Music', icon: '🎵' },
    { id: 'spotify', name: 'Spotify', icon: '💚' },
    { id: 'alldebrid', name: 'AllDebrid', icon: '☁️' },
  ];

  const presets = [
    { id: 'surround_7_0', name: '🔊 7.0 Surround', desc: 'Upmix to 7.0 with timbre-matching for Polk T50 + Sony surrounds' },
  ];

  const formats = [
    { id: 'flac', name: 'FLAC (7.0 Surround)' },
  ];

  useEffect(() => {
    checkToolsStatus();
  }, []);

  const checkToolsStatus = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/music/tools/status');
      const data: ToolsStatus = await response.json();
      setToolsStatus(data);
    } catch (error) {
      console.error('Failed to check tools status:', error);
    }
  };

  const updateTools = async (): Promise<void> => {
    setUpdatingTools(true);
    window.addLog?.('🔄 Updating yt-dlp and spotdl...', 'info');

    try {
      const response = await fetch('/api/v1/music/tools/update', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        toast.success('Tools updated successfully');
        window.addLog?.('✅ Tools updated', 'success');
        await checkToolsStatus();
      } else {
        toast.error('Failed to update tools');
        window.addLog?.('❌ Tool update failed', 'error');
      }
    } catch (error) {
      toast.error('Failed to update tools');
      window.addLog?.('❌ Tool update error', 'error');
    } finally {
      setUpdatingTools(false);
    }
  };

  const parseUrls = (text: string): string[] => {
    const urlPattern = /https?:\/\/[^\s<>"']+[^\s<>"'.,;:)\]}]/g;
    const matches = text.match(urlPattern) || [];
    return [...new Set(matches)];
  };

  const detectUrlTypes = (
    parsedUrls: string[]
  ): { youtube: number; spotify: number; alldebrid: number; other: number } => {
    const counts = { youtube: 0, spotify: 0, alldebrid: 0, other: 0 };

    for (const url of parsedUrls) {
      if (url.includes('youtube.com') || url.includes('youtu.be') || url.includes('music.youtube.com')) {
        counts.youtube++;
      } else if (url.includes('spotify.com')) {
        counts.spotify++;
      } else if (url.includes('alldebrid.com')) {
        counts.alldebrid++;
      } else {
        counts.other++;
      }
    }

    return counts;
  };

  const handleDownload = async (): Promise<void> => {
    const parsedUrls = parseUrls(urls);

    if (parsedUrls.length === 0) {
      toast.error('No valid URLs found');
      return;
    }

    setLoading(true);
    const urlTypes = detectUrlTypes(parsedUrls);
    window.addLog?.(`🎵 Starting download of ${parsedUrls.length} URLs...`, 'info');
    window.addLog?.(
      `   YouTube: ${urlTypes.youtube}, Spotify: ${urlTypes.spotify}, AllDebrid: ${urlTypes.alldebrid}`,
      'info'
    );

    try {
      const response = await fetch('/api/v1/music/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: parsedUrls,
          source,
          audio_format: audioFormat,
          preset,
          enhance_audio: enhanceAudio,
          lookup_metadata: lookupMetadata,
        }),
      });

      const data: DownloadResponse = await response.json();

      if (data.success) {
        toast.success(data.message || 'Download started');
        window.addLog?.(`✅ ${data.message}`, 'success');
        setUrls('');
      } else {
        toast.error(data.detail || 'Download failed');
        window.addLog?.(`❌ ${data.detail}`, 'error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to start download');
      window.addLog?.(`❌ Error: ${errorMessage}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const parsedUrls = parseUrls(urls);
  const urlCount = parsedUrls.length;
  const urlTypes = detectUrlTypes(parsedUrls);

  return (
    <Card variant="glass">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-green-500/20 to-purple-500/20 border border-green-500/20">
            <Music className="h-5 w-5 text-green-400" />
          </div>
          Music Downloader
        </CardTitle>
        <CardDescription>
          Download from YouTube Music, Spotify, or AllDebrid with auto-detection
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Tools Status */}
        {toolsStatus && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center gap-4 text-xs">
              <span
                className={`flex items-center gap-1 ${toolsStatus.tools['yt-dlp'] ? 'text-green-400' : 'text-red-400'}`}
              >
                {toolsStatus.tools['yt-dlp'] ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                yt-dlp
              </span>
              <span
                className={`flex items-center gap-1 ${toolsStatus.tools.spotdl ? 'text-green-400' : 'text-red-400'}`}
              >
                {toolsStatus.tools.spotdl ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                spotdl
              </span>
              <span
                className={`flex items-center gap-1 ${toolsStatus.alldebrid_configured ? 'text-green-400' : 'text-yellow-400'}`}
              >
                {toolsStatus.alldebrid_configured ? (
                  <CheckCircle className="h-3 w-3" />
                ) : (
                  <AlertCircle className="h-3 w-3" />
                )}
                AllDebrid
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={updateTools}
              disabled={updatingTools}
              className="text-xs"
            >
              {updatingTools ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
              Update
            </Button>
          </div>
        )}

        {/* URL Input */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-white flex items-center gap-2">
            <Link2 className="h-4 w-4 text-green-400" />
            Music URLs
          </label>
          <textarea
            value={urls}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setUrls(e.target.value)}
            placeholder="Paste YouTube Music, Spotify, or AllDebrid links here...

Examples:
• https://music.youtube.com/playlist?list=...
• https://open.spotify.com/album/...
• https://open.spotify.com/playlist/...
• https://alldebrid.com/f/..."
            className="w-full h-32 px-4 py-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-green-500/50 resize-none placeholder-slate-500"
          />
          {urlCount > 0 && (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-green-400 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {urlCount} URL{urlCount !== 1 ? 's' : ''}
              </span>
              {urlTypes.youtube > 0 && <span className="text-red-400">🎵 {urlTypes.youtube} YouTube</span>}
              {urlTypes.spotify > 0 && <span className="text-green-400">💚 {urlTypes.spotify} Spotify</span>}
              {urlTypes.alldebrid > 0 && <span className="text-orange-400">☁️ {urlTypes.alldebrid} AllDebrid</span>}
            </div>
          )}
        </div>

        {/* Source Selection */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-white">Source</label>
          <div className="grid grid-cols-4 gap-2">
            {sources.map((s) => (
              <button
                key={s.id}
                onClick={() => setSource(s.id)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  source === s.id
                    ? 'bg-green-500/30 border-green-500/50 text-green-300 border'
                    : 'bg-white/5 border-white/10 text-slate-400 border hover:bg-white/10'
                }`}
              >
                {s.icon} {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* Format & Preset */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-white">Audio Format</label>
            <select
              value={audioFormat}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setAudioFormat(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500/50"
            >
              {formats.map((f) => (
                <option key={f.id} value={f.id} className="bg-slate-800">
                  {f.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-white">Enhancement Preset</label>
            <select
              value={preset}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setPreset(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500/50"
            >
              {presets.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-800">
                  {p.name}
                </option>
              ))}
            </select>
            {/* Show selected preset description */}
            <p className="text-xs text-slate-400">
              {presets.find(p => p.id === preset)?.desc}
            </p>
          </div>
        </div>

        {/* Options */}
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={enhanceAudio}
              onChange={(e) => setEnhanceAudio(e.target.checked)}
              className="w-4 h-4 rounded border-white/20 bg-white/5 text-green-500 focus:ring-green-500/50"
            />
            <span className="text-sm text-slate-300">Enhance Audio</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={lookupMetadata}
              onChange={(e) => setLookupMetadata(e.target.checked)}
              className="w-4 h-4 rounded border-white/20 bg-white/5 text-green-500 focus:ring-green-500/50"
            />
            <span className="text-sm text-slate-300">MusicBrainz Lookup</span>
          </label>
        </div>

        {/* Download Button */}
        <div className="relative">
          {loading && <DownloadAnimation variant="bar" className="mb-2" />}
          <Button
            onClick={handleDownload}
            disabled={loading || urlCount === 0}
            size="lg"
            className={`w-full relative overflow-hidden ${
              loading 
                ? 'bg-gradient-to-r from-emerald-600 to-emerald-500' 
                : 'bg-gradient-to-r from-green-500 to-purple-500 hover:from-green-600 hover:to-purple-600'
            }`}
          >
            {loading && <DownloadAnimation variant="overlay" />}
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="h-5 w-5" />
                Download & Organize ({urlCount} URL{urlCount !== 1 ? 's' : ''})
              </>
            )}
          </Button>
        </div>

        <p className="text-xs text-slate-500 text-center flex items-center justify-center gap-1">
          <Music className="h-3 w-3" />
          Auto-detect source → Download → MusicBrainz → Audio enhancement → Organized library
        </p>
      </CardContent>
    </Card>
  );
};

export default MusicDownloadPanel;
