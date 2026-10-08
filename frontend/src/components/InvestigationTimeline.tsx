import { Clock } from 'lucide-react';
import type { Match } from '../types';

interface InvestigationTimelineProps {
  matches: Match[];
  selectedMatch: Match | null;
  onSelectEvent: (match: Match) => void;
  maxDuration?: number;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function InvestigationTimeline({
  matches,
  selectedMatch,
  onSelectEvent,
  maxDuration = 60,
}: InvestigationTimelineProps) {
  // Compute max timestamp if any match exceeds 60s
  const effectiveMax = Math.max(
    maxDuration,
    ...matches.map((m) => Math.ceil(m.timestamp + 5))
  );

  return (
    <div className="tactical-panel rounded-xl p-3.5 border border-white/[0.08]">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
            INVESTIGATION TIMELINE
          </span>
          <span className="text-[10px] text-slate-400 mono">
            [SYNCHRONIZED EVENT LINE]
          </span>
        </div>

        <div className="text-[10px] font-mono text-slate-400">
          SPAN: <span className="text-cyan-300 font-bold">00:00 — {formatTs(effectiveMax)}</span>
        </div>
      </div>

      {/* Timeline track */}
      <div className="relative pt-6 pb-4 px-4">
        {/* Main horizontal line */}
        <div className="h-1.5 w-full bg-command-900 border border-white/[0.1] rounded-full relative overflow-visible">
          {/* Tick marks */}
          <div className="absolute inset-0 flex justify-between pointer-events-none -top-2">
            {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
              <div key={pct} className="flex flex-col items-center">
                <div className="w-0.5 h-2 bg-white/20" />
                <span className="text-[9px] font-mono text-slate-400 mt-1">
                  {formatTs(effectiveMax * pct)}
                </span>
              </div>
            ))}
          </div>

          {/* Event markers */}
          {matches.map((match, i) => {
            const leftPct = Math.min(100, Math.max(2, (match.timestamp / effectiveMax) * 100));
            const isSelected =
              selectedMatch?.camera_id === match.camera_id &&
              selectedMatch?.timestamp === match.timestamp;

            return (
              <div
                key={`${match.camera_id}-${match.timestamp}-${i}`}
                style={{ left: `${leftPct}%` }}
                onClick={() => onSelectEvent(match)}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 cursor-pointer group z-10"
              >
                {/* Visual marker dot */}
                <div
                  className={`
                    w-3.5 h-3.5 rounded-full border-2 transition-all duration-200
                    flex items-center justify-center
                    ${
                      isSelected
                        ? 'bg-cyan-400 border-white scale-125 shadow-[0_0_12px_rgba(6,182,212,0.8)]'
                        : 'bg-command-950 border-cyan-400 group-hover:scale-110 group-hover:bg-cyan-500'
                    }
                  `}
                >
                  <span className="w-1 h-1 rounded-full bg-white" />
                </div>

                {/* Event tooltip / badge on hover or selected */}
                <div
                  className={`
                    absolute bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap
                    px-2 py-1 rounded bg-command-900 border border-cyan-500/40 text-[10px] font-mono
                    pointer-events-none transition-all duration-150 shadow-lg
                    ${isSelected ? 'opacity-100 scale-100 ring-1 ring-cyan-400' : 'opacity-0 group-hover:opacity-100 scale-95 group-hover:scale-100'}
                  `}
                >
                  <div className="font-bold text-cyan-300">
                    {match.camera_id} • {match.timestamp.toFixed(1)}s
                  </div>
                  <div className="text-[9px] text-slate-300 truncate max-w-[120px]">
                    {match.description}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
