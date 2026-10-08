import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.query import TrajectoryRequest, TrajectoryResponse
from app.services.trajectory_service import trajectory_service
from app.db.session import get_db

logger = logging.getLogger("visiontrace.api.trajectory")

router = APIRouter(tags=["Trajectory"])

@router.post("/trajectory", response_model=TrajectoryResponse, summary="Compute Cross-Camera Trajectory (POST)")
def post_trajectory(
    request: TrajectoryRequest,
    db: Session = Depends(get_db),
) -> TrajectoryResponse:
    """
    Compute cross-camera trajectory for a specific object class and color.
    Uses NetworkX topology to validate transitions and chronological plausibility.
    Note: Represents a 'consistent visual match' rather than confirmed re-identification.
    """
    try:
        return trajectory_service.calculate_trajectory(
            object_type=request.object_type,
            color=request.color,
            db=db,
        )
    except Exception as e:
        logger.error(f"Error computing trajectory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trajectory calculation error: {str(e)}"
        )

@router.get("/trajectory", response_model=TrajectoryResponse, summary="Compute Cross-Camera Trajectory (GET)")
def get_trajectory(
    object_type: str = Query(..., description="Target object type (e.g., car, person)"),
    color: Optional[str] = Query(None, description="Optional color of target object"),
    db: Session = Depends(get_db),
) -> TrajectoryResponse:
    """
    GET endpoint for cross-camera trajectory computation.
    """
    try:
        return trajectory_service.calculate_trajectory(
            object_type=object_type,
            color=color,
            db=db,
        )
    except Exception as e:
        logger.error(f"Error computing trajectory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trajectory calculation error: {str(e)}"
        )
