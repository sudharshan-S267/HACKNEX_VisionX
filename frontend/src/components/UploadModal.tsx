import { useState, useRef, useCallback } from 'react';
import {
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Film,
  Plus,
  Trash2,
} from 'lucide-react';
import { uploadVideo } from '../services/api';
import type { UploadEntry } from '../types';

interface UploadModalProps {
  onUploaded: () => void;
  onClose: () => void;
}

const DEFAULT_CAMERAS = [
  { id: 'CAM-01', name: 'Main Gate' },
  { id: 'CAM-02', name: 'Parking Area' },
  { id: 'CAM-03', name: 'Building Entrance' },
  { id: 'CAM-04', name: 'Exit Gate' },
];

function genId() {
  return Math.random().toString(36).slice(2, 9);
}

// Processing stage pipeline labels
function StageStatusBadge({ status }: { status: UploadEntry['status'] }) {
  if (status === 'uploading') {
    return (
      <div className="flex items-center gap-1.5 text-cyan-400 font-mono text-[10px] font-bold">
        <Loader2 size={12} className="animate-spin" />
        <span>UPLOADING</span>
      </div>
    );
  }
  if (status === 'processing') {
    return (
      <div className="flex items-center gap-1.5 text-amber-400 font-mono text-[10px] font-bold">
        <Loader2 size={12} className="animate-spin" />
        <span>PROCESSING → ANALYZING</span>
      </div>
    );
  }
  if (status === 'ready') {
    return (
      <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[10px] font-bold">
        <CheckCircle2 size={12} />
        <span>INDEXED & READY</span>
      </div>
    );
  }
  if (status === 'error') {
    return (
      <div className="flex items-center gap-1.5 text-rose-400 font-mono text-[10px] font-bold">
        <AlertCircle size={12} />
        <span>FAILED</span>
      </div>
    );
  }
  return (
    <span className="text-[10px] font-mono text-slate-400 font-semibold">
      STANDBY
    </span>
  );
}

