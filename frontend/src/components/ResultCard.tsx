import { ExternalLink, Camera, Clock, Target, ChevronRight } from 'lucide-react';
import type { Match } from '../types';
import { buildEvidenceUrl } from '../services/api';

interface ResultCardProps {
  match: Match;
  index: number;
  isSelected?: boolean;
  onClick: (match: Match) => void;
}

function confidenceColor(c: number) {
  if (c >= 0.85) return { text: 'text-emerald-400', bar: 'bg-emerald-500', label: 'HIGH' };
  if (c >= 0.6) return { text: 'text-yellow-400', bar: 'bg-yellow-500', label: 'MED' };
  return { text: 'text-red-400', bar: 'bg-red-500', label: 'LOW' };
}

function eventTypeLabel(t: string) {
  return t
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  const ms = Math.round((ts % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
}

export default function ResultCard({ match, index, isSelected, onClick }: ResultCardProps) {
  const conf = confidenceColor(match.confidence);

  return (
    <div
      onClick={() => onClick(match)}
      className={`
        glass glass-hover rounded-xl p-4 cursor-pointer
        transition-all duration-200 animate-fade-in-up
        ${isSelected ? 'result-card-selected' : ''}
      `}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {/* Index */}
          <div className="w-5 h-5 rounded bg-blue-500/15 border border-blue-500/25 flex items-center justify-center">
            <span className="text-blue-400 text-[10px] font-bold mono">{index + 1}</span>
          </div>

          {/* Camera badge */}
          <span className="mono text-[10px] font-semibold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
            {match.camera_id}
          </span>
          <span className="text-xs font-medium text-white truncate max-w-[120px]">
            {match.camera_name}
          </span>
        </div>

        {/* Confidence */}
        <div className="flex flex-col items-end gap-1">
          <div className={`flex items-center gap-1 ${conf.text}`}>
            <Target size={11} />
            <span className="text-[10px] font-bold mono">{conf.label}</span>
          </div>
          <span className={`text-xs font-semibold mono ${conf.text}`}>
            {Math.round(match.confidence * 100)}%
          </span>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="confidence-bar mb-3">
        <div
          className={`confidence-fill ${conf.bar}`}
          style={{ width: `${match.confidence * 100}%` }}
        />
      </div>

      {/* Event type + timestamp */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex items-center gap-1.5">
          <Camera size={11} className="text-slate-500" />
          <span className="text-[11px] text-slate-400 font-medium">
            {eventTypeLabel(match.event_type)}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock size={11} className="text-slate-500" />
          <span className="mono text-[11px] text-slate-400">
            {formatTs(match.timestamp)}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-slate-300 leading-relaxed mb-3">
        {match.description}
      </p>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={(e) => { e.stopPropagation(); onClick(match); }}
          className="flex items-center gap-1.5 text-[11px] text-blue-400 hover:text-blue-300 font-medium transition-colors"
        >
          <ChevronRight size={12} />
          Jump to timestamp
        </button>

        {match.evidence_url && (
          <a
            href={buildEvidenceUrl(match.evidence_url)}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-violet-500/10 border border-violet-500/20 text-violet-400 hover:bg-violet-500/20 transition-colors text-[11px] font-medium"
          >
            <ExternalLink size={10} />
            View Evidence
          </a>
        )}
      </div>
    </div>
  );
}
