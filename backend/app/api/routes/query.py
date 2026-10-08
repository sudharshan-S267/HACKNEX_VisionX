import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_service import query_service
from app.db.session import get_db

logger = logging.getLogger("visiontrace.api.query")

router = APIRouter(tags=["Query"])

@router.post("/query", response_model=QueryResponse, summary="Query Surveillance Footage")
def post_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Process natural-language surveillance queries.
    
    Pipeline:
    1. Deterministic query parsing (object, color, action, location, camera, time, operation)
    2. Event retrieval and ranking from SQLite
    3. Trajectory compilation (if tracking requested)
    4. Grounded answer generation (summarizing only retrieved events via Ollama or deterministic engine)
    """
    try:
        response = query_service.process_query(request, db)
        return response
    except Exception as e:
        logger.error(f"Error executing query '{request.query}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution error: {str(e)}"
        )
