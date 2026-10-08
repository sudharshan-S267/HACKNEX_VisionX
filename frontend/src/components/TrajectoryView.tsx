import { GitBranch, ArrowDown, Play } from 'lucide-react';
import type { TrajectoryPoint } from '../types';

interface TrajectoryViewProps {
  trajectory?: TrajectoryPoint[];
  onJump: (cameraId: string, timestamp: number) => void;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  const ms = Math.round((ts % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
}

export default function TrajectoryView({
  trajectory,
  onJump,
}: TrajectoryViewProps) {
  if (!trajectory || trajectory.length === 0) return null;

  return (
    <div className="tactical-panel rounded-xl p-3.5 border border-white/[0.08]">
      {/* Title */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <GitBranch size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
            CROSS-CAMERA TRAJECTORY
          </span>
          <span className="text-[10px] text-slate-400 mono">
            [OBJECT MOVEMENT CORRELATION]
          </span>
        </div>

        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
          {trajectory.length} HOPS DETECTED
        </span>
      </div>

      {/* Horizontal Flow on Wide, Vertical Flow on Compact */}
      <div className="flex flex-wrap items-center justify-center gap-3 py-2">
        {trajectory.map((point, index) => {
          const isLast = index === trajectory.length - 1;

          return (
            <div key={`${point.camera_id}-${point.timestamp}-${index}`} className="flex items-center gap-3">
              {/* Node Card */}
              <div
                onClick={() => onJump(point.camera_id, point.timestamp)}
                className="
                  tactical-card group px-3.5 py-2.5 rounded-lg border border-cyan-500/30 hover:border-cyan-400
                  cursor-pointer transition-all duration-200 hover:shadow-[0_0_15px_rgba(6,182,212,0.25)]
                  min-w-[150px]
                "
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 pulse-dot" />
                    <span className="text-xs font-bold text-white mono">
                      {point.camera_id}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold text-cyan-300 mono bg-cyan-950/60 px-1 rounded">
                    {point.timestamp.toFixed(1)}s
                  </span>
                </div>

                <div className="text-[11px] font-semibold text-slate-300 truncate">
                  {point.camera_name || 'Camera Stream'}
                </div>

                <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400 font-mono">
                  <span>{formatTs(point.timestamp)}</span>
                  <span className="text-cyan-400 group-hover:underline flex items-center gap-0.5">
                    SEEK <Play size={8} />
                  </span>
                </div>
              </div>

              {/* Connecting Indicator */}
              {!isLast && (
                <div className="flex items-center text-cyan-400/80 px-1 animate-pulse">
                  <span className="hidden sm:inline font-mono text-xs font-bold tracking-widest text-cyan-400">
                    ───►
                  </span>
                  <ArrowDown size={14} className="sm:hidden text-cyan-400" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
