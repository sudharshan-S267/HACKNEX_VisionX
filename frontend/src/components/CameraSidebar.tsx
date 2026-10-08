import { Camera as CameraIcon, Upload, Cpu } from 'lucide-react';
import type { Camera, BackendStatus } from '../types';

interface CameraSidebarProps {
  cameras: Camera[];
  selectedCameraId?: string;
  onSelectCamera: (camera: Camera) => void;
  onOpenUpload: () => void;
  backendStatus: BackendStatus;
}

export default function CameraSidebar({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onOpenUpload,
  backendStatus,
}: CameraSidebarProps) {
  return (
    <aside className="tactical-panel w-64 flex-shrink-0 flex flex-col rounded-xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-3.5 border-b border-white/[0.08] bg-command-900/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CameraIcon size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-slate-200 tracking-wider uppercase font-mono">
            CAMERA CONTROL
          </span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
          {cameras.length} CH
        </span>
      </div>

      {/* Camera List */}
      <div className="flex-1 p-2.5 space-y-1.5 overflow-y-auto">
        {cameras.map((cam) => {
          const isSelected = selectedCameraId === cam.camera_id;
          const isOnline = cam.status === 'online';

          return (
            <div
              key={cam.camera_id}
              onClick={() => onSelectCamera(cam)}
              className={`
                group relative p-3 rounded-lg cursor-pointer border transition-all duration-200
                ${isSelected 
                  ? 'bg-cyan-500/15 border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.25)]' 
                  : 'tactical-card hover:border-cyan-500/30'
                }
              `}
            >
              {/* Corner reticle on selected */}
              {isSelected && (
                <>
                  <div className="reticle-corner-tl" />
                  <div className="reticle-corner-tr" />
                </>
              )}

              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isOnline ? 'bg-emerald-400 pulse-dot' : 'bg-rose-500'
                    }`}
                  />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-white mono tracking-wide">
                        {cam.camera_id}
                      </span>
                      {isSelected && (
                        <span className="text-[9px] font-bold text-cyan-400 mono bg-cyan-500/20 px-1 rounded">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 font-medium truncate max-w-[125px]">
                      {cam.camera_name}
                    </div>
                  </div>
                </div>

                <div className="text-right flex flex-col items-end">
                  <span
                    className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      isOnline
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                    }`}
                  >
                    {isOnline ? 'LIVE' : 'OFF'}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono mt-1">
                    {cam.event_count || 0} evt
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Upload button & Quick actions */}
      <div className="p-3 border-t border-white/[0.08] bg-command-900/80 space-y-2">
        <button
          onClick={onOpenUpload}
          className="
            w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg
            bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500
            text-white text-xs font-bold tracking-wider uppercase mono
            shadow-glow transition-all duration-200 active:scale-[0.98]
          "
        >
          <Upload size={14} />
          UPLOAD CAMERAS
        </button>

        {/* System telemetry footer */}
        <div className="pt-2 border-t border-white/[0.05] flex items-center justify-between text-[10px] font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <Cpu size={12} className="text-cyan-400" />
            <span>AI ENGINE</span>
          </div>
          <span className="text-emerald-400 font-semibold">
            {backendStatus === 'connected' ? 'OPTIMAL' : 'STANDBY'}
          </span>
        </div>
      </div>
    </aside>
  );
}
