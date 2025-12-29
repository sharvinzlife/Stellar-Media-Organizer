import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileVideo,
  Music,
  FolderTree,
  Trash2,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  ChevronDown,
  ChevronUp,
  Download,
  HardDrive,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Job, JobStats } from '../types';

interface JobsResponse {
  success: boolean;
  jobs: Job[];
}

interface StatsResponse {
  success: boolean;
  stats: JobStats;
}

type FilterType = 'all' | 'in_progress' | 'completed' | 'failed';


const JobHistory: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<JobStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [filter, setFilter] = useState<FilterType>('all');
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const fetchJobs = async (showError = false): Promise<void> => {
    try {
      const statusParam = filter !== 'all' ? `?status=${filter}` : '';
      const response = await fetch(`/api/v1/jobs/recent${statusParam}`);
      const data: JobsResponse = await response.json();

      if (data.success) {
        setJobs(data.jobs);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      if (showError) {
        toast.error('Failed to load job history');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchStats = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/jobs/stats');
      const data: StatsResponse = await response.json();

      if (data.success) {
        setStats(data.stats);
      }
    } catch {
      // Silently fail - backend may not be running
    }
  };

  useEffect(() => {
    fetchJobs(true);
    fetchStats();

    const interval = setInterval(() => {
      fetchJobs(false);
      fetchStats();
    }, 2000);

    return () => clearInterval(interval);
  }, [filter]);

  const handleRefresh = (): void => {
    setRefreshing(true);
    fetchJobs(true);
    fetchStats();
  };


  const handleDeleteJob = async (jobId: number): Promise<void> => {
    try {
      const response = await fetch(`/api/v1/jobs/${jobId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('Job deleted');
        fetchJobs();
        fetchStats();
      } else {
        toast.error('Failed to delete job');
      }
    } catch (error) {
      console.error('Failed to delete job:', error);
      toast.error('Failed to delete job');
    }
  };

  const getStatusIcon = (status: Job['status']): React.ReactNode => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'running':
      case 'in_progress':
        return <Loader2 className="w-5 h-5 text-green-400 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const formatDuration = (seconds: number | undefined): string => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatDate = (isoString: string | undefined): string => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const formatSize = (mb: number | undefined): string => {
    if (!mb) return '';
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${mb.toFixed(0)} MB`;
  };


  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-green-500" />
        </CardContent>
      </Card>
    );
  }

  const filterTypes: FilterType[] = ['all', 'in_progress', 'completed', 'failed'];

  return (
    <div className="space-y-4">
      {/* Collapsible Header with Stats Summary */}
      <Card variant="glass">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors rounded-xl"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/20">
              <Activity className="h-5 w-5 text-green-400" />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-white">Job History</h3>
              {stats && (
                <p className="text-sm text-slate-400">
                  {stats.total} jobs • {stats.completed} completed • {stats.success_rate.toFixed(0)}% success
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {stats && (
              <div className="hidden md:flex items-center gap-4 mr-4">
                <span className="flex items-center gap-1 text-sm text-green-400">
                  <CheckCircle2 className="h-4 w-4" />
                  {stats.completed}
                </span>
                <span className="flex items-center gap-1 text-sm text-red-400">
                  <XCircle className="h-4 w-4" />
                  {stats.failed}
                </span>
                <span className="flex items-center gap-1 text-sm text-green-400">
                  <Loader2 className="h-4 w-4" />
                  {stats.in_progress}
                </span>
              </div>
            )}
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-slate-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-slate-400" />
            )}
          </div>
        </button>
      </Card>

      {/* Expanded Content */}
      {isExpanded && (
        <>
          {/* Statistics Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Total Jobs</p>
                      <p className="text-2xl font-bold text-white">{stats.total}</p>
                    </div>
                    <Activity className="w-8 h-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Completed</p>
                      <p className="text-2xl font-bold text-green-400">{stats.completed}</p>
                    </div>
                    <CheckCircle2 className="w-8 h-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Failed</p>
                      <p className="text-2xl font-bold text-red-400">{stats.failed}</p>
                    </div>
                    <XCircle className="w-8 h-8 text-red-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Success Rate</p>
                      <p className="text-2xl font-bold text-white">{stats.success_rate.toFixed(1)}%</p>
                    </div>
                    {stats.success_rate >= 90 ? (
                      <TrendingUp className="w-8 h-8 text-green-500" />
                    ) : (
                      <TrendingDown className="w-8 h-8 text-orange-500" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Job History */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Jobs</CardTitle>
                <div className="flex items-center gap-2">
                  {/* Filter Buttons */}
                  <div className="flex gap-1">
                    {filterTypes.map((filterType) => (
                      <button
                        key={filterType}
                        onClick={() => setFilter(filterType)}
                        className={`px-3 py-1 text-sm rounded transition-colors ${
                          filter === filterType
                            ? 'bg-green-500 text-white'
                            : 'bg-white/10 text-slate-300 hover:bg-white/20'
                        }`}
                      >
                        {filterType.replace('_', ' ')}
                      </button>
                    ))}
                  </div>

                  {/* Refresh Button */}
                  <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="p-2 rounded hover:bg-white/10 disabled:opacity-50 text-slate-300 transition-colors"
                    title="Refresh"
                  >
                    <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              {jobs.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No jobs found</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {jobs.map((job) => (
                    <div
                      key={job.id}
                      className="p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                    >
                      {/* Header Row */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(job.status)}
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white">Job #{job.id}</span>
                              <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                                {job.job_type}
                              </span>
                              {job.language && (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
                                  {job.language}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              {formatDate(job.created_at)} • {formatDuration(job.duration)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {(job.status === 'in_progress' || job.status === 'running') ? (
                            <div className="flex flex-col items-end gap-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-green-400">{job.progress}%</span>
                              </div>
                              {/* Animated Progress Bar with Green Sparkle */}
                              <div className="w-40 h-3 bg-slate-800 rounded-full overflow-hidden relative shadow-inner">
                                <div
                                  className="h-full rounded-full transition-all duration-300 ease-out relative overflow-hidden"
                                  style={{ 
                                    width: `${job.progress}%`,
                                    background: 'linear-gradient(90deg, #059669, #10b981, #34d399, #10b981, #059669)',
                                    backgroundSize: '200% 100%',
                                    animation: 'gradient-flow 2s linear infinite',
                                    boxShadow: '0 0 10px rgba(16, 185, 129, 0.5), inset 0 1px 0 rgba(255,255,255,0.2)'
                                  }}
                                >
                                  {/* Sparkle sweep animation */}
                                  <div 
                                    className="absolute inset-0"
                                    style={{
                                      background: 'linear-gradient(90deg, transparent 0%, transparent 40%, rgba(255,255,255,0.4) 50%, transparent 60%, transparent 100%)',
                                      backgroundSize: '200% 100%',
                                      animation: 'sparkle-sweep 1.5s ease-in-out infinite'
                                    }}
                                  />
                                  {/* Glowing particles */}
                                  <div className="absolute inset-0 overflow-hidden">
                                    <div className="absolute w-1 h-1 bg-white rounded-full opacity-80 animate-ping" style={{ left: '20%', top: '30%' }} />
                                    <div className="absolute w-1 h-1 bg-white rounded-full opacity-60 animate-ping" style={{ left: '60%', top: '50%', animationDelay: '0.3s' }} />
                                    <div className="absolute w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{ left: '80%', top: '40%', animationDelay: '0.6s' }} />
                                  </div>
                                </div>
                                {/* Glow effect */}
                                <div 
                                  className="absolute top-0 left-0 h-full rounded-full pointer-events-none"
                                  style={{ 
                                    width: `${job.progress}%`,
                                    boxShadow: '0 0 15px rgba(16, 185, 129, 0.6), 0 0 30px rgba(16, 185, 129, 0.3)'
                                  }}
                                />
                              </div>
                              {job.current_status && (
                                <span className="text-xs text-green-400 font-medium flex items-center gap-1">
                                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                                  {job.current_status}
                                </span>
                              )}
                              {job.current_file && (
                                <span className="text-xs text-slate-500 truncate max-w-[200px]">{job.current_file}</span>
                              )}
                            </div>
                          ) : job.status !== 'in_progress' && (
                            <button
                              onClick={() => handleDeleteJob(job.id)}
                              className="p-1.5 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                              title="Delete job"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Summary Stats */}
                      {job.summary && (
                        <div className="flex flex-wrap gap-3 mb-3">
                          {job.summary.downloaded > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-green-500/10 px-2 py-1 rounded-lg">
                              <Download className="w-3.5 h-3.5 text-green-400" />
                              <span className="text-slate-400">Downloaded:</span>
                              <span className="text-green-400 font-medium">{job.summary.downloaded}</span>
                            </div>
                          )}
                          {job.summary.renamed > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-blue-500/10 px-2 py-1 rounded-lg">
                              <FileVideo className="w-3.5 h-3.5 text-blue-400" />
                              <span className="text-slate-400">Renamed:</span>
                              <span className="text-blue-400 font-medium">{job.summary.renamed}</span>
                            </div>
                          )}
                          {job.summary.filtered > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-purple-500/10 px-2 py-1 rounded-lg">
                              <Music className="w-3.5 h-3.5 text-purple-400" />
                              <span className="text-slate-400">Audio Filtered:</span>
                              <span className="text-purple-400 font-medium">{job.summary.filtered}</span>
                            </div>
                          )}
                          {job.summary.transferred > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-cyan-500/10 px-2 py-1 rounded-lg">
                              <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
                              <span className="text-slate-400">Transferred:</span>
                              <span className="text-cyan-400 font-medium">{job.summary.transferred}</span>
                            </div>
                          )}
                          {job.summary.total_size_mb > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-amber-500/10 px-2 py-1 rounded-lg">
                              <Zap className="w-3.5 h-3.5 text-amber-400" />
                              <span className="text-slate-400">Total Size:</span>
                              <span className="text-amber-400 font-medium">{formatSize(job.summary.total_size_mb)}</span>
                            </div>
                          )}
                          {job.summary.space_saved_mb && job.summary.space_saved_mb > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-emerald-500/10 px-2 py-1 rounded-lg">
                              <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-slate-400">Space Saved:</span>
                              <span className="text-emerald-400 font-medium">{formatSize(job.summary.space_saved_mb)}</span>
                            </div>
                          )}
                          {job.summary.failed > 0 && (
                            <div className="flex items-center gap-1.5 text-xs bg-red-500/10 px-2 py-1 rounded-lg">
                              <XCircle className="w-3.5 h-3.5 text-red-400" />
                              <span className="text-slate-400">Failed:</span>
                              <span className="text-red-400 font-medium">{job.summary.failed}</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Destination Info */}
                      {job.nas_destination && job.nas_destination.nas_name && (
                        <div className="flex items-center gap-2 mb-3 text-xs">
                          <FolderTree className="w-3.5 h-3.5 text-slate-500" />
                          <span className="text-slate-400">Destination:</span>
                          <span className="text-amber-400 font-medium">
                            {job.nas_destination.nas_name}/{job.detected_category || job.nas_destination.category}
                          </span>
                        </div>
                      )}

                      {/* File Details */}
                      {job.summary?.files && job.summary.files.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                          <div className="text-xs text-slate-500 mb-2 flex items-center gap-2">
                            <FileVideo className="w-3.5 h-3.5" />
                            Processed Files ({job.summary.files.length}):
                          </div>
                          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                            {job.summary.files.map((file: any, idx: number) => (
                              <div key={idx} className="bg-slate-800/70 rounded-lg p-3 border border-slate-700/50">
                                {/* File name row */}
                                <div className="flex items-start gap-2 mb-2">
                                  <FileVideo className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm text-white font-medium truncate" title={file.name || file.renamed || file.original}>
                                      {file.name || file.renamed || file.original}
                                    </div>
                                    {file.original && file.renamed && file.original !== file.renamed && (
                                      <div className="text-xs text-slate-500 truncate mt-0.5" title={file.original}>
                                        Original: {file.original}
                                      </div>
                                    )}
                                  </div>
                                  {file.status === 'transferred' && (
                                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                                  )}
                                </div>
                                
                                {/* File stats row */}
                                <div className="flex flex-wrap items-center gap-2 text-xs">
                                  {file.size_mb > 0 && (
                                    <span className="flex items-center gap-1 bg-slate-700/50 px-2 py-0.5 rounded">
                                      <HardDrive className="w-3 h-3 text-slate-400" />
                                      <span className="text-slate-300">{formatSize(file.size_mb)}</span>
                                    </span>
                                  )}
                                  {file.filtered && (
                                    <span className="flex items-center gap-1 bg-purple-500/20 px-2 py-0.5 rounded text-purple-400">
                                      <Music className="w-3 h-3" />
                                      Audio filtered
                                    </span>
                                  )}
                                  {file.speed_mbps > 0 && (
                                    <span className="flex items-center gap-1 bg-green-500/20 px-2 py-0.5 rounded text-green-400">
                                      <Zap className="w-3 h-3" />
                                      {file.speed_mbps} MB/s
                                    </span>
                                  )}
                                  {file.category && (
                                    <span className="flex items-center gap-1 bg-cyan-500/20 px-2 py-0.5 rounded text-cyan-400">
                                      <FolderTree className="w-3 h-3" />
                                      {file.category}
                                    </span>
                                  )}
                                </div>
                                
                                {/* Destination row */}
                                {file.destination && (
                                  <div className="flex items-center gap-1.5 mt-2 text-xs text-amber-400">
                                    <span className="text-slate-500">→</span>
                                    <span className="truncate" title={file.destination}>
                                      {file.destination}
                                    </span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Error Message */}
                      {job.error_message && (
                        <div className="mt-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                          <div className="text-xs text-red-400">{job.error_message}</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default JobHistory;
