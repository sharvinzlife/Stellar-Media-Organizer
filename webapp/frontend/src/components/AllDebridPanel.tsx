import React, { useState, useEffect, ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import Button from './ui/Button';
import { Cloud, Download, Loader2, Link2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

interface AllDebridStatusResponse {
  configured: boolean;
}

interface AllDebridDownloadResponse {
  success: boolean;
  message?: string;
  detail?: string;
}

// Extend Window interface for global addLog function
declare global {
  interface Window {
    addLog?: (message: string, type?: string) => void;
  }
}


const AllDebridPanel: React.FC = () => {
  const [links, setLinks] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [configured, setConfigured] = useState<boolean>(false);
  const [language, setLanguage] = useState<string>('malayalam');

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/alldebrid/status');
      const data: AllDebridStatusResponse = await response.json();
      setConfigured(data.configured);
    } catch (error) {
      console.error('Failed to check AllDebrid status:', error);
    }
  };

  const parseLinks = (text: string): string[] => {
    const pattern = /https:\/\/alldebrid\.com\/f\/[A-Za-z0-9_-]+/g;
    const matches = text.match(pattern) || [];
    return [...new Set(matches)];
  };

  const handleDownload = async (): Promise<void> => {
    const parsedLinks = parseLinks(links);

    if (parsedLinks.length === 0) {
      toast.error('No valid AllDebrid links found');
      return;
    }

    setLoading(true);
    window.addLog?.(`Starting AllDebrid download of ${parsedLinks.length} links...`, 'info');

    try {
      const response = await fetch('/api/v1/alldebrid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          links: parsedLinks,
          language: language,
          download_only: false,
        }),
      });

      const data: AllDebridDownloadResponse = await response.json();

      if (data.success) {
        toast.success(data.message || 'Download started');
        window.addLog?.(`✅ ${data.message}`, 'success');
        setLinks('');
      } else {
        toast.error(data.detail || 'Download failed');
        window.addLog?.(`❌ ${data.detail}`, 'error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to start download');
      window.addLog?.(`❌ Error: ${errorMessage}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const linkCount = parseLinks(links).length;


  if (!configured) {
    return (
      <Card variant="glass" className="border-warning/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-warning/20 border border-warning/20">
              <Cloud className="h-5 w-5 text-warning" />
            </div>
            AllDebrid Downloads
          </CardTitle>
          <CardDescription>
            ⚠️ AllDebrid API key not configured. Set ALLDEBRID_API_KEY environment variable.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card variant="glass">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/20">
            <Cloud className="h-5 w-5 text-blue-500" />
          </div>
          AllDebrid Downloads
        </CardTitle>
        <CardDescription>
          Paste AllDebrid links to download, organize, and filter audio automatically
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            AllDebrid Links
          </label>
          <textarea
            value={links}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setLinks(e.target.value)}
            placeholder="Paste AllDebrid links here (one per line or all together)..."
            className="w-full h-32 px-4 py-3 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
          />
          {linkCount > 0 && (
            <p className="text-xs text-success flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              Found {linkCount} valid link{linkCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>


        <div className="space-y-2">
          <label className="text-sm font-semibold text-base-content">Audio Language</label>
          <select
            value={language}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)}
            className="w-full h-11 px-4 rounded-xl border border-base-content/20 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm text-base-content font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="malayalam">🇮🇳 Malayalam</option>
            <option value="tamil">🇮🇳 Tamil</option>
            <option value="telugu">🇮🇳 Telugu</option>
            <option value="hindi">🇮🇳 Hindi</option>
            <option value="english">🇬🇧 English</option>
            <option value="kannada">🇮🇳 Kannada</option>
          </select>
        </div>

        <Button
          onClick={handleDownload}
          disabled={loading || linkCount === 0}
          size="lg"
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              <Download className="h-5 w-5" />
              Download & Organize ({linkCount} link{linkCount !== 1 ? 's' : ''})
            </>
          )}
        </Button>

        <p className="text-xs text-base-content/50 text-center">
          Files will be downloaded with aria2c (16 connections), organized, and filtered to keep only {language} audio + English subtitles
        </p>
      </CardContent>
    </Card>
  );
};

export default AllDebridPanel;