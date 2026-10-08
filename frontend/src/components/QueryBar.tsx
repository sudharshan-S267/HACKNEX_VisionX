import { useState, useRef, useCallback } from 'react';
import { Search, Send, Loader2, ChevronRight, Sparkles } from 'lucide-react';

const SUGGESTED_QUERIES = [
  'Find the red car',
  'Where was the person with a black backpack?',
  'Track the red car across all cameras',
  'Did the red car enter and later leave?',
  'Show all sightings of the red car',
];

interface QueryBarProps {
  onSubmit: (query: string) => void;
  loading: boolean;
  disabled?: boolean;
}

export default function QueryBar({ onSubmit, loading, disabled }: QueryBarProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(() => {
    const q = value.trim();
    if (!q || loading) return;
    onSubmit(q);
  }, [value, loading, onSubmit]);

  const handleKey = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleSubmit();
    },
    [handleSubmit]
  );

  const handleSuggestion = useCallback(
    (s: string) => {
      setValue(s);
      inputRef.current?.focus();
    },
    []
  );

  return (
    <div className="space-y-3">
      {/* Label */}
      <div className="flex items-center gap-2">
        <Sparkles size={14} className="text-violet-400" />
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Intelligence Query
        </span>
      </div>

      {/* Input row */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
          />
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKey}
            disabled={disabled || loading}
            placeholder="Ask anything about the cameras…"
            className="
              query-input w-full
              bg-slate-100 border border-slate-300 rounded-lg
              pl-9 pr-4 py-3
              text-sm text-black placeholder-slate-500
              font-medium
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-all duration-200
            "
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || loading || disabled}
          className="
            flex items-center gap-2 px-5 py-3 rounded-lg
            bg-gradient-to-r from-blue-600 to-violet-600
            text-white text-sm font-semibold
            hover:from-blue-500 hover:to-violet-500
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all duration-200 shadow-glow
            min-w-[90px] justify-center
          "
        >
          {loading ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              <span>Query…</span>
            </>
          ) : (
            <>
              <Send size={14} />
              <span>Query</span>
            </>
          )}
        </button>
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTED_QUERIES.map((s) => (
          <button
            key={s}
            onClick={() => handleSuggestion(s)}
            disabled={loading || disabled}
            className="
              flex items-center gap-1 px-2.5 py-1
              rounded-full text-[11px] text-slate-400
              border border-subtle bg-surface-3
              hover:border-blue-500/30 hover:text-blue-400
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-all duration-150
            "
          >
            <ChevronRight size={10} />
            {s}
          </button>
        ))}
      </div>

      {disabled && (
        <p className="text-xs text-red-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
          Backend unavailable. Start the backend server to run queries.
        </p>
      )}
    </div>
  );
}
