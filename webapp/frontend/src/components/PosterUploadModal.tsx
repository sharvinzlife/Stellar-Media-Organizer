import React, { useState } from 'react';
import { X, Upload, Link2, Image, Loader2 } from 'lucide-react';
import Button from './ui/Button';
import { toast } from 'sonner';

interface PosterUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  ratingKey: string;
  title: string;
}

const PosterUploadModal: React.FC<PosterUploadModalProps> = ({
  isOpen,
  onClose,
  ratingKey,
  title,
}) => {
  const [posterUrl, setPosterUrl] = useState('');
  const [artUrl, setArtUrl] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadType, setUploadType] = useState<'poster' | 'art'>('poster');

  if (!isOpen) return null;

  const handleUrlUpload = async (type: 'poster' | 'art') => {
    const url = type === 'poster' ? posterUrl : artUrl;
    if (!url) {
      toast.error(`Please enter a ${type} URL`);
      return;
    }

    setUploading(true);
    try {
      const endpoint = type === 'poster' 
        ? '/api/v1/plex/poster/url' 
        : '/api/v1/plex/art/url';
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rating_key: ratingKey,
          [`${type}_url`]: url,
        }),
      });

      const data = await response.json();
      if (data.success) {
        toast.success(`${type === 'poster' ? 'Poster' : 'Background'} uploaded successfully!`);
        if (type === 'poster') setPosterUrl('');
        else setArtUrl('');
      } else {
        toast.error(data.detail || `Failed to upload ${type}`);
      }
    } catch (error) {
      toast.error(`Failed to upload ${type}`);
    } finally {
      setUploading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: 'poster' | 'art') => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const endpoint = type === 'poster'
        ? `/api/v1/plex/poster/upload/${ratingKey}`
        : `/api/v1/plex/art/upload/${ratingKey}`;

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        toast.success(`${type === 'poster' ? 'Poster' : 'Background'} uploaded successfully!`);
      } else {
        toast.error(data.detail || `Failed to upload ${type}`);
      }
    } catch (error) {
      toast.error(`Failed to upload ${type}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-slate-900 rounded-2xl border border-slate-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <Image className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Upload Media Artwork</h3>
              <p className="text-xs text-slate-400 truncate max-w-[250px]">{title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* Type Toggle */}
          <div className="flex items-center gap-2 p-1 bg-slate-800 rounded-xl">
            <button
              onClick={() => setUploadType('poster')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                uploadType === 'poster'
                  ? 'bg-amber-500 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🎬 Poster
            </button>
            <button
              onClick={() => setUploadType('art')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                uploadType === 'art'
                  ? 'bg-purple-500 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🖼️ Background
            </button>
          </div>

          {/* URL Upload */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Link2 className="w-4 h-4 text-cyan-400" />
              Upload from URL
            </label>
            <div className="flex gap-2">
              <input
                type="url"
                value={uploadType === 'poster' ? posterUrl : artUrl}
                onChange={(e) => uploadType === 'poster' ? setPosterUrl(e.target.value) : setArtUrl(e.target.value)}
                placeholder={`Paste ${uploadType} image URL...`}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 text-sm"
              />
              <Button
                onClick={() => handleUrlUpload(uploadType)}
                disabled={uploading}
                className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
              >
                {uploading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="text-xs text-slate-500">OR</span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>

          {/* File Upload */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Upload className="w-4 h-4 text-emerald-400" />
              Upload from File
            </label>
            <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-700 rounded-xl cursor-pointer hover:border-amber-500/50 hover:bg-slate-800/50 transition-all">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFileUpload(e, uploadType)}
                className="hidden"
                disabled={uploading}
              />
              <Image className="w-10 h-10 text-slate-500 mb-2" />
              <p className="text-sm text-slate-400">
                Click to upload or drag and drop
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PNG, JPG, WEBP up to 10MB
              </p>
            </label>
          </div>

          {/* Info */}
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <p className="text-xs text-amber-300">
              💡 For movies without IMDB/TMDB data, you can manually upload cover art and background images.
              The changes will be reflected in Plex immediately.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-slate-700">
          <Button
            onClick={onClose}
            className="bg-slate-700 hover:bg-slate-600"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default PosterUploadModal;
