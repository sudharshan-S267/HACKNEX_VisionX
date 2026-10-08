import { X, Play } from 'lucide-react';
import VideoPlayer from './VideoPlayer';
import type { Match } from '../types';
import { buildEvidenceUrl } from '../services/api';

interface EvidenceViewerProps {
  match: Match | null;
  onClose: () => void;
  onOpenCamera: (cameraId: string) => void;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  const ms = Math.round((ts % 1) * 100);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

export default function EvidenceViewer({
  match,
  onClose,
  onOpenCamera,
}: EvidenceViewerProps) {
  if (!match) return null;

  const videoSrc = match.evidence_url
    ? buildEvidenceUrl(match.evidence_url)
    : undefined;

  const confidencePct = Math.round(match.confidence * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in-up">
      <div
        className="tactical-panel rounded-2xl overflow-hidden w-full max-w-3xl border border-cyan-500/30 shadow-[0_0_50px_rgba(0,0,0,0.8)] flex flex-col"
        style={{ maxHeight: '92vh' }}
      >
        {/* TOP BAR */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.08] bg-command-900/90">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center shadow-glow">
              <Play size={14} className="text-cyan-400 fill-cyan-400 ml-0.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-extrabold text-white tracking-wider uppercase font-mono">
                  EVIDENCE CLIP
                </h2>
                <span className="text-[10px] font-bold text-cyan-300 mono bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-500/30">
                  {match.camera_id} • {match.camera_name}
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono">
                GROUNDED VIDEO TIMESTAMP: {formatTs(match.timestamp)}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-rose-500/20 border border-white/[0.08] hover:border-rose-500/40 flex items-center justify-center text-slate-400 hover:text-rose-300 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* VIDEO DISPLAY */}
        <div className="aspect-video bg-black relative scan-line border-b border-white/[0.08]">
          <div className="reticle-corner-tl" />
          <div className="reticle-corner-tr" />
          <div className="reticle-corner-bl" />
          <div className="reticle-corner-br" />

          <VideoPlayer
            src={videoSrc}
            seekTo={match.timestamp}
            cameraName={match.camera_name}
            autoPlay
            muted={false}
            className="absolute inset-0 w-full h-full"
          />
        </div>

        {/* EVENT DETAILS */}
        <div className="p-5 bg-command-900/40 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
            <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
              EVENT DETAILS
            </span>
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-slate-400 uppercase">Confidence:</span>
              <span className="font-extrabold text-emerald-400">{confidencePct}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-xs">
            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Camera</span>
              <span className="text-white font-bold">{match.camera_id} ({match.camera_name})</span>
            </div>

            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Timestamp</span>
              <span className="text-cyan-300 font-bold">{match.timestamp.toFixed(1)} seconds</span>
            </div>

            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Detection Type</span>
              <span className="text-purple-300 font-bold capitalize">
                {match.event_type.replace(/_/g, ' ')}
              </span>
            </div>
          </div>

          <div className="bg-command-950 p-3 rounded border border-white/[0.06]">
            <span className="text-[10px] text-slate-400 font-mono uppercase block mb-1">Description</span>
            <p className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
              {match.description}
            </p>
          </div>

          {/* ACTION BUTTONS */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-mono font-semibold text-slate-400 hover:text-white bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] transition-all"
            >
              CLOSE
            </button>

            <button
              onClick={() => {
                onOpenCamera(match.camera_id);
                onClose();
              }}
              className="
                flex items-center gap-2 px-5 py-2 rounded-lg
                bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500
                text-white text-xs font-bold font-mono tracking-wider uppercase
                shadow-glow transition-all active:scale-95
              "
            >
              OPEN CAMERA
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
