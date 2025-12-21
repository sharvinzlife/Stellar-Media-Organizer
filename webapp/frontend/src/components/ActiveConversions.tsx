import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import ConversionProgress from './ConversionProgress';
import { Activity, CheckCircle, AlertCircle, Zap, LucideIcon } from 'lucide-react';
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

interface StatBoxProps {
  value: number;
  label: string;
  color: string;
  icon: LucideIcon;
  pulse?: boolean;
}


const ActiveConversions: React.FC = () => {
  const [activeJobs, setActiveJobs] = useState<ConversionJob[]>([]);
  const [completedCount, setCompletedCount] = useState<number>(0);
  const [failedCount, setFailedCount] = useState<number>(0);

  useEffect(() => {
    checkActiveJobs();
    const interval = setInterval(checkActiveJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkActiveJobs = async (): Promise<void> => {
    try {
      const response = await fetch(`${GPU_SERVICE_URL}/health`);
      const data: HealthResponse = await response.json();
      if (data.active_jobs > activeJobs.length) {
        console.log(`Active jobs: ${data.active_jobs}`);
      }
    } catch {
      // GPU service may not be running
    }
  };

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
      setActiveJobs((prev) => [...prev, { jobId, fileName }]);
    };

    window.addEventListener('conversionStart', handleConversionStart);
    return () => window.removeEventListener('conversionStart', handleConversionStart);
  }, []);

  const hasActivity = activeJobs.length > 0 || completedCount > 0 || failedCount > 0;


  return (
    <div className="space-y-4">
      {/* Summary Card */}
      {hasActivity && (
        <Card variant="glass">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 border border-primary/20">
                <Activity className="h-4 w-4 text-primary" />
              </div>
              Conversion Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              <StatBox
                value={activeJobs.length}
                label="Active"
                color="primary"
                icon={Activity}
                pulse={activeJobs.length > 0}
              />
              <StatBox
                value={completedCount}
                label="Completed"
                color="success"
                icon={CheckCircle}
              />
              <StatBox value={failedCount} label="Failed" color="error" icon={AlertCircle} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Jobs */}
      {activeJobs.length > 0 ? (
        <div className="space-y-4">
          {activeJobs.map((job) => (
            <ConversionProgress
              key={job.jobId}
              jobId={job.jobId}
              fileName={job.fileName}
              onComplete={(data) => {
                handleJobComplete(data);
                setActiveJobs((prev) => prev.filter((j) => j.jobId !== job.jobId));
              }}
            />
          ))}
        </div>
      ) : (
        <Card variant="default" className="border-dashed border-2 border-base-content/20">
          <CardContent className="p-10 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-base-content/5 mb-4">
              <Zap className="h-8 w-8 text-base-content/30" />
            </div>
            <h3 className="text-lg font-semibold text-base-content/70 mb-2">
              No Active Conversions
            </h3>
            <p className="text-sm text-base-content/50">
              Start a conversion to see real-time progress here
            </p>
          </CardContent>
        </Card>
      )}
    </div>
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