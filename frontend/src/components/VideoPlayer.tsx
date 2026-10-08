import { useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize2 } from 'lucide-react';
import { useState } from 'react';

export interface HighlightBox {
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  norm_x?: number;
  norm_y?: number;
  norm_w?: number;
  norm_h?: number;
  label?: string;
}

interface VideoPlayerProps {
  src?: string;
  seekTo?: number;
  cameraName?: string;
  autoPlay?: boolean;
  muted?: boolean;
  loop?: boolean;
  showControls?: boolean;
  className?: string;
  highlightBox?: HighlightBox;
  onTimeUpdate?: (time: number) => void;
  onError?: () => void;
}

export default function VideoPlayer({
  src,
  seekTo,
  cameraName,
  autoPlay = false,
  muted: initialMuted = true,
  loop = false,
  showControls = true,
  className = '',
  highlightBox,
  onTimeUpdate,
  onError,
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

  // Auto-play without waiting on React state for preview loops
  useEffect(() => {
    const video = videoRef.current;
    if (!autoPlay || !src || !video) return;
    video.muted = true;
    const playPromise = video.play();
    if (playPromise) {
      playPromise.then(() => setPlaying(true)).catch(() => {});
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
    onTimeUpdate?.(v.currentTime);
    if (!showControls) return;
    setCurrentTime(v.currentTime);
  }, [onTimeUpdate, showControls]);

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
            loop={loop}
            autoPlay={autoPlay}
            playsInline
            preload="auto"
            disablePictureInPicture
            disableRemotePlayback
            className="w-full h-full object-cover [transform:translateZ(0)]"
            onTimeUpdate={showControls || onTimeUpdate ? handleTimeUpdate : undefined}
            onLoadedMetadata={() => {
              if (showControls) {
                setDuration(videoRef.current?.duration || 0);
              }
            }}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onError={onError}
          />

          {/* Target Bounding Box Overlay (Single Requested Object Only) */}
          {highlightBox && highlightBox.norm_w && highlightBox.norm_h && (
            <div
              className="absolute pointer-events-none transition-all duration-150 z-20"
              style={{
                left: `${Math.max(0, Math.min(100, (highlightBox.norm_x ?? 0) * 100))}%`,
                top: `${Math.max(0, Math.min(100, (highlightBox.norm_y ?? 0) * 100))}%`,
                width: `${Math.max(2, Math.min(100, (highlightBox.norm_w ?? 0) * 100))}%`,
                height: `${Math.max(2, Math.min(100, (highlightBox.norm_h ?? 0) * 100))}%`,
              }}
            >
              <div className="w-full h-full border-2 border-cyan-400 bg-cyan-400/10 rounded-sm relative shadow-[0_0_15px_rgba(6,182,212,0.45)]">
                {/* Corner bracket accents */}
                <div className="absolute -top-1 -left-1 w-2.5 h-2.5 border-t-2 border-l-2 border-cyan-300" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 border-t-2 border-r-2 border-cyan-300" />
                <div className="absolute -bottom-1 -left-1 w-2.5 h-2.5 border-b-2 border-l-2 border-cyan-300" />
                <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 border-b-2 border-r-2 border-cyan-300" />

                {/* Target badge */}
                {highlightBox.label && (
                  <div className="absolute -top-6 left-0 flex items-center gap-1.5 bg-black/90 border border-cyan-400/80 px-2 py-0.5 rounded text-[10px] font-mono font-bold text-cyan-300 whitespace-nowrap shadow-lg">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                    {highlightBox.label}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Overlay controls */}
          {showControls && (
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
          )}
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
