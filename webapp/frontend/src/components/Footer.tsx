import React, { useState, useEffect, useRef } from 'react';
import { Github, Instagram, Twitter, Facebook, Heart, Sparkles, Code2, Zap, Star, Play, Pause, SkipForward, SkipBack, Volume2, VolumeX, Radio } from 'lucide-react';

// Classic uplifting songs playlist
const playlist = [
  { title: "Don't Stop Believin'", artist: "Journey", year: 1981, spotifyId: "4bHsxqR3GMrXTxEPLuK5ue", youtubeId: "1k8craCGpgs" },
  { title: "Here Comes The Sun", artist: "The Beatles", year: 1969, spotifyId: "6dGnYIeXmHdcikdzNNDMm2", youtubeId: "KQetemT1sWc" },
  { title: "Walking on Sunshine", artist: "Katrina & The Waves", year: 1985, spotifyId: "05wIrZSwuaVWhcv5FfqeH0", youtubeId: "iPUmE-tne5U" },
  { title: "September", artist: "Earth, Wind & Fire", year: 1978, spotifyId: "2grjqo0Frpf2okIBiifQKs", youtubeId: "Gs069dndIYk" },
  { title: "I Gotta Feeling", artist: "Black Eyed Peas", year: 2009, spotifyId: "2H1047e0oMSj10dgp7p2VG", youtubeId: "uSD4vsh1zDA" },
  { title: "Happy", artist: "Pharrell Williams", year: 2013, spotifyId: "60nZcImufyMA1MKQY3dcCH", youtubeId: "ZbZSe6N_BXs" },
  { title: "Uptown Funk", artist: "Bruno Mars", year: 2014, spotifyId: "32OlwWuMpZ6b0aN2RZOeMS", youtubeId: "OPf0YbXqDm0" },
  { title: "Livin' on a Prayer", artist: "Bon Jovi", year: 1986, spotifyId: "37ZJ0p5Jm13JPevGcx4SkF", youtubeId: "lDK9QqIzhwk" },
];

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const [currentTrack, setCurrentTrack] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [audioFxEnabled, setAudioFxEnabled] = useState(true);
  const [screenGlitch, setScreenGlitch] = useState(false);
  const [intensiveGlitch, setIntensiveGlitch] = useState(false);
  const [colorShift, setColorShift] = useState(0);
  const [vinylRotation, setVinylRotation] = useState(0);
  const [playerReady, setPlayerReady] = useState(false);
  const animationRef = useRef<number>();
  const playerRef = useRef<YT.Player | null>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const convolverRef = useRef<ConvolverNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);

  // Load YouTube IFrame API
  useEffect(() => {
    if (typeof window !== 'undefined' && !(window as any).YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);
      (window as any).onYouTubeIframeAPIReady = () => initPlayer();
    } else if ((window as any).YT?.Player) {
      initPlayer();
    }
  }, []);

  const initPlayer = () => {
    if (playerContainerRef.current && !playerRef.current) {
      playerRef.current = new (window as any).YT.Player('youtube-player', {
        height: '0',
        width: '0',
        videoId: playlist[0].youtubeId,
        playerVars: { autoplay: 0, controls: 0, disablekb: 1, fs: 0, modestbranding: 1, rel: 0 },
        events: {
          onReady: () => setPlayerReady(true),
          onStateChange: (event: any) => {
            if (event.data === (window as any).YT.PlayerState.ENDED) nextTrack();
          },
        },
      });
    }
  };

  // Vinyl rotation
  useEffect(() => {
    if (isPlaying) {
      const animate = () => {
        setVinylRotation(prev => (prev + 1.5) % 360);
        animationRef.current = requestAnimationFrame(animate);
      };
      animationRef.current = requestAnimationFrame(animate);
    } else if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    return () => { if (animationRef.current) cancelAnimationFrame(animationRef.current); };
  }, [isPlaying]);

  // Glitch effects
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      const rand = Math.random();
      if (rand > 0.88) {
        setIntensiveGlitch(true);
        setTimeout(() => setIntensiveGlitch(false), 200);
      } else if (rand > 0.65) {
        setScreenGlitch(true);
        setTimeout(() => setScreenGlitch(false), 150);
      }
    }, 2500);
    const colorInterval = setInterval(() => setColorShift(prev => (prev + 1) % 360), 50);
    return () => { clearInterval(glitchInterval); clearInterval(colorInterval); };
  }, []);

  const playTrack = (index: number) => {
    if (playerRef.current && playerReady) {
      playerRef.current.loadVideoById(playlist[index].youtubeId);
      playerRef.current.playVideo();
      setIsPlaying(true);
    }
  };

  const nextTrack = () => {
    const next = (currentTrack + 1) % playlist.length;
    setCurrentTrack(next);
    setScreenGlitch(true);
    setTimeout(() => setScreenGlitch(false), 200);
    if (isPlaying) playTrack(next);
  };

  const prevTrack = () => {
    const prev = (currentTrack - 1 + playlist.length) % playlist.length;
    setCurrentTrack(prev);
    setScreenGlitch(true);
    setTimeout(() => setScreenGlitch(false), 200);
    if (isPlaying) playTrack(prev);
  };

  const togglePlay = () => {
    if (!playerReady) return;
    setIntensiveGlitch(true);
    setTimeout(() => setIntensiveGlitch(false), 150);
    if (isPlaying) {
      playerRef.current?.pauseVideo();
      setIsPlaying(false);
    } else {
      playerRef.current?.loadVideoById(playlist[currentTrack].youtubeId);
      playerRef.current?.playVideo();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (playerRef.current) {
      isMuted ? playerRef.current.unMute() : playerRef.current.mute();
      setIsMuted(!isMuted);
    }
  };

  const toggleAudioFx = () => setAudioFxEnabled(!audioFxEnabled);

  const socialLinks = [
    { name: 'GitHub', icon: Github, url: 'https://github.com/sharvinzlife', className: 'github' },
    { name: 'Instagram', icon: Instagram, url: 'https://instagram.com/sharvinzlife', className: 'instagram' },
    { name: 'X', icon: Twitter, url: 'https://x.com/sharvinzlife', className: 'twitter' },
    { name: 'Facebook', icon: Facebook, url: 'https://facebook.com/sharvinzlife', className: 'facebook' },
  ];

  const track = playlist[currentTrack];

  return (
    <footer className="footer-glitch relative mt-20">
      {/* Hidden YouTube Player */}
      <div ref={playerContainerRef} className="hidden"><div id="youtube-player"></div></div>
      
      {/* Glitch lines at top */}
      <div className="absolute top-0 left-0 right-0 h-[3px] overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500 to-transparent animate-pulse" />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" style={{ animationDelay: '0.5s' }} />
      </div>
      
      <div className="container mx-auto px-6 pt-16 pb-8">
        {/* JUKEBOX Section */}
        <div className="flex justify-center mb-16">
          <div className="jukebox-container group relative">
            {/* Jukebox Top Arch */}
            <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-[540px] h-20 bg-gradient-to-b from-amber-600 via-amber-700 to-amber-800 rounded-t-[120px] border-t-4 border-x-4 border-amber-500 overflow-hidden z-0">
              <div className="absolute inset-0 opacity-20" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
              {/* Neon lights */}
              <div className="absolute top-2 left-1/2 -translate-x-1/2 flex gap-3">
                {[...Array(7)].map((_, i) => (
                  <div key={i} className={`w-3 h-3 rounded-full ${isPlaying ? 'animate-pulse' : ''}`}
                       style={{ background: `hsl(${(i * 50 + colorShift) % 360}, 80%, 60%)`, boxShadow: `0 0 10px hsl(${(i * 50 + colorShift) % 360}, 80%, 60%)`, animationDelay: `${i * 0.1}s` }} />
                ))}
              </div>
              {/* Neon JUKEBOX text */}
              <div className="flex items-center justify-center h-full pt-4">
                <span className="text-xl font-black tracking-[0.25em] text-transparent bg-clip-text bg-gradient-to-r from-pink-400 via-purple-400 to-cyan-400"
                      style={{ textShadow: '0 0 20px rgba(236, 72, 153, 0.8), 0 0 40px rgba(168, 85, 247, 0.6)', fontFamily: '"VT323", monospace' }}>
                  ★ STELLAR JUKEBOX ★
                </span>
              </div>
            </div>

            {/* Main Jukebox Body */}
            <div className="flex items-center gap-0 relative z-10">
              {/* LEFT VINYL RECORD */}
              <div className="relative w-44 h-56 flex-shrink-0 -mr-4 z-10">
                {/* Vinyl sleeve */}
                <div className="absolute inset-0 bg-gradient-to-r from-amber-900 via-amber-800 to-amber-700 rounded-l-2xl border-l-4 border-y-4 border-amber-600 shadow-2xl overflow-hidden">
                  <div className="absolute inset-0 opacity-20" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                  <div className="absolute top-3 bottom-3 right-0 w-3 bg-black/80 rounded-l" />
                  {/* Retro label */}
                  <div className="absolute top-2 left-2 right-6 h-8 bg-gradient-to-r from-red-800 to-red-900 rounded flex items-center justify-center border border-red-700">
                    <span className="text-[8px] font-bold text-yellow-300 tracking-wider" style={{ fontFamily: '"VT323", monospace' }}>♪ NOW SPINNING ♪</span>
                  </div>
                  {/* Equalizer INSIDE the panel - properly positioned */}
                  {isPlaying && (
                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1 items-end">
                      {[4, 6, 5, 7, 4, 6, 5, 7, 4].map((h, i) => (
                        <div key={i} className="w-1.5 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t animate-bounce shadow-lg shadow-emerald-400/50"
                             style={{ height: `${h * 3}px`, animationDelay: `${i * 40}ms`, animationDuration: '0.4s' }} />
                      ))}
                    </div>
                  )}
                </div>
                
                {/* Vinyl record */}
                <div className="absolute top-16 left-1/2 w-32 h-32 rounded-full shadow-2xl"
                     style={{ transform: `translateX(-50%) rotate(${vinylRotation}deg)`, background: '#1a1a1a',
                       boxShadow: isPlaying ? '0 0 40px rgba(168, 85, 247, 0.6), 0 0 80px rgba(236, 72, 153, 0.3), inset 0 0 30px rgba(0,0,0,0.9)' : 'inset 0 0 30px rgba(0,0,0,0.9), 0 5px 20px rgba(0,0,0,0.5)' }}>
                  {/* Grooves */}
                  <div className="absolute inset-0 rounded-full" style={{ background: 'repeating-radial-gradient(circle at center, transparent 0px, transparent 1px, rgba(40,40,40,0.8) 1px, rgba(40,40,40,0.8) 2px, transparent 2px, transparent 3px, rgba(50,50,50,0.6) 3px, rgba(50,50,50,0.6) 4px)' }} />
                  {/* Shine */}
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/15 via-transparent to-transparent" />
                  <div className="absolute inset-0 rounded-full" style={{ background: 'conic-gradient(from 0deg, transparent 0deg, rgba(255,255,255,0.1) 10deg, transparent 20deg, transparent 180deg, rgba(255,255,255,0.05) 190deg, transparent 200deg)' }} />
                  {/* Center label */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full overflow-hidden"
                       style={{ background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%)', boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.3), inset 0 -2px 4px rgba(0,0,0,0.3)' }}>
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-0.5">
                      <span className="text-[5px] font-bold text-yellow-300 tracking-wider">STELLAR</span>
                      <span className="text-[5px] font-black text-white text-center leading-tight truncate w-full px-0.5" style={{ fontFamily: '"VT323", monospace' }}>
                        {track.title.length > 10 ? track.title.substring(0, 10) + '..' : track.title}
                      </span>
                      <span className="text-[4px] text-yellow-200 truncate w-full text-center">{track.artist}</span>
                    </div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-black shadow-inner" />
                  </div>
                  {/* Noise */}
                  <div className="absolute inset-0 rounded-full opacity-30 mix-blend-overlay animate-noise pointer-events-none" />
                </div>
              </div>

              {/* CENTER - TV SCREEN */}
              <div className={`relative w-[420px] h-[340px] bg-gradient-to-b from-amber-700 via-amber-800 to-amber-900 rounded-2xl p-3 shadow-2xl border-4 border-amber-600 ${intensiveGlitch ? 'animate-tv-shake' : ''}`}>
                <div className="absolute inset-0 opacity-20 rounded-2xl" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                
                {/* Inner frame */}
                <div className="w-full h-full bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 rounded-xl p-2 border-2 border-slate-600 relative">
                  {/* Screen bezel */}
                  <div className="relative w-full h-full bg-gradient-to-b from-slate-500 via-slate-600 to-slate-700 rounded-lg p-2 border border-slate-400 shadow-inner">
                    {/* CRT Screen */}
                    <div className="relative w-full h-full bg-black rounded-md overflow-hidden">
                      {/* Background gradient */}
                      <div className="absolute inset-0 opacity-20" style={{ background: `linear-gradient(${colorShift}deg, rgba(168, 85, 247, 0.4), rgba(34, 211, 238, 0.4), rgba(236, 72, 153, 0.4))` }} />
                      {/* Scanlines */}
                      <div className="absolute inset-0 pointer-events-none z-20 opacity-30" style={{ background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.4) 2px, rgba(0,0,0,0.4) 4px)' }} />
                      {/* Screen glow */}
                      <div className={`absolute inset-0 bg-gradient-to-br from-purple-900/30 via-transparent to-cyan-900/30 ${intensiveGlitch ? 'opacity-80' : 'opacity-100'}`} />
                      {/* CRT curvature */}
                      <div className="absolute inset-0 shadow-[inset_0_0_50px_rgba(0,0,0,0.9)] rounded-md" />
                      {/* Screen reflection */}
                      <div className="absolute top-0 left-0 right-0 h-1/6 bg-gradient-to-b from-white/8 to-transparent rounded-t-md" />
                      {/* Glitch lines */}
                      {(screenGlitch || intensiveGlitch) && (
                        <>
                          <div className="absolute left-0 right-0 h-1 bg-cyan-400/60 z-30" style={{ top: '20%' }} />
                          <div className="absolute left-0 right-0 h-0.5 bg-pink-400/40 z-30" style={{ top: '40%' }} />
                          <div className="absolute left-0 right-0 h-2 bg-white/5 z-30" style={{ top: '60%' }} />
                        </>
                      )}
                      {/* Noise overlay */}
                      <div className={`absolute inset-0 mix-blend-overlay animate-noise pointer-events-none z-10 ${audioFxEnabled ? 'opacity-15' : 'opacity-5'}`} />

                      {/* Screen content - BETTER SPACING */}
                      <div className={`relative z-10 flex flex-col items-center justify-center h-full py-6 px-8 ${screenGlitch ? 'animate-screen-glitch' : ''} ${intensiveGlitch ? 'animate-intensive-glitch' : ''}`}>
                        {/* Status indicator - more padding from top */}
                        <div className="flex items-center gap-2 mb-4">
                          <div className={`w-2.5 h-2.5 rounded-full ${isPlaying ? 'bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50' : 'bg-red-500 shadow-lg shadow-red-500/50'}`} />
                          <span className="text-sm tracking-[0.2em] font-mono uppercase" 
                                style={{ color: isPlaying ? '#34d399' : '#f87171', textShadow: `0 0 10px ${isPlaying ? 'rgba(52, 211, 153, 0.8)' : 'rgba(248, 113, 113, 0.8)'}`, fontFamily: '"VT323", monospace' }}>
                            {isPlaying ? '▶ NOW PLAYING' : '⏸ PAUSED'}
                          </span>
                          {/* Audio FX indicator */}
                          {audioFxEnabled && <span className="text-[10px] text-purple-400 ml-2">🎛️ FX</span>}
                        </div>
                        
                        {/* Track Title */}
                        <h2 className={`font-black text-center leading-tight mb-3 ${screenGlitch ? 'animate-text-glitch' : ''}`}
                            style={{ background: 'linear-gradient(135deg, #c084fc, #22d3ee, #f472b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                              textShadow: '0 0 30px rgba(168, 85, 247, 0.5)', fontFamily: '"VT323", monospace', fontSize: '1.8rem', letterSpacing: '0.05em' }}>
                          {track.title}
                        </h2>
                        
                        {/* Artist */}
                        <p className="text-lg font-mono text-pink-300 mb-1" style={{ textShadow: '0 0 10px rgba(244, 114, 182, 0.6)', fontFamily: '"VT323", monospace' }}>
                          {track.artist}
                        </p>
                        
                        {/* Year */}
                        <span className="text-sm font-mono text-slate-400 mb-5" style={{ fontFamily: '"VT323", monospace' }}>{track.year}</span>
                        
                        {/* Playback controls */}
                        <div className="flex items-center gap-3 mb-4">
                          <button onClick={prevTrack} className="p-2 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            <SkipBack className="w-4 h-4 text-cyan-400" />
                          </button>
                          <button onClick={togglePlay} className={`p-3.5 rounded-full transition-all hover:scale-110 border-2 ${isPlaying ? 'bg-emerald-500/30 border-emerald-500/50 hover:bg-emerald-500/50' : 'bg-purple-500/30 border-purple-500/50 hover:bg-purple-500/50'}`}>
                            {isPlaying ? <Pause className="w-5 h-5 text-emerald-400" /> : <Play className="w-5 h-5 text-purple-400" />}
                          </button>
                          <button onClick={nextTrack} className="p-2 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            <SkipForward className="w-4 h-4 text-cyan-400" />
                          </button>
                          <button onClick={toggleMute} className="p-2 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4 text-cyan-400" />}
                          </button>
                          <button onClick={toggleAudioFx} className={`p-2 rounded-full transition-all hover:scale-110 border ${audioFxEnabled ? 'bg-purple-500/30 border-purple-500/50' : 'bg-slate-800/60 border-slate-600/50'}`}
                                  title="Audio Effects (Reverb/Noise)">
                            <Radio className={`w-4 h-4 ${audioFxEnabled ? 'text-purple-400' : 'text-slate-500'}`} />
                          </button>
                        </div>
                        
                        {/* Track dots */}
                        <div className="flex items-center gap-2 mb-4">
                          {playlist.map((_, i) => (
                            <button key={i} onClick={() => { setCurrentTrack(i); if (isPlaying) playTrack(i); }}
                              className={`w-2.5 h-2.5 rounded-full transition-all ${i === currentTrack ? 'bg-purple-400 scale-150 shadow-lg shadow-purple-400/60' : 'bg-slate-600 hover:bg-slate-500 hover:scale-125'}`} />
                          ))}
                        </div>
                        
                        {/* External links */}
                        <div className="flex items-center gap-3">
                          <a href={`https://open.spotify.com/track/${track.spotifyId}`} target="_blank" rel="noopener noreferrer"
                             className="px-4 py-1.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/40 transition-all border border-emerald-500/30">
                            🎵 Spotify
                          </a>
                          <a href={`https://www.youtube.com/watch?v=${track.youtubeId}`} target="_blank" rel="noopener noreferrer"
                             className="px-4 py-1.5 text-xs font-bold rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/40 transition-all border border-red-500/30">
                            ▶️ YouTube
                          </a>
                        </div>
                      </div>
                      
                      {/* Corner decorations */}
                      <div className="absolute top-3 left-3 w-4 h-4 border-l-2 border-t-2 border-cyan-500/40 rounded-tl" />
                      <div className="absolute top-3 right-3 w-4 h-4 border-r-2 border-t-2 border-cyan-500/40 rounded-tr" />
                      <div className="absolute bottom-3 left-3 w-4 h-4 border-l-2 border-b-2 border-purple-500/40 rounded-bl" />
                      <div className="absolute bottom-3 right-3 w-4 h-4 border-r-2 border-b-2 border-purple-500/40 rounded-br" />
                    </div>
                  </div>
                </div>
              </div>

              {/* RIGHT CASSETTE TAPE */}
              <div className="relative w-44 h-56 flex-shrink-0 -ml-4 z-10">
                {/* Cassette slot */}
                <div className="absolute inset-0 bg-gradient-to-l from-amber-900 via-amber-800 to-amber-700 rounded-r-2xl border-r-4 border-y-4 border-amber-600 shadow-2xl overflow-hidden">
                  <div className="absolute inset-0 opacity-20" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                  <div className="absolute top-3 bottom-3 left-0 w-3 bg-black/80 rounded-r" />
                  {/* Retro label */}
                  <div className="absolute top-2 left-6 right-2 h-8 bg-gradient-to-r from-blue-800 to-blue-900 rounded flex items-center justify-center border border-blue-700">
                    <span className="text-[8px] font-bold text-cyan-300 tracking-wider" style={{ fontFamily: '"VT323", monospace' }}>♫ MIXTAPE ♫</span>
                  </div>
                  {/* Equalizer INSIDE the panel */}
                  {isPlaying && (
                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1 items-end">
                      {[5, 7, 4, 6, 5, 7, 4, 6, 5].map((h, i) => (
                        <div key={i} className="w-1.5 bg-gradient-to-t from-pink-500 to-pink-300 rounded-t animate-bounce shadow-lg shadow-pink-400/50"
                             style={{ height: `${h * 3}px`, animationDelay: `${i * 50}ms`, animationDuration: '0.45s' }} />
                      ))}
                    </div>
                  )}
                </div>
                
                {/* Cassette tape */}
                <div className="absolute top-16 left-1/2 -translate-x-1/2 w-32 h-20 rounded-lg shadow-2xl overflow-hidden"
                     style={{ background: 'linear-gradient(180deg, #374151 0%, #1f2937 50%, #374151 100%)' }}>
                  {/* Label */}
                  <div className="absolute top-1 left-1 right-1 h-7 rounded bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-500 flex flex-col items-center justify-center px-1">
                    <span className="text-[7px] font-bold text-white tracking-wider">STELLAR HITS</span>
                    <span className="text-[5px] text-white/80 truncate w-full text-center">{track.artist}</span>
                  </div>
                  {/* Tape reels */}
                  <div className="absolute bottom-2 left-3 w-7 h-7 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center overflow-hidden">
                    <div className="w-5 h-5 rounded-full bg-gradient-to-br from-amber-800 to-amber-950" style={{ transform: `rotate(${vinylRotation}deg)` }}>
                      <div className="absolute inset-0.5 rounded-full border border-amber-700/50" />
                    </div>
                  </div>
                  <div className="absolute bottom-2 right-3 w-7 h-7 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center overflow-hidden">
                    <div className="w-5 h-5 rounded-full bg-gradient-to-br from-amber-800 to-amber-950" style={{ transform: `rotate(${-vinylRotation}deg)` }}>
                      <div className="absolute inset-0.5 rounded-full border border-amber-700/50" />
                    </div>
                  </div>
                  {/* Tape window */}
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-10 h-4 bg-slate-900/90 rounded-sm border border-slate-600 flex items-center justify-center">
                    <div className="w-6 h-2 bg-amber-900/50 rounded-sm" />
                  </div>
                  {/* Screw holes */}
                  <div className="absolute top-9 left-1.5 w-1.5 h-1.5 rounded-full bg-slate-500 shadow-inner" />
                  <div className="absolute top-9 right-1.5 w-1.5 h-1.5 rounded-full bg-slate-500 shadow-inner" />
                  {/* Noise */}
                  <div className="absolute inset-0 opacity-20 mix-blend-overlay animate-noise pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Jukebox Base */}
            <div className="flex justify-center mt-0 relative z-10">
              <div className="w-[540px] h-7 bg-gradient-to-b from-amber-700 to-amber-900 rounded-b-xl border-x-4 border-b-4 border-amber-600 relative overflow-hidden">
                <div className="absolute inset-0 opacity-20" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-slate-500 via-slate-300 to-slate-500" />
                <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-20 h-3.5 bg-slate-800 rounded-full border border-slate-600 flex items-center justify-center overflow-hidden">
                  <div className="w-10 h-1 bg-slate-900 rounded-full" />
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
                </div>
              </div>
            </div>
            {/* Legs */}
            <div className="flex justify-center gap-[440px] -mt-0.5 relative z-10">
              <div className="w-6 h-10 rounded-b transform -skew-x-6 border-l border-b border-amber-600" style={{ background: 'linear-gradient(180deg, #b45309, #78350f, #451a03)' }} />
              <div className="w-6 h-10 rounded-b transform skew-x-6 border-r border-b border-amber-600" style={{ background: 'linear-gradient(180deg, #b45309, #78350f, #451a03)' }} />
            </div>
            {/* Ambient glow */}
            <div className={`absolute -inset-16 rounded-full blur-3xl pointer-events-none transition-opacity duration-500 ${isPlaying ? 'opacity-100' : 'opacity-30'}`}
                 style={{ background: 'radial-gradient(ellipse at center, rgba(168, 85, 247, 0.15), rgba(236, 72, 153, 0.1), transparent 70%)' }} />
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
                  <span className="glitch-wrapper"><span className="glitch-text" data-text="Stellar Media">Stellar Media</span></span>
                </h3>
                <p className="text-sm text-slate-400 font-semibold">Organizer Pro v3.1</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
              Professional media organization tool with IMDB/MusicBrainz integration, GPU video conversion, and audio enhancement for Plex & Jellyfin.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Star className="h-4 w-4 text-yellow-400 animate-pulse" />
              <span className="font-medium">Built for media enthusiasts</span>
            </div>
          </div>

          {/* Features section */}
          <div className="space-y-5 group/features">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-2 border-yellow-500/30 group-hover/features:border-yellow-400/50 transition-all">
                <Zap className="h-6 w-6 text-yellow-400" />
              </div>
              <span className="glitch-wrapper"><span className="glitch-text" data-text="Features">Features</span></span>
            </h4>
            <ul className="space-y-3 text-sm text-slate-400">
              {[
                { color: 'emerald', text: 'Smart file renaming with metadata' },
                { color: 'purple', text: 'GPU-accelerated video conversion' },
                { color: 'cyan', text: 'Professional audio enhancement' },
                { color: 'pink', text: 'NAS integration (Synology/Unraid)' },
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 group cursor-default p-2 -mx-2 rounded-lg hover:bg-white/5 transition-all">
                  <span className={`w-3 h-3 rounded-full bg-${item.color}-400 group-hover:scale-150 group-hover:shadow-lg group-hover:shadow-${item.color}-400/60 transition-all duration-300`} />
                  <span className={`group-hover:text-${item.color}-300 group-hover:translate-x-1 transition-all font-medium`}>{item.text}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Connect section */}
          <div className="space-y-5 group/connect">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-2 border-cyan-500/30 group-hover/connect:border-cyan-400/50 transition-all">
                <Sparkles className="h-6 w-6 text-cyan-400" />
              </div>
              <span className="glitch-wrapper"><span className="glitch-text" data-text="Connect">Connect</span></span>
            </h4>
            <div className="flex items-center gap-5">
              {socialLinks.map((social, index) => (
                <a key={social.name} href={social.url} target="_blank" rel="noopener noreferrer"
                   className={`social-icon ${social.className} p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-purple-500/50 hover:bg-purple-500/10 hover:scale-125 hover:shadow-lg hover:shadow-purple-500/20 transition-all duration-300`}
                   title={social.name} style={{ animationDelay: `${index * 0.1}s` }}>
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

        {/* Divider */}
        <div className="relative h-[2px] mb-8">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/40 to-transparent animate-pulse" />
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-sm">
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>© {currentYear}</span>
            <span className="footer-glitch-text font-bold text-slate-400" data-text="Stellar Media Organizer">Stellar Media Organizer</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>Made with</span>
            <Heart className="h-5 w-5 text-pink-500 animate-pulse" />
            <span>by</span>
            <a href="https://github.com/sharvinzlife" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 transition-colors font-bold hover:underline">sharvinzlife</a>
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
