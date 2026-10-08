import { Loader2, Camera as CameraIcon } from 'lucide-react';
import CameraCard from './CameraCard';
import type { Camera, ActiveView } from '../types';

interface CameraGridProps {
  cameras: Camera[];
  loading: boolean;
  activeView: ActiveView | null;
  highlightedCameraId?: string;
  seekTimestamps: Record<string, number | undefined>;
  onOpenCamera: (camera: Camera) => void;
}

// Placeholder cameras shown before backend responds
const PLACEHOLDER_CAMERAS: Camera[] = [
  { camera_id: 'CAM-01', camera_name: 'Main Gate', location: 'North Entrance', status: 'offline', event_count: 0 },
  { camera_id: 'CAM-02', camera_name: 'Parking Area', location: 'West Wing', status: 'offline', event_count: 0 },
  { camera_id: 'CAM-03', camera_name: 'Building Entrance', location: 'Lobby', status: 'offline', event_count: 0 },
  { camera_id: 'CAM-04', camera_name: 'Exit Gate', location: 'South Exit', status: 'offline', event_count: 0 },
];

export default function CameraGrid({
  cameras,
  loading,
  activeView,
  highlightedCameraId,
  seekTimestamps,
  onOpenCamera,
}: CameraGridProps) {
  const displayCameras = cameras.length > 0 ? cameras : PLACEHOLDER_CAMERAS;

  return (
    <div className="relative">
      {/* Section label */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CameraIcon size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
            Camera Grid
          </span>
          {!loading && cameras.length > 0 && (
            <span className="text-[10px] text-slate-600 mono">
              {cameras.filter(c => c.status === 'online').length}/{cameras.length} online
            </span>
          )}
        </div>
        {loading && (
          <div className="flex items-center gap-1.5 text-slate-500">
            <Loader2 size={12} className="animate-spin" />
            <span className="text-[10px]">Loading cameras…</span>
          </div>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-3">
        {displayCameras.map((cam, i) => (
          <div
            key={cam.camera_id}
            style={{ animationDelay: `${i * 60}ms` }}
            className="animate-fade-in-up"
          >
            <CameraCard
              camera={cam}
              isSelected={
                activeView?.camera_id === cam.camera_id ||
                highlightedCameraId === cam.camera_id
              }
              seekTo={seekTimestamps[cam.camera_id]}
              onOpen={onOpenCamera}
            />
          </div>
        ))}
      </div>

      {/* Empty state (no cameras from backend) */}
      {!loading && cameras.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <p className="text-slate-500 text-xs font-medium">
              No cameras registered — upload a video to get started
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
