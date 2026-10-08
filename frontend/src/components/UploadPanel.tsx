import { useState, useRef, useCallback } from 'react';
import {
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Film,
  Camera,
  Plus,
  Trash2,
} from 'lucide-react';
import { uploadVideo, getVideoStatus } from '../services/api';
import type { UploadEntry, VideoStatusResponse } from '../types';

interface UploadPanelProps {
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

function StatusIcon({ status }: { status: UploadEntry['status'] }) {
  switch (status) {
    case 'uploading':
      return <Loader2 size={14} className="animate-spin text-blue-400" />;
    case 'processing':
      return <Loader2 size={14} className="animate-spin text-yellow-400" />;
    case 'ready':
      return <CheckCircle2 size={14} className="text-emerald-400" />;
    case 'error':
      return <AlertCircle size={14} className="text-red-400" />;
    default:
      return <Film size={14} className="text-slate-500" />;
  }
}

function StatusLabel({ status }: { status: UploadEntry['status'] }) {
  const labels: Record<UploadEntry['status'], string> = {
    idle: 'Ready to upload',
    uploading: 'Uploading…',
    processing: 'Processing…',
    ready: 'Ready',
    error: 'Error',
  };
  const colors: Record<UploadEntry['status'], string> = {
    idle: 'text-slate-500',
    uploading: 'text-blue-400',
    processing: 'text-yellow-400',
    ready: 'text-emerald-400',
    error: 'text-red-400',
  };
  return (
    <span className={`text-[10px] font-medium ${colors[status]}`}>
      {labels[status]}
    </span>
  );
}

export default function UploadPanel({ onUploaded, onClose }: UploadPanelProps) {
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
          const res = await uploadVideo(entry.camera_id, entry.file, (pct) => {
            updateEntry(entry.id, { progress: pct });
          });
          
          if (!res.video_id) {
             throw new Error("No video ID returned from upload");
          }
          
          updateEntry(entry.id, { status: 'processing', progress: 100 });
          
          // Poll for processing completion
          while (true) {
            await new Promise((r) => setTimeout(r, 2000)); // check every 2s
            const status: VideoStatusResponse = await getVideoStatus(res.video_id);
            if (status.status === 'completed') {
              updateEntry(entry.id, { status: 'ready' });
              break;
            } else if (status.status === 'failed') {
              throw new Error(status.error_message || "Processing failed");
            }
          }
          
        } catch (err) {
          updateEntry(entry.id, {
            status: 'error',
            error: err instanceof Error ? err.message : 'Upload/Processing failed',
          });
        }
      })
    );

    setUploading(false);
    onUploaded();
  }, [entries, updateEntry, onUploaded]);

  const pendingCount = entries.filter((e) => e.status === 'idle' || e.status === 'error').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="glass rounded-2xl overflow-hidden w-full max-w-lg animate-fade-in-up shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-subtle">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
              <Upload size={13} className="text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Upload Camera Videos</h2>
              <p className="text-[10px] text-slate-500">Assign each video to a camera</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg bg-white/5 border border-subtle flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="
              border-2 border-dashed border-slate-700 rounded-xl p-8
              flex flex-col items-center justify-center gap-3 cursor-pointer
              hover:border-blue-500/50 hover:bg-blue-500/5
              transition-all duration-200
            "
          >
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Plus size={20} className="text-blue-400" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-300">
                Drop videos here or click to browse
              </p>
              <p className="text-[11px] text-slate-600 mt-1">MP4, MOV, AVI, MKV supported</p>
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

          {/* Entry list */}
          {entries.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                {entries.length} file{entries.length !== 1 ? 's' : ''} queued
              </p>
              {entries.map((entry) => (
                <div key={entry.id} className="glass rounded-xl p-3 space-y-2">
                  {/* File name + remove */}
                  <div className="flex items-center gap-2">
                    <Film size={13} className="text-slate-500 flex-shrink-0" />
                    <span className="text-xs text-slate-300 flex-1 truncate font-medium">
                      {entry.file.name}
                    </span>
                    <span className="text-[10px] text-slate-600 mono flex-shrink-0">
                      {(entry.file.size / 1024 / 1024).toFixed(1)} MB
                    </span>
                    {entry.status === 'idle' && (
                      <button
                        onClick={() => removeEntry(entry.id)}
                        className="text-slate-600 hover:text-red-400 transition-colors flex-shrink-0"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>

                  {/* Camera assignment */}
                  <div className="flex items-center gap-2">
                    <Camera size={11} className="text-slate-600 flex-shrink-0" />
                    <input
                      type="text"
                      value={entry.camera_id}
                      onChange={(e) => patchCamera(entry.id, 'camera_id', e.target.value)}
                      disabled={entry.status !== 'idle'}
                      placeholder="CAM-01"
                      className="mono text-[11px] bg-surface-3 border border-subtle rounded px-2 py-1 text-blue-400 w-20 disabled:opacity-50"
                    />
                    <input
                      type="text"
                      value={entry.camera_name}
                      onChange={(e) => patchCamera(entry.id, 'camera_name', e.target.value)}
                      disabled={entry.status !== 'idle'}
                      placeholder="Camera name"
                      className="text-[11px] bg-surface-3 border border-subtle rounded px-2 py-1 text-slate-300 flex-1 disabled:opacity-50"
                    />
                  </div>

                  {/* Progress + status */}
                  <div className="flex items-center gap-2">
                    <StatusIcon status={entry.status} />
                    <StatusLabel status={entry.status} />
                    {(entry.status === 'uploading' || entry.status === 'processing') && (
                      <div className="flex-1 confidence-bar">
                        <div
                          className="confidence-fill bg-blue-500"
                          style={{ width: `${entry.progress}%` }}
                        />
                      </div>
                    )}
                    {entry.error && (
                      <span className="text-[10px] text-red-400 truncate">{entry.error}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-subtle flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            {pendingCount > 0
              ? `${pendingCount} file${pendingCount !== 1 ? 's' : ''} ready to upload`
              : entries.length > 0
              ? 'All uploads complete'
              : 'No files selected'}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-subtle hover:bg-white/5 transition-all"
            >
              {entries.some((e) => e.status === 'ready') ? 'Done' : 'Cancel'}
            </button>
            <button
              onClick={handleUploadAll}
              disabled={uploading || pendingCount === 0}
              className="
                flex items-center gap-2 px-4 py-2 rounded-lg
                bg-gradient-to-r from-blue-600 to-violet-600
                text-white text-xs font-semibold
                hover:from-blue-500 hover:to-violet-500
                disabled:opacity-40 disabled:cursor-not-allowed
                transition-all duration-200
              "
            >
              {uploading ? (
                <>
                  <Loader2 size={12} className="animate-spin" />
                  Uploading…
                </>
              ) : (
                <>
                  <Upload size={12} />
                  Upload All
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
