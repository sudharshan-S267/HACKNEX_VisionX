import { useState } from 'react';
import { Eye, Sparkles, AlertCircle } from 'lucide-react';
import VideoPlayer from './VideoPlayer';
import type { Camera } from '../types';

const DEMO_VIDEOS: Record<string, string> = {
  'CAM-01': '/demo/cam01-preview.mp4',
  'CAM-02': '/demo/cam02-preview.mp4',
  'CAM-03': '/demo/cam03-preview.mp4',
  'CAM-04': '/demo/cam04-preview.mp4',
};

interface CameraCardProps {
  camera: Camera;
  isSelected?: boolean;
  seekTo?: number;
  matchedTimestamp?: number;
  onOpen: (camera: Camera) => void;
}

export default function CameraCard({
  camera,
  isSelected,
  seekTo,
  matchedTimestamp,
  onOpen,
}: CameraCardProps) {
  const [hover, setHover] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const isOnline = camera.status === 'online';

  // Priority: 1. Real uploaded video, 2. Built-in CCTV preview, 3. Empty fallback
  const hasRealVideo = Boolean(camera.video_url);
  const demoPreviewSrc = DEMO_VIDEOS[camera.camera_id] || '/demo/cam01-preview.mp4';
  const effectiveVideoSrc = hasRealVideo
    ? camera.video_url
    : previewFailed
    ? undefined
    : demoPreviewSrc;

  const isPreviewMode = !hasRealVideo && Boolean(effectiveVideoSrc);

  return (
    <div
      className={`
        tactical-panel rounded-xl overflow-hidden cursor-pointer relative group
        transition-all duration-300
        ${isSelected 
          ? 'ring-2 ring-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.3)]' 
          : 'hover:border-cyan-500/40 hover:shadow-[0_0_20px_rgba(6,182,212,0.15)]'
        }
      `}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={() => onOpen(camera)}
    >
      {/* Reticle corner markers */}
      <div className="reticle-corner-tl" />
      <div className="reticle-corner-tr" />
      <div className="reticle-corner-bl" />
      <div className="reticle-corner-br" />

      {/* VIDEO PREVIEW CONTAINER */}
      <div className="relative aspect-video bg-black scan-line">
        <VideoPlayer
          src={effectiveVideoSrc}
          seekTo={hasRealVideo ? seekTo : undefined}
          cameraName={camera.camera_name}
          autoPlay={true}
          loop={isPreviewMode}
          muted={true}
          showControls={hasRealVideo}
          onError={() => {
            if (isPreviewMode) {
              setPreviewFailed(true);
            }
          }}
          className={`absolute inset-0 w-full h-full transition-opacity duration-300 ${hover ? 'brightness-110' : 'brightness-95'}`}
        />

        {/* TOP BAR: CAM ID, NAME & LIVE BADGE */}
        <div className="absolute top-0 left-0 right-0 flex items-center justify-between p-3 bg-gradient-to-b from-black/85 via-black/40 to-transparent z-10 pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="mono text-[11px] font-extrabold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/40 shadow-sm">
              {camera.camera_id}
            </span>
            <span className="text-xs font-bold text-white drop-shadow-md truncate max-w-[140px]">
              {camera.camera_name}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Active camera badge */}
            {isSelected && (
              <span className="text-[9px] font-extrabold tracking-wider mono bg-cyan-500 text-black px-1.5 py-0.5 rounded shadow-sm">
                ACTIVE
              </span>
            )}

            {/* Live/Offline status indicator */}
            <div
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold mono tracking-wider border ${
                isOnline
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
                  : 'bg-rose-950/80 text-rose-400 border-rose-500/40'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isOnline ? 'bg-emerald-400 pulse-dot' : 'bg-rose-500'
                }`}
              />
              {isOnline ? 'LIVE' : 'OFFLINE'}
            </div>
          </div>
        </div>

        {/* AI MATCH BADGE OVERLAY (When triggered by query) */}
        {matchedTimestamp !== undefined && (
          <div className="absolute top-12 left-3 z-20 flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/90 text-black font-mono text-[10px] font-extrabold shadow-glow-match animate-pulse">
            <Sparkles size={11} className="text-black" />
            <span>AI MATCH {matchedTimestamp.toFixed(1)}s</span>
          </div>
        )}

        {/* BOTTOM OVERLAY INFO: Events & Open button */}
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-2 bg-gradient-to-t from-black/90 via-black/50 to-transparent z-10">
          <div className="flex items-center gap-1.5">
            <AlertCircle size={11} className="text-amber-400" />
            <span className="text-[10px] text-amber-300 font-mono font-semibold">
              {camera.event_count || 0} events detected
            </span>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onOpen(camera);
            }}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-[10px] font-mono font-semibold transition-colors pointer-events-auto"
          >
            <Eye size={10} />
            OPEN
          </button>
        </div>
      </div>
    </div>
  );
}
