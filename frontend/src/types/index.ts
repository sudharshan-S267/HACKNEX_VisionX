// ─── Camera ────────────────────────────────────────────────────────────────

export interface Camera {
  camera_id: string;
  camera_name: string;
  location?: string;
  status: 'online' | 'offline' | 'processing';
  stream_url?: string;
  video_url?: string;
  event_count: number;
  last_seen?: string;
  thumbnail_url?: string;
}

// ─── Events ────────────────────────────────────────────────────────────────

export interface CameraEvent {
  event_id: string;
  camera_id: string;
  event_type: string;
  timestamp: number;
  confidence: number;
  description: string;
  thumbnail_url?: string;
}

// ─── Query ─────────────────────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  camera_ids?: string[];
  time_range?: {
    start: number;
    end: number;
  };
}

export interface Match {
  id?: number;
  camera_id: string;
  camera_name: string;
  timestamp: number;
  confidence: number;
  event_type: string;
  object_type?: string;
  color?: string;
  description: string;
  evidence_url?: string;
  thumbnail_url?: string;
  bounding_box?: {
    x: number;
    y: number;
    w: number;
    h: number;
    norm_x?: number;
    norm_y?: number;
    norm_w?: number;
    norm_h?: number;
  };
}

export interface TrajectoryPoint {
  camera_id: string;
  camera_name?: string;
  timestamp: number;
  location?: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  matches: Match[];
  trajectory?: TrajectoryPoint[];
  processing_time_ms?: number;
  total_frames_analyzed?: number;
}

// ─── Evidence ──────────────────────────────────────────────────────────────

export interface Evidence {
  evidence_id: string;
  camera_id: string;
  camera_name: string;
  timestamp: number;
  duration: number;
  video_url: string;
  thumbnail_url?: string;
  description?: string;
}

// ─── Upload ────────────────────────────────────────────────────────────────

export interface UploadEntry {
  id: string;
  camera_id: string;
  camera_name: string;
  file: File;
  progress: number;
  status: 'idle' | 'uploading' | 'processing' | 'ready' | 'error';
  error?: string;
  video_url?: string;
}

export interface UploadResponse {
  camera_id: string;
  camera_name?: string;
  status: 'processing' | 'ready';
  video_url?: string;
  message?: string;
  video_id?: number;
}

export interface VideoStatusResponse {
  video_id: number;
  camera_id: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  fps?: number;
  duration?: number;
  event_count?: number;
}

// ─── Health ────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version?: string;
  uptime_seconds?: number;
  cameras_online?: number;
  message?: string;
}

// ─── UI State ──────────────────────────────────────────────────────────────

export type BackendStatus = 'connected' | 'connecting' | 'disconnected';

export interface ActiveView {
  camera_id: string;
  timestamp?: number;
}
