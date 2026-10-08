# VisionTrace AI — Frontend

> Multi-Camera Video Intelligence Dashboard  
> Built for **HACKNEX 2026** Hackathon

---

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open → **http://localhost:5173**

---

## Environment Variables

Create a `.env` file in `frontend/` (already provided):

```env
VITE_API_BASE_URL=http://localhost:8000
```

Change the URL to point at your backend server.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| React 18 + Vite | SPA framework & bundler |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| React Router v6 | Client-side routing |
| Axios | HTTP requests |
| Lucide React | Icons |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── CameraCard.tsx      # Individual camera tile with video + status
│   │   ├── CameraGrid.tsx      # 2×2 responsive grid of CameraCards
│   │   ├── VideoPlayer.tsx     # HTML5 video player with seek support
│   │   ├── QueryBar.tsx        # NL query input with suggestions
│   │   ├── ResultCard.tsx      # Single query match card
│   │   ├── Timeline.tsx        # Cross-camera trajectory visualizer
│   │   ├── EvidencePanel.tsx   # Modal overlay for evidence video
│   │   ├── UploadPanel.tsx     # Drag-and-drop multi-video uploader
│   │   └── Header.tsx          # Top bar with brand + backend status
│   ├── pages/
│   │   └── Dashboard.tsx       # Main page — orchestrates all state
│   ├── services/
│   │   └── api.ts              # All backend API calls (Axios)
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css               # Tailwind + custom glass/dark theme
├── .env
├── index.html
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── vite.config.ts
└── tsconfig.json
```

---

## Backend API Contract

The frontend expects the following endpoints:

### `GET /api/v1/health`
```json
{ "status": "ok", "version": "1.0.0" }
```

### `GET /api/v1/cameras`
```json
[
  {
    "camera_id": "CAM-01",
    "camera_name": "Main Gate",
    "location": "North Entrance",
    "status": "online",
    "video_url": "/api/v1/cameras/CAM-01/stream",
    "event_count": 3,
    "last_seen": "2026-10-08T14:00:00Z"
  }
]
```

### `POST /api/v1/cameras/{camera_id}/video`
- **Body**: `multipart/form-data` — field `video` (file), field `camera_id` (string)
- **Response**:
```json
{ "camera_id": "CAM-01", "camera_name": "Main Gate", "status": "processing" }
```

### `POST /api/v1/query`
- **Body**:
```json
{ "query": "Find the red car" }
```
- **Response**:
```json
{
  "query": "Find the red car",
  "answer": "The red car was detected at the Main Gate and later at the Parking Area.",
  "matches": [
    {
      "camera_id": "CAM-01",
      "camera_name": "Main Gate",
      "timestamp": 12.4,
      "confidence": 0.94,
      "event_type": "vehicle_detected",
      "description": "Red sedan entering the main gate",
      "evidence_url": "/api/v1/evidence/clip-001"
    }
  ],
  "trajectory": [
    { "camera_id": "CAM-01", "camera_name": "Main Gate", "timestamp": 12.4 },
    { "camera_id": "CAM-02", "camera_name": "Parking Area", "timestamp": 18.7 }
  ],
  "processing_time_ms": 420
}
```

### `GET /api/v1/evidence/{evidence_id}`
```json
{
  "evidence_id": "clip-001",
  "camera_id": "CAM-01",
  "camera_name": "Main Gate",
  "timestamp": 12.4,
  "duration": 10.0,
  "video_url": "/api/v1/evidence/clip-001/video"
}
```

### `GET /api/v1/cameras/{camera_id}/events`
```json
[
  {
    "event_id": "evt-001",
    "camera_id": "CAM-01",
    "event_type": "vehicle_detected",
    "timestamp": 12.4,
    "confidence": 0.94,
    "description": "Red sedan at gate"
  }
]
```

---

## CORS

Your backend must allow `http://localhost:5173` in its CORS policy.

---

## When Backend is Offline

- Red banner shows the backend URL and a Retry button
- Camera grid shows placeholder cards (no data)
- Query input is disabled with a clear error message
- Upload button opens the modal but uploads will fail gracefully with per-file error labels

---

## Assumptions

1. Backend serves video files as static media at the URLs returned in `video_url` / `evidence_url`.
2. Video files are seekable (range requests supported).
3. `evidence_url` in query matches is a path like `/api/v1/evidence/clip-001` — the frontend prepends `VITE_API_BASE_URL`.
4. Camera status values are one of `"online"`, `"offline"`, or `"processing"`.
5. `timestamp` fields are in **seconds** (float).
6. The backend is responsible for all AI/ML inference — the frontend only renders results.
