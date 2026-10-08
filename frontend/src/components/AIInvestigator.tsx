import { useState, useRef, useCallback } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  ShieldCheck,
  AlertCircle,
  Cpu,
} from 'lucide-react';
import ResultCard from './ResultCard';
import type { QueryResponse, Match } from '../types';

interface AIInvestigatorProps {
  onQuery: (query: string) => void;
  loading: boolean;
  disabled?: boolean;
  queryResult: QueryResponse | null;
  queryError: string | null;
  selectedMatch: Match | null;
  onSelectMatch: (match: Match) => void;
  onViewEvidence: (match: Match) => void;
}

const EXAMPLE_SUGGESTIONS = [
  'Find the red car',
  'Find the person with a black backpack',
  'Track the red car',
  'What happened at the main gate?',
  'Show all red vehicles',
];

export default function AIInvestigator({
  onQuery,
  loading,
  disabled,
  queryResult,
  queryError,
  selectedMatch,
  onSelectMatch,
  onViewEvidence,
}: AIInvestigatorProps) {
  const [inputVal, setInputVal] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(() => {
    const q = inputVal.trim();
    if (!q || loading || disabled) return;
    onQuery(q);
  }, [inputVal, loading, disabled, onQuery]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleSubmit();
    },
    [handleSubmit]
  );

  const handlePickSuggestion = useCallback(
    (s: string) => {
      setInputVal(s);
      inputRef.current?.focus();
    },
    []
  );

  return (
    <aside className="tactical-panel w-84 lg:w-96 flex-shrink-0 flex flex-col rounded-xl border border-white/[0.08] overflow-hidden">
      {/* HEADER */}
      <div className="p-3.5 border-b border-white/[0.08] bg-command-900/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-cyan-400" />
            <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
              AI INVESTIGATOR
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
            <span className="text-[10px] font-bold text-emerald-400 font-mono tracking-wider">
              GROUNDED SEARCH
            </span>
          </div>
        </div>
        <p className="text-[11px] text-slate-400 mt-1 font-sans">
          Ask questions about your camera footage.
        </p>
      </div>

      {/* BODY: CONVERSATIONAL QUERY & RESULTS */}
      <div className="flex-1 p-3.5 space-y-4 overflow-y-auto">
        {/* INPUT SECTION */}
        <div className="space-y-2">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled || loading}
              placeholder="Ask anything about your cameras..."
              className="
                query-input w-full bg-slate-100 border border-slate-300 rounded-lg
                px-3 py-2.5 text-xs text-black placeholder-slate-500 font-medium
                disabled:opacity-40 disabled:cursor-not-allowed
              "
            />
            <button
              onClick={handleSubmit}
              disabled={!inputVal.trim() || loading || disabled}
              className="
                absolute right-1.5 top-1/2 -translate-y-1/2
                px-2.5 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-800
                text-black disabled:text-slate-500 text-xs font-bold
                transition-all duration-150 active:scale-95
              "
            >
              {loading ? (
                <Loader2 size={13} className="animate-spin text-black" />
              ) : (
                <Send size={13} />
              )}
            </button>
          </div>

          {/* EXAMPLE SUGGESTIONS */}
          <div className="space-y-1">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
              SUGGESTED QUERIES
            </span>
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLE_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handlePickSuggestion(s)}
                  disabled={loading || disabled}
                  className="
                    px-2 py-1 rounded text-[10px] font-medium text-slate-300
                    bg-white/[0.04] hover:bg-cyan-500/10 hover:text-cyan-300
                    border border-white/[0.06] hover:border-cyan-500/30
                    transition-all duration-150 text-left disabled:opacity-40
                  "
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* LOADING PROGRESS PIPELINE (Shown during processing) */}
        {loading && (
          <div className="tactical-card rounded-lg p-3.5 border border-cyan-500/30 space-y-2.5 animate-pulse">
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold mono">
              <Cpu size={14} className="animate-spin" />
              <span>ANALYZING CAMERA NETWORK</span>
            </div>
            <div className="space-y-1.5 pl-3 border-l border-cyan-500/30 text-[10px] font-mono text-slate-300">
              <div className="flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-cyan-400" />
                <span>Scanning: CAM-01, CAM-02, CAM-03, CAM-04</span>
              </div>
              <div className="flex items-center gap-2 text-cyan-300">
                <span className="w-1 h-1 rounded-full bg-cyan-400 animate-ping" />
                <span>SEARCHING EVENTS...</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <span className="w-1 h-1 rounded-full bg-slate-500" />
                <span>MATCHING EVIDENCE...</span>
              </div>
            </div>
          </div>
        )}

        {/* ERROR STATE */}
        {queryError && (
          <div className="tactical-card rounded-lg p-3 border border-rose-500/40 bg-rose-950/20 flex items-start gap-2.5">
            <AlertCircle size={15} className="text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-rose-300 leading-snug">
              {queryError}
            </div>
          </div>
        )}

        {/* QUERY RESULT & AI ANALYSIS */}
        {queryResult && (
          <div className="space-y-3.5">
            {/* User Query Echo */}
            <div className="bg-white/[0.03] p-2.5 rounded-lg border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">
                QUERY
              </span>
              <p className="text-xs font-semibold text-white mt-0.5 italic">
                "{queryResult.query}"
              </p>
            </div>

            {/* AI Analysis Box */}
            <div className="tactical-card rounded-lg p-3 border border-cyan-500/30 bg-cyan-950/20">
              <div className="flex items-center gap-2 mb-1.5">
                <ShieldCheck size={13} className="text-cyan-400" />
                <span className="text-[10px] font-bold text-cyan-400 font-mono uppercase tracking-wider">
                  AI ANALYSIS
                </span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {queryResult.answer}
              </p>
            </div>

            {/* MATCH RESULTS CARDS */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
                  MATCH RESULTS ({queryResult.matches.length})
                </span>
                {queryResult.processing_time_ms && (
                  <span className="text-[10px] text-slate-500 font-mono">
                    {queryResult.processing_time_ms}ms
                  </span>
                )}
              </div>

              {queryResult.matches.length === 0 ? (
                <div className="text-xs text-slate-400 p-3 bg-white/[0.02] rounded border border-white/[0.05] text-center font-mono">
                  No matching event was found in the indexed footage.
                </div>
              ) : (
                <div className="space-y-2 max-h-[380px] overflow-y-auto pr-0.5">
                  {queryResult.matches.map((match, i) => (
                    <ResultCard
                      key={`${match.camera_id}-${match.timestamp}-${i}`}
                      match={match}
                      index={i}
                      isSelected={
                        selectedMatch?.camera_id === match.camera_id &&
                        selectedMatch?.timestamp === match.timestamp
                      }
                      onClick={onSelectMatch}
                      onViewEvidence={onViewEvidence}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
