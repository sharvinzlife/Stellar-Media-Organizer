import React, { useState, useEffect } from 'react';
import { Sparkles, Wifi, Music, Film, Zap, Star } from 'lucide-react';

const Header: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [currentEmoji, setCurrentEmoji] = useState(0);
  
  const emojis = ['🎬', '🎵', '🎧', '🎥', '🎶', '✨'];
  
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
  
  // Rotate emoji every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentEmoji((prev) => (prev + 1) % emojis.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative container mx-auto px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center gap-4 group">
            {/* Animated logo container */}
            <div className="relative">
              {/* Glow effect */}
              <div className="absolute -inset-2 bg-gradient-to-r from-purple-500 via-cyan-500 to-pink-500 rounded-2xl blur-lg opacity-40 group-hover:opacity-70 transition-all duration-500 animate-pulse-slow" />
              
              {/* Rotating ring */}
              <div className="absolute -inset-1 rounded-xl border border-purple-500/30 animate-spin-slow opacity-50" />
              
              {/* Main logo */}
              <div className="relative flex items-center justify-center w-12 h-12 bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 rounded-xl shadow-lg shadow-purple-500/30 group-hover:shadow-purple-500/50 transition-all duration-300 group-hover:scale-110">
                <span 
                  className="text-2xl transition-all duration-500 transform"
                  style={{ 
                    animation: 'bounce-subtle 2s ease-in-out infinite',
                  }}
                >
                  {emojis[currentEmoji]}
                </span>
              </div>
            </div>

            <div className="space-y-0.5">
              <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
                <span className="text-gradient-animated">Stellar</span>
                <span className="text-white">Media Organizer</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 text-purple-300 font-medium animate-pulse">
                  ⭐ v2.0
                </span>
              </h1>
              <p className="text-xs md:text-sm text-slate-400 flex items-center gap-2 font-medium">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400 animate-pulse" />
                <span className="hidden sm:inline">🎬 Movies</span>
                <span className="hidden sm:inline text-slate-600">•</span>
                <span className="hidden sm:inline">📺 Series</span>
                <span className="hidden sm:inline text-slate-600">•</span>
                <span className="hidden sm:inline">🎵 Music</span>
                <span className="sm:hidden">Organize with Elegance</span>
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {/* Feature badges */}
            <div className="hidden lg:flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium">
                <Film className="h-3.5 w-3.5" />
                IMDB
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-pink-500/10 border border-pink-500/20 text-pink-300 text-xs font-medium">
                <Music className="h-3.5 w-3.5" />
                MusicBrainz
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-medium">
                <Zap className="h-3.5 w-3.5" />
                GPU
              </div>
            </div>
            
            {/* Status Badge */}
            <div className="flex items-center gap-2 px-3 md:px-4 py-1.5 md:py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 backdrop-blur-sm hover:bg-emerald-500/20 transition-all duration-300 cursor-default group">
              <span className="relative flex h-2 w-2 md:h-2.5 md:w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-full w-full bg-emerald-400" />
              </span>
              <span className="text-xs md:text-sm font-semibold text-emerald-400 flex items-center gap-1.5">
                <Wifi className="h-3 w-3 md:h-3.5 md:w-3.5 group-hover:animate-pulse" />
                <span className="hidden sm:inline">Online</span>
              </span>
            </div>
          </div>
        </div>
      </div>
  );
};

export default Header;
