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
    fetchJobs(true); // Show error on initial load only
    fetchStats();

    const interval = setInterval(() => {
      fetchJobs(false); // Silent polling
      fetchStats();
    }, 2000);

    return () => clearInterval(interval);
  }, [filter]);

  const handleRefresh = (): void => {
    setRefreshing(true);
    fetchJobs(true); // Show error on manual refresh
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
      case 'in_progress':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getJobTypeIcon = (jobType: string): React.ReactNode => {
    switch (jobType) {
      case 'convert':
        return <FileVideo className="w-4 h-4" />;
      case 'filter_audio':
        return <Music className="w-4 h-4" />;
      case 'organize':
        return <FolderTree className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
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


  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
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
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/20">
              <Activity className="h-5 w-5 text-blue-400" />
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
                <span className="flex items-center gap-1 text-sm text-blue-400">
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
                    <Activity className="w-8 h-8 text-blue-500" />
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

          {/* Job History Table */}
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
                            ? 'bg-primary text-white'
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
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left p-2 text-slate-300">Status</th>
                        <th className="text-left p-2 text-slate-300">Type</th>
                        <th className="text-left p-2 text-slate-300">File/Path</th>
                        <th className="text-left p-2 text-slate-300">Progress</th>
                        <th className="text-left p-2 text-slate-300">Duration</th>
                        <th className="text-left p-2 text-slate-300">Created</th>
                        <th className="text-left p-2 text-slate-300">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobs.map((job) => (
                        <tr key={job.id} className="border-b border-white/10 hover:bg-white/5 transition-colors">
                          <td className="p-2">
                            <div className="flex items-center gap-2">
                              {getStatusIcon(job.status)}
                              <span className="text-sm capitalize text-slate-300">{job.status.replace('_', ' ')}</span>
                            </div>
                          </td>
                          <td className="p-2">
                            <div className="flex items-center gap-2">
                              {getJobTypeIcon(job.job_type)}
                              <span className="text-sm capitalize text-slate-300">{job.job_type.replace('_', ' ')}</span>
                            </div>
                          </td>
                          <td className="p-2">
                            <div className="max-w-xs truncate text-sm text-slate-300" title={job.input_path}>
                              {job.filename || job.input_path}
                            </div>
                            {job.language && (
                              <div className="text-xs text-slate-500">Lang: {job.language}</div>
                            )}
                          </td>
                          <td className="p-2">
                            {job.status === 'in_progress' ? (
                              <div>
                                <div className="text-sm font-medium text-slate-300">{job.progress.toFixed(0)}%</div>
                                <div className="w-32 h-2 bg-white/10 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300"
                                    style={{ width: `${job.progress}%` }}
                                  />
                                </div>
                              </div>
                            ) : (
                              <span className="text-sm text-slate-400">
                                {job.processed_files || 0}/{job.total_files || '?'} files
                              </span>
                            )}
                          </td>
                          <td className="p-2 text-sm text-slate-400">{formatDuration(job.duration)}</td>
                          <td className="p-2 text-sm text-slate-400">{formatDate(job.created_at)}</td>
                          <td className="p-2">
                            {job.status !== 'in_progress' && (
                              <button
                                onClick={() => handleDeleteJob(job.id)}
                                className="p-1 text-red-400 hover:bg-red-500/20 rounded transition-colors"
                                title="Delete job"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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