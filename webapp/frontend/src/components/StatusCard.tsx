import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { CheckCircle, XCircle, AlertCircle, Activity, Server, Cpu, HardDrive, LucideIcon } from 'lucide-react';
import { healthCheck } from '@/lib/api';
import type { HealthResponse } from '../types';

interface StatusItemProps {
  label: string;
  status: boolean | undefined;
  icon: LucideIcon;
  warning?: boolean;
}

interface StatusConfig {
  icon: LucideIcon;
  color: string;
  bg: string;
  text: string;
}

const StatusCard: React.FC = () => {
  const [status, setStatus] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async (): Promise<void> => {
    try {
      const data = await healthCheck();
      setStatus(data);
    } catch {
      setStatus({ status: 'error' } as HealthResponse);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card variant="glass">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-base-300/50 rounded-xl" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-base-300/50 rounded w-3/4" />
                <div className="h-3 bg-base-300/50 rounded w-1/2" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-12 bg-base-300/50 rounded-xl" />
              <div className="h-12 bg-base-300/50 rounded-xl" />
              <div className="h-12 bg-base-300/50 rounded-xl" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="glass">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
            <Activity className="h-5 w-5 text-primary" />
          </div>
          System Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <StatusItem
          label="API Server"
          status={status?.status === 'healthy'}
          icon={Server}
        />
        <StatusItem
          label="MKVToolNix"
          status={status?.mkvtoolnix_available}
          icon={HardDrive}
          warning={!status?.mkvtoolnix_available}
        />
        <StatusItem
          label="FFmpeg"
          status={status?.ffmpeg_available}
          icon={Cpu}
          warning={!status?.ffmpeg_available}
        />

        {status && (
          <div className="mt-4 pt-4 border-t border-base-content/10">
            <div className="flex items-center justify-between text-sm">
              <span className="text-base-content/60">Version</span>
              <span className="font-mono font-semibold text-base-content">{status.version}</span>
            </div>
            <div className="flex items-center gap-2 mt-3 p-3 rounded-xl bg-success/10 border border-success/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
              </span>
              <span className="text-sm font-medium text-success">All systems operational</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const StatusItem: React.FC<StatusItemProps> = ({ label, status, icon: Icon, warning }) => {
  const getStatusConfig = (): StatusConfig => {
    if (status) {
      return {
        icon: CheckCircle,
        color: 'text-success',
        bg: 'bg-success/10 border-success/20',
        text: 'Ready',
      };
    }
    if (warning) {
      return {
        icon: AlertCircle,
        color: 'text-warning',
        bg: 'bg-warning/10 border-warning/20',
        text: 'Optional',
      };
    }
    return {
      icon: XCircle,
      color: 'text-error',
      bg: 'bg-error/10 border-error/20',
      text: 'Missing',
    };
  };

  const config = getStatusConfig();
  const StatusIcon = config.icon;

  return (
    <div className={`flex items-center justify-between p-3 rounded-xl border ${config.bg} transition-all duration-200 hover:scale-[1.02]`}>
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-base-content/60" />
        <span className="text-sm font-medium text-base-content">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <StatusIcon className={`h-4 w-4 ${config.color}`} />
        <span className={`text-xs font-semibold ${config.color}`}>{config.text}</span>
      </div>
    </div>
  );
};

export default StatusCard;
