import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import Button from './ui/Button';
import Input from './ui/Input';
import { FolderOpen, Play, Loader2, Film, Music, Zap, Video, LucideIcon } from 'lucide-react';
import { processFiles, getSupportedLanguages } from '@/lib/api';
import { toast } from 'sonner';
import type { ProcessResult, Language } from '../types';

interface OperationPanelProps {
  onProcessComplete?: (result: ProcessResult) => void;
}

interface Operation {
  id: string;
  label: string;
  icon: LucideIcon;
  color: string;
}

interface ConversionResponse {
  success: boolean;
  message: string;
  jobs?: Array<{
    job_id: string;
    input_file?: string;
  }>;
  detail?: string;
}

interface AutoFillPathEvent extends CustomEvent {
  detail: { path: string };
}

// Extend Window interface for global addLog function
declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}


const OperationPanel: React.FC<OperationPanelProps> = ({ onProcessComplete }) => {
  const [sourcePath, setSourcePath] = useState<string>('');
  const [operation, setOperation] = useState<string>('both');
  const [convertPreset, setConvertPreset] = useState<string>('hevc_best');
  const [language, setLanguage] = useState<string>('auto');
  const [volumeBoost, setVolumeBoost] = useState<number>(1.0);
  const [processing, setProcessing] = useState<boolean>(false);
  const [languages, setLanguages] = useState<Language[]>([]);

  useEffect(() => {
    loadLanguages();

    const handleAutoFillPath = (event: Event): void => {
      const customEvent = event as AutoFillPathEvent;
      setSourcePath(customEvent.detail.path);
    };

    window.addEventListener('autoFillPath', handleAutoFillPath);
    return () => window.removeEventListener('autoFillPath', handleAutoFillPath);
  }, []);

  const loadLanguages = async (): Promise<void> => {
    try {
      const data = await getSupportedLanguages();
      setLanguages(data.languages);
    } catch {
      // Use defaults
    }
  };

  const handleProcess = async (): Promise<void> => {
    if (!sourcePath) {
      toast.error('Please enter a source directory path');
      return;
    }

    setProcessing(true);
    const langLabel = language === 'auto' ? 'Auto-detect' : language;
    window.addLog?.(`Starting ${operation} operation (${langLabel})...`, 'info');

    try {
      if (operation === 'convert') {
        const response = await fetch('/api/v1/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            directory_path: sourcePath,
            preset: convertPreset,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMsg = errorData.detail || `Error: ${response.status}`;
          toast.error(errorMsg);
          window.addLog?.(`❌ ${errorMsg}`, 'error');
          return;
        }

        const result: ConversionResponse = await response.json();

        if (result.jobs?.length) {
          result.jobs.forEach((job) => {
            const event = new CustomEvent('conversionStart', {
              detail: { jobId: job.job_id, fileName: job.input_file || 'Unknown file' },
            });
            window.dispatchEvent(event);
          });
        }

        if (result.success) {
          toast.success(result.message);
          window.addLog?.(`✅ ${result.message}`, 'success');
          onProcessComplete?.(result as unknown as ProcessResult);
        } else {
          toast.error(result.message || 'Conversion failed');
          window.addLog?.(`❌ ${result.message}`, 'error');
        }
      } else {
        const result = await processFiles({
          operation,
          directory_path: sourcePath,
          target_language: language === 'auto' ? 'malayalam' : language,
          volume_boost: parseFloat(String(volumeBoost)),
          auto_detect_language: language === 'auto',
        });

        if (result.success) {
          toast.success(result.message);
          window.addLog?.(`✅ ${result.message}`, 'success');
          onProcessComplete?.(result);
        } else {
          toast.error(result.message);
          window.addLog?.(`❌ ${result.message}`, 'error');
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to process files');
      window.addLog?.(`❌ Error: ${errorMessage}`, 'error');
    } finally {
      setProcessing(false);
    }
  };


  const operations: Operation[] = [
    { id: 'organize', label: 'Organize', icon: Film, color: 'secondary' },
    { id: 'filter_audio', label: 'Filter Audio', icon: Music, color: 'accent' },
    { id: 'both', label: 'Both', icon: Zap, color: 'primary' },
    { id: 'convert', label: 'Convert H.265', icon: Video, color: 'primary' },
  ];

  return (
    <Card variant="glass">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 border border-primary/20">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          Process Local Files
        </CardTitle>
        <CardDescription>Organize and filter audio for files already on your machine</CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Source Directory Path */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-primary" />
            Source Folder
          </label>
          <Input
            type="text"
            placeholder="/path/to/media/files"
            value={sourcePath}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSourcePath(e.target.value)}
          />
          <p className="text-xs text-base-content/50">
            💡 Files will be organized in-place (renamed and restructured)
          </p>
        </div>

        {/* Operation Type */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content">Operation</label>
          <div className="grid grid-cols-2 gap-2">
            {operations.map((op) => {
              const Icon = op.icon;
              const isActive = operation === op.id;
              return (
                <button
                  key={op.id}
                  onClick={() => setOperation(op.id)}
                  className={`
                    flex items-center gap-2 p-3 rounded-xl border-2 transition-all duration-200 text-sm
                    ${
                      isActive
                        ? `border-${op.color} bg-${op.color}/10 shadow-lg shadow-${op.color}/20`
                        : 'border-base-content/10 hover:border-base-content/30 hover:bg-base-content/5'
                    }
                  `}
                >
                  <Icon
                    className={`h-4 w-4 ${isActive ? `text-${op.color}` : 'text-base-content/50'}`}
                  />
                  <span
                    className={`font-medium ${isActive ? 'text-base-content' : 'text-base-content/70'}`}
                  >
                    {op.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Conversion Preset */}
        {operation === 'convert' && (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-base-content">Quality</label>
            <select
              value={convertPreset}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setConvertPreset(e.target.value)}
              className="w-full h-10 px-4 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="hevc_best">Best Quality (Slower)</option>
              <option value="hevc_balanced">Balanced</option>
              <option value="hevc_fast">Fast (Lower Quality)</option>
            </select>
          </div>
        )}

        {/* Language Selection */}
        {(operation === 'filter_audio' || operation === 'both') && (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-base-content">Target Language</label>
            <select
              value={language}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)}
              className="w-full h-10 px-4 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="auto">✨ Auto-detect (Malayalam → English → Hindi)</option>
              {languages.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.emoji} {lang.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Volume Boost */}
        {(operation === 'filter_audio' || operation === 'both') && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-base-content">Volume Boost</label>
              <span className="text-sm font-bold text-primary">{volumeBoost}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={volumeBoost}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setVolumeBoost(parseFloat(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer bg-base-content/10 accent-primary"
            />
            <div className="flex justify-between text-xs text-base-content/50">
              <span>0.5x</span>
              <span>3.0x</span>
            </div>
          </div>
        )}

        {/* Process Button */}
        <Button
          onClick={handleProcess}
          disabled={processing || !sourcePath}
          size="lg"
          className="w-full"
        >
          {processing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Play className="h-5 w-5" />
              Process Files
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
};

export default OperationPanel;
