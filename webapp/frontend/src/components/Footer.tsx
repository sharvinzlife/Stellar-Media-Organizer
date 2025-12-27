import React, { useState, useEffect, useRef } from 'react';
import { Github, Instagram, Twitter, Facebook, Heart, Sparkles, Code2, Zap, Star, Play, Pause, SkipForward, SkipBack, Volume2, VolumeX, Radio } from 'lucide-react';

// Classic uplifting songs playlist with lyrics snippets
const playlist = [
  { title: "Don't Stop Believin'", artist: "Journey", year: 1981, youtubeId: "1k8craCGpgs",
    lyrics: ["Just a small town girl", "Livin' in a lonely world", "She took the midnight train", "Goin' anywhere"] },
  { title: "Here Comes The Sun", artist: "The Beatles", year: 1969, youtubeId: "KQetemT1sWc",
    lyrics: ["Here comes the sun", "And I say, it's all right", "Little darling", "It's been a long cold lonely winter"] },
  { title: "Walking on Sunshine", artist: "Katrina & The Waves", year: 1985, youtubeId: "iPUmE-tne5U",
    lyrics: ["I'm walking on sunshine", "And don't it feel good!", "I'm walking on sunshine", "And don't it feel good!"] },
  { title: "September", artist: "Earth, Wind & Fire", year: 1978, youtubeId: "Gs069dndIYk",
    lyrics: ["Do you remember", "The 21st night of September?", "Love was changin' the minds", "Of pretenders"] },
  { title: "I Gotta Feeling", artist: "Black Eyed Peas", year: 2009, youtubeId: "uSD4vsh1zDA",
    lyrics: ["I gotta feeling", "That tonight's gonna be a good night", "That tonight's gonna be a good night", "A good, good night"] },
  { title: "Happy", artist: "Pharrell Williams", year: 2013, youtubeId: "ZbZSe6N_BXs",
    lyrics: ["Because I'm happy", "Clap along if you feel", "Like a room without a roof", "Clap along if you feel like happiness is the truth"] },
  { title: "Uptown Funk", artist: "Bruno Mars", year: 2014, youtubeId: "OPf0YbXqDm0",
    lyrics: ["Don't believe me just watch!", "Uptown funk you up", "Uptown funk you up", "Saturday night and we in the spot"] },
  { title: "Livin' on a Prayer", artist: "Bon Jovi", year: 1986, youtubeId: "lDK9QqIzhwk",
    lyrics: ["Whoa, we're half way there", "Whoa, livin' on a prayer", "Take my hand, we'll make it I swear", "Whoa, livin' on a prayer"] },
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
  const [currentLyricIndex, setCurrentLyricIndex] = useState(0);
  const animationRef = useRef<number>();
  const playerRef = useRef<YT.Player | null>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);

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
        height: '0', width: '0',
        videoId: playlist[0].youtubeId,
        playerVars: { autoplay: 0, controls: 0, disablekb: 1, fs: 0, modestbranding: 1, rel: 0 },
        events: {
          onReady: () => setPlayerReady(true),
          onStateChange: (event: any) => {
            // Sync play state with YouTube player state
            const state = event.data;
            if (state === (window as any).YT.PlayerState.PLAYING) {
              setIsPlaying(true);
            } else if (state === (window as any).YT.PlayerState.PAUSED) {
              setIsPlaying(false);
            } else if (state === (window as any).YT.PlayerState.ENDED) {
              nextTrack();
            }
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

  // Lyrics rotation when playing
  useEffect(() => {
    if (isPlaying) {
      const lyricsInterval = setInterval(() => {
        setCurrentLyricIndex(prev => (prev + 1) % playlist[currentTrack].lyrics.length);
      }, 3000);
      return () => clearInterval(lyricsInterval);
    }
  }, [isPlaying, currentTrack]);

  // Reset lyrics when track changes
  useEffect(() => {
    setCurrentLyricIndex(0);
  }, [currentTrack]);

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
    } else {
      // If first time playing this track, load it
      playerRef.current?.playVideo();
    }
  };

  const toggleMute = () => {
    if (playerRef.current) {
      isMuted ? playerRef.current.unMute() : playerRef.current.mute();
      setIsMuted(!isMuted);
    }
  };

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
              <div className="flex items-center justify-center h-full pt-4">
                <span className="text-xl font-black tracking-[0.25em] text-transparent bg-clip-text bg-gradient-to-r from-pink-400 via-purple-400 to-cyan-400"
                      style={{ textShadow: '0 0 20px rgba(236, 72, 153, 0.8)', fontFamily: '"VT323", monospace' }}>
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
                  <div className="absolute top-2 left-2 right-6 h-7 bg-gradient-to-r from-red-800 to-red-900 rounded flex items-center justify-center border border-red-700">
                    <span className="text-[7px] font-bold text-yellow-300 tracking-wider" style={{ fontFamily: '"VT323", monospace' }}>♪ NOW SPINNING ♪</span>
                  </div>
                </div>
                
                {/* Vinyl record - moved down */}
                <div className="absolute top-14 left-1/2 w-28 h-28 rounded-full shadow-2xl"
                     style={{ transform: `translateX(-50%) rotate(${vinylRotation}deg)`, background: '#1a1a1a',
                       boxShadow: isPlaying ? '0 0 30px rgba(168, 85, 247, 0.5), inset 0 0 20px rgba(0,0,0,0.9)' : 'inset 0 0 20px rgba(0,0,0,0.9)' }}>
                  <div className="absolute inset-0 rounded-full" style={{ background: 'repeating-radial-gradient(circle at center, transparent 0px, transparent 1px, rgba(40,40,40,0.8) 1px, rgba(40,40,40,0.8) 2px)' }} />
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/10 via-transparent to-transparent" />
                  {/* Center label */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full overflow-hidden"
                       style={{ background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%)' }}>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-[4px] font-bold text-yellow-300">STELLAR</span>
                      <span className="text-[4px] font-black text-white text-center leading-tight truncate w-full px-0.5" style={{ fontFamily: '"VT323", monospace' }}>
                        {track.title.length > 8 ? track.title.substring(0, 8) + '..' : track.title}
                      </span>
                    </div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-black" />
                  </div>
                </div>
                
                {/* Equalizer - moved down with more space from vinyl */}
                {isPlaying && (
                  <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-0.5 items-end">
                    {[3, 5, 4, 6, 3, 5, 4, 6, 3].map((h, i) => (
                      <div key={i} className="w-1 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t animate-bounce shadow-lg shadow-emerald-400/50"
                           style={{ height: `${h * 2.5}px`, animationDelay: `${i * 40}ms`, animationDuration: '0.4s' }} />
                    ))}
                  </div>
                )}
              </div>

              {/* CENTER - TV SCREEN - More compact content */}
              <div className={`relative w-[400px] h-[300px] bg-gradient-to-b from-amber-700 via-amber-800 to-amber-900 rounded-2xl p-2.5 shadow-2xl border-4 border-amber-600 ${intensiveGlitch ? 'animate-tv-shake' : ''}`}>
                <div className="absolute inset-0 opacity-20 rounded-2xl" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                
                {/* Inner frame */}
                <div className="w-full h-full bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 rounded-xl p-1.5 border-2 border-slate-600 relative">
                  {/* Screen bezel */}
                  <div className="relative w-full h-full bg-gradient-to-b from-slate-500 via-slate-600 to-slate-700 rounded-lg p-1.5 border border-slate-400 shadow-inner">
                    {/* CRT Screen */}
                    <div className="relative w-full h-full bg-black rounded overflow-hidden">
                      {/* Background gradient */}
                      <div className="absolute inset-0 opacity-20" style={{ background: `linear-gradient(${colorShift}deg, rgba(168, 85, 247, 0.4), rgba(34, 211, 238, 0.4), rgba(236, 72, 153, 0.4))` }} />
                      {/* Scanlines */}
                      <div className="absolute inset-0 pointer-events-none z-20 opacity-25" style={{ background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.4) 2px, rgba(0,0,0,0.4) 4px)' }} />
                      {/* CRT curvature */}
                      <div className="absolute inset-0 shadow-[inset_0_0_40px_rgba(0,0,0,0.9)] rounded" />
                      {/* Glitch lines */}
                      {(screenGlitch || intensiveGlitch) && (
                        <>
                          <div className="absolute left-0 right-0 h-0.5 bg-cyan-400/60 z-30" style={{ top: '25%' }} />
                          <div className="absolute left-0 right-0 h-1 bg-white/5 z-30" style={{ top: '55%' }} />
                        </>
                      )}
                      {/* Noise overlay */}
                      <div className={`absolute inset-0 mix-blend-overlay animate-noise pointer-events-none z-10 ${audioFxEnabled ? 'opacity-12' : 'opacity-5'}`} />

                      {/* Screen content - COMPACT */}
                      <div className={`relative z-10 flex flex-col items-center justify-between h-full py-3 px-4 ${screenGlitch ? 'animate-screen-glitch' : ''} ${intensiveGlitch ? 'animate-intensive-glitch' : ''}`}>
                        {/* Status indicator */}
                        <div className="flex items-center gap-1.5">
                          <div className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
                          <span className="text-[10px] tracking-[0.15em] font-mono uppercase" 
                                style={{ color: isPlaying ? '#34d399' : '#f87171', textShadow: `0 0 8px currentColor`, fontFamily: '"VT323", monospace' }}>
                            {isPlaying ? '▶ PLAYING' : '⏸ PAUSED'}
                          </span>
                          {audioFxEnabled && <span className="text-[8px] text-purple-400 ml-1">FX</span>}
                        </div>
                        
                        {/* Track Title - smaller */}
                        <h2 className={`font-black text-center leading-none ${screenGlitch ? 'animate-text-glitch' : ''}`}
                            style={{ background: 'linear-gradient(135deg, #c084fc, #22d3ee, #f472b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                              fontFamily: '"VT323", monospace', fontSize: '1.4rem', letterSpacing: '0.03em' }}>
                          {track.title}
                        </h2>
                        
                        {/* Artist & Year - single line */}
                        <p className="text-sm font-mono text-pink-300" style={{ textShadow: '0 0 8px rgba(244, 114, 182, 0.5)', fontFamily: '"VT323", monospace' }}>
                          {track.artist} • {track.year}
                        </p>
                        
                        {/* Lyrics display */}
                        <div className="h-10 flex items-center justify-center overflow-hidden">
                          <p className={`text-xs text-center text-cyan-300/80 italic transition-all duration-500 ${isPlaying ? 'opacity-100' : 'opacity-40'}`}
                             style={{ fontFamily: '"VT323", monospace', textShadow: '0 0 10px rgba(34, 211, 238, 0.5)' }}>
                            "{track.lyrics[currentLyricIndex]}"
                          </p>
                        </div>
                        
                        {/* Playback controls - compact */}
                        <div className="flex items-center gap-2">
                          <button onClick={prevTrack} className="p-1.5 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            <SkipBack className="w-3.5 h-3.5 text-cyan-400" />
                          </button>
                          <button onClick={togglePlay} className={`p-2.5 rounded-full transition-all hover:scale-110 border-2 ${isPlaying ? 'bg-emerald-500/30 border-emerald-500/50' : 'bg-purple-500/30 border-purple-500/50'}`}>
                            {isPlaying ? <Pause className="w-4 h-4 text-emerald-400" /> : <Play className="w-4 h-4 text-purple-400" />}
                          </button>
                          <button onClick={nextTrack} className="p-1.5 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            <SkipForward className="w-3.5 h-3.5 text-cyan-400" />
                          </button>
                          <button onClick={toggleMute} className="p-1.5 rounded-full bg-slate-800/60 hover:bg-slate-700/60 transition-all hover:scale-110 border border-slate-600/50">
                            {isMuted ? <VolumeX className="w-3.5 h-3.5 text-red-400" /> : <Volume2 className="w-3.5 h-3.5 text-cyan-400" />}
                          </button>
                          <button onClick={() => setAudioFxEnabled(!audioFxEnabled)} className={`p-1.5 rounded-full transition-all hover:scale-110 border ${audioFxEnabled ? 'bg-purple-500/30 border-purple-500/50' : 'bg-slate-800/60 border-slate-600/50'}`}>
                            <Radio className={`w-3.5 h-3.5 ${audioFxEnabled ? 'text-purple-400' : 'text-slate-500'}`} />
                          </button>
                        </div>
                        
                        {/* Track dots - smaller */}
                        <div className="flex items-center gap-1.5">
                          {playlist.map((_, i) => (
                            <button key={i} onClick={() => { setCurrentTrack(i); if (isPlaying) playTrack(i); }}
                              className={`w-1.5 h-1.5 rounded-full transition-all ${i === currentTrack ? 'bg-purple-400 scale-150 shadow-lg shadow-purple-400/60' : 'bg-slate-600 hover:bg-slate-500'}`} />
                          ))}
                        </div>
                      </div>
                      
                      {/* Corner decorations */}
                      <div className="absolute top-2 left-2 w-3 h-3 border-l border-t border-cyan-500/30 rounded-tl" />
                      <div className="absolute top-2 right-2 w-3 h-3 border-r border-t border-cyan-500/30 rounded-tr" />
                      <div className="absolute bottom-2 left-2 w-3 h-3 border-l border-b border-purple-500/30 rounded-bl" />
                      <div className="absolute bottom-2 right-2 w-3 h-3 border-r border-b border-purple-500/30 rounded-br" />
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
                  <div className="absolute top-2 left-6 right-2 h-7 bg-gradient-to-r from-blue-800 to-blue-900 rounded flex items-center justify-center border border-blue-700">
                    <span className="text-[7px] font-bold text-cyan-300 tracking-wider" style={{ fontFamily: '"VT323", monospace' }}>♫ MIXTAPE ♫</span>
                  </div>
                </div>
                
                {/* Cassette tape - moved down */}
                <div className="absolute top-14 left-1/2 -translate-x-1/2 w-28 h-18 rounded-lg shadow-2xl overflow-hidden"
                     style={{ background: 'linear-gradient(180deg, #374151 0%, #1f2937 50%, #374151 100%)' }}>
                  {/* Label */}
                  <div className="absolute top-0.5 left-0.5 right-0.5 h-6 rounded bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-500 flex flex-col items-center justify-center">
                    <span className="text-[6px] font-bold text-white tracking-wider">STELLAR HITS</span>
                    <span className="text-[4px] text-white/80 truncate w-full text-center">{track.artist}</span>
                  </div>
                  {/* Tape reels */}
                  <div className="absolute bottom-1.5 left-2 w-6 h-6 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-gradient-to-br from-amber-800 to-amber-950" style={{ transform: `rotate(${vinylRotation}deg)` }} />
                  </div>
                  <div className="absolute bottom-1.5 right-2 w-6 h-6 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-gradient-to-br from-amber-800 to-amber-950" style={{ transform: `rotate(${-vinylRotation}deg)` }} />
                  </div>
                  {/* Tape window */}
                  <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-3 bg-slate-900/90 rounded-sm border border-slate-600" />
                </div>
                
                {/* Equalizer - moved down */}
                {isPlaying && (
                  <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-0.5 items-end">
                    {[4, 6, 3, 5, 4, 6, 3, 5, 4].map((h, i) => (
                      <div key={i} className="w-1 bg-gradient-to-t from-pink-500 to-pink-300 rounded-t animate-bounce shadow-lg shadow-pink-400/50"
                           style={{ height: `${h * 2.5}px`, animationDelay: `${i * 50}ms`, animationDuration: '0.45s' }} />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Jukebox Base */}
            <div className="flex justify-center mt-0 relative z-10">
              <div className="w-[540px] h-6 bg-gradient-to-b from-amber-700 to-amber-900 rounded-b-xl border-x-4 border-b-4 border-amber-600 relative overflow-hidden">
                <div className="absolute inset-0 opacity-20" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(139, 69, 19, 0.4) 3px, rgba(139, 69, 19, 0.4) 6px)' }} />
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-slate-500 via-slate-300 to-slate-500" />
                <div className="absolute top-1 left-1/2 -translate-x-1/2 w-16 h-3 bg-slate-800 rounded-full border border-slate-600 flex items-center justify-center">
                  <div className="w-8 h-0.5 bg-slate-900 rounded-full" />
                </div>
              </div>
            </div>
            {/* Legs */}
            <div className="flex justify-center gap-[440px] -mt-0.5 relative z-10">
              <div className="w-5 h-8 rounded-b transform -skew-x-6 border-l border-b border-amber-600" style={{ background: 'linear-gradient(180deg, #b45309, #78350f, #451a03)' }} />
              <div className="w-5 h-8 rounded-b transform skew-x-6 border-r border-b border-amber-600" style={{ background: 'linear-gradient(180deg, #b45309, #78350f, #451a03)' }} />
            </div>
            {/* Ambient glow */}
            <div className={`absolute -inset-12 rounded-full blur-3xl pointer-events-none transition-opacity duration-500 ${isPlaying ? 'opacity-100' : 'opacity-30'}`}
                 style={{ background: 'radial-gradient(ellipse at center, rgba(168, 85, 247, 0.12), rgba(236, 72, 153, 0.08), transparent 70%)' }} />
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
              Professional media organization with IMDB/MusicBrainz integration, GPU conversion, and audio enhancement.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Star className="h-4 w-4 text-yellow-400 animate-pulse" />
              <span className="font-medium">Built for media enthusiasts</span>
            </div>
          </div>

          {/* Features section */}
          <div className="space-y-5 group/features">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-2 border-yellow-500/30 transition-all">
                <Zap className="h-6 w-6 text-yellow-400" />
              </div>
              <span className="glitch-wrapper"><span className="glitch-text" data-text="Features">Features</span></span>
            </h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li className="flex items-center gap-3 group cursor-default p-1.5 -mx-1.5 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="group-hover:text-emerald-300 transition-all font-medium">Smart file renaming</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-1.5 -mx-1.5 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                <span className="group-hover:text-purple-300 transition-all font-medium">GPU video conversion</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-1.5 -mx-1.5 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                <span className="group-hover:text-cyan-300 transition-all font-medium">Audio enhancement</span>
              </li>
              <li className="flex items-center gap-3 group cursor-default p-1.5 -mx-1.5 rounded-lg hover:bg-white/5 transition-all">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-400" />
                <span className="group-hover:text-pink-300 transition-all font-medium">NAS integration</span>
              </li>
            </ul>
          </div>

          {/* Connect section */}
          <div className="space-y-5 group/connect">
            <h4 className="font-black text-white flex items-center gap-3 text-xl">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-2 border-cyan-500/30 transition-all">
                <Sparkles className="h-6 w-6 text-cyan-400" />
              </div>
              <span className="glitch-wrapper"><span className="glitch-text" data-text="Connect">Connect</span></span>
            </h4>
            <div className="flex items-center gap-4">
              {socialLinks.map((social, index) => (
                <a key={social.name} href={social.url} target="_blank" rel="noopener noreferrer"
                   className={`social-icon ${social.className} p-2.5 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-purple-500/50 hover:scale-125 transition-all duration-300`}
                   title={social.name}>
                  <social.icon className="h-5 w-5 text-slate-400 hover:text-white transition-colors" />
                </a>
              ))}
            </div>
            <p className="text-sm text-slate-500 flex items-center gap-2 font-medium">
              <span className="text-purple-400 animate-pulse">@</span>
              <span>sharvinzlife everywhere</span>
            </p>
          </div>
        </div>

        {/* Divider */}
        <div className="relative h-[2px] mb-6">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/40 to-transparent animate-pulse" />
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>© {currentYear}</span>
            <span className="footer-glitch-text font-bold text-slate-400" data-text="Stellar Media Organizer">Stellar Media Organizer</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <span>Made with</span>
            <Heart className="h-4 w-4 text-pink-500 animate-pulse" />
            <span>by</span>
            <a href="https://github.com/sharvinzlife" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 font-bold">sharvinzlife</a>
          </div>
          <div className="flex items-center gap-2 text-slate-500 font-medium">
            <Code2 className="h-4 w-4 text-emerald-400" />
            <span>React + FastAPI + FFmpeg</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
