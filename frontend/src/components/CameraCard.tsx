import { useState } from 'react';
import { Eye, Circle, AlertCircle, Loader2, ZapOff } from 'lucide-react';
import VideoPlayer from './VideoPlayer';
import type { Camera } from '../types';

interface CameraCardProps {
  camera: Camera;
  isSelected?: boolean;
  seekTo?: number;
  onOpen: (camera: Camera) => void;
}

const STATUS_CONFIG = {
  online: {
    label: 'LIVE',
    icon: Circle,
    textClass: 'text-emerald-400',
    dotClass: 'bg-emerald-400',
    borderClass: 'border-emerald-500/20',
  },
  offline: {
    label: 'OFFLINE',
    icon: ZapOff,
    textClass: 'text-red-400',
    dotClass: 'bg-red-400',
    borderClass: 'border-red-500/15',
  },
  processing: {
    label: 'PROC.',
    icon: Loader2,
    textClass: 'text-yellow-400',
    dotClass: 'bg-yellow-400',
    borderClass: 'border-yellow-500/15',
  },
};

export default function CameraCard({ camera, isSelected, seekTo, onOpen }: CameraCardProps) {
  const [hover, setHover] = useState(false);
  const cfg = STATUS_CONFIG[camera.status];

  return (
    <div
      className={`
        glass glass-hover rounded-xl overflow-hidden cursor-pointer
        transition-all duration-200 relative
        ${isSelected ? 'result-card-selected' : ''}
        ${hover ? 'scale-[1.01]' : 'scale-100'}
      `}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={() => onOpen(camera)}
    >
      {/* Video / Thumbnail area */}
      <div className="relative aspect-video bg-black scan-line">
        <VideoPlayer
          src={camera.video_url}
          seekTo={seekTo}
          cameraName={camera.camera_name}
          className="absolute inset-0 w-full h-full"
          muted
        />

        {/* Top overlay: camera ID badge + status */}
        <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-3 py-2 bg-gradient-to-b from-black/70 to-transparent z-10">
          <div className="flex items-center gap-2">
            <span className="mono text-[10px] font-semibold text-blue-400 bg-blue-500/15 px-1.5 py-0.5 rounded border border-blue-500/20">
              {camera.camera_id}
            </span>
            <span className="text-[11px] font-medium text-white/80 truncate max-w-[100px]">
              {camera.camera_name}
            </span>
          </div>

          {/* Status indicator */}
          <div className={`flex items-center gap-1 ${cfg.textClass}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotClass} ${camera.status === 'online' ? 'pulse-dot' : ''}`} />
            <span className="text-[9px] font-bold mono tracking-wider">{cfg.label}</span>
          </div>
        </div>

        {/* Bottom overlay: event count + timestamp */}
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-2 bg-gradient-to-t from-black/70 to-transparent z-10">
          <div className="flex items-center gap-1">
            {camera.event_count > 0 ? (
              <>
                <AlertCircle size={11} className="text-yellow-400" />
                <span className="text-yellow-400 text-[10px] font-semibold mono">
                  {camera.event_count} event{camera.event_count !== 1 ? 's' : ''}
                </span>
              </>
            ) : (
              <span className="text-slate-600 text-[10px] mono">No events</span>
            )}
          </div>
          {camera.last_seen && (
            <span className="text-[10px] text-slate-500 mono">
              {new Date(camera.last_seen).toLocaleTimeString('en-US', {
                hour12: false, hour: '2-digit', minute: '2-digit',
              })}
            </span>
          )}
        </div>

        {/* Selected ring */}
        {isSelected && (
          <div className="absolute inset-0 border-2 border-blue-500/60 rounded-inherit z-20 pointer-events-none" />
        )}
      </div>

      {/* Card footer */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface-2 border-t border-subtle">
        <div className="flex flex-col">
          <span className="text-[11px] font-medium text-slate-300 truncate">{camera.camera_name}</span>
          {camera.location && (
            <span className="text-[10px] text-slate-600 truncate">{camera.location}</span>
          )}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onOpen(camera); }}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-400 hover:bg-blue-500/20 transition-colors text-[11px] font-medium"
        >
          <Eye size={11} />
          Open
        </button>
      </div>
    </div>
  );
}
