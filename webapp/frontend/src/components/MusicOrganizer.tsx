import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import Input from './ui/Input';
import {
  Music,
  FolderOpen,
  Play,
  Loader2,
  Sparkles,
  Volume2,
  Disc3,
  CheckCircle,
  AlertCircle,
  Settings2,
  Headphones,
  Radio,
} from 'lucide-react';
import { toast } from 'sonner';

interface Preset {
  id: string;
  name: string;
  description: string;
  recommended?: boolean;
}

interface Format {
  id: string;
  name: string;
  description: string;
}

interface MusicStatus {
  configured: boolean;
  musicbrainz_available: boolean;
  musicbrainz_configured: boolean;
  mutagen_available: boolean;
  default_output: string;
}

interface PresetsResponse {
  presets: Preset[];
  formats: Format[];
}

interface ProcessResponse {
  success: boolean;
  message: string;
  job_id?: number;
}

declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

const MusicOrganizer: React.FC = () => {
  const [sourcePath, setSourcePath] = useState<string>('');
  const [outputPath, setOutputPath] = useState<string>('/Users/sharvin/Documents/Music');
  const [preset, setPreset] = useState<string>('optimal');
  const [outputFormat, setOutputFormat] = useState<string>('keep');
  const [enhanceAudio, setEnhanceAudio] = useState<boolean>(true);
  const [lookupMetadata, setLookupMetadata] = useState<boolean>(true);
  const [processing, setProcessing] = useState<boolean>(false);
  
  const [status, setStatus] = useState<MusicStatus | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [formats, setFormats] = useState<Format[]>([]);

  useEffect(() => {
    fetchStatus();
    fetchPresets();
  }, []);

  const fetchStatus = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/music/status');
      const data: MusicStatus = await response.json();
      setStatus(data);
      if (data.default_output) {
        setOutputPath(data.default_output);
      }
    } catch (error) {
      console.error('Failed to fetch music status:', error);
    }
  };

  const fetchPresets = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/music/presets');
      const data: PresetsResponse = await response.json();
      setPresets(data.presets);
      setFormats(data.formats);
    } catch (error) {
      console.error('Failed to fetch presets:', error);
    }
  };

  const handleProcess = async (): Promise<void> => {
    if (!sourcePath) {
      toast.error('Please enter a source directory path');
      return;
    }

    setProcessing(true);
    window.addLog?.(`🎵 Starting music processing...`, 'info');
    window.addLog?.(`   Preset: ${preset}, Format: ${outputFormat}`, 'info');

    try {
      const response = await fetch('/api/v1/music/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          output_path: outputPath,
          preset,
          output_format: outputFormat,
          enhance_audio: enhanceAudio,
          lookup_metadata: lookupMetadata,
        }),
      });

      const data: ProcessResponse = await response.json();

      if (data.success) {
        toast.success(data.message);
        window.addLog?.(`✅ ${data.message}`, 'success');
      } else {
        toast.error(data.message || 'Processing failed');
        window.addLog?.(`❌ ${data.message}`, 'error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to process music files');
      window.addLog?.(`❌ Error: ${errorMessage}`, 'error');
    } finally {
      setProcessing(false);
    }
  };

  const getPresetIcon = (presetId: string) => {
    switch (presetId) {
      case 'optimal': return <Sparkles className="h-4 w-4" />;
      case 'clarity': return <Radio className="h-4 w-4" />;
      case 'bass_boost': return <Volume2 className="h-4 w-4" />;
      case 'warm': return <Headphones className="h-4 w-4" />;
      case 'bright': return <Disc3 className="h-4 w-4" />;
      case 'flat': return <Settings2 className="h-4 w-4" />;
      default: return <Music className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Card */}
      {status && (
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 border border-pink-500/20">
                  <Music className="h-5 w-5 text-pink-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Music Organizer</h3>
                  <p className="text-sm text-slate-400">
                    {status.musicbrainz_configured ? 'MusicBrainz connected' : 'MusicBrainz not configured'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {status.musicbrainz_available && (
                  <span className="flex items-center gap-1 text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
                    <CheckCircle className="h-3 w-3" />
                    Metadata
                  </span>
                )}
                {status.mutagen_available && (
                  <span className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">
                    <CheckCircle className="h-3 w-3" />
                    Tags
                  </span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Panel */}
      <Card variant="glass">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 border border-pink-500/20">
              <Music className="h-5 w-5 text-pink-400" />
            </div>
            Music Library Organizer
          </CardTitle>
          <CardDescription>
            Organize music for Plex/Jellyfin with MusicBrainz metadata and audio enhancement
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Source Directory */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-pink-400" />
              Source Folder
            </label>
            <Input
              type="text"
              placeholder="/path/to/music/files"
              value={sourcePath}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSourcePath(e.target.value)}
            />
          </div>

          {/* Output Directory */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-purple-400" />
              Output Folder
            </label>
            <Input
              type="text"
              placeholder="/Users/sharvin/Documents/Music"
              value={outputPath}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setOutputPath(e.target.value)}
            />
            <p className="text-xs text-slate-500">
              📁 Structure: /Artist/Album (Year)/01 - Track.ext
            </p>
          </div>

          {/* Audio Enhancement Preset */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-yellow-400" />
              Audio Enhancement Preset
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {presets.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPreset(p.id)}
                  className={`
                    flex items-center gap-2 p-3 rounded-xl border-2 transition-all duration-200 text-left
                    ${preset === p.id
                      ? 'border-pink-500 bg-pink-500/10 shadow-lg shadow-pink-500/20'
                      : 'border-white/10 hover:border-white/30 hover:bg-white/5'
                    }
                  `}
                >
                  <div className={`${preset === p.id ? 'text-pink-400' : 'text-slate-400'}`}>
                    {getPresetIcon(p.id)}
                  </div>
                  <div>
                    <div className={`font-semibold text-sm ${preset === p.id ? 'text-white' : 'text-slate-300'}`}>
                      {p.name}
                      {p.recommended && (
                        <span className="ml-1 text-xs text-yellow-400">★</span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 line-clamp-1">{p.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Output Format */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white">Output Format</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {formats.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setOutputFormat(f.id)}
                  className={`
                    p-3 rounded-xl border-2 transition-all duration-200 text-center
                    ${outputFormat === f.id
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-white/10 hover:border-white/30 hover:bg-white/5'
                    }
                  `}
                >
                  <div className={`font-semibold text-sm ${outputFormat === f.id ? 'text-white' : 'text-slate-300'}`}>
                    {f.name}
                  </div>
                  <div className="text-xs text-slate-500">{f.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Options */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enhanceAudio}
                onChange={(e) => setEnhanceAudio(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/10 text-pink-500 focus:ring-pink-500/50"
              />
              <span className="text-sm text-slate-300">Enhance Audio (EQ + Normalization)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={lookupMetadata}
                onChange={(e) => setLookupMetadata(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/10 text-pink-500 focus:ring-pink-500/50"
              />
              <span className="text-sm text-slate-300">Lookup MusicBrainz Metadata</span>
            </label>
          </div>

          {/* Process Button */}
          <Button
            onClick={handleProcess}
            disabled={processing || !sourcePath}
            size="lg"
            className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600"
          >
            {processing ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Processing Music...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                Organize & Enhance Music
              </>
            )}
          </Button>

          {/* Info */}
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-blue-400" />
              What this does:
            </h4>
            <ul className="text-sm text-slate-400 space-y-1 ml-6 list-disc">
              <li>Looks up metadata from MusicBrainz (artist, album, track #, year)</li>
              <li>Organizes files to: <code className="text-pink-400">/Artist/Album (Year)/01 - Track.ext</code></li>
              <li>Applies professional audio enhancement (EQ, loudness normalization)</li>
              <li>Updates ID3/Vorbis tags with accurate metadata</li>
              <li>Perfect for Plex, Jellyfin, Emby, and other media servers</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MusicOrganizer;
