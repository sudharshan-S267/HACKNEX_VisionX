import { ArrowDown, MapPin, Clock, GitBranch } from 'lucide-react';
import type { TrajectoryPoint } from '../types';

interface TimelineProps {
  trajectory: TrajectoryPoint[];
  onJump: (cameraId: string, timestamp: number) => void;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

const CAMERA_COLORS = [
  'border-blue-500 bg-blue-500/15 text-blue-400',
  'border-violet-500 bg-violet-500/15 text-violet-400',
  'border-cyan-500 bg-cyan-500/15 text-cyan-400',
  'border-emerald-500 bg-emerald-500/15 text-emerald-400',
  'border-orange-500 bg-orange-500/15 text-orange-400',
];

export default function Timeline({ trajectory, onJump }: TimelineProps) {
  if (!trajectory.length) return null;

  return (
    <div className="glass rounded-xl p-4 animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <GitBranch size={14} className="text-violet-400" />
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Cross-Camera Trajectory
        </span>
        <span className="text-[10px] text-slate-600 mono">
          {trajectory.length} camera{trajectory.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Timeline nodes */}
      <div className="flex flex-col items-center gap-0">
        {trajectory.map((pt, i) => {
          const colorClass = CAMERA_COLORS[i % CAMERA_COLORS.length];
          const isLast = i === trajectory.length - 1;

          return (
            <div key={`${pt.camera_id}-${i}`} className="flex flex-col items-center w-full">
              {/* Node */}
              <button
                onClick={() => onJump(pt.camera_id, pt.timestamp)}
                className={`
                  group w-full flex items-center gap-3 px-3 py-2.5
                  rounded-lg border ${colorClass.split(' ').slice(0, 2).join(' ')}
                  hover:opacity-90 transition-all duration-150 text-left
                `}
              >
                {/* Camera badge */}
                <div className={`
                  flex-shrink-0 w-6 h-6 rounded-full border-2
                  flex items-center justify-center
                  ${colorClass}
                `}>
                  <span className="text-[9px] font-bold mono">{i + 1}</span>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-semibold text-white mono">
                      {pt.camera_id}
                    </span>
                    {pt.camera_name && (
                      <span className="text-[10px] text-slate-400 truncate">
                        {pt.camera_name}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <div className="flex items-center gap-1">
                      <Clock size={9} className="text-slate-600" />
                      <span className="mono text-[10px] text-slate-500">{formatTs(pt.timestamp)}</span>
                    </div>
                    {pt.location && (
                      <div className="flex items-center gap-1">
                        <MapPin size={9} className="text-slate-600" />
                        <span className="text-[10px] text-slate-500 truncate">{pt.location}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Jump hint */}
                <span className={`text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity ${colorClass.split(' ').pop()}`}>
                  Jump →
                </span>
              </button>

              {/* Connector */}
              {!isLast && (
                <div className="flex flex-col items-center py-1">
                  <div className="w-px h-3 bg-gradient-to-b from-blue-500/40 to-transparent" />
                  <ArrowDown size={12} className="text-blue-500/40" />
                  <div className="w-px h-1 bg-gradient-to-b from-transparent to-violet-500/40" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="mt-3 pt-3 border-t border-subtle">
        <p className="text-[10px] text-slate-600 text-center">
          Subject tracked across{' '}
          <span className="text-slate-400 font-medium">{trajectory.length} cameras</span>
          {trajectory.length >= 2 && (
            <>
              {' '}· Δt{' '}
              <span className="mono text-slate-400 font-medium">
                +{formatTs(trajectory[trajectory.length - 1].timestamp - trajectory[0].timestamp)}
              </span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
