import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import { Cloud, Download, Loader2, Link2, CheckCircle, Music } from 'lucide-react';
import { toast } from 'sonner';

interface AllDebridStatusResponse {
  configured: boolean;
}

interface AllDebridDownloadResponse {
  success: boolean;
  message?: string;
  detail?: string;
}

interface Preset {
  id: string;
  name: string;
}

declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

const MusicAllDebridPanel: React.FC = () => {
  const [links, setLinks] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [configured, setConfigured] = useState<boolean>(false);
  const [preset, setPreset] = useState<string>('optimal');
  const [outputFormat, setOutputFormat] = useState<string>('flac');

  const presets: Preset[] = [
    { id: 'optimal', name: 'Optimal' },
    { id: 'clarity', name: 'Clarity' },
    { id: 'bass_boost', name: 'Bass Boost' },
    { id: 'warm', name: 'Warm' },
    { id: 'bright', name: 'Bright' },
    { id: 'flat', name: 'Flat' },
  ];

  const formats = [
    { id: 'keep', name: 'Keep Original' },
    { id: 'flac', name: 'FLAC' },
    { id: 'mp3', name: 'MP3' },
    { id: 'm4a', name: 'M4A' },
  ];

  useEffect(() => {
    checkStatus();
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

    setLoading(true);
    window.addLog?.(`🎵 Starting music download of ${parsedLinks.length} links...`, 'info');
    window.addLog?.(`   Preset: ${preset}, Format: ${outputFormat}`, 'info');

    try {
      const response = await fetch('/api/v1/music/alldebrid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          links: parsedLinks,
          preset,
          output_format: outputFormat,
        }),
      });

      const data: AllDebridDownloadResponse = await response.json();

      if (data.success) {
        toast.success(data.message || 'Download started');
        window.addLog?.(`✅ ${data.message}`, 'success');
        setLinks('');
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

  const linkCount = parseLinks(links).length;

  if (!configured) {
    return (
      <Card variant="glass" className="border-warning/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-warning/20 border border-warning/20">
              <Cloud className="h-5 w-5 text-warning" />
            </div>
            AllDebrid Music Downloads
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
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500/20 to-orange-500/20 border border-pink-500/20">
            <Cloud className="h-5 w-5 text-pink-400" />
          </div>
          AllDebrid Music Downloads
        </CardTitle>
        <CardDescription>
          Download music from AllDebrid, organize with MusicBrainz metadata, and enhance audio
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-semibold text-white flex items-center gap-2">
            <Link2 className="h-4 w-4 text-pink-400" />
            AllDebrid Links
          </label>
          <textarea
            value={links}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setLinks(e.target.value)}
            placeholder="Paste AllDebrid music links here..."
            className="w-full h-24 px-4 py-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/50 resize-none placeholder-slate-500"
          />
          {linkCount > 0 && (
            <p className="text-xs text-green-400 flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              Found {linkCount} valid link{linkCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-white">Audio Preset</label>
            <select
              value={preset}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setPreset(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/50"
            >
              {presets.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-800">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-white">Output Format</label>
            <select
              value={outputFormat}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setOutputFormat(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/50"
            >
              {formats.map((f) => (
                <option key={f.id} value={f.id} className="bg-slate-800">
                  {f.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <Button
          onClick={handleDownload}
          disabled={loading || linkCount === 0}
          size="lg"
          className="w-full bg-gradient-to-r from-pink-500 to-orange-500 hover:from-pink-600 hover:to-orange-600"
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

        <p className="text-xs text-slate-500 text-center flex items-center justify-center gap-1">
          <Music className="h-3 w-3" />
          Downloads → MusicBrainz lookup → Audio enhancement → Organized library
        </p>
      </CardContent>
    </Card>
  );
};

export default MusicAllDebridPanel;
