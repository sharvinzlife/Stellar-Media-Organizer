import React, { useState, useEffect } from 'react';
import { Github, Instagram, Twitter, Facebook, Heart, Sparkles, Code2, Zap, Star } from 'lucide-react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const [glitchText, setGlitchText] = useState('STELLAR MEDIA');
  const [screenGlitch, setScreenGlitch] = useState(false);
  const [intensiveGlitch, setIntensiveGlitch] = useState(false);

  // Random glitch effects on the TV screen
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      const rand = Math.random();
      if (rand > 0.85) {
        setIntensiveGlitch(true);
        setTimeout(() => setIntensiveGlitch(false), 200);
      } else if (rand > 0.6) {
        setScreenGlitch(true);
        setTimeout(() => setScreenGlitch(false), 150);
      }
    }, 1500);

    const textInterval = setInterval(() => {
      const texts = ['STELLAR MEDIA', 'ORGANIZER PRO', '⭐ v3.0 ⭐', 'PLEX READY', 'JELLYFIN ✓', '📺 MEDIA TV'];
      setGlitchText(texts[Math.floor(Math.random() * texts.length)]);
    }, 2500);

    return () => {
      clearInterval(glitchInterval);
      clearInterval(textInterval);
    };
  }, []);

  const socialLinks = [
    { name: 'GitHub', icon: Github, url: 'https://github.com/sharvinzlife', className: 'github' },
    { name: 'Instagram', icon: Instagram, url: 'https://instagram.com/sharvinzlife', className: 'instagram' },
    { name: 'X', icon: Twitter, url: 'https://x.com/sharvinzlife', className: 'twitter' },
    { name: 'Facebook', icon: Facebook, url: 'https://facebook.com/sharvinzlife', className: 'facebook' },
  ];

  return (
    <footer className="footer-glitch relative mt-20">
      {/* Multiple glitch lines at top */}
      <div className="absolute top-0 left-0 right-0 h-[3px] overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500 to-transparent animate-pulse" />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" style={{ animationDelay: '0.5s' }} />
      </div>
      
      <div className="container mx-auto px-6 pt-16 pb-8">
        {/* Retro TV Section */}
        <div className="flex justify-center mb-16">
          <div className="retro-tv-container group">
            {/* Antennas - Simple metal rods without balls */}
            <div className="relative flex justify-center mb-0">
              {/* Left Antenna */}
              <div className="absolute -top-20 left-1/2 -translate-x-16">
                <div 
                  className="w-1.5 h-24 bg-gradient-to-b from-slate-300 via-slate-400 to-slate-500 rounded-full shadow-lg"
                  style={{ transform: 'rotate(-30deg)', transformOrigin: 'bottom center' }}
                />
              </div>
              
              {/* Right Antenna */}
              <div className="absolute -top-20 left-1/2 translate-x-14">
                <div 
                  className="w-1.5 h-24 bg-gradient-to-b from-slate-300 via-slate-400 to-slate-500 rounded-full shadow-lg"
                  style={{ transform: 'rotate(30deg)', transformOrigin: 'bottom center' }}
                />
              </div>
              
              {/* Antenna base */}
              <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-12 h-3 bg-gradient-to-b from-slate-600 to-slate-800 rounded-t-lg" />
            </div>

            {/* TV Body - Grey/Black modern retro */}
            <div className="relative mt-2">
              {/* TV Outer Frame - Dark grey/black */}
              <div className={`w-[420px] h-80 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 rounded-2xl p-5 shadow-2xl border-4 border-slate-600 relative overflow-hidden ${intensiveGlitch ? 'animate-tv-shake' : ''}`}>
                {/* Brushed metal texture */}
                <div className="absolute inset-0 opacity-10" 
                     style={{ 
                       background: 'repeating-linear-gradient(90deg, transparent, transparent 1px, rgba(255,255,255,0.03) 1px, rgba(255,255,255,0.03) 2px)' 
                     }} 
                />
                
                {/* Screen area with control panel */}
                <div className="flex h-full gap-4">
                  {/* Main Screen */}
                  <div className="flex-1 relative">
                    {/* TV Screen Bezel - Dark chrome */}
                    <div className="relative w-full h-full bg-gradient-to-b from-slate-500 via-slate-600 to-slate-700 rounded-xl p-2 border border-slate-400 shadow-inner">
                      {/* CRT Screen */}
                      <div className={`relative w-full h-full bg-black rounded-lg overflow-hidden ${screenGlitch ? 'animate-screen-glitch' : ''} ${intensiveGlitch ? 'animate-intensive-glitch' : ''}`}
                           style={{ borderRadius: '12px' }}>
                        {/* Scanlines */}
                        <div className="absolute inset-0 pointer-events-none z-20 opacity-30" 
                             style={{ 
                               background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.5) 2px, rgba(0,0,0,0.5) 4px)' 
                             }} 
                        />
                        
                        {/* Screen glow */}
                        <div className={`absolute inset-0 bg-gradient-to-br from-purple-900/50 via-transparent to-cyan-900/50 ${intensiveGlitch ? 'opacity-80' : 'opacity-100'}`} />
                        
                        {/* CRT curvature effect */}
                        <div className="absolute inset-0 shadow-[inset_0_0_100px_rgba(0,0,0,0.95)] rounded-lg" />
                        
                        {/* Screen reflection */}
                        <div className="absolute top-0 left-0 right-0 h-1/4 bg-gradient-to-b from-white/8 to-transparent rounded-t-lg" />
                        
                        {/* Horizontal glitch lines */}
                        {(screenGlitch || intensiveGlitch) && (
                          <>
                            <div className="absolute left-0 right-0 h-1 bg-cyan-400/60 z-30" style={{ top: '20%' }} />
                            <div className="absolute left-0 right-0 h-0.5 bg-pink-400/40 z-30" style={{ top: '45%' }} />
                            <div className="absolute left-0 right-0 h-1.5 bg-purple-400/50 z-30" style={{ top: '70%' }} />
                          </>
                        )}
                        
                        {/* Screen content */}
                        <div className="relative z-10 flex flex-col items-center justify-center h-full">
                          {/* Glitchy text */}
                          <div className="relative">
                            <h2 
                              className={`text-3xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-cyan-400 to-pink-400 ${screenGlitch ? 'animate-text-glitch' : ''} ${intensiveGlitch ? 'animate-text-intensive' : ''}`}
                              style={{ 
                                textShadow: '0 0 15px rgba(168, 85, 247, 0.9), 0 0 30px rgba(34, 211, 238, 0.7), 0 0 45px rgba(236, 72, 153, 0.5)',
                                fontFamily: '"VT323", monospace',
                                fontSize: '2.5rem',
                                letterSpacing: '0.15em'
                              }}
                            >
                              {glitchText}
                            </h2>
                            {/* Glitch layers */}
                            <h2 
                              className="absolute top-0 left-0 text-3xl font-black tracking-wider text-cyan-400 opacity-80"
                              style={{ 
                                clipPath: 'inset(10% 0 60% 0)',
                                transform: screenGlitch || intensiveGlitch ? 'translateX(-4px)' : 'translateX(0)',
                                fontFamily: '"VT323", monospace',
                                fontSize: '2.5rem',
                                letterSpacing: '0.15em',
                                transition: 'transform 0.05s'
                              }}
                            >
                              {glitchText}
                            </h2>
                            <h2 
                              className="absolute top-0 left-0 text-3xl font-black tracking-wider text-pink-400 opacity-80"
                              style={{ 
                                clipPath: 'inset(60% 0 10% 0)',
                                transform: screenGlitch || intensiveGlitch ? 'translateX(4px)' : 'translateX(0)',
                                fontFamily: '"VT323", monospace',
                                fontSize: '2.5rem',
                                letterSpacing: '0.15em',
                                transition: 'transform 0.05s'
                              }}
                            >
                              {glitchText}
                            </h2>
                          </div>
                          
                          {/* Subtitle */}
                          <p className={`mt-5 text-sm tracking-widest font-mono ${intensiveGlitch ? 'text-pink-400' : 'text-emerald-400'} ${screenGlitch ? 'opacity-50' : 'opacity-100'}`}>
                            ▶ NOW PLAYING ▶
                          </p>
                        </div>
                        
                        {/* Random noise overlay on glitch */}
                        {(screenGlitch || intensiveGlitch) && (
                          <div className="absolute inset-0 z-30 opacity-40 mix-blend-overlay animate-noise" />
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Control Panel - Right side */}
                  <div className="w-20 flex flex-col justify-between py-2">
                    {/* Top buttons */}
                    <div className="space-y-3">
                      {/* Power button */}
                      <button className="w-full group/btn">
                        <div className="w-10 h-10 mx-auto rounded-full bg-gradient-to-br from-slate-600 to-slate-800 border-2 border-slate-500 shadow-lg flex items-center justify-center hover:scale-110 hover:border-emerald-500/50 transition-all">
                          <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse" />
                        </div>
                        <span className="text-[8px] text-slate-400 mt-1 block">POWER</span>
                      </button>
                      
                      {/* Channel buttons */}
                      <div className="space-y-2">
                        <button className="w-full">
                          <div className="w-8 h-6 mx-auto rounded bg-gradient-to-b from-slate-500 to-slate-700 border border-slate-400 shadow flex items-center justify-center hover:scale-110 hover:bg-slate-600 transition-all">
                            <span className="text-[10px] text-slate-300 font-bold">▲</span>
                          </div>
                        </button>
                        <span className="text-[8px] text-slate-400 block text-center">CH</span>
                        <button className="w-full">
                          <div className="w-8 h-6 mx-auto rounded bg-gradient-to-b from-slate-500 to-slate-700 border border-slate-400 shadow flex items-center justify-center hover:scale-110 hover:bg-slate-600 transition-all">
                            <span className="text-[10px] text-slate-300 font-bold">▼</span>
                          </div>
                        </button>
                      </div>
                    </div>
                    
                    {/* Volume buttons */}
                    <div className="space-y-2">
                      <button className="w-full">
                        <div className="w-8 h-6 mx-auto rounded bg-gradient-to-b from-slate-500 to-slate-700 border border-slate-400 shadow flex items-center justify-center hover:scale-110 hover:bg-slate-600 transition-all">
                          <span className="text-[10px] text-slate-300 font-bold">+</span>
                        </div>
                      </button>
                      <span className="text-[8px] text-slate-400 block text-center">VOL</span>
                      <button className="w-full">
                        <div className="w-8 h-6 mx-auto rounded bg-gradient-to-b from-slate-500 to-slate-700 border border-slate-400 shadow flex items-center justify-center hover:scale-110 hover:bg-slate-600 transition-all">
                          <span className="text-[10px] text-slate-300 font-bold">−</span>
                        </div>
                      </button>
                    </div>
                    
                    {/* Brand */}
                    <div className="text-center">
                      <span className="text-[9px] text-slate-500 font-bold tracking-widest">STELLAR</span>
                    </div>
                  </div>
                </div>
                
                {/* Bottom vent/speaker grille */}
                <div className="absolute bottom-2 left-5 right-24 flex gap-0.5">
                  {[...Array(30)].map((_, i) => (
                    <div key={i} className="flex-1 h-1 bg-slate-900 rounded-full" />
                  ))}
                </div>
              </div>
              
              {/* TV Stand - Modern */}
              <div className="flex justify-center">
                <div className="w-40 h-2 bg-gradient-to-b from-slate-600 to-slate-800 rounded-b-lg" />
              </div>
              <div className="flex justify-center gap-20 -mt-0.5">
                {/* Left leg */}
                <div className="w-4 h-8 bg-gradient-to-b from-slate-700 to-slate-900 rounded-b transform -skew-x-6" />
                {/* Right leg */}
                <div className="w-4 h-8 bg-gradient-to-b from-slate-700 to-slate-900 rounded-b transform skew-x-6" />
              </div>
            </div>
          </div>
        </div>

        {/* Main footer content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
          {/* Brand section */}
          <div className="space-y-5">
            <div className="flex items-center gap-4 group">
              <div className="relative">
                <div className="absolute -inset-2 bg-gradient-to-r from-emerald-500 via-purple-500 to-cyan-500 rounded-2xl blur-lg opacity-40 group-hover:opacity-70 transition-all duration-500 animate-pulse-slow" />
                <div className="relative flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <span className="text-3xl">🎬</span>
                </div>
              </div>
              <div>
                <h3 className="font-black text-white text-2xl group-hover:text-purple-300 transition-colors">
                  <span className="glitch-wrapper">
                    <span className="glitch-text" data-text="Stellar Media">
                      Stellar Media
                    </span>
                  </span>
                </h3>
                <p className="text-sm text-slate-400 font-semibold">Organizer Pro v3.0</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
              Professional media organization tool with IMDB/MusicBrainz integration, 
              GPU video conversion, and audio enhancement for Plex & Jellyfin.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Star className="h-4 w-4 text-yellow-400 animate-pulse" />
              <span className="font-medium">Built for media enthusiasts</span>
            </div>
          </div>

          {/* Features section */}
          <div className="space-y-5 group/features">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-2 border-yellow-500/30 group-hover/features:border-yellow-400/50 group-hover/features:shadow-lg group-hover/features:shadow-yellow-500/20 transition-all">
                <Zap className="h-6 w-6 text-yellow-400" />
              </div>
              <span className="glitch-wrapper">
                <span className="glitch-text" data-text="Features">Features</span>
              </span>
            </h4>
            <ul className="space-y-3 text-sm text-slate-400">
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-3 h-3 rounded-full bg-emerald-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-emerald-400/60 transition-all duration-300" />
                <span className="group-hover:text-emerald-300 group-hover:translate-x-1 transition-all font-medium">Smart file renaming with metadata</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-3 h-3 rounded-full bg-purple-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-purple-400/60 transition-all duration-300" />
                <span className="group-hover:text-purple-300 group-hover:translate-x-1 transition-all font-medium">GPU-accelerated video conversion</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-3 h-3 rounded-full bg-cyan-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-cyan-400/60 transition-all duration-300" />
                <span className="group-hover:text-cyan-300 group-hover:translate-x-1 transition-all font-medium">Professional audio enhancement</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-3 h-3 rounded-full bg-pink-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-pink-400/60 transition-all duration-300" />
                <span className="group-hover:text-pink-300 group-hover:translate-x-1 transition-all font-medium">NAS integration (Synology/Unraid)</span>
              </li>
            </ul>
          </div>

          {/* Connect section */}
          <div className="space-y-5 group/connect">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-2 border-cyan-500/30 group-hover/connect:border-cyan-400/50 group-hover/connect:shadow-lg group-hover/connect:shadow-cyan-500/20 transition-all">
                <Sparkles className="h-6 w-6 text-cyan-400" />
              </div>
              <span className="glitch-wrapper">
                <span className="glitch-text" data-text="Connect">Connect</span>
              </span>
            </h4>
            <div className="flex items-center gap-5">
              {socialLinks.map((social, index) => (
                <a
                  key={social.name}
                  href={social.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`social-icon ${social.className} p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-purple-500/50 hover:bg-purple-500/10 hover:scale-125 hover:shadow-lg hover:shadow-purple-500/20 transition-all duration-300`}
                  title={social.name}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <social.icon className="h-6 w-6 text-slate-400 hover:text-white transition-colors" />
                </a>
              ))}
            </div>
            <p className="text-sm text-slate-500 flex items-center gap-2 font-medium">
              <span className="text-purple-400 animate-pulse text-lg">@</span>
              <span className="hover:text-purple-300 transition-colors cursor-default">sharvinzlife everywhere</span>
            </p>
          </div>
        </div>

        {/* Divider with glitch effect */}
        <div className="relative h-[2px] mb-8">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/40 to-transparent animate-pulse" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent animate-pulse" style={{ animationDelay: '0.5s' }} />
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-sm">
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>© {currentYear}</span>
            <span className="footer-glitch-text font-bold text-slate-400" data-text="Stellar Media Organizer">
              Stellar Media Organizer
            </span>
          </div>
          
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>Made with</span>
            <Heart className="h-5 w-5 text-pink-500 animate-pulse" />
            <span>by</span>
            <a 
              href="https://github.com/sharvinzlife" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-purple-400 hover:text-purple-300 transition-colors font-bold hover:underline"
            >
              sharvinzlife
            </a>
          </div>

          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <Code2 className="h-5 w-5 text-emerald-400" />
            <span>React + FastAPI + FFmpeg</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
