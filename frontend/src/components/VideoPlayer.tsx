import { useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize2 } from 'lucide-react';
import { useState } from 'react';

interface VideoPlayerProps {
  src?: string;
  seekTo?: number;
  cameraName?: string;
  autoPlay?: boolean;
  muted?: boolean;
  className?: string;
  onTimeUpdate?: (time: number) => void;
}

export default function VideoPlayer({
  src,
  seekTo,
  cameraName,
  autoPlay = false,
  muted: initialMuted = true,
  className = '',
  onTimeUpdate,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(initialMuted);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Seek when timestamp changes from parent
  useEffect(() => {
    if (seekTo !== undefined && videoRef.current) {
      videoRef.current.currentTime = seekTo;
      videoRef.current.play().catch(() => {});
      setPlaying(true);
    }
  }, [seekTo]);

  // Auto-play
  useEffect(() => {
    if (autoPlay && src && videoRef.current) {
      videoRef.current.play().catch(() => {});
      setPlaying(true);
    }
  }, [autoPlay, src]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play().catch(() => {});
      setPlaying(true);
    } else {
      v.pause();
      setPlaying(false);
    }
  }, []);

  const toggleMute = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  }, []);

  const handleFullscreen = useCallback(() => {
    videoRef.current?.requestFullscreen?.();
  }, []);

  const handleTimeUpdate = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    setCurrentTime(v.currentTime);
    onTimeUpdate?.(v.currentTime);
  }, [onTimeUpdate]);

  const handleScrub = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Number(e.target.value);
  }, []);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  return (
    <div className={`video-container rounded-lg overflow-hidden bg-black ${className}`}>
      {src ? (
        <>
          <video
            ref={videoRef}
            src={src}
            muted={muted}
            playsInline
            className="w-full h-full object-cover"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
          />

          {/* Overlay controls */}
          <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 hover:opacity-100 transition-opacity duration-200">
            {/* Scrubber */}
            <div className="px-3 pb-1">
              <input
                type="range"
                min={0}
                max={duration || 0}
                value={currentTime}
                step={0.1}
                onChange={handleScrub}
                className="w-full h-1 accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Controls bar */}
            <div className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={togglePlay}
                  className="text-white/90 hover:text-white transition-colors"
                >
                  {playing
                    ? <Pause size={15} />
                    : <Play size={15} />}
                </button>
                <button
                  onClick={toggleMute}
                  className="text-white/70 hover:text-white transition-colors"
                >
                  {muted ? <VolumeX size={13} /> : <Volume2 size={13} />}
                </button>
                <span className="mono text-[10px] text-white/60">
                  {fmt(currentTime)} / {fmt(duration)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {cameraName && (
                  <span className="text-[10px] text-white/50 font-medium truncate max-w-[120px]">
                    {cameraName}
                  </span>
                )}
                <button
                  onClick={handleFullscreen}
                  className="text-white/70 hover:text-white transition-colors"
                >
                  <Maximize2 size={13} />
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        // No source placeholder
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="w-10 h-10 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center mb-2">
            <Play size={16} className="text-slate-600 ml-0.5" />
          </div>
          <p className="text-slate-600 text-xs font-medium">No video source</p>
          <p className="text-slate-700 text-[10px] mt-0.5">Upload a video to begin</p>
        </div>
      )}
    </div>
  );
}
