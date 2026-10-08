import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import engine, Base
from app.db.seed import seed_database
from app.api.routes.query import router as query_router
from app.api.routes.trajectory import router as trajectory_router
from app.api.routes.cameras import router as cameras_router
from app.services.query_service import query_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("visiontrace.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and seed initial data
    logger.info("Initializing VisionTrace backend database tables...")
    Base.metadata.create_all(bind=engine)
    seed_database()
    logger.info("Startup complete.")
    yield
    # Shutdown
    logger.info("Shutting down VisionTrace backend.")


app = FastAPI(
    title="VisionTrace AI",
    description="Multi-Camera Video Intelligence, Grounded Query, Trajectory and Video Ingestion Engine",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if "*" not in settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
# 1. Cameras, Video Upload & Ingestion, Evidence & Events: /api/v1/...
app.include_router(cameras_router)

# 2. Conversational & Grounded Query Engine: /api/v1/query
app.include_router(query_router, prefix="/api/v1")

# 3. Cross-Camera Trajectory Engine: /api/v1/trajectory
app.include_router(trajectory_router, prefix="/api/v1")


# Health Check Endpoints (both /health and /api/v1/health supported)
@app.get("/api/v1/health", summary="Service Health Check")
@app.get("/health", summary="Root Health Check")
def health_check():
    ollama_ok = query_service._check_ollama_health()
    return {
        "status": "ok",
        "version": settings.VERSION,
        "ollama": {
            "status": "connected" if ollama_ok else "unavailable",
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
        },
        "database": "sqlite",
    }


# Static Mounts for Direct Video/Evidence File Access
if settings.VIDEO_DIR.exists():
    app.mount("/data/videos", StaticFiles(directory=str(settings.VIDEO_DIR)), name="videos")

if settings.EVIDENCE_DIR.exists():
    app.mount("/data/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
