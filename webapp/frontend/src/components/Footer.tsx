import React, { useState, useEffect } from 'react';
import { Github, Instagram, Twitter, Facebook, Heart, Sparkles, Code2, Zap, Star } from 'lucide-react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const [glitchText, setGlitchText] = useState('STELLAR MEDIA');
  const [screenGlitch, setScreenGlitch] = useState(false);

  // Random glitch effect on the TV screen
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      if (Math.random() > 0.7) {
        setScreenGlitch(true);
        setTimeout(() => setScreenGlitch(false), 150);
      }
    }, 2000);

    const textInterval = setInterval(() => {
      const texts = ['STELLAR MEDIA', 'ORGANIZER PRO', '⭐ v3.0 ⭐', 'PLEX READY', 'JELLYFIN ✓'];
      setGlitchText(texts[Math.floor(Math.random() * texts.length)]);
    }, 3000);

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
            {/* Antennas */}
            <div className="relative flex justify-center mb-0">
              {/* Left Antenna */}
              <div className="absolute -top-16 left-1/2 -translate-x-20">
                <div className="relative">
                  {/* Antenna pole */}
                  <div 
                    className="w-2 h-20 bg-gradient-to-b from-slate-400 via-slate-500 to-slate-600 rounded-full shadow-lg"
                    style={{ transform: 'rotate(-25deg)', transformOrigin: 'bottom center' }}
                  />
                  {/* Antenna ball */}
                  <div 
                    className="absolute -top-1 left-1/2 -translate-x-1/2 w-4 h-4 bg-gradient-to-br from-slate-300 to-slate-500 rounded-full shadow-lg border border-slate-400"
                    style={{ transform: 'rotate(-25deg) translateY(-76px) translateX(8px)' }}
                  />
                </div>
              </div>
              
              {/* Right Antenna */}
              <div className="absolute -top-16 left-1/2 translate-x-12">
                <div className="relative">
                  {/* Antenna pole */}
                  <div 
                    className="w-2 h-20 bg-gradient-to-b from-slate-400 via-slate-500 to-slate-600 rounded-full shadow-lg"
                    style={{ transform: 'rotate(25deg)', transformOrigin: 'bottom center' }}
                  />
                  {/* Antenna ball */}
                  <div 
                    className="absolute -top-1 left-1/2 -translate-x-1/2 w-4 h-4 bg-gradient-to-br from-slate-300 to-slate-500 rounded-full shadow-lg border border-slate-400"
                    style={{ transform: 'rotate(25deg) translateY(-76px) translateX(-8px)' }}
                  />
                </div>
              </div>
              
              {/* Antenna base */}
              <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-16 h-4 bg-gradient-to-b from-slate-500 to-slate-700 rounded-t-lg" />
            </div>

            {/* TV Body */}
            <div className="relative mt-2">
              {/* TV Outer Frame - Retro wooden style */}
              <div className="w-96 h-72 bg-gradient-to-b from-amber-800 via-amber-900 to-amber-950 rounded-3xl p-5 shadow-2xl border-4 border-amber-700 relative overflow-hidden">
                {/* Wood grain texture overlay */}
                <div className="absolute inset-0 opacity-20" 
                     style={{ 
                       background: 'repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(139, 69, 19, 0.3) 2px, rgba(139, 69, 19, 0.3) 4px)' 
                     }} 
                />
                
                {/* Inner frame shadow */}
                <div className="absolute inset-4 rounded-2xl shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]" />
                
                {/* TV Screen Bezel - Silver/Chrome */}
                <div className="relative w-full h-full bg-gradient-to-b from-slate-400 via-slate-500 to-slate-600 rounded-2xl p-3 border-2 border-slate-300 shadow-inner">
                  {/* CRT Screen */}
                  <div className={`relative w-full h-full bg-black rounded-xl overflow-hidden ${screenGlitch ? 'animate-screen-glitch' : ''}`}
                       style={{ borderRadius: '20px / 15px' }}>
                    {/* Scanlines */}
                    <div className="absolute inset-0 pointer-events-none z-20 opacity-20" 
                         style={{ 
                           background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.4) 2px, rgba(0,0,0,0.4) 4px)' 
                         }} 
                    />
                    
                    {/* Screen glow */}
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-900/40 via-transparent to-cyan-900/40" />
                    
                    {/* CRT curvature effect */}
                    <div className="absolute inset-0 shadow-[inset_0_0_80px_rgba(0,0,0,0.9)] rounded-xl" />
                    
                    {/* Screen reflection */}
                    <div className="absolute top-0 left-0 right-0 h-1/3 bg-gradient-to-b from-white/5 to-transparent rounded-t-xl" />
                    
                    {/* Screen content */}
                    <div className="relative z-10 flex flex-col items-center justify-center h-full">
                      {/* Glitchy text */}
                      <div className="relative">
                        <h2 
                          className={`text-2xl md:text-3xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-cyan-400 to-pink-400 ${screenGlitch ? 'animate-text-glitch' : ''}`}
                          style={{ 
                            textShadow: '0 0 10px rgba(168, 85, 247, 0.8), 0 0 20px rgba(34, 211, 238, 0.6), 0 0 30px rgba(236, 72, 153, 0.4)',
                            fontFamily: '"VT323", "Press Start 2P", monospace',
                            fontSize: '2rem'
                          }}
                        >
                          {glitchText}
                        </h2>
                        {/* Glitch layers */}
                        <h2 
                          className="absolute top-0 left-0 text-2xl md:text-3xl font-black tracking-wider text-cyan-400 opacity-70"
                          style={{ 
                            clipPath: 'inset(10% 0 60% 0)',
                            transform: screenGlitch ? 'translateX(-3px)' : 'translateX(0)',
                            fontFamily: '"VT323", "Press Start 2P", monospace',
                            fontSize: '2rem'
                          }}
                        >
                          {glitchText}
                        </h2>
                        <h2 
                          className="absolute top-0 left-0 text-2xl md:text-3xl font-black tracking-wider text-pink-400 opacity-70"
                          style={{ 
                            clipPath: 'inset(60% 0 10% 0)',
                            transform: screenGlitch ? 'translateX(3px)' : 'translateX(0)',
                            fontFamily: '"VT323", "Press Start 2P", monospace',
                            fontSize: '2rem'
                          }}
                        >
                          {glitchText}
                        </h2>
                      </div>
                      
                      {/* Subtitle */}
                      <p className="mt-4 text-sm text-emerald-400 tracking-widest animate-pulse font-mono">
                        ▶ NOW PLAYING ▶
                      </p>
                    </div>
                    
                    {/* Random noise overlay on glitch */}
                    {screenGlitch && (
                      <div className="absolute inset-0 z-30 opacity-30 bg-white mix-blend-overlay" 
                           style={{ 
                             background: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")' 
                           }} 
                      />
                    )}
                  </div>
                </div>
                
                {/* Control Panel - Right side */}
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex flex-col gap-4 bg-gradient-to-b from-amber-700 to-amber-800 p-2 rounded-lg border border-amber-600">
                  {/* Channel knob */}
                  <div className="relative group/knob cursor-pointer">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-200 via-slate-300 to-slate-400 border-4 border-slate-500 shadow-lg hover:scale-110 transition-transform">
                      <div className="absolute inset-2 rounded-full bg-gradient-to-br from-slate-100 to-slate-300 flex items-center justify-center">
                        <div className="w-1 h-3 bg-slate-600 rounded-full" />
                      </div>
                    </div>
                    <span className="absolute -left-12 top-1/2 -translate-y-1/2 text-[8px] text-amber-300 font-bold opacity-0 group-hover/knob:opacity-100 transition-opacity">CH</span>
                  </div>
                  
                  {/* Volume knob */}
                  <div className="relative group/knob cursor-pointer">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-200 via-slate-300 to-slate-400 border-4 border-slate-500 shadow-lg hover:scale-110 transition-transform">
                      <div className="absolute inset-2 rounded-full bg-gradient-to-br from-slate-100 to-slate-300 flex items-center justify-center">
                        <div className="w-1 h-3 bg-slate-600 rounded-full transform rotate-45" />
                      </div>
                    </div>
                    <span className="absolute -left-12 top-1/2 -translate-y-1/2 text-[8px] text-amber-300 font-bold opacity-0 group-hover/knob:opacity-100 transition-opacity">VOL</span>
                  </div>
                </div>
                
                {/* Bottom panel with speaker grille and power */}
                <div className="absolute bottom-2 left-5 right-5 flex items-center justify-between">
                  {/* Speaker grille */}
                  <div className="flex gap-1">
                    {[...Array(8)].map((_, i) => (
                      <div key={i} className="w-1 h-8 bg-gradient-to-b from-amber-600 to-amber-800 rounded-full opacity-60" />
                    ))}
                  </div>
                  
                  {/* Brand and Power */}
                  <div className="flex items-center gap-4">
                    <span className="text-[10px] text-amber-400 font-bold tracking-widest">STELLAR</span>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse border border-emerald-400" />
                      <span className="text-[8px] text-amber-400 font-bold">POWER</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* TV Stand - Retro legs */}
              <div className="flex justify-center">
                <div className="w-48 h-3 bg-gradient-to-b from-amber-700 to-amber-900 rounded-b-lg border-x-2 border-b-2 border-amber-600" />
              </div>
              <div className="flex justify-center gap-24 -mt-0.5">
                {/* Left leg */}
                <div className="w-6 h-12 bg-gradient-to-b from-amber-800 to-amber-950 rounded-b-lg transform -skew-x-12 border-l-2 border-b-2 border-amber-700" />
                {/* Right leg */}
                <div className="w-6 h-12 bg-gradient-to-b from-amber-800 to-amber-950 rounded-b-lg transform skew-x-12 border-r-2 border-b-2 border-amber-700" />
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

      {/* Floating particles effect */}
      <div className="absolute bottom-0 left-0 right-0 h-40 pointer-events-none overflow-hidden">
        <div className="absolute w-2 h-2 bg-emerald-400/40 rounded-full animate-float" style={{ left: '8%', bottom: '25%' }} />
        <div className="absolute w-1.5 h-1.5 bg-purple-400/50 rounded-full animate-float-delayed" style={{ left: '20%', bottom: '45%' }} />
        <div className="absolute w-2 h-2 bg-cyan-400/40 rounded-full animate-float" style={{ left: '40%', bottom: '35%' }} />
        <div className="absolute w-1 h-1 bg-pink-400/60 rounded-full animate-float-delayed" style={{ left: '55%', bottom: '55%' }} />
        <div className="absolute w-2.5 h-2.5 bg-yellow-400/30 rounded-full animate-float" style={{ left: '70%', bottom: '30%' }} />
        <div className="absolute w-1.5 h-1.5 bg-emerald-400/40 rounded-full animate-float-delayed" style={{ left: '85%', bottom: '50%' }} />
        <div className="absolute w-1 h-1 bg-purple-400/50 rounded-full animate-float" style={{ left: '92%', bottom: '40%' }} />
      </div>
    </footer>
  );
};

export default Footer;
