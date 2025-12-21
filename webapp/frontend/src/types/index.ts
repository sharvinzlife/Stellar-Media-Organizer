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

export interface Job {
  id: number;
  job_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  input_path: string;
  output_path?: string;
  filename?: string;
  language?: string;
  volume_boost?: number;
  progress: number;
  current_file?: string;
  total_files?: number;
  processed_files?: number;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  duration?: number;
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
