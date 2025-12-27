import axios, { AxiosProgressEvent } from 'axios';
import type { HealthResponse, ProcessResult, UploadResult, Language } from '../types';

// Use environment variable or fallback to relative path (works with Vite proxy)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Export base URL for components that need direct fetch
export const GPU_SERVICE_URL = import.meta.env.VITE_GPU_SERVICE_URL || 'http://localhost:8888';

export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
};

export interface AnalyzeRequest {
  directory_path: string;
}

export const analyzeFiles = async (directoryPath: string) => {
  const response = await api.post('/analyze', { directory_path: directoryPath });
  return response.data;
};

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

export const processFiles = async (data: ProcessRequest): Promise<ProcessResult> => {
  const response = await api.post<ProcessResult>('/process', data);
  return response.data;
};

export const getSupportedLanguages = async (): Promise<{ languages: Language[] }> => {
  const response = await api.get<{ languages: Language[] }>('/languages');
  return response.data;
};

export const getSupportedFormats = async () => {
  const response = await api.get('/formats');
  return response.data;
};

export const uploadFiles = async (
  files: File[],
  onProgress?: (percent: number) => void
): Promise<UploadResult> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post<UploadResult>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export default api;
