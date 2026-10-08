import axios, { AxiosError } from 'axios';
import type {
  Camera,
  CameraEvent,
  Evidence,
  HealthResponse,
  QueryRequest,
  QueryResponse,
  UploadResponse,
} from '../types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Error Helpers ─────────────────────────────────────────────────────────

function extractMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    return (
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message
    );
  }
  return 'Unknown error';
}

// ─── Health ────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<HealthResponse> {
  const { data } = await client.get<HealthResponse>('/api/v1/health');
  return data;
}

// ─── Cameras ───────────────────────────────────────────────────────────────

export async function getCameras(): Promise<Camera[]> {
  try {
    const { data } = await client.get<Camera[]>('/api/v1/cameras');
    return data;
  } catch (err) {
    throw new Error(`Failed to load cameras: ${extractMessage(err)}`);
  }
}

export async function getCameraEvents(cameraId: string): Promise<CameraEvent[]> {
  try {
    const { data } = await client.get<CameraEvent[]>(
      `/api/v1/cameras/${cameraId}/events`
    );
    return data;
  } catch (err) {
    throw new Error(`Failed to load events: ${extractMessage(err)}`);
  }
}

// ─── Upload ────────────────────────────────────────────────────────────────

export async function uploadVideo(
  cameraId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  const form = new FormData();
  form.append('video', file);
  form.append('camera_id', cameraId);

  try {
    const { data } = await client.post<UploadResponse>(
      `/api/v1/cameras/${cameraId}/video`,
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress(event) {
          if (event.total) {
            onProgress?.(Math.round((event.loaded / event.total) * 100));
          }
        },
      }
    );
    return data;
  } catch (err) {
    throw new Error(`Upload failed: ${extractMessage(err)}`);
  }
}

export async function getVideoStatus(videoId: number) {
  try {
    const { data } = await client.get(`/api/v1/videos/${videoId}/status`);
    return data;
  } catch (err) {
    throw new Error(`Failed to check video status: ${extractMessage(err)}`);
  }
}

// ─── Query ─────────────────────────────────────────────────────────────────

export async function queryVideos(req: QueryRequest): Promise<QueryResponse> {
  try {
    const { data } = await client.post<QueryResponse>('/api/v1/query', req);
    return data;
  } catch (err) {
    throw new Error(`Query failed: ${extractMessage(err)}`);
  }
}

// ─── Evidence ──────────────────────────────────────────────────────────────

export async function getEvidence(evidenceId: string): Promise<Evidence> {
  try {
    const { data } = await client.get<Evidence>(
      `/api/v1/evidence/${evidenceId}`
    );
    return data;
  } catch (err) {
    throw new Error(`Failed to load evidence: ${extractMessage(err)}`);
  }
}

export function buildEvidenceUrl(path: string): string {
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL}${path}`;
}
