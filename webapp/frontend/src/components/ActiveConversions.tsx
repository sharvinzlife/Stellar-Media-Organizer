import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import ConversionProgress from './ConversionProgress';
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Zap,
  LucideIcon,
  Loader2,
  Music,
  Video,
  Download,
  FolderOpen,
  Clock,
  Ban,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { GPU_SERVICE_URL } from '@/lib/api';
import type { ConversionJob } from '../types';

interface HealthResponse {
  active_jobs: number;
}

interface ConversionStartEvent extends CustomEvent {
  detail: {
    jobId: string;
    fileName: string;
  };
}

interface JobCompleteData {
  status?: string;
  compression?: number;
  progress?: number;
  eta?: string;
  message?: string;
  current_time?: string;
  input_size?: number;
  output_size?: number;
}

interface BackendJob {
  id: number;
  job_type: string;
  status: string;
  input_path: string;
  output_path: string;
  language: string;
  progress: number;
  current_file: string | null;
  total_files: number;
  processed_files: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration: number | null;
  error_message: string | null;
}

interface StatBoxProps {
  value: number | string;
  label: string;
  color: string;
  icon: LucideIcon;
  pulse?: boolean;
}

const ActiveConversions: React.FC = () => {
  const [gpuJobs, setGpuJobs] = useState<ConversionJob[]>([]);
  const [backendJobs, setBackendJobs] = useState<BackendJob[]>([]);
  const [recentJobs, setRecentJobs] = useState<BackendJob[]>([]);
  const [completedCount, setCompletedCount] = useState<number>(0);
  const [failedCount, setFailedCount] = useState<number>(0);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Fetch backend jobs (music downloads, video processing, etc.)
  const fetchBackendJobs = useCallback(async () => {
    try {
      // Fetch active jobs
      const activeRes = await fetch('/api/v1/jobs/active');
      const activeData = await activeRes.json();
      setBackendJobs(activeData.jobs || []);

      // Fetch recent jobs for history
      const recentRes = await fetch('/api/v1/jobs/recent?limit=10');
      const recentData = await recentRes.json();
      const jobs = recentData.jobs || [];
      setRecentJobs(jobs.slice(0, 5));

      // Count completed/failed from recent
      const completed = jobs.filter((j: BackendJob) => j.status === 'completed').length;
      const failed = jobs.filter((j: BackendJob) => j.status === 'failed').length;
      setCompletedCount(completed);
      setFailedCount(failed);

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch backend jobs:', error);
    }
  }, []);

  useEffect(() => {
    fetchBackendJobs();
    const interval = setInterval(fetchBackendJobs, 2000);
    return () => clearInterval(interval);
  }, [fetchBackendJobs]);

  // Check GPU service for active conversions
  useEffect(() => {
    const checkGpuJobs = async () => {
      try {
        const response = await fetch(`${GPU_SERVICE_URL}/health`);
        const data: HealthResponse = await response.json();
        if (data.active_jobs > gpuJobs.length) {
          console.log(`GPU active jobs: ${data.active_jobs}`);
        }
      } catch {
        // GPU service may not be running
      }
    };

    checkGpuJobs();
    const interval = setInterval(checkGpuJobs, 5000);
    return () => clearInterval(interval);
  }, [gpuJobs.length]);

  const handleJobComplete = (jobData: JobCompleteData): void => {
    if (jobData.status === 'completed') {
      setCompletedCount((prev) => prev + 1);
      toast.success(`Conversion completed! Saved ${jobData.compression?.toFixed(1)}% space`);
    } else if (jobData.status === 'failed') {
      setFailedCount((prev) => prev + 1);
      toast.error('Conversion failed');
    }
  };

  useEffect(() => {
    const handleConversionStart = (event: Event): void => {
      const customEvent = event as ConversionStartEvent;
      const { jobId, fileName } = customEvent.detail;
      setGpuJobs((prev) => [...prev, { jobId, fileName }]);
    };

    window.addEventListener('conversionStart', handleConversionStart);
    return () => window.removeEventListener('conversionStart', handleConversionStart);
  }, []);

  const cancelJob = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        toast.success(`Job #${jobId} cancelled`);
        fetchBackendJobs();
      } else {
        toast.error(data.detail || 'Failed to cancel job');
      }
    } catch {
      toast.error('Failed to cancel job');
    }
  };

  const hasActivity = gpuJobs.length > 0 || backendJobs.length > 0 || recentJobs.length > 0;
  const totalActive = gpuJobs.length + backendJobs.length;

  const getJobIcon = (job: BackendJob) => {
    if (job.output_path?.includes('Music') || job.language?.includes('optimal')) {
      return <Music className="h-4 w-4 text-pink-400" />;
    }
    if (job.job_type === 'convert') {
      return <Video className="h-4 w-4 text-blue-400" />;
    }
    if (job.input_path?.includes('AllDebrid') || job.input_path?.includes('http')) {
      return <Download className="h-4 w-4 text-green-400" />;
    }
    return <FolderOpen className="h-4 w-4 text-purple-400" />;
  };

  const getJobTypeLabel = (job: BackendJob) => {
    if (job.output_path?.includes('Music')) return 'Music';
    if (job.job_type === 'convert') return 'Convert';
    if (job.input_path?.includes('AllDebrid')) return 'Download';
    if (job.input_path?.includes('http')) return 'Download';
    return 'Organize';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'completed':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'failed':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'pending':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'cancelled':
        return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-400" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-400" />;
      default:
        return <Activity className="h-4 w-4 text-slate-400" />;
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString();
  };

  const getPresetLabel = (preset: string) => {
    const presets: Record<string, string> = {
      optimal: '✨ Optimal',
      clarity: '🎯 Clarity',
      bass_boost: '🔊 Bass',
      warm: '🌅 Warm',
      bright: '☀️ Bright',
      flat: '📊 Flat',
      malayalam: '🎬 Malayalam',
      tamil: '🎬 Tamil',
      hindi: '🎬 Hindi',
      english: '🎬 English',
    };
    return presets[preset] || preset;
  };

  return (
    <Card variant="glass">
      <CardHeader className="cursor-pointer select-none" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 border border-primary/20">
              <Activity className="h-5 w-5 text-primary" />
            </div>
            Active Conversions
            {totalActive > 0 && (
              <span className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full animate-pulse">
                <Loader2 className="h-3 w-3 animate-spin" />
                {totalActive} active
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-3">
            <button
              onClick={(e) => {
                e.stopPropagation();
                fetchBackendJobs();
              }}
              className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <span className="text-xs text-slate-500">Updated {lastUpdate.toLocaleTimeString()}</span>
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-slate-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Summary Stats */}
          {hasActivity && (
            <div className="grid grid-cols-3 gap-3 mb-4">
              <StatBox
                value={totalActive}
                label="Active"
                color="primary"
                icon={Activity}
                pulse={totalActive > 0}
              />
              <StatBox value={completedCount} label="Completed" color="success" icon={CheckCircle} />
              <StatBox value={failedCount} label="Failed" color="error" icon={AlertCircle} />
            </div>
          )}

          {/* Active Backend Jobs */}
          {backendJobs.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                Processing
              </h4>
              {backendJobs.map((job) => (
                <div
                  key={job.id}
                  className="p-4 rounded-xl border border-blue-500/30 bg-blue-500/10 transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getJobIcon(job)}
                      <span className="font-semibold text-white">
                        {getJobTypeLabel(job)} #{job.id}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}
                      >
                        {job.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">{getPresetLabel(job.language)}</span>
                      {(job.status === 'running' || job.status === 'pending') && (
                        <button
                          onClick={(e) => cancelJob(job.id, e)}
                          className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/30 text-red-400 hover:text-red-300 transition-colors border border-red-500/30"
                          title="Cancel job"
                        >
                          <Ban className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mb-2">
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span className="truncate max-w-[70%]">
                        {job.current_file || job.input_path || 'Processing...'}
                      </span>
                      <span>{Math.round(job.progress)}%</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <FolderOpen className="h-3 w-3" />
                      {job.processed_files}/{job.total_files || '?'} files
                    </span>
                    {job.started_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Started {formatTime(job.started_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* GPU Conversion Jobs */}
          {gpuJobs.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-400" />
                GPU Conversions
              </h4>
              {gpuJobs.map((job) => (
                <ConversionProgress
                  key={job.jobId}
                  jobId={job.jobId}
                  fileName={job.fileName}
                  onComplete={(data) => {
                    handleJobComplete(data);
                    setGpuJobs((prev) => prev.filter((j) => j.jobId !== job.jobId));
                  }}
                />
              ))}
            </div>
          )}

          {/* Recent Jobs */}
          {recentJobs.length > 0 && totalActive === 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-400" />
                Recent Activity
              </h4>
              <div className="space-y-2">
                {recentJobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/5 hover:border-white/20 transition-all"
                  >
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <div className="flex items-center gap-2">
                        {getJobIcon(job)}
                        <span className="text-sm text-white">{getJobTypeLabel(job)}</span>
                        <span className="text-xs text-slate-500">#{job.id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-slate-500">{getPresetLabel(job.language)}</span>
                      <span className={`px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}>
                        {job.status}
                      </span>
                      {job.duration && <span className="text-slate-500">{formatDuration(job.duration)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {!hasActivity && (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-base-content/5 mb-4">
                <Zap className="h-8 w-8 text-base-content/30" />
              </div>
              <h3 className="text-lg font-semibold text-base-content/70 mb-2">No Active Conversions</h3>
              <p className="text-sm text-base-content/50">Start a conversion to see real-time progress here</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
};

const StatBox: React.FC<StatBoxProps> = ({ value, label, color, icon: Icon, pulse }) => (
  <div
    className={`
    relative p-4 rounded-xl text-center
    bg-${color}/10 border border-${color}/20
    transition-all duration-200 hover:scale-[1.02]
  `}
  >
    {pulse && (
      <span className="absolute top-2 right-2 flex h-2 w-2">
        <span
          className={`animate-ping absolute inline-flex h-full w-full rounded-full bg-${color} opacity-75`}
        />
        <span className={`relative inline-flex rounded-full h-2 w-2 bg-${color}`} />
      </span>
    )}
    <div className={`text-2xl font-bold text-${color}`}>{value}</div>
    <div className="text-xs text-base-content/60 flex items-center justify-center gap-1 mt-1">
      <Icon className="h-3 w-3" />
      {label}
    </div>
  </div>
);

export default ActiveConversions;
