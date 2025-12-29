import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { toast } from 'sonner';
import {
  Music,
  Download,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Disc3,
  Sparkles,
  FolderOpen,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Trash2,
  Ban,
} from 'lucide-react';

interface MusicJob {
  id: number;
  job_type: string;
  status: string;
  input_path: string;
  output_path: string;
  language: string; // preset for music
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

interface JobLog {
  id: number;
  job_id: number;
  timestamp: string;
  level: string;
  message: string;
}

const MusicActivityDashboard: React.FC = () => {
  const [activeJobs, setActiveJobs] = useState<MusicJob[]>([]);
  const [recentJobs, setRecentJobs] = useState<MusicJob[]>([]);
  const [selectedJobLogs, setSelectedJobLogs] = useState<JobLog[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchJobs = useCallback(async () => {
    try {
      // Fetch active jobs
      const activeRes = await fetch('/api/v1/jobs/active');
      const activeData = await activeRes.json();
      
      // Filter for music-related jobs (organize type with music output path)
      const musicActive = (activeData.jobs || []).filter((job: MusicJob) => 
        job.output_path?.includes('Music') || job.language?.includes('surround_7_0')
      );
      setActiveJobs(musicActive);

      // Fetch recent jobs
      const recentRes = await fetch('/api/v1/jobs/recent?limit=10');
      const recentData = await recentRes.json();
      
      // Filter for music jobs
      const musicRecent = (recentData.jobs || []).filter((job: MusicJob) => 
        job.output_path?.includes('Music') || job.language?.includes('surround_7_0')
      );
      setRecentJobs(musicRecent.slice(0, 5));

      setLastUpdate(new Date());

      // Auto-select first active job for logs
      if (musicActive.length > 0 && !selectedJobId) {
        setSelectedJobId(musicActive[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch music jobs:', error);
    }
  }, [selectedJobId]);

  const fetchJobLogs = useCallback(async () => {
    if (!selectedJobId) return;
    
    try {
      const res = await fetch(`/api/v1/jobs/${selectedJobId}/logs`);
      const data = await res.json();
      setSelectedJobLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to fetch job logs:', error);
    }
  }, [selectedJobId]);

  const cancelJob = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        toast.success(`Job #${jobId} cancelled`);
        fetchJobs();
      } else {
        toast.error(data.detail || 'Failed to cancel job');
      }
    } catch (error) {
      toast.error('Failed to cancel job');
    }
  };

  const deleteJob = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        toast.success(`Job #${jobId} deleted`);
        if (selectedJobId === jobId) setSelectedJobId(null);
        fetchJobs();
      } else {
        toast.error(data.detail || 'Failed to delete job');
      }
    } catch (error) {
      toast.error('Failed to delete job');
    }
  };

  const cleanupStaleJobs = async () => {
    try {
      const res = await fetch('/api/v1/jobs/cleanup-stale', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        fetchJobs();
      }
    } catch (error) {
      toast.error('Failed to cleanup stale jobs');
    }
  };

  // Poll every 2 seconds
  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 2000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // Fetch logs when selected job changes
  useEffect(() => {
    fetchJobLogs();
    const interval = setInterval(fetchJobLogs, 2000);
    return () => clearInterval(interval);
  }, [fetchJobLogs]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-400" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-400" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-400" />;
      default:
        return <Activity className="h-4 w-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'completed': return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'failed': return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'pending': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  const getPresetLabel = (preset: string) => {
    const presets: Record<string, string> = {
      surround_7_0: '🔊 7.0 Surround',
    };
    return presets[preset] || preset;
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

  const hasActivity = activeJobs.length > 0 || recentJobs.length > 0;

  return (
    <Card variant="glass">
      <CardHeader 
        className="cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 border border-pink-500/20">
              <Activity className="h-5 w-5 text-pink-400" />
            </div>
            Music Activity
            {activeJobs.length > 0 && (
              <span className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full animate-pulse">
                <Loader2 className="h-3 w-3 animate-spin" />
                {activeJobs.length} active
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
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
          {!hasActivity ? (
            <div className="text-center py-8 text-slate-500">
              <Music className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No music activity yet</p>
              <p className="text-xs mt-1">Start a download or organize task to see activity here</p>
            </div>
          ) : (
            <>
              {/* Active Jobs */}
              {activeJobs.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                    Active Tasks
                  </h4>
                  {activeJobs.map((job) => (
                    <div
                      key={job.id}
                      onClick={() => setSelectedJobId(job.id)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        selectedJobId === job.id
                          ? 'border-pink-500/50 bg-pink-500/10'
                          : 'border-white/10 bg-white/5 hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(job.status)}
                          <span className="font-semibold text-white">Job #{job.id}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}>
                            {job.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-500">
                            {getPresetLabel(job.language)}
                          </span>
                          <button
                            onClick={(e) => cancelJob(job.id, e)}
                            className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/30 text-red-400 hover:text-red-300 transition-colors border border-red-500/30"
                            title="Cancel job"
                          >
                            <Ban className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      
                      {/* Progress bar */}
                      <div className="mb-2">
                        <div className="flex justify-between text-xs text-slate-400 mb-1">
                          <span>{job.current_file || 'Processing...'}</span>
                          <span>{Math.round(job.progress)}%</span>
                        </div>
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-pink-500 to-purple-500 transition-all duration-500"
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Download className="h-3 w-3" />
                          {job.input_path}
                        </span>
                        <span className="flex items-center gap-1">
                          <FolderOpen className="h-3 w-3" />
                          {job.processed_files}/{job.total_files || '?'} files
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Live Logs */}
              {selectedJobId && selectedJobLogs.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-yellow-400" />
                    Live Activity (Job #{selectedJobId})
                  </h4>
                  <div className="bg-black/30 rounded-xl p-3 max-h-48 overflow-y-auto font-mono text-xs space-y-1">
                    {selectedJobLogs.slice(-20).map((log) => (
                      <div
                        key={log.id}
                        className={`flex gap-2 ${
                          log.level === 'error' ? 'text-red-400' :
                          log.level === 'warning' ? 'text-yellow-400' :
                          log.level === 'success' ? 'text-green-400' :
                          'text-slate-400'
                        }`}
                      >
                        <span className="text-slate-600 shrink-0">
                          {formatTime(log.timestamp)}
                        </span>
                        <span>{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Jobs */}
              {recentJobs.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Clock className="h-4 w-4 text-slate-400" />
                      Recent Tasks
                    </h4>
                    <button
                      onClick={cleanupStaleJobs}
                      className="text-xs text-slate-500 hover:text-white flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-white/10 transition-colors"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Cleanup Stale
                    </button>
                  </div>
                  <div className="space-y-2">
                    {recentJobs.map((job) => (
                      <div
                        key={job.id}
                        onClick={() => setSelectedJobId(job.id)}
                        className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                          selectedJobId === job.id
                            ? 'border-pink-500/50 bg-pink-500/10'
                            : 'border-white/10 bg-white/5 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {getStatusIcon(job.status)}
                          <div>
                            <span className="text-sm text-white">Job #{job.id}</span>
                            <span className="text-xs text-slate-500 ml-2">
                              {job.input_path}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-500">
                            {getPresetLabel(job.language)}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}>
                            {job.status}
                          </span>
                          {job.duration && (
                            <span className="text-slate-500">
                              {formatDuration(job.duration)}
                            </span>
                          )}
                          {/* Action buttons */}
                          {(job.status === 'pending' || job.status === 'running') && (
                            <button
                              onClick={(e) => cancelJob(job.id, e)}
                              className="p-1 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                              title="Cancel job"
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          )}
                          {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                            <button
                              onClick={(e) => deleteJob(job.id, e)}
                              className="p-1 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                              title="Delete job"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      )}
    </Card>
  );
};

export default MusicActivityDashboard;
