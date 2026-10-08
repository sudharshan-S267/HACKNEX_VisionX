import { Loader2, LayoutGrid } from 'lucide-react';
import CameraCard from './CameraCard';
import type { Camera, ActiveView } from '../types';

interface CameraWallProps {
  cameras: Camera[];
  loading: boolean;
  activeView: ActiveView | null;
  highlightedCameraId?: string;
  seekTimestamps: Record<string, number | undefined>;
  onOpenCamera: (camera: Camera) => void;
}

export default function CameraWall({
  cameras,
  loading,
  activeView,
  highlightedCameraId,
  seekTimestamps,
  onOpenCamera,
}: CameraWallProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Wall Header bar */}
      <div className="flex items-center justify-between mb-2.5 px-1">
        <div className="flex items-center gap-2">
          <LayoutGrid size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-slate-200 tracking-wider uppercase font-mono">
            CAMERA WALL
          </span>
          <span className="text-[10px] text-slate-400 mono">
            [2×2 SYNCHRONIZED MATRIX]
          </span>
        </div>

        <div className="flex items-center gap-3">
          {loading ? (
            <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-mono">
              <Loader2 size={12} className="animate-spin" />
              <span>SYNCING MATRIX…</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-emerald-400 text-[10px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
              <span>STREAMS ACTIVE</span>
            </div>
          )}
        </div>
      </div>

      {/* 2x2 Grid */}
      <div className="grid grid-cols-2 gap-3 flex-1 min-h-[460px]">
        {cameras.map((cam) => {
          const isSelected =
            activeView?.camera_id === cam.camera_id ||
            highlightedCameraId === cam.camera_id;

          return (
            <CameraCard
              key={cam.camera_id}
              camera={cam}
              isSelected={isSelected}
              seekTo={seekTimestamps[cam.camera_id]}
              matchedTimestamp={seekTimestamps[cam.camera_id]}
              onOpen={onOpenCamera}
            />
          );
        })}
      </div>
    </div>
  );
}
