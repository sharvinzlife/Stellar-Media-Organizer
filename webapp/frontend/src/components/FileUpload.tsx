import React, { useCallback, useState, MouseEvent } from 'react';
import { useDropzone, FileRejection, DropEvent } from 'react-dropzone';
import { Upload, File, X, CheckCircle, CloudUpload } from 'lucide-react';
import { Card, CardContent } from './ui/Card';
import Button from './ui/Button';
import { uploadFiles } from '@/lib/api';
import { toast } from 'sonner';
import type { UploadResult } from '../types';

interface FileUploadProps {
  onUploadComplete?: (result: UploadResult) => void;
}

// Extend Window interface for global addLog function
declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}

// Extend File interface for path property (available in Electron/native drag)
interface FileWithPath extends File {
  path?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadComplete }) => {
  const [files, setFiles] = useState<FileWithPath[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const onDrop = useCallback((acceptedFiles: FileWithPath[], _rejectedFiles: FileRejection[], event: DropEvent) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);

    // Try to get path from different sources
    let dirPath: string | null = null;

    // Method 1: Check file.path (works with Electron/native drag)
    if (acceptedFiles.length > 0 && acceptedFiles[0].path) {
      const filePath = acceptedFiles[0].path;
      if (filePath.includes('/')) {
        dirPath = filePath.substring(0, filePath.lastIndexOf('/'));
      }
    }

    // Method 2: Check webkitRelativePath (works with directory selection)
    if (!dirPath && acceptedFiles.length > 0 && acceptedFiles[0].webkitRelativePath) {
      const relativePath = acceptedFiles[0].webkitRelativePath;
      if (relativePath.includes('/')) {
        dirPath = relativePath.substring(0, relativePath.lastIndexOf('/'));
      }
    }

    // Method 3: Try to get from dataTransfer (native drag from Finder)
    if (!dirPath && event && 'dataTransfer' in event && event.dataTransfer?.items) {
      const items = event.dataTransfer.items;
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.getAsFile) {
          const file = item.getAsFile() as FileWithPath;
          if (file?.path) {
            dirPath = file.path.substring(0, file.path.lastIndexOf('/'));
            break;
          }
        }
      }
    }

    if (dirPath && dirPath.length > 0) {
      const customEvent = new CustomEvent('autoFillPath', { detail: { path: dirPath } });
      window.dispatchEvent(customEvent);
      toast.success(`📁 Auto-filled path: ${dirPath}`);
    } else {
      // Show hint that path couldn't be detected
      toast.info('💡 Drag files from Finder to auto-fill path, or enter it manually');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ['.mkv', '.mp4', '.avi'] },
    noClick: false,
    noKeyboard: false,
  });

  const removeFile = (index: number): void => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async (): Promise<void> => {
    if (files.length === 0) return;

    setUploading(true);
    window.addLog?.(`Uploading ${files.length} file(s)...`, 'info');
    try {
      const result = await uploadFiles(files, setUploadProgress);
      toast.success(`✅ Uploaded ${result.files.length} files successfully!`);
      window.addLog?.(`✅ Uploaded ${result.files.length} files successfully`, 'success');

      // Auto-fill source path with the upload directory
      if (result.upload_dir) {
        const event = new CustomEvent('autoFillPath', { detail: { path: result.upload_dir } });
        window.dispatchEvent(event);
        toast.info(`📁 Source path set to: ${result.upload_dir}`);
      }

      onUploadComplete?.(result);
      setFiles([]);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error(`❌ Upload failed: ${errorMessage}`);
      window.addLog?.(`❌ Upload failed: ${errorMessage}`, 'error');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleRemoveClick = (e: MouseEvent<HTMLButtonElement>, index: number): void => {
    e.stopPropagation();
    removeFile(index);
  };

  return (
    <Card variant="glass">
      <CardContent className="p-6">
        <div
          {...getRootProps()}
          className={`
            relative rounded-2xl p-10 text-center cursor-pointer
            border-2 border-dashed transition-all duration-300
            ${
              isDragActive
                ? 'border-primary bg-primary/10 scale-[1.02]'
                : 'border-base-content/20 hover:border-primary/50 hover:bg-primary/5'
            }
          `}
        >
          <input {...getInputProps()} />

          {isDragActive && (
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 animate-pulse" />
          )}

          <div className="relative z-10">
            <div
              className={`
                inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4
                transition-all duration-300
                ${isDragActive ? 'bg-primary/20 scale-110' : 'bg-base-content/5'}
              `}
            >
              <CloudUpload
                className={`h-8 w-8 transition-all duration-300 ${
                  isDragActive ? 'text-primary animate-bounce' : 'text-base-content/40'
                }`}
              />
            </div>

            <p className="text-lg font-semibold text-base-content mb-1">
              {isDragActive ? 'Drop files here!' : 'Drag & drop media files'}
            </p>
            <p className="text-sm text-base-content/50">
              Drag from Finder to auto-fill path • Supports MKV, MP4, AVI
            </p>
          </div>
        </div>

        {files.length > 0 && (
          <div className="mt-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-base-content flex items-center gap-2">
                <File className="h-4 w-4 text-primary" />
                Selected Files
              </h4>
              <span className="text-sm text-base-content/60 font-medium">
                {files.length} file{files.length !== 1 ? 's' : ''}
              </span>
            </div>

            <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="group flex items-center justify-between p-3 rounded-xl bg-base-content/5 border border-base-content/10 hover:border-primary/30 transition-all duration-200"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <File className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-base-content truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-base-content/50">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleRemoveClick(e, index)}
                    className="p-1.5 rounded-lg text-base-content/40 hover:text-error hover:bg-error/10 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <Button
              onClick={handleUpload}
              disabled={uploading}
              variant="secondary"
              size="lg"
              className="w-full"
            >
              {uploading ? (
                <>
                  <Upload className="h-5 w-5 animate-pulse" />
                  Uploading... {uploadProgress}%
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  Upload {files.length} file{files.length !== 1 ? 's' : ''}
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default FileUpload;
