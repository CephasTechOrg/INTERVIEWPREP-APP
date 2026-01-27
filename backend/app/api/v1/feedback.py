"""API endpoints for session feedback."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.feedback import (
    create_feedback,
    get_feedback_by_session,
    get_user_feedback,
    get_feedback_stats,
)
from app.crud.session import get_session
from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback")


def _create_embedding_background(session_id: int, rating: int):
    """Background task to create/update embedding after feedback."""
    from app.db.session import SessionLocal
    from app.services.session_embedder import on_feedback_submitted
    
    db = SessionLocal()
    try:
        on_feedback_submitted(db, session_id, rating)
    except Exception as e:
        logger.error(f"Failed to create embedding for session {session_id}: {e}")
    finally:
        db.close()


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    payload: FeedbackCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Submit feedback for a completed interview session.
    
    Users can only submit feedback for their own sessions.
    Submitting again for the same session updates the existing feedback.
    Also triggers embedding creation in the background.
    """
    # Verify session exists and belongs to user
    session = get_session(db, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    
    feedback = create_feedback(
        db=db,
        session_id=payload.session_id,
        user_id=user.id,
        rating=payload.rating,
        thumbs=payload.thumbs,
        comment=payload.comment,
        rating_questions=payload.rating_questions,
        rating_feedback=payload.rating_feedback,
        rating_difficulty=payload.rating_difficulty,
    )
    
    # Create/update embedding in background
    background_tasks.add_task(
        _create_embedding_background, 
        payload.session_id, 
        payload.rating
    )
    
    return feedback


@router.get("/session/{session_id}", response_model=FeedbackOut | None)
def get_session_feedback(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get feedback for a specific session."""
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    
    return get_feedback_by_session(db, session_id)


@router.get("/me", response_model=list[FeedbackOut])
def get_my_feedback(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get all feedback submitted by the current user."""
    return get_user_feedback(db, user.id, limit=limit, offset=offset)


@router.get("/stats", response_model=FeedbackStats)
def get_my_feedback_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get aggregated feedback statistics for the current user's sessions."""
    stats = get_feedback_stats(db, user_id=user.id)
    return FeedbackStats(**stats)
