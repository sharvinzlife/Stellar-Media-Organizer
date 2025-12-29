import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import Input from './ui/Input';
import {
  Music,
  FolderOpen,
  Play,
  Loader2,
  Volume2,
  CheckCircle,
  AlertCircle,
  HardDrive,
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';

interface MusicStatus {
  configured: boolean;
  musicbrainz_available: boolean;
  musicbrainz_configured: boolean;
  mutagen_available: boolean;
  default_output: string;
}

interface NASLocation {
  name: string;
  host: string;
  type: string;
  mounted: boolean;
  categories: string[];
}

declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

const MusicOrganizer: React.FC = () => {
  const [sourcePath, setSourcePath] = useState<string>('');
  const [outputPath, setOutputPath] = useState<string>('');
  const [processing, setProcessing] = useState<boolean>(false);
  
  // NAS destination - NAS is primary
  const [destinationType, setDestinationType] = useState<'local' | 'nas'>('nas');
  const [nasLocations, setNasLocations] = useState<NASLocation[]>([]);
  const [selectedNAS, setSelectedNAS] = useState<string>('');
  
  const [status, setStatus] = useState<MusicStatus | null>(null);

  useEffect(() => {
    fetchStatus();
    loadNASLocations();
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

  const loadNASLocations = async (): Promise<void> => {
    try {
      const response = await api.get('/nas/list');
      const locations = response.data.nas_locations || [];
      // Filter to only NAS with music category (Lharmony)
      const musicNAS = locations.filter((nas: NASLocation) => 
        nas.categories.includes('music')
      );
      setNasLocations(musicNAS);
      if (musicNAS.length > 0) {
        setSelectedNAS(musicNAS[0].name);
      }
    } catch {
      // NAS not configured
    }
  };

  const handleProcess = async (): Promise<void> => {
    if (!sourcePath) {
      toast.error('Please enter a source directory path');
      return;
    }

    if (destinationType === 'nas' && !selectedNAS) {
      toast.error('Please select a NAS destination');
      return;
    }

    setProcessing(true);
    const dest = destinationType === 'nas' ? `NAS: ${selectedNAS}` : `Local: ${outputPath}`;
    window.addLog?.(`🔊 Starting 7.0 surround upmix → ${dest}`, 'info');

    try {
      const response = await fetch('/api/v1/music/enhance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          output_path: destinationType === 'local' ? outputPath : undefined,
          preset: 'surround_7_0',
          output_format: 'flac',
          nas_destination: destinationType === 'nas' ? {
            nas_name: selectedNAS,
            category: 'music',
          } : undefined,
        }),
      });

      const data = await response.json();

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

  return (
    <div className="space-y-6">
      {/* Status Card */}
      {status && (
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20">
                  <Volume2 className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">7.0 Surround Upmixer</h3>
                  <p className="text-sm text-slate-400">
                    Timbre-matching for Polk T50 + Sony surrounds
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
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20">
              <Volume2 className="h-5 w-5 text-cyan-400" />
            </div>
            7.0 Surround Upmixer
          </CardTitle>
          <CardDescription>
            Upmix stereo music to 7.0 surround with timbre-matching for your home theater
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Source Directory */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-cyan-400" />
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
              <FolderOpen className="h-4 w-4 text-blue-400" />
              Destination
            </label>
            
            {/* Destination Type Toggle */}
            <div className="flex items-center gap-2 p-1 bg-white/5 rounded-xl">
              <button
                onClick={() => setDestinationType('local')}
                className={`
                  flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg transition-all
                  ${destinationType === 'local' 
                    ? 'bg-blue-500 text-white shadow-lg' 
                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                  }
                `}
              >
                <FolderOpen className="h-4 w-4" />
                <span className="font-medium">Local Folder</span>
              </button>
              <button
                onClick={() => setDestinationType('nas')}
                disabled={nasLocations.length === 0}
                className={`
                  flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg transition-all
                  ${destinationType === 'nas' 
                    ? 'bg-emerald-500 text-white shadow-lg' 
                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                  }
                  ${nasLocations.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <HardDrive className="h-4 w-4" />
                <span className="font-medium">NAS Storage</span>
              </button>
            </div>

            {/* Local Folder Input */}
            {destinationType === 'local' && (
              <>
                <Input
                  type="text"
                  placeholder="~/Documents/Music"
                  value={outputPath}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setOutputPath(e.target.value)}
                />
                <p className="text-xs text-slate-500">
                  📁 Output: Album Name/01 - Track.mkv (7.0 FLAC)
                </p>
              </>
            )}

            {/* NAS Destination Selector */}
            {destinationType === 'nas' && (
              <div className="space-y-3">
                <select
                  value={selectedNAS}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedNAS(e.target.value)}
                  className="w-full h-11 px-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 text-white font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                >
                  {nasLocations.map((nas) => (
                    <option key={nas.name} value={nas.name}>
                      {nas.name} ({nas.host}) - {nas.type}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-emerald-400/70 bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20">
                  🌐 Music will be moved to NAS: {selectedNAS} → /music/Album Name/
                </p>
              </div>
            )}
          </div>

          {/* 7.0 Surround Info Card */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-500/30">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <Volume2 className="h-5 w-5 text-cyan-400" />
              </div>
              <div>
                <h4 className="font-semibold text-white">7.0 Surround Timbre-Matching</h4>
                <p className="text-xs text-slate-400">Optimized for Polk T50 + Sony surrounds + Denon AVR</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="flex items-center gap-2 text-slate-300">
                <span className="text-cyan-400">●</span> Presence +3dB @ 3500Hz
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <span className="text-cyan-400">●</span> Air +2dB @ 12000Hz
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <span className="text-pink-400">●</span> Output: FLAC in MKV
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <span className="text-pink-400">●</span> Plex Direct Play ready
              </div>
            </div>
          </div>

          {/* Process Button */}
          <Button
            onClick={handleProcess}
            disabled={processing || !sourcePath}
            size="lg"
            className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
          >
            {processing ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Upmixing to 7.0 Surround...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                Upmix to 7.0 Surround
              </>
            )}
          </Button>

          {/* Denon AVR Tips */}
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-emerald-400" />
              📺 Denon AVR Calibration Tips
            </h4>
            <ul className="text-sm text-slate-400 space-y-1 ml-6 list-disc">
              <li>Channel Levels: Increase Surround/Back by <span className="text-cyan-400">+1.5dB to +2.0dB</span></li>
              <li>Crossover: Set Front Speakers to <span className="text-cyan-400">"Large"</span> (no sub)</li>
              <li>Plex: Use <span className="text-pink-400">"Direct Play"</span> for best quality</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MusicOrganizer;
