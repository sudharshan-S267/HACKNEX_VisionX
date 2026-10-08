import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';

import TopBar from '../components/TopBar';
import CameraSidebar from '../components/CameraSidebar';
import CameraWall from '../components/CameraWall';
import AIInvestigator from '../components/AIInvestigator';
import InvestigationTimeline from '../components/InvestigationTimeline';
import TrajectoryView from '../components/TrajectoryView';
import EvidenceViewer from '../components/EvidenceViewer';
import UploadModal from '../components/UploadModal';

import { healthCheck, getCameras, queryVideos } from '../services/api';
import type {
  Camera,
  QueryResponse,
  Match,
  BackendStatus,
  ActiveView,
} from '../types';

const HEALTH_POLL_INTERVAL = 10_000;

// Default 4 fallback CCTV channels
const PLACEHOLDER_CAMERAS: Camera[] = [
  { camera_id: 'CAM-01', camera_name: 'Main Gate', location: 'North Perimeter', status: 'online', event_count: 0 },
  { camera_id: 'CAM-02', camera_name: 'Parking Area', location: 'Zone B Parking', status: 'online', event_count: 0 },
  { camera_id: 'CAM-03', camera_name: 'Building Entrance', location: 'Lobby Portal', status: 'online', event_count: 0 },
  { camera_id: 'CAM-04', camera_name: 'Exit Gate', location: 'South Perimeter', status: 'online', event_count: 0 },
];

