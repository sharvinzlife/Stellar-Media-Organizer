import React, { useState, useEffect, useRef, ChangeEvent, MouseEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Terminal, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import type { LogEntry } from '../types';

interface JobLogResponse {
  success: boolean;
  logs: Array<{
    message: string;
    level: string;
    timestamp: string;
  }>;
}

interface ActiveJobsResponse {
  success: boolean;
  jobs: Array<{
    id: string;
  }>;
}

// Extend Window interface for global addLog function
declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

const LogViewer: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [autoScroll, setAutoScroll] = useState<boolean>(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (): void => {
    if (autoScroll) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // Poll for active job logs
  useEffect(() => {
    const pollLogs = async (): Promise<void> => {
      try {
        // Get active jobs
        const activeRes = await fetch('/api/v1/jobs/active');
        const activeData: ActiveJobsResponse = await activeRes.json();

        if (activeData.success && activeData.jobs.length > 0) {
          const job = activeData.jobs[0];

          // Get logs for this job
          const logsRes = await fetch(`/api/v1/jobs/${job.id}/logs`);
          const logsData: JobLogResponse = await logsRes.json();

          if (logsData.success && logsData.logs.length > 0) {
            setLogs(
              logsData.logs.map((log, idx) => ({
                id: `${job.id}-${idx}`,
                message: log.message,
                type: log.level as LogEntry['type'],
                timestamp: new Date(log.timestamp).toLocaleTimeString(),
              }))
            );
          }
        }
      } catch (error) {
        console.error('Failed to poll logs:', error);
      }
    };

    const interval = setInterval(pollLogs, 1000);
    pollLogs(); // Initial poll

    return () => clearInterval(interval);
  }, []);

  const addLog = (message: string, type: string = 'info'): void => {
    const timestamp = new Date().toLocaleTimeString();
    const logType = ['info', 'success', 'error', 'warning'].includes(type) 
      ? type as LogEntry['type'] 
      : 'info';
    setLogs((prev) => [...prev, { message, type: logType, timestamp, id: Date.now() }]);
  };

  const clearLogs = (): void => {
    setLogs([]);
  };

  useEffect(() => {
    window.addLog = addLog;
    return () => {
      delete window.addLog;
    };
  }, []);

  const getLogStyles = (type: LogEntry['type']): string => {
    switch (type) {
      case 'success':
        return 'text-success bg-success/10 border-success/20';
      case 'error':
        return 'text-error bg-error/10 border-error/20';
      case 'warning':
        return 'text-warning bg-warning/10 border-warning/20';
      default:
        return 'text-base-content/80 bg-base-content/5 border-base-content/10';
    }
  };

  const handleClearClick = (e: MouseEvent<HTMLButtonElement>): void => {
    e.stopPropagation();
    clearLogs();
  };

  const handleAutoScrollChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setAutoScroll(e.target.checked);
  };

  return (
    <Card variant="glass">
      <CardHeader
        className="cursor-pointer hover:bg-base-content/5 transition-colors rounded-t-2xl"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent/10 border border-accent/20">
              <Terminal className="h-4 w-4 text-accent" />
            </div>
            <span>Activity Logs</span>
            {logs.length > 0 && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-base-content/10 text-base-content/60">
                {logs.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {logs.length > 0 && (
              <button
                onClick={handleClearClick}
                className="p-1.5 rounded-lg text-base-content/40 hover:text-error hover:bg-error/10 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-base-content/40" />
            ) : (
              <ChevronDown className="h-5 w-5 text-base-content/40" />
            )}
          </div>
        </CardTitle>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-0">
          <div className="max-h-80 overflow-y-auto bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-xl p-4 font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                No logs yet. Activity will appear here.
              </div>
            ) : (
              <div className="space-y-2">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className={`p-2.5 rounded-lg border ${getLogStyles(log.type)} transition-all duration-200`}
                  >
                    <span className="text-slate-500 text-xs">[{log.timestamp}]</span>{' '}
                    <span className="text-xs">{log.message}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
          <div className="border-t border-base-content/10 p-3 flex items-center justify-between text-xs bg-base-content/5 rounded-b-2xl">
            <label className="flex items-center gap-2 text-base-content/60 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={handleAutoScrollChange}
                className="rounded accent-primary w-3.5 h-3.5"
              />
              Auto-scroll
            </label>
            <span className="text-base-content/40">{logs.length} entries</span>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default LogViewer;
