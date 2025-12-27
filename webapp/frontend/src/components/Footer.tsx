import React from 'react';
import { Github, Instagram, Twitter, Facebook, Heart, Sparkles, Code2, Zap, Star } from 'lucide-react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  const socialLinks = [
    { name: 'GitHub', icon: Github, url: 'https://github.com/sharvinzlife', className: 'github' },
    { name: 'Instagram', icon: Instagram, url: 'https://instagram.com/sharvinzlife', className: 'instagram' },
    { name: 'X', icon: Twitter, url: 'https://x.com/sharvinzlife', className: 'twitter' },
    { name: 'Facebook', icon: Facebook, url: 'https://facebook.com/sharvinzlife', className: 'facebook' },
  ];

  return (
    <footer className="footer-glitch relative mt-20">
      {/* Multiple glitch lines at top */}
      <div className="absolute top-0 left-0 right-0 h-[2px] overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500 to-transparent animate-pulse" />
      </div>
      
      <div className="container mx-auto px-6 pt-16 pb-8">
        {/* Main footer content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
          {/* Brand section */}
          <div className="space-y-5">
            <div className="flex items-center gap-4 group">
              <div className="relative">
                <div className="absolute -inset-2 bg-gradient-to-r from-emerald-500 via-purple-500 to-cyan-500 rounded-2xl blur-lg opacity-40 group-hover:opacity-70 transition-all duration-500 animate-pulse-slow" />
                <div className="relative flex items-center justify-center w-14 h-14 bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <span className="text-2xl">🎬</span>
                </div>
              </div>
              <div>
                <h3 className="font-bold text-white text-xl group-hover:text-purple-300 transition-colors">
                  <span className="glitch-wrapper">
                    <span className="glitch-text text-lg" data-text="Stellar Media">
                      Stellar Media
                    </span>
                  </span>
                </h3>
                <p className="text-sm text-slate-500">Organizer Pro v3.0</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
              Professional media organization tool with IMDB/MusicBrainz integration, 
              GPU video conversion, and audio enhancement.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Star className="h-3 w-3 text-yellow-400" />
              <span>Built for media enthusiasts</span>
            </div>
          </div>

          {/* Features section */}
          <div className="space-y-5 group/features">
            <h4 className="font-semibold text-white flex items-center gap-3 text-lg">
              <div className="p-2 rounded-xl bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 group-hover/features:border-yellow-400/50 group-hover/features:shadow-lg group-hover/features:shadow-yellow-500/20 transition-all">
                <Zap className="h-5 w-5 text-yellow-400" />
              </div>
              <span className="glitch-wrapper">
                <span className="glitch-text text-base" data-text="Features">Features</span>
              </span>
            </h4>
            <ul className="space-y-3 text-sm text-slate-400">
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-emerald-400/60 transition-all duration-300" />
                <span className="group-hover:text-emerald-300 group-hover:translate-x-1 transition-all">Smart file renaming with metadata</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-purple-400/60 transition-all duration-300" />
                <span className="group-hover:text-purple-300 group-hover:translate-x-1 transition-all">GPU-accelerated video conversion</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-cyan-400/60 transition-all duration-300" />
                <span className="group-hover:text-cyan-300 group-hover:translate-x-1 transition-all">Professional audio enhancement</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-pink-400/60 transition-all duration-300" />
                <span className="group-hover:text-pink-300 group-hover:translate-x-1 transition-all">NAS integration (Synology/Unraid)</span>
              </li>
            </ul>
          </div>

          {/* Connect section */}
          <div className="space-y-5 group/connect">
            <h4 className="font-semibold text-white flex items-center gap-3 text-lg">
              <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 group-hover/connect:border-cyan-400/50 group-hover/connect:shadow-lg group-hover/connect:shadow-cyan-500/20 transition-all">
                <Sparkles className="h-5 w-5 text-cyan-400" />
              </div>
              <span className="glitch-wrapper">
                <span className="glitch-text text-base" data-text="Connect">Connect</span>
              </span>
            </h4>
            <div className="flex items-center gap-4">
              {socialLinks.map((social, index) => (
                <a
                  key={social.name}
                  href={social.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`social-icon ${social.className}`}
                  title={social.name}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <social.icon className="h-5 w-5 text-slate-400 group-hover:text-white transition-colors" />
                </a>
              ))}
            </div>
            <p className="text-sm text-slate-500 flex items-center gap-2">
              <span className="text-purple-400 animate-pulse">@</span>
              <span className="hover:text-purple-300 transition-colors cursor-default">sharvinzlife everywhere</span>
            </p>
          </div>
        </div>

        {/* Divider with glitch effect */}
        <div className="relative h-px mb-8">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/30 to-transparent animate-pulse" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent animate-pulse" style={{ animationDelay: '0.5s' }} />
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-sm">
          <div className="flex items-center gap-2 text-slate-500">
            <span>© {currentYear}</span>
            <span className="footer-glitch-text font-medium" data-text="Stellar Media Organizer">
              Stellar Media Organizer
            </span>
          </div>
          
          <div className="flex items-center gap-2 text-slate-500">
            <span>Made with</span>
            <Heart className="h-4 w-4 text-pink-500 animate-pulse" />
            <span>by</span>
            <a 
              href="https://github.com/sharvinzlife" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-purple-400 hover:text-purple-300 transition-colors font-semibold hover:underline"
            >
              sharvinzlife
            </a>
          </div>

          <div className="flex items-center gap-2 text-slate-500">
            <Code2 className="h-4 w-4 text-emerald-400" />
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
