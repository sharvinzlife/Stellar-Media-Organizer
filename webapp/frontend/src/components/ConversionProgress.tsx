import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Film, Loader2, CheckCircle2, XCircle, Zap, Clock, TrendingUp, LucideIcon } from 'lucide-react';
import { GPU_SERVICE_URL } from '@/lib/api';

interface ConversionProgressProps {
  jobId: string;
  fileName: string;
  onComplete?: (data: JobStatusData) => void;
}

interface JobStatusData {
  progress?: number;
  eta?: string;
  status?: string;
  message?: string;
  current_time?: string;
  input_size?: number;
  output_size?: number;
  compression?: number;
}

interface StatusConfig {
  icon: LucideIcon;
  color: string;
  text: string;
  bg: string;
  spin?: boolean;
}

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  color: string;
}


const ConversionProgress: React.FC<ConversionProgressProps> = ({ jobId, fileName, onComplete }) => {
  const [progress, setProgress] = useState<number>(0);
  const [eta, setEta] = useState<string>('Calculating...');
  const [status, setStatus] = useState<string>('queued');
  const [message, setMessage] = useState<string>('Starting...');
  const [speed, setSpeed] = useState<string>('--');
  const [inputSize, setInputSize] = useState<number>(0);
  const [outputSize, setOutputSize] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let pollInterval: NodeJS.Timeout | undefined;
    let wsAttempted = false;

    const connectWebSocket = (): void => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const ws = new WebSocket(`${protocol}//${host}/api/v1/ws/conversion/${jobId}`);

        ws.onopen = (): void => {
          wsAttempted = true;
        };

        ws.onmessage = (event: MessageEvent): void => {
          try {
            const data: JobStatusData = JSON.parse(event.data);
            updateProgress(data);
            if (data.status === 'completed' || data.status === 'failed') {
              onComplete?.(data);
              ws.close();
            }
          } catch {
            // Parse error
          }
        };

        ws.onerror = (): void => {
          if (!wsAttempted) {
            startHttpPolling();
          }
        };

        wsRef.current = ws;

        setTimeout(() => {
          if (!wsAttempted) {
            startHttpPolling();
          }
        }, 2000);
      } catch {
        startHttpPolling();
      }
    };


    const updateProgress = (data: JobStatusData): void => {
      setProgress(data.progress || 0);
      setEta(data.eta || 'Calculating...');
      setStatus(data.status || 'running');
      setMessage(data.message || 'Processing...');
      setInputSize(data.input_size || 0);
      setOutputSize(data.output_size || 0);

      if (data.current_time) {
        const match = data.current_time.match(/(\d+):(\d+):(\d+)/);
        if (match) {
          setSpeed(`${(parseFloat(String(data.progress)) / 100).toFixed(1)}x`);
        }
      }
    };

    const startHttpPolling = (): void => {
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`${GPU_SERVICE_URL}/status/${jobId}`);
          if (response.ok) {
            const data: JobStatusData = await response.json();
            updateProgress(data);
            if (data.status === 'completed' || data.status === 'failed') {
              clearInterval(pollInterval);
              onComplete?.(data);
            }
          }
        } catch {
          // Polling error
        }
      }, 1000);
    };

    connectWebSocket();

    return () => {
      wsRef.current?.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [jobId, onComplete]);

  const formatFileSize = (bytes: number): string => {
    if (!bytes) return '0 B';
    const gb = bytes / 1024 ** 3;
    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    const mb = bytes / 1024 ** 2;
    return `${mb.toFixed(2)} MB`;
  };


  const getStatusConfig = (): StatusConfig => {
    switch (status) {
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'success',
          text: 'Completed',
          bg: 'bg-success/10 border-success/20',
        };
      case 'failed':
        return {
          icon: XCircle,
          color: 'error',
          text: 'Failed',
          bg: 'bg-error/10 border-error/20',
        };
      case 'running':
        return {
          icon: Loader2,
          color: 'primary',
          text: 'Converting',
          bg: 'bg-primary/10 border-primary/20',
          spin: true,
        };
      default:
        return {
          icon: Clock,
          color: 'warning',
          text: 'Queued',
          bg: 'bg-warning/10 border-warning/20',
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;
  const compression =
    inputSize && outputSize ? ((1 - outputSize / inputSize) * 100).toFixed(1) : '0';


  return (
    <Card variant="glass" className="animate-fade-up">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3">
            <div className={`p-2 rounded-xl ${statusConfig.bg}`}>
              <StatusIcon
                className={`h-5 w-5 text-${statusConfig.color} ${statusConfig.spin ? 'animate-spin' : ''}`}
              />
            </div>
            <div>
              <div className="font-semibold text-base-content">{statusConfig.text}</div>
              <div className="text-sm font-normal text-base-content/60 mt-0.5 truncate max-w-xs">
                {fileName}
              </div>
            </div>
          </CardTitle>
          {status === 'running' && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-accent bg-accent/10 px-3 py-1.5 rounded-full border border-accent/20">
              <Zap className="h-3.5 w-3.5" />
              GPU Active
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-base-content/60 font-medium">Progress</span>
            <span className="font-bold text-base-content">{progress.toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-base-content/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary via-secondary to-accent transition-all duration-300 rounded-full"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard icon={Clock} label="ETA" value={eta} color="primary" />
          <StatCard icon={TrendingUp} label="Speed" value={speed} color="secondary" />
          {(inputSize > 0 || outputSize > 0) && (
            <StatCard icon={Film} label="Saved" value={`${compression}%`} color="accent" />
          )}
        </div>


        {/* File Sizes */}
        {(inputSize > 0 || outputSize > 0) && (
          <div className="flex justify-between text-sm p-3 rounded-xl bg-base-content/5 border border-base-content/10">
            <div>
              <span className="text-base-content/50">Input:</span>
              <span className="ml-2 font-semibold text-base-content">
                {formatFileSize(inputSize)}
              </span>
            </div>
            {outputSize > 0 && (
              <div>
                <span className="text-base-content/50">Output:</span>
                <span className="ml-2 font-semibold text-base-content">
                  {formatFileSize(outputSize)}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Status Message */}
        <div className="text-sm p-3 rounded-xl bg-base-content/5 border border-base-content/10">
          <span className="font-semibold text-base-content/70">Status:</span>{' '}
          <span className="text-base-content/80">{message}</span>
        </div>
      </CardContent>
    </Card>
  );
};

const StatCard: React.FC<StatCardProps> = ({ icon: Icon, label, value, color }) => (
  <div className="p-3 rounded-xl bg-base-content/5 border border-base-content/10">
    <div className="flex items-center gap-1.5 text-xs text-base-content/50 font-medium mb-1">
      <Icon className={`h-3 w-3 text-${color}`} />
      {label}
    </div>
    <div className="text-base font-bold text-base-content truncate">{value}</div>
  </div>
);

export default ConversionProgress;