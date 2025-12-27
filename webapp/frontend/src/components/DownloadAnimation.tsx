import React from 'react';

interface DownloadAnimationProps {
  isActive?: boolean;
  className?: string;
  variant?: 'bar' | 'overlay' | 'inline';
}

const DownloadAnimation: React.FC<DownloadAnimationProps> = ({ 
  isActive = true, 
  className = '',
  variant = 'bar'
}) => {
  if (!isActive) return null;

  if (variant === 'bar') {
    return (
      <div className={`relative overflow-hidden ${className}`}>
        {/* Main glitch bar */}
        <div className="glitch-bar h-1 rounded-full" />
        
        {/* Sparkle overlay */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute w-1 h-1 bg-emerald-400 rounded-full animate-ping" style={{ left: '20%', top: '50%' }} />
          <div className="absolute w-1 h-1 bg-emerald-300 rounded-full animate-ping" style={{ left: '50%', top: '50%', animationDelay: '0.3s' }} />
          <div className="absolute w-1 h-1 bg-emerald-400 rounded-full animate-ping" style={{ left: '80%', top: '50%', animationDelay: '0.6s' }} />
        </div>
      </div>
    );
  }

  if (variant === 'overlay') {
    return (
      <div className={`download-animation absolute inset-0 pointer-events-none ${className}`}>
        {/* Green sweep effect handled by CSS */}
      </div>
    );
  }

  // Inline variant - small indicator
  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <div className="relative flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" style={{ animationDelay: '0.2s' }} />
        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" style={{ animationDelay: '0.4s' }} />
      </div>
      <span className="text-emerald-400 text-sm font-medium animate-pulse">Downloading...</span>
    </div>
  );
};

// Progress bar with glitch effect
interface GlitchProgressBarProps {
  progress: number;
  className?: string;
  showPercentage?: boolean;
}

export const GlitchProgressBar: React.FC<GlitchProgressBarProps> = ({ 
  progress, 
  className = '',
  showPercentage = true 
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
        {/* Progress fill */}
        <div 
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-600 via-emerald-400 to-emerald-500 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
        
        {/* Glitch overlay on progress */}
        <div 
          className="absolute inset-y-0 left-0 overflow-hidden rounded-full"
          style={{ width: `${progress}%` }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
        </div>
        
        {/* Sparkle at progress edge */}
        {progress > 0 && progress < 100 && (
          <div 
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-emerald-300 rounded-full blur-sm animate-pulse"
            style={{ left: `calc(${progress}% - 6px)` }}
          />
        )}
      </div>
      
      {showPercentage && (
        <div className="flex justify-between text-xs">
          <span className="text-emerald-400 font-medium">{progress}%</span>
          <span className="text-slate-500">
            {progress < 100 ? 'Processing...' : 'Complete!'}
          </span>
        </div>
      )}
    </div>
  );
};

// Sparkling download button effect
interface SparkleButtonProps {
  children: React.ReactNode;
  isLoading?: boolean;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

export const SparkleButton: React.FC<SparkleButtonProps> = ({
  children,
  isLoading = false,
  onClick,
  className = '',
  disabled = false
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`
        relative overflow-hidden px-6 py-3 rounded-xl font-semibold
        bg-gradient-to-r from-emerald-600 to-emerald-500
        hover:from-emerald-500 hover:to-emerald-400
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-all duration-300 text-white
        ${className}
      `}
    >
      {/* Sparkle effect when loading */}
      {isLoading && (
        <>
          <div className="absolute inset-0 download-animation" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        </>
      )}
      
      {/* Button content */}
      <span className={`relative z-10 flex items-center justify-center gap-2 ${isLoading ? 'opacity-80' : ''}`}>
        {children}
      </span>
      
      {/* Hover glow */}
      <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-300">
        <div className="absolute inset-0 bg-emerald-400/20 blur-xl" />
      </div>
    </button>
  );
};

export default DownloadAnimation;
