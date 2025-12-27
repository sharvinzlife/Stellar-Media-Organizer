import React, { useState, useEffect } from 'react';
import { Sparkles, Wifi, Music, Film, Zap, Star } from 'lucide-react';

const Header: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [currentEmoji, setCurrentEmoji] = useState(0);
  const [glitchActive, setGlitchActive] = useState(false);
  const [intensiveGlitch, setIntensiveGlitch] = useState(false);
  
  const emojis = ['🎬', '🎵', '🎧', '🎥', '🎶', '✨', '🌟', '💫'];
  
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
  
  // Rotate emoji every 2.5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentEmoji((prev) => (prev + 1) % emojis.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  // Random glitch bursts - more frequent
  useEffect(() => {
    const triggerGlitch = () => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 150);
    };
    
    const triggerIntensiveGlitch = () => {
      setIntensiveGlitch(true);
      setTimeout(() => setIntensiveGlitch(false), 300);
    };
    
    const interval = setInterval(() => {
      const rand = Math.random();
      if (rand > 0.85) triggerIntensiveGlitch();
      else if (rand > 0.6) triggerGlitch();
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative container mx-auto px-6 py-4">
        {/* Multiple glitch lines */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/60 to-transparent" style={{ animation: 'header-line-1 3s ease-in-out infinite' }} />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" style={{ animation: 'header-line-2 3s ease-in-out infinite 0.5s' }} />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-pink-500/30 to-transparent" style={{ animation: 'header-line-3 3s ease-in-out infinite 1s' }} />
        </div>
        
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center gap-4 group cursor-pointer">
            {/* Animated logo container */}
            <div className="relative">
              {/* Outer glow pulse */}
              <div className={`absolute -inset-3 bg-gradient-to-r from-purple-500 via-cyan-500 to-pink-500 rounded-2xl blur-xl opacity-30 group-hover:opacity-70 transition-all duration-500 ${intensiveGlitch ? 'animate-pulse' : 'animate-pulse-slow'}`} />
              
              {/* Rotating rings */}
              <div className="absolute -inset-1 rounded-xl border-2 border-purple-500/40 animate-spin-slow opacity-60 group-hover:opacity-100 group-hover:border-purple-400/60" />
              <div className="absolute -inset-2 rounded-xl border border-cyan-500/30 opacity-40 group-hover:opacity-70" style={{ animation: 'spin-slow 15s linear infinite reverse' }} />
              <div className="absolute -inset-0.5 rounded-lg border border-pink-500/20 opacity-30" style={{ animation: 'spin-slow 20s linear infinite' }} />
              
              {/* Main logo */}
              <div className={`relative flex items-center justify-center w-14 h-14 bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 rounded-xl shadow-lg shadow-purple-500/40 group-hover:shadow-purple-500/70 transition-all duration-300 group-hover:scale-110 ${glitchActive ? 'animate-icon-glitch' : ''} ${intensiveGlitch ? 'animate-glitch-burst' : ''}`}>
                <span 
                  className="text-2xl transition-all duration-300 transform group-hover:scale-110"
                  style={{ 
                    animation: 'bounce-subtle 2s ease-in-out infinite',
                  }}
                >
                  {emojis[currentEmoji]}
                </span>
                
                {/* Inner glow */}
                <div className="absolute inset-0 rounded-xl bg-gradient-to-t from-transparent to-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>

            <div className="space-y-1">
              <h1 className="text-xl md:text-2xl font-bold flex items-center gap-3">
                <span className={`glitch-wrapper ${intensiveGlitch ? 'glitch-intensive' : ''}`}>
                  <span className={`glitch-text ${glitchActive ? 'glitch-burst' : ''}`} data-text="Stellar Media Organizer">
                    Stellar Media Organizer
                  </span>
                </span>
                <span className="text-xs px-2.5 py-1 rounded-full bg-gradient-to-r from-purple-500/30 to-pink-500/30 border border-purple-500/40 text-purple-300 font-bold animate-pulse hover:scale-110 hover:border-purple-400/60 transition-all cursor-default shadow-lg shadow-purple-500/20">
                  ⭐ v3.0
                </span>
              </h1>
              <p className="text-xs md:text-sm text-slate-400 flex items-center gap-2 font-medium">
                <Sparkles className={`h-3.5 w-3.5 text-cyan-400 ${glitchActive ? 'animate-spin' : 'animate-pulse'}`} />
                <span className="hidden sm:inline hover:text-purple-300 transition-colors cursor-default group-hover:text-purple-400">🎬 Movies</span>
                <span className="hidden sm:inline text-purple-500/50">•</span>
                <span className="hidden sm:inline hover:text-cyan-300 transition-colors cursor-default group-hover:text-cyan-400">📺 Series</span>
                <span className="hidden sm:inline text-cyan-500/50">•</span>
                <span className="hidden sm:inline hover:text-pink-300 transition-colors cursor-default group-hover:text-pink-400">🎵 Music</span>
                <span className="sm:hidden">Organize with Elegance</span>
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {/* Feature badges with glitch hover */}
            <div className="hidden lg:flex items-center gap-2">
              <div className={`flex items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-bold hover:bg-purple-500/25 hover:border-purple-400/50 hover:scale-110 hover:shadow-lg hover:shadow-purple-500/30 transition-all cursor-default ${glitchActive ? 'translate-x-0.5' : ''}`}>
                <Film className="h-4 w-4" />
                IMDB
              </div>
              <div className={`flex items-center gap-1.5 px-3 py-2 rounded-xl bg-pink-500/10 border border-pink-500/30 text-pink-300 text-xs font-bold hover:bg-pink-500/25 hover:border-pink-400/50 hover:scale-110 hover:shadow-lg hover:shadow-pink-500/30 transition-all cursor-default ${glitchActive ? '-translate-x-0.5' : ''}`}>
                <Music className="h-4 w-4" />
                MusicBrainz
              </div>
              <div className={`flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-bold hover:bg-cyan-500/25 hover:border-cyan-400/50 hover:scale-110 hover:shadow-lg hover:shadow-cyan-500/30 transition-all cursor-default ${glitchActive ? 'translate-y-0.5' : ''}`}>
                <Zap className="h-4 w-4" />
                GPU
              </div>
            </div>
            
            {/* Status Badge */}
            <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/15 border-2 border-emerald-500/40 backdrop-blur-sm hover:bg-emerald-500/25 hover:border-emerald-400/60 hover:scale-105 transition-all duration-300 cursor-default group shadow-lg shadow-emerald-500/20 ${intensiveGlitch ? 'border-emerald-400' : ''}`}>
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-full w-full bg-emerald-400 shadow-lg shadow-emerald-400/50" />
              </span>
              <span className="text-sm font-bold text-emerald-400 flex items-center gap-1.5">
                <Wifi className="h-4 w-4 group-hover:animate-pulse" />
                <span className="hidden sm:inline">Online</span>
              </span>
            </div>
          </div>
        </div>
      </div>
  );
};

export default Header;
