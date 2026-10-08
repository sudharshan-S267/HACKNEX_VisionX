import { Clock, Play } from 'lucide-react';
import type { Match } from '../types';

interface ResultCardProps {
  match: Match;
  index: number;
  isSelected?: boolean;
  onClick: (match: Match) => void;
  onViewEvidence: (match: Match) => void;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  const ms = Math.round((ts % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
}

export default function ResultCard({
  match,
  index: _index,
  isSelected,
  onClick,
  onViewEvidence,
}: ResultCardProps) {
  const confidencePct = Math.round(match.confidence * 100);
  const isHighConf = confidencePct >= 80;

  return (
    <div
      onClick={() => onClick(match)}
      className={`
        tactical-card rounded-lg p-3 cursor-pointer relative group transition-all duration-200 border
        ${
          isSelected
            ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]'
            : 'hover:border-cyan-500/40'
        }
      `}
    >
      {/* Reticle on selected */}
      {isSelected && (
        <>
          <div className="reticle-corner-tl" />
          <div className="reticle-corner-tr" />
        </>
      )}

      {/* Top row: Camera ID, Name, Target Badge & Timestamp */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="mono text-[10px] font-extrabold text-cyan-300 bg-cyan-900/40 border border-cyan-500/30 px-1.5 py-0.5 rounded">
            {match.camera_id}
          </span>
          <span className="text-xs font-bold text-white truncate max-w-[110px]">
            {match.camera_name}
          </span>
          {match.object_type && (
            <span className="mono text-[9px] font-bold text-amber-300 bg-amber-950/70 border border-amber-500/40 px-1.5 py-0.5 rounded uppercase tracking-wider">
              {match.color ? `${match.color} ` : ''}{match.object_type}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-slate-300 mono text-xs font-semibold bg-white/[0.04] px-1.5 py-0.5 rounded border border-white/[0.05]">
          <Clock size={11} className="text-cyan-400" />
          <span>{formatTs(match.timestamp)}</span>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-slate-300 leading-snug mb-2 font-medium">
        {match.description}
      </p>

      {/* Attribute badges */}
      {(match.clothing_upper_color || match.clothing_lower_color || match.has_backpack || match.has_cap || match.has_hat) && (
        <div className="flex flex-wrap gap-1 mb-2">
          {match.clothing_upper_color && match.clothing_upper_color !== 'unknown' && (
            <span className="mono text-[9px] font-semibold bg-sky-950/80 border border-sky-500/40 text-sky-300 px-1.5 py-0.5 rounded capitalize">
              Top: {match.clothing_upper_color}
            </span>
          )}
          {match.clothing_lower_color && match.clothing_lower_color !== 'unknown' && (
            <span className="mono text-[9px] font-semibold bg-indigo-950/80 border border-indigo-500/40 text-indigo-300 px-1.5 py-0.5 rounded capitalize">
              Bottom: {match.clothing_lower_color}
            </span>
          )}
          {match.has_backpack && (
            <span className="mono text-[9px] font-semibold bg-purple-950/80 border border-purple-500/40 text-purple-300 px-1.5 py-0.5 rounded">
              Backpack
            </span>
          )}
          {(match.has_cap || match.has_hat) && (
            <span className="mono text-[9px] font-semibold bg-teal-950/80 border border-teal-500/40 text-teal-300 px-1.5 py-0.5 rounded">
              Cap / Hat
            </span>
          )}
        </div>
      )}

      {/* Confidence Bar */}
      <div className="mb-3 space-y-1">
        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="text-slate-400 uppercase tracking-wider">Detection Conf</span>
          <span
            className={`font-bold ${
              isHighConf ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            {confidencePct}%
          </span>
        </div>
        <div className="confidence-bar">
          <div
            className={`confidence-fill ${
              isHighConf ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-amber-400'
            }`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>

        {match.attribute_confidence != null && (
          <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 pt-0.5">
            <span className="uppercase tracking-wider text-slate-500">Attr Conf</span>
            <span className="text-cyan-400 font-semibold">
              {Math.round(match.attribute_confidence * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Action: VIEW EVIDENCE */}
      <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
        <span className="text-[10px] text-cyan-400 font-mono tracking-wider">
          CLICK TO SEEK
        </span>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewEvidence(match);
          }}
          className="
            flex items-center gap-1.5 px-2.5 py-1 rounded
            bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 hover:border-cyan-500/60
            text-cyan-300 hover:text-white text-[10px] font-bold tracking-wider uppercase mono
            transition-all duration-150 active:scale-95
          "
        >
          <Play size={10} className="fill-cyan-400" />
          VIEW EVIDENCE
        </button>
      </div>
    </div>
  );
}
