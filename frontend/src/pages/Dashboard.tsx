import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Upload,
  RefreshCw,
  Bot,
  AlertTriangle,
  CheckCircle2,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

import Header from '../components/Header';
import CameraGrid from '../components/CameraGrid';
import QueryBar from '../components/QueryBar';
import ResultCard from '../components/ResultCard';
import Timeline from '../components/Timeline';
import EvidencePanel from '../components/EvidencePanel';
import UploadPanel from '../components/UploadPanel';

import { healthCheck, getCameras, queryVideos } from '../services/api';
import type {
  Camera,
  QueryResponse,
  Match,
  BackendStatus,
  ActiveView,
} from '../types';

const HEALTH_POLL_INTERVAL = 10_000; // 10 s

export default function Dashboard() {
  // ─── Backend state ────────────────────────────────────────────────────────
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('connecting');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [camerasLoading, setCamerasLoading] = useState(false);

  // ─── Query state ──────────────────────────────────────────────────────────
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);

  // ─── Active view / seeking ────────────────────────────────────────────────
  const [activeView, setActiveView] = useState<ActiveView | null>(null);
  const [seekTimestamps, setSeekTimestamps] = useState<Record<string, number | undefined>>({});
  const [highlightedCameraId, setHighlightedCameraId] = useState<string | undefined>();

  // ─── UI panels ────────────────────────────────────────────────────────────
  const [showUpload, setShowUpload] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [resultsCollapsed, setResultsCollapsed] = useState(false);

  // ─── Ticker for live clock in header ─────────────────────────────────────
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // ─── Health check ─────────────────────────────────────────────────────────
  const checkHealth = useCallback(async () => {
    try {
      await healthCheck();
      setBackendStatus('connected');
    } catch {
      setBackendStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, HEALTH_POLL_INTERVAL);
    return () => clearInterval(id);
  }, [checkHealth]);

  // ─── Load cameras ─────────────────────────────────────────────────────────
  const loadCameras = useCallback(async () => {
    if (backendStatus !== 'connected') return;
    setCamerasLoading(true);
    try {
      const data = await getCameras();
      setCameras(data);
    } catch {
      // silently fall back to placeholder grid
    } finally {
      setCamerasLoading(false);
    }
  }, [backendStatus]);

  useEffect(() => {
    loadCameras();
  }, [loadCameras]);

  // ─── Query submission ─────────────────────────────────────────────────────
  const handleQuery = useCallback(async (query: string) => {
    setQueryLoading(true);
    setQueryError(null);
    setQueryResult(null);
    setSelectedMatch(null);
    setSeekTimestamps({});
    setHighlightedCameraId(undefined);

    try {
      const result = await queryVideos({ query });
      setQueryResult(result);
      setResultsCollapsed(false);
    } catch (err) {
      setQueryError(
        err instanceof Error ? err.message : 'Unable to process query. Please try again.'
      );
    } finally {
      setQueryLoading(false);
    }
  }, []);

  // ─── Result click: jump to camera + timestamp ─────────────────────────────
  const handleMatchClick = useCallback((match: Match) => {
    setSelectedMatch(match);
    setHighlightedCameraId(match.camera_id);
    setActiveView({ camera_id: match.camera_id, timestamp: match.timestamp });
    setSeekTimestamps((prev) => ({
      ...prev,
      [match.camera_id]: match.timestamp,
    }));
  }, []);

  // ─── Trajectory jump ──────────────────────────────────────────────────────
  const handleTrajectoryJump = useCallback((cameraId: string, timestamp: number) => {
    setHighlightedCameraId(cameraId);
    setActiveView({ camera_id: cameraId, timestamp });
    setSeekTimestamps((prev) => ({ ...prev, [cameraId]: timestamp }));
  }, []);

  // ─── Open camera full view ────────────────────────────────────────────────
  const handleOpenCamera = useCallback((camera: Camera) => {
    setActiveView({ camera_id: camera.camera_id });
    setHighlightedCameraId(camera.camera_id);
  }, []);

  // ─── After upload, reload cameras ─────────────────────────────────────────
  const handleUploaded = useCallback(() => {
    loadCameras();
  }, [loadCameras]);

  const onlineCount = cameras.filter((c) => c.status === 'online').length;
  const hasResults = queryResult && queryResult.matches.length > 0;

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col">
      <Header
        backendStatus={backendStatus}
        cameraCount={cameras.length || 4}
        onlineCount={onlineCount}
      />

      {/* Offline banner */}
      {backendStatus === 'disconnected' && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-6 py-2 flex items-center gap-3">
          <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
          <p className="text-red-300 text-xs font-medium">
            Backend unavailable. Start the backend server at{' '}
            <code className="mono text-red-200 bg-red-500/10 px-1 rounded">
              {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
            </code>{' '}
            — queries and uploads are disabled until the connection is restored.
          </p>
          <button
            onClick={checkHealth}
            className="ml-auto flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 transition-colors flex-shrink-0"
          >
            <RefreshCw size={12} />
            Retry
          </button>
        </div>
      )}

      {/* Main layout */}
      <main className="flex-1 flex gap-4 p-4 overflow-hidden">
        {/* ── LEFT COLUMN: Camera grid ──────────────────────────────────── */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          {/* Camera grid */}
          <div className="glass rounded-xl p-4">
            <CameraGrid
              cameras={cameras}
              loading={camerasLoading}
              activeView={activeView}
              highlightedCameraId={highlightedCameraId}
              seekTimestamps={seekTimestamps}
              onOpenCamera={handleOpenCamera}
            />
          </div>

          {/* Query interface */}
          <div className="glass rounded-xl p-4">
            <QueryBar
              onSubmit={handleQuery}
              loading={queryLoading}
              disabled={backendStatus === 'disconnected'}
            />
          </div>

          {/* Query results */}
          {(queryResult || queryError) && (
            <div className="glass rounded-xl overflow-hidden animate-fade-in-up">
              {/* Results header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-subtle">
                <div className="flex items-center gap-2">
                  <Bot size={14} className="text-violet-400" />
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                    AI Response
                  </span>
                  {hasResults && (
                    <span className="text-[10px] text-slate-600 mono">
                      {queryResult!.matches.length} match{queryResult!.matches.length !== 1 ? 'es' : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {queryResult?.processing_time_ms && (
                    <span className="text-[10px] text-slate-600 mono">
                      {queryResult.processing_time_ms}ms
                    </span>
                  )}
                  <button
                    onClick={() => setResultsCollapsed((c) => !c)}
                    className="text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {resultsCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                  </button>
                  <button
                    onClick={() => { setQueryResult(null); setQueryError(null); }}
                    className="text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>

              {!resultsCollapsed && (
                <div className="p-4 space-y-4">
                  {/* Error */}
                  {queryError && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                      <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-red-300">{queryError}</p>
                    </div>
                  )}

                  {/* AI answer */}
                  {queryResult?.answer && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-violet-500/8 border border-violet-500/15">
                      <div className="w-5 h-5 rounded-md bg-violet-600/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Bot size={11} className="text-violet-400" />
                      </div>
                      <p className="text-sm text-slate-200 leading-relaxed">{queryResult.answer}</p>
                    </div>
                  )}

                  {/* No matches */}
                  {queryResult && queryResult.matches.length === 0 && (
                    <div className="flex items-center gap-2 text-slate-500 text-sm py-2">
                      <CheckCircle2 size={14} />
                      No matching events found for this query.
                    </div>
                  )}

                  {/* Match cards */}
                  {hasResults && (
                    <div className="space-y-2">
                      <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                        Matched Events
                      </p>
                      <div className="grid grid-cols-1 gap-2 max-h-[340px] overflow-y-auto pr-1">
                        {queryResult!.matches.map((match, i) => (
                          <ResultCard
                            key={`${match.camera_id}-${match.timestamp}-${i}`}
                            match={match}
                            index={i}
                            isSelected={
                              selectedMatch?.camera_id === match.camera_id &&
                              selectedMatch?.timestamp === match.timestamp
                            }
                            onClick={(m) => {
                              handleMatchClick(m);
                              if (m.evidence_url) setShowEvidence(true);
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── RIGHT COLUMN: Trajectory + actions ───────────────────────── */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-4">
          {/* Action buttons */}
          <div className="glass rounded-xl p-4 space-y-2">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium mb-3">
              System Actions
            </p>
            <button
              onClick={() => setShowUpload(true)}
              className="
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                bg-blue-500/10 border border-blue-500/20
                text-blue-400 hover:bg-blue-500/15 hover:border-blue-500/35
                transition-all text-sm font-medium
              "
            >
              <Upload size={14} />
              Upload Camera Videos
            </button>
            <button
              onClick={loadCameras}
              disabled={backendStatus !== 'connected'}
              className="
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                bg-white/5 border border-subtle
                text-slate-400 hover:text-white hover:bg-white/8
                disabled:opacity-40 disabled:cursor-not-allowed
                transition-all text-sm font-medium
              "
            >
              <RefreshCw size={14} />
              Refresh Cameras
            </button>
          </div>

          {/* Trajectory panel */}
          {queryResult?.trajectory && queryResult.trajectory.length > 0 && (
            <Timeline
              trajectory={queryResult.trajectory}
              onJump={handleTrajectoryJump}
            />
          )}

          {/* Evidence quick-view */}
          {selectedMatch && !showEvidence && (
            <div className="glass rounded-xl p-4 animate-slide-in-right">
              <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium mb-3">
                Selected Event
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="mono text-xs text-blue-400">{selectedMatch.camera_id}</span>
                  <span className="mono text-xs text-slate-500">
                    {Math.floor(selectedMatch.timestamp / 60).toString().padStart(2, '0')}:
                    {Math.floor(selectedMatch.timestamp % 60).toString().padStart(2, '0')}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {selectedMatch.description}
                </p>
                {selectedMatch.evidence_url && (
                  <button
                    onClick={() => setShowEvidence(true)}
                    className="
                      w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                      bg-violet-500/10 border border-violet-500/20
                      text-violet-400 hover:bg-violet-500/20
                      transition-all text-xs font-medium
                    "
                  >
                    View Evidence Clip
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Stats card */}
          <div className="glass rounded-xl p-4">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium mb-3">
              Session Stats
            </p>
            <div className="space-y-2">
              {[
                { label: 'Cameras', value: cameras.length || 4 },
                { label: 'Online', value: onlineCount },
                {
                  label: 'Events',
                  value: cameras.reduce((a, c) => a + c.event_count, 0),
                },
                { label: 'Query Results', value: queryResult?.matches.length ?? '—' },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">{label}</span>
                  <span className="mono text-xs font-semibold text-white">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      {showUpload && (
        <UploadPanel
          onUploaded={handleUploaded}
          onClose={() => setShowUpload(false)}
        />
      )}

      {showEvidence && selectedMatch && (
        <EvidencePanel
          match={selectedMatch}
          onClose={() => setShowEvidence(false)}
        />
      )}
    </div>
  );
}
