// API Response Types
export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  gpu_available: boolean;
  mkvtoolnix_available: boolean;
  ffmpeg_available: boolean;
}

export interface ProcessedFile {
  original_name: string;
  new_name: string;
}

export interface ProcessResult {
  success: boolean;
  message: string;
  total_files?: number;
  successful?: number;
  failed?: number;
  compression_ratio?: number;
  processed_files?: ProcessedFile[];
  errors?: string[];
}

export interface UploadResult {
  success: boolean;
  message: string;
  files: string[];
  upload_dir: string;
}

export interface JobFileSummary {
  name?: string;
  original?: string;
  renamed?: string;
  destination?: string;
  size_mb?: number;
  size_before_mb?: number;
  size_after_mb?: number;
  space_saved_mb?: number;
  speed_mbps?: number;
  category?: string;
  status?: string;
  filtered?: boolean;
}

export interface JobSummary {
  total_files: number;
  downloaded: number;
  renamed: number;
  transferred: number;
  failed: number;
  filtered: number;
  total_size_mb: number;
  space_saved_mb?: number;
  files: JobFileSummary[];
}

export interface Job {
  id: number;
  job_type: string;
  status: 'pending' | 'running' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  input_path: string;
  output_path?: string;
  filename?: string;
  language?: string;
  volume_boost?: number;
  progress: number;
  current_file?: string;
  current_status?: string;
  total_files?: number;
  processed_files?: number;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  // Detailed tracking
  summary?: JobSummary;
  detected_category?: string;
  nas_destination?: {
    nas_name: string;
    category: string;
  };
}

export interface JobStats {
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
  success_rate: number;
}

export interface LogEntry {
  id: string | number;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
  timestamp: string;
}

export interface Language {
  value: string;
  label: string;
  emoji: string;
}

export interface NASDestination {
  nas_name: string;
  category: string;
}

export interface ProcessRequest {
  operation: string;
  directory_path: string;
  output_path?: string;
  target_language?: string;
  volume_boost?: number;
  nas_destination?: NASDestination;
}

export interface ConversionJob {
  jobId: string;
  fileName: string;
  status?: string;
  progress?: number;
  eta?: string;
  compression?: number;
}

// Component Props Types
export interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'neon';
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}
