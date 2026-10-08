from app.api.routes.query import router as query_router
from app.api.routes.trajectory import router as trajectory_router
from app.api.routes.cameras import router as cameras_router

__all__ = ["query_router", "trajectory_router", "cameras_router"]
