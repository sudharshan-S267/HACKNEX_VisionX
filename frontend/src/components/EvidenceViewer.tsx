import { useState } from 'react';
import { X, Play, Image as ImageIcon, Crosshair, CheckCircle2 } from 'lucide-react';
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
  const [viewMode, setViewMode] = useState<'video' | 'frame'>('video');

  if (!match) return null;

  const videoSrc = match.evidence_url
    ? buildEvidenceUrl(match.evidence_url)
    : undefined;

  const frameSrc = match.thumbnail_url
    ? buildEvidenceUrl(match.thumbnail_url)
    : match.id
    ? buildEvidenceUrl(`/api/v1/evidence/${match.id}/frame`)
    : undefined;

  const confidencePct = Math.round(match.confidence * 100);

  const targetLabel = `${(match.color || '').toUpperCase()} ${(match.object_type || match.event_type || 'TARGET').toUpperCase()} [${confidencePct}%]`.trim();

  const highlightBox = match.bounding_box
    ? {
        ...match.bounding_box,
        label: targetLabel,
      }
    : undefined;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in-up">
      <div
        className="tactical-panel rounded-2xl overflow-hidden w-full max-w-3xl border border-cyan-500/30 shadow-[0_0_50px_rgba(0,0,0,0.85)] flex flex-col"
        style={{ maxHeight: '92vh' }}
      >
        {/* TOP BAR */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.08] bg-command-900/90">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center shadow-glow">
              <Crosshair size={15} className="text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-extrabold text-white tracking-wider uppercase font-mono">
                  TARGET EVIDENCE
                </h2>
                <span className="text-[10px] font-bold text-cyan-300 mono bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-500/30">
                  {match.camera_id} • {match.camera_name}
                </span>
                {match.object_type && (
                  <span className="text-[10px] font-bold text-amber-300 mono bg-amber-950/70 px-2 py-0.5 rounded border border-amber-500/40 uppercase">
                    {match.color ? `${match.color} ` : ''}{match.object_type}
                  </span>
                )}
              </div>
              <p className="text-[10px] text-slate-400 font-mono">
                GROUNDED VIDEO TIMESTAMP: {formatTs(match.timestamp)}
              </p>
            </div>
          </div>

          {/* VIEW SWITCHER & CLOSE */}
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-black/50 p-0.5 rounded-lg border border-white/[0.08]">
              <button
                onClick={() => setViewMode('video')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-mono font-bold transition-all ${
                  viewMode === 'video'
                    ? 'bg-cyan-500 text-black shadow-glow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Play size={10} className={viewMode === 'video' ? 'fill-black' : ''} />
                VIDEO CLIP
              </button>
              {frameSrc && (
                <button
                  onClick={() => setViewMode('frame')}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-mono font-bold transition-all ${
                    viewMode === 'frame'
                      ? 'bg-cyan-500 text-black shadow-glow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <ImageIcon size={10} />
                  TARGET RETICLE
                </button>
              )}
            </div>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-rose-500/20 border border-white/[0.08] hover:border-rose-500/40 flex items-center justify-center text-slate-400 hover:text-rose-300 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* VISUAL DISPLAY (VIDEO OR ISOLATED TARGET FRAME) */}
        <div className="aspect-video bg-black relative scan-line border-b border-white/[0.08] overflow-hidden">
          <div className="reticle-corner-tl" />
          <div className="reticle-corner-tr" />
          <div className="reticle-corner-bl" />
          <div className="reticle-corner-br" />

          {viewMode === 'video' ? (
            <VideoPlayer
              src={videoSrc}
              seekTo={0}
              loop
              cameraName={match.camera_name}
              autoPlay
              muted={false}
              highlightBox={highlightBox}
              className="absolute inset-0 w-full h-full"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-black">
              {frameSrc ? (
                <>
                  <img
                    src={frameSrc}
                    alt="Target Single Detection Frame"
                    className="w-full h-full object-contain"
                  />
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/85 border border-cyan-500/50 px-2.5 py-1 rounded text-[10px] font-mono text-cyan-300 shadow-md">
                    <CheckCircle2 size={12} className="text-emerald-400" />
                    <span>ISOLATED TARGET BOX (OTHER OBJECTS UNBOUNDED)</span>
                  </div>
                </>
              ) : (
                <div className="text-center text-slate-500 text-xs font-mono">
                  TARGET FRAME UNAVAILABLE
                </div>
              )}
            </div>
          )}
        </div>

        {/* EVENT DETAILS */}
        <div className="p-4 bg-command-900/40 space-y-3">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
                GROUNDED DETECTION METRICS
              </span>
              <span className="text-[9px] font-bold text-emerald-400 mono bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
                DB-FILTERED
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-slate-400 uppercase">Confidence:</span>
              <span className="font-extrabold text-emerald-400">{confidencePct}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono text-xs">
            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Target Class</span>
              <span className="text-amber-300 font-bold uppercase truncate block">
                {match.object_type || match.event_type}
              </span>
            </div>

            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Detected Color</span>
              <span className="text-cyan-300 font-bold uppercase truncate block">
                {match.color || 'N/A'}
              </span>
            </div>

            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Camera</span>
              <span className="text-white font-bold truncate block">{match.camera_id}</span>
            </div>

            <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
              <span className="text-[10px] text-slate-400 uppercase block mb-0.5">Timestamp</span>
              <span className="text-cyan-300 font-bold">{match.timestamp.toFixed(1)}s</span>
            </div>
          </div>

          <div className="bg-command-950 p-2.5 rounded border border-white/[0.06]">
            <span className="text-[10px] text-slate-400 font-mono uppercase block mb-1">Description</span>
            <p className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
              {match.description}
            </p>
          </div>

          {/* ACTION BUTTONS */}
          <div className="flex items-center justify-end gap-3 pt-1">
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