export default function UploadModal({ onUploaded, onClose }: UploadModalProps) {
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateEntry = useCallback((id: string, patch: Partial<UploadEntry>) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }, []);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    const newEntries: UploadEntry[] = Array.from(files).map((file, i) => {
      const cam = DEFAULT_CAMERAS[i % DEFAULT_CAMERAS.length];
      return {
        id: genId(),
        camera_id: cam.id,
        camera_name: cam.name,
        file,
        progress: 0,
        status: 'idle',
      };
    });
    setEntries((prev) => [...prev, ...newEntries]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const removeEntry = useCallback((id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const patchCamera = useCallback(
    (id: string, field: 'camera_id' | 'camera_name', val: string) => {
      updateEntry(id, { [field]: val });
    },
    [updateEntry]
  );

  const handleUploadAll = useCallback(async () => {
    const pending = entries.filter((e) => e.status === 'idle' || e.status === 'error');
    if (!pending.length) return;
    setUploading(true);

    await Promise.allSettled(
      pending.map(async (entry) => {
        updateEntry(entry.id, { status: 'uploading', progress: 0, error: undefined });
        try {
          await uploadVideo(entry.camera_id, entry.file, (pct) => {
            updateEntry(entry.id, { progress: pct });
          });
          updateEntry(entry.id, { status: 'processing', progress: 100 });
          // Short simulated index step for smooth transition feedback
          await new Promise((r) => setTimeout(r, 1200));
          updateEntry(entry.id, { status: 'ready' });
        } catch (err) {
          updateEntry(entry.id, {
            status: 'error',
            error: err instanceof Error ? err.message : 'Upload failed',
          });
        }
      })
    );

    setUploading(false);
    onUploaded();
  }, [entries, updateEntry, onUploaded]);

  const pendingCount = entries.filter((e) => e.status === 'idle' || e.status === 'error').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in-up">
      <div className="tactical-panel rounded-2xl overflow-hidden w-full max-w-xl border border-cyan-500/30 shadow-[0_0_50px_rgba(0,0,0,0.8)] flex flex-col max-h-[90vh]">
        {/* HEADER */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.08] bg-command-900/90">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
              <Upload size={15} className="text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wider uppercase font-mono">
                UPLOAD CAMERA FOOTAGE
              </h2>
              <p className="text-[10px] text-slate-400 font-mono">
                Assign stream channels & ingest into VisionTrace index
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-rose-500/20 border border-white/[0.08] hover:border-rose-500/40 flex items-center justify-center text-slate-400 hover:text-rose-300 transition-colors"
          >
            <X size={15} />
          </button>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* DRAG AND DROP ZONE */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="
              border-2 border-dashed border-cyan-500/30 hover:border-cyan-400 rounded-xl p-7
              flex flex-col items-center justify-center gap-2.5 cursor-pointer
              bg-command-950/60 hover:bg-cyan-500/5 transition-all duration-200
            "
          >
            <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shadow-glow">
              <Plus size={22} className="text-cyan-400" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-xs font-bold text-slate-200 font-mono tracking-wide uppercase">
                Drag & drop videos here
              </p>
              <p className="text-[10px] text-cyan-400 font-mono font-semibold">
                or click to [ SELECT FILES ]
              </p>
              <p className="text-[10px] text-slate-400">MP4, MOV, AVI, WebM (H.264 supported)</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>

          {/* QUEUED VIDEOS */}
          {entries.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                <span>Queued Channels ({entries.length})</span>
                <span>STATUS / PROGRESS</span>
              </div>

              {entries.map((entry) => (
                <div key={entry.id} className="tactical-card rounded-lg p-3 space-y-2 border border-white/[0.08]">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Film size={14} className="text-cyan-400 flex-shrink-0" />
                      <span className="text-xs font-semibold text-white truncate max-w-[200px]">
                        {entry.file.name}
                      </span>
                      <span className="text-[10px] text-slate-400 mono">
                        {(entry.file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <StageStatusBadge status={entry.status} />
                      {entry.status === 'idle' && (
                        <button
                          onClick={() => removeEntry(entry.id)}
                          className="text-slate-400 hover:text-rose-400 transition-colors p-1"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Channel assignment */}
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={entry.camera_id}
                      onChange={(e) => patchCamera(entry.id, 'camera_id', e.target.value)}
                      disabled={entry.status !== 'idle'}
                      placeholder="CAM-01"
                      className="mono text-[10px] font-bold bg-command-950 border border-white/[0.1] rounded px-2 py-1 text-cyan-300 w-20"
                    />
                    <input
                      type="text"
                      value={entry.camera_name}
                      onChange={(e) => patchCamera(entry.id, 'camera_name', e.target.value)}
                      disabled={entry.status !== 'idle'}
                      placeholder="Camera name"
                      className="text-xs bg-command-950 border border-white/[0.1] rounded px-2.5 py-1 text-slate-200 flex-1 font-medium"
                    />
                  </div>

                  {/* Progress bar */}
                  {(entry.status === 'uploading' || entry.status === 'processing') && (
                    <div className="space-y-1">
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.6)]"
                          style={{ width: `${entry.progress}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-[9px] font-mono text-slate-400">
                        <span>Uploading byte chunks...</span>
                        <span>{entry.progress}%</span>
                      </div>
                    </div>
                  )}

                  {entry.error && (
                    <div className="text-[10px] font-mono text-rose-400 bg-rose-950/20 p-1.5 rounded border border-rose-500/30">
                      {entry.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div className="px-5 py-3.5 border-t border-white/[0.08] bg-command-900/90 flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-400">
            {pendingCount > 0
              ? `${pendingCount} stream${pendingCount !== 1 ? 's' : ''} ready to ingest`
              : 'All files ingested'}
          </span>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-mono font-semibold text-slate-400 hover:text-white bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] transition-all"
            >
              {entries.some((e) => e.status === 'ready') ? 'DONE' : 'CANCEL'}
            </button>

            <button
              onClick={handleUploadAll}
              disabled={uploading || pendingCount === 0}
              className="
                flex items-center gap-2 px-5 py-2 rounded-lg
                bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500
                text-white text-xs font-bold font-mono tracking-wider uppercase
                disabled:opacity-40 disabled:cursor-not-allowed
                shadow-glow transition-all active:scale-95
              "
            >
              {uploading ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  INGESTING…
                </>
              ) : (
                <>
                  <Upload size={13} />
                  INGEST ALL
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
