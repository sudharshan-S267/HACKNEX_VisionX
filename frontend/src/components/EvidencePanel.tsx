import { X, Play, Clock, Camera } from 'lucide-react';
import VideoPlayer from './VideoPlayer';
import type { Match } from '../types';
import { buildEvidenceUrl } from '../services/api';

interface EvidencePanelProps {
  match: Match | null;
  onClose: () => void;
}

function formatTs(ts: number) {
  const m = Math.floor(ts / 60);
  const s = Math.floor(ts % 60);
  const ms = Math.round((ts % 1) * 100);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

export default function EvidencePanel({ match, onClose }: EvidencePanelProps) {
  if (!match) return null;

  const videoSrc = match.evidence_url
    ? buildEvidenceUrl(match.evidence_url)
    : undefined;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div
        className="glass rounded-2xl overflow-hidden w-full max-w-2xl animate-fade-in-up shadow-2xl"
        style={{ maxHeight: '90vh' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-subtle">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
              <Play size={13} className="text-white ml-0.5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Evidence Clip</h2>
              <p className="text-[10px] text-slate-500">
                {match.camera_id} · {match.camera_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg bg-white/5 border border-subtle flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Video */}
        <div className="aspect-video bg-black relative">
          <VideoPlayer
            src={videoSrc}
            seekTo={match.timestamp}
            cameraName={match.camera_name}
            autoPlay
            muted={false}
            className="absolute inset-0 w-full h-full"
          />
        </div>

        {/* Metadata */}
        <div className="px-5 py-4 grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Camera</p>
            <div className="flex items-center gap-2">
              <Camera size={12} className="text-blue-400" />
              <span className="text-sm font-medium text-white">
                {match.camera_id} — {match.camera_name}
              </span>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Timestamp</p>
            <div className="flex items-center gap-2">
              <Clock size={12} className="text-violet-400" />
              <span className="mono text-sm font-medium text-white">{formatTs(match.timestamp)}</span>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Event Type</p>
            <span className="text-sm font-medium text-white capitalize">
              {match.event_type.replace(/_/g, ' ')}
            </span>
          </div>

          <div className="space-y-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Confidence</p>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold mono ${
                match.confidence >= 0.85 ? 'text-emerald-400' :
                match.confidence >= 0.6 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {Math.round(match.confidence * 100)}%
              </span>
            </div>
          </div>

          <div className="col-span-2 space-y-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Description</p>
            <p className="text-sm text-slate-300 leading-relaxed">{match.description}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
