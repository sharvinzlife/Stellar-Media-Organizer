import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'sonner';
import UniverseBackground from './components/UniverseBackground';
import Header from './components/Header';
import Footer from './components/Footer';
import FileUpload from './components/FileUpload';
import OperationPanel from './components/OperationPanel';
import StatusCard from './components/StatusCard';
import LogViewer from './components/LogViewer';
import ActiveConversions from './components/ActiveConversions';
import JobHistory from './components/JobHistory';
import AllDebridPanel from './components/AllDebridPanel';
import MusicOrganizer from './components/MusicOrganizer';
import MusicDownloadPanel from './components/MusicDownloadPanel';
import MusicActivityDashboard from './components/MusicActivityDashboard';
import NASPanel from './components/NASPanel';
import { Card, CardContent } from './components/ui/Card';
import { FolderTree, Music, Music2, Zap, CheckCircle, XCircle, Film, LucideIcon } from 'lucide-react';
import type { ProcessResult, UploadResult } from './types';

type TabType = 'video' | 'music';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('video');
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null);
  const [showLoader, setShowLoader] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setShowLoader(false), 1600);
    return () => clearTimeout(t);
  }, []);

  const handleUploadComplete = (result: UploadResult) => {
    toast.success(`🎉 Uploaded ${result.files.length} files successfully!`);
  };

  const handleProcessComplete = (result: ProcessResult) => {
    setProcessResult(result);
  };

  return (
    <>
      <UniverseBackground />
      
      <div className="min-h-screen relative flex flex-col">
        {showLoader && <div className="top-loading-bar" />}
        <Toaster
          position="top-right"
          toastOptions={{
            className: 'ultra-glass border border-white/10 text-white',
          }}
        />

        <header className="sticky top-0 z-50 w-full backdrop-blur-2xl bg-slate-900/40 shadow-lg shadow-purple-500/5 border-b border-white/5">
          <Header />
        </header>

        <main className="relative container mx-auto px-4 py-8 max-w-7xl flex-1">
        {/* Hero Section */}
        <div className="mb-10 text-center animate-fade-up">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-white hero-title">
            <span className="hero-title-word">Media</span>{' '}
            <span className="hero-title-word">Organization</span>{' '}
            <span className="hero-title-word hero-gradient-text">Made Simple</span>
          </h2>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto hero-subtitle">
            Organize movies, series & music for Plex/Jellyfin with metadata lookup and audio enhancement
          </p>
        </div>

        {/* Tab Navigation - Bigger & Cooler */}
        <div className="flex justify-center mb-10 animate-fade-up">
          <div className="tab-toggle-container">
            <button
              onClick={() => setActiveTab('video')}
              className={`tab-toggle-btn ${activeTab === 'video' ? 'active video' : ''}`}
            >
              <Film className={`h-6 w-6 tab-toggle-icon ${activeTab === 'video' ? 'text-white' : ''}`} />
              <span>Video</span>
            </button>
            <button
              onClick={() => setActiveTab('music')}
              className={`tab-toggle-btn ${activeTab === 'music' ? 'active music' : ''}`}
            >
              <Music className={`h-6 w-6 tab-toggle-icon ${activeTab === 'music' ? 'text-white' : ''}`} />
              <span>Music</span>
            </button>
          </div>
        </div>

        {/* Video Tab Content */}
        {activeTab === 'video' && (
          <>
            {/* Feature Cards */}
            <div className="grid md:grid-cols-3 gap-6 mb-10 animate-fade-up">
              <FeatureCard
                icon={FolderTree}
                title="Smart Organization"
                description="Automatically detects and organizes movies and TV series with proper naming"
                gradient="from-purple-500 to-indigo-500"
              />
              <FeatureCard
                icon={Music2}
                title="Audio Filtering"
                description="Filter audio tracks by language and boost volume for better experience"
                gradient="from-cyan-500 to-blue-500"
              />
              <FeatureCard
                icon={Zap}
                title="GPU Conversion"
                description="Hardware-accelerated video conversion with HEVC/H.265 encoding"
                gradient="from-pink-500 to-rose-500"
              />
            </div>

            {/* Active Conversions */}
            <div className="mb-8 animate-fade-up">
              <ActiveConversions />
            </div>

            {/* Job History Dashboard */}
            <div className="mb-8 animate-fade-up">
              <JobHistory />
            </div>

            {/* Main Content Grid */}
            <div className="grid lg:grid-cols-3 gap-6 mb-8 animate-fade-up">
              <div className="lg:col-span-2 space-y-6">
                <LogViewer />
                <AllDebridPanel />
                <FileUpload onUploadComplete={handleUploadComplete} />
                <OperationPanel onProcessComplete={handleProcessComplete} />
              </div>
              <div className="space-y-6">
                <NASPanel mediaType="video" />
                <StatusCard />
              </div>
            </div>

            {/* Results Section */}
            {processResult && (
              <div className="mt-8 animate-slide-up">
                <Card variant="glass" className="border-emerald-500/30">
                  <div className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      {processResult.success ? (
                        <div className="p-2 rounded-xl bg-emerald-500/10">
                          <CheckCircle className="h-5 w-5 text-emerald-400" />
                        </div>
                      ) : (
                        <div className="p-2 rounded-xl bg-red-500/10">
                          <XCircle className="h-5 w-5 text-red-400" />
                        </div>
                      )}
                      <div>
                        <h3 className="text-xl font-bold text-white">Processing Complete</h3>
                        <p className="text-sm text-slate-400">{processResult.message}</p>
                      </div>
                    </div>

                    {processResult.total_files !== undefined && (
                      <div className="grid grid-cols-3 gap-4 mb-4">
                        <StatBox label="Total Files" value={processResult.total_files} color="purple" />
                        <StatBox label="Successful" value={processResult.successful || 0} color="emerald" />
                        <StatBox
                          label="Space Saved"
                          value={`${processResult.compression_ratio?.toFixed(1) || 0}%`}
                          color="cyan"
                        />
                      </div>
                    )}

                    {processResult.processed_files && processResult.processed_files.length > 0 && (
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                          <FolderTree className="h-4 w-4 text-purple-400" />
                          Processed Files
                        </h4>
                        <ul className="space-y-2 max-h-48 overflow-y-auto">
                          {processResult.processed_files.map((file, index) => (
                            <li
                              key={index}
                              className="flex items-center gap-2 text-sm p-2 rounded-lg bg-white/5"
                            >
                              <CheckCircle className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                              <span className="text-slate-400 truncate flex-1">
                                {file.original_name}
                              </span>
                              {file.new_name && (
                                <>
                                  <span className="text-slate-600">→</span>
                                  <span className="font-medium text-purple-400 truncate">
                                    {file.new_name}
                                  </span>
                                </>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {processResult.errors && processResult.errors.length > 0 && (
                      <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 mt-4">
                        <h4 className="font-semibold text-red-400 mb-3">Errors</h4>
                        <ul className="space-y-2">
                          {processResult.errors.map((error, index) => (
                            <li key={index} className="flex items-center gap-2 text-sm text-red-400">
                              <XCircle className="h-4 w-4 flex-shrink-0" />
                              {error}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            )}
          </>
        )}

        {/* Music Tab Content */}
        {activeTab === 'music' && (
          <div className="animate-fade-up space-y-6">
            {/* Activity Dashboard */}
            <MusicActivityDashboard />
            
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <MusicDownloadPanel />
                <MusicOrganizer />
              </div>
              <div className="space-y-6">
                <NASPanel mediaType="audio" />
                <StatusCard />
                <LogViewer />
              </div>
            </div>
          </div>
        )}
      </main>
      
      {/* Footer */}
      <Footer />
    </div>
    </>
  );
};

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  gradient: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon: Icon, title, description, gradient }) => (
  <Card variant="glass" className="group cursor-default">
    <CardContent className="p-6">
      <div className="flex items-start gap-4">
        <div
          className={`p-3 rounded-xl bg-gradient-to-br ${gradient} shadow-lg group-hover:scale-110 transition-transform duration-300`}
        >
          <Icon className="h-6 w-6 text-white" />
        </div>
        <div>
          <h3 className="font-bold text-white mb-1 group-hover:text-purple-400 transition-colors">
            {title}
          </h3>
          <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
        </div>
      </div>
    </CardContent>
  </Card>
);

interface StatBoxProps {
  label: string;
  value: number | string;
  color: string;
}

const StatBox: React.FC<StatBoxProps> = ({ label, value, color }) => (
  <div className="text-center p-4 rounded-xl bg-white/5 border border-white/10">
    <div className={`text-2xl font-bold text-${color}-400`}>{value}</div>
    <div className="text-xs text-slate-500 mt-1">{label}</div>
  </div>
);

export default App;