export default function Dashboard() {
  // Backend & Camera state
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('connecting');
  const [cameras, setCameras] = useState<Camera[]>(PLACEHOLDER_CAMERAS);
  const [camerasLoading, setCamerasLoading] = useState(false);

  // Query & Matches state
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);

  // Active Camera view / seeking state
  const [activeView, setActiveView] = useState<ActiveView | null>({ camera_id: 'CAM-01' });
  const [seekTimestamps, setSeekTimestamps] = useState<Record<string, number | undefined>>({});
  const [highlightedCameraId, setHighlightedCameraId] = useState<string | undefined>('CAM-01');

  // Modals state
  const [showUpload, setShowUpload] = useState(false);
  const [evidenceMatch, setEvidenceMatch] = useState<Match | null>(null);

  // Health check polling
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

  // Load cameras
  const loadCameras = useCallback(async () => {
    if (backendStatus !== 'connected') return;
    setCamerasLoading(true);
    try {
      const data = await getCameras();
      if (data && data.length > 0) {
        setCameras(data);
      }
    } catch {
      // Keep existing/placeholder cameras
    } finally {
      setCamerasLoading(false);
    }
  }, [backendStatus]);

  useEffect(() => {
    loadCameras();
  }, [loadCameras]);

  // Natural language query handler
  const handleQuery = useCallback(async (query: string) => {
    setQueryLoading(true);
    setQueryError(null);
    setQueryResult(null);
    setSelectedMatch(null);
    setSeekTimestamps({});

    try {
      const result = await queryVideos({ query });
      setQueryResult(result);

      // If matches exist, auto-select the highest confidence match
      if (result.matches && result.matches.length > 0) {
        const first = result.matches[0];
        setSelectedMatch(first);
        setHighlightedCameraId(first.camera_id);
        setActiveView({ camera_id: first.camera_id, timestamp: first.timestamp });
        setSeekTimestamps({ [first.camera_id]: first.timestamp });
      }
    } catch (err) {
      setQueryError(
        err instanceof Error ? err.message : 'Unable to process query. Please try again.'
      );
    } finally {
      setQueryLoading(false);
    }
  }, []);

  // Jump to specific match (seek video & highlight)
  const handleSelectMatch = useCallback((match: Match) => {
    setSelectedMatch(match);
    setHighlightedCameraId(match.camera_id);
    setActiveView({ camera_id: match.camera_id, timestamp: match.timestamp });
    setSeekTimestamps((prev) => ({
      ...prev,
      [match.camera_id]: match.timestamp,
    }));
  }, []);

  // Open evidence viewer modal
  const handleViewEvidence = useCallback((match: Match) => {
    setEvidenceMatch(match);
  }, []);

  // Select camera from sidebar
  const handleSelectCamera = useCallback((camera: Camera) => {
    setActiveView({ camera_id: camera.camera_id });
    setHighlightedCameraId(camera.camera_id);
  }, []);

  // Jump from timeline or trajectory
  const handleJumpToCamera = useCallback((cameraId: string, timestamp: number) => {
    setHighlightedCameraId(cameraId);
    setActiveView({ camera_id: cameraId, timestamp });
    setSeekTimestamps((prev) => ({ ...prev, [cameraId]: timestamp }));
  }, []);

  const totalEvents = cameras.reduce((sum, c) => sum + (c.event_count || 0), 0);
  const onlineCount = cameras.filter((c) => c.status === 'online').length;

  return (
    <div className="min-h-screen bg-command-950 text-slate-200 flex flex-col font-sans tactical-grid-bg">
      {/* 1. TOP BAR NAVIGATION */}
      <TopBar
        backendStatus={backendStatus}
        cameraCount={cameras.length}
        onlineCount={onlineCount}
        totalEvents={totalEvents}
        onRetryConnection={checkHealth}
      />

      {/* 2. BACKEND OFFLINE BANNER (Enhanced presentation, does not disable UI inspection) */}
      {backendStatus === 'disconnected' && (
        <div className="bg-rose-950/40 border-b border-rose-500/30 px-6 py-2 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-rose-500 pulse-dot" />
            <span className="text-rose-300 text-xs font-mono font-bold tracking-wider uppercase">
              BACKEND OFFLINE
            </span>
            <span className="text-slate-400 text-xs font-mono">
              API TARGET: <code className="text-rose-200 bg-rose-900/30 px-1 py-0.5 rounded border border-rose-500/20">{import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}</code>
            </span>
            <span className="text-slate-400 text-xs hidden md:inline">
              — Dashboard in inspection standby mode. Start backend server to query footage.
            </span>
          </div>

          <button
            onClick={checkHealth}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 hover:text-white text-xs font-mono font-bold transition-all"
          >
            <RefreshCw size={12} />
            RETRY
          </button>
        </div>
      )}

      {/* 3. MAIN COMMAND CENTER GRID */}
      <div className="flex-1 flex flex-col gap-3.5 p-4 overflow-y-auto">
        {/* UPPER SECTION: SIDEBAR + CAMERA WALL + AI INVESTIGATOR */}
        <div className="flex flex-col lg:flex-row gap-3.5 items-stretch">
          {/* LEFT: Camera Control Panel */}
          <CameraSidebar
            cameras={cameras}
            selectedCameraId={highlightedCameraId}
            onSelectCamera={handleSelectCamera}
            onOpenUpload={() => setShowUpload(true)}
            backendStatus={backendStatus}
          />

          {/* CENTER: Camera Wall (2x2 Grid) */}
          <CameraWall
            cameras={cameras}
            loading={camerasLoading}
            activeView={activeView}
            highlightedCameraId={highlightedCameraId}
            seekTimestamps={seekTimestamps}
            onOpenCamera={handleSelectCamera}
          />

          {/* RIGHT: AI Investigator */}
          <AIInvestigator
            onQuery={handleQuery}
            loading={queryLoading}
            disabled={backendStatus === 'disconnected'}
            queryResult={queryResult}
            queryError={queryError}
            selectedMatch={selectedMatch}
            onSelectMatch={handleSelectMatch}
            onViewEvidence={handleViewEvidence}
          />
        </div>

        {/* 4. LOWER SECTION: INVESTIGATION TIMELINE & CROSS-CAMERA TRAJECTORY */}
        <div className="space-y-3">
          {/* Horizontal Investigation Timeline */}
          <InvestigationTimeline
            matches={queryResult?.matches || []}
            selectedMatch={selectedMatch}
            onSelectEvent={handleSelectMatch}
          />

          {/* Cross-Camera Trajectory (When available in query response) */}
          <TrajectoryView
            trajectory={queryResult?.trajectory}
            onJump={handleJumpToCamera}
          />
        </div>
      </div>

      {/* MODALS */}
      {showUpload && (
        <UploadModal
          onUploaded={() => {
            loadCameras();
            setShowUpload(false);
          }}
          onClose={() => setShowUpload(false)}
        />
      )}

      {evidenceMatch && (
        <EvidenceViewer
          match={evidenceMatch}
          onClose={() => setEvidenceMatch(null)}
          onOpenCamera={(camId) => {
            setHighlightedCameraId(camId);
            setActiveView({ camera_id: camId });
          }}
        />
      )}
    </div>
  );
}
