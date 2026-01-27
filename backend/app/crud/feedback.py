"""CRUD operations for session feedback."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.session_feedback import SessionFeedback
from app.models.interview_session import InterviewSession


def create_feedback(
    db: Session,
    session_id: int,
    user_id: int,
    rating: int,
    thumbs: str | None = None,
    comment: str | None = None,
    rating_questions: int | None = None,
    rating_feedback: int | None = None,
    rating_difficulty: int | None = None,
) -> SessionFeedback:
    """Create or update feedback for a session."""
    
    # Check if feedback already exists (upsert pattern)
    existing = db.query(SessionFeedback).filter(
        SessionFeedback.session_id == session_id
    ).first()
    
    if existing:
        existing.rating = rating
        existing.thumbs = thumbs
        existing.comment = comment
        existing.rating_questions = rating_questions
        existing.rating_feedback = rating_feedback
        existing.rating_difficulty = rating_difficulty
        db.commit()
        db.refresh(existing)
        return existing
    
    feedback = SessionFeedback(
        session_id=session_id,
        user_id=user_id,
        rating=rating,
        thumbs=thumbs,
        comment=comment,
        rating_questions=rating_questions,
        rating_feedback=rating_feedback,
        rating_difficulty=rating_difficulty,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_by_session(db: Session, session_id: int) -> SessionFeedback | None:
    """Get feedback for a specific session."""
    return db.query(SessionFeedback).filter(
        SessionFeedback.session_id == session_id
    ).first()


def get_user_feedback(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> list[SessionFeedback]:
    """Get all feedback submitted by a user."""
    return (
        db.query(SessionFeedback)
        .filter(SessionFeedback.user_id == user_id)
        .order_by(SessionFeedback.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_feedback_stats(db: Session, user_id: int | None = None) -> dict:
    """Get aggregated feedback statistics.
    
    Args:
        db: Database session
        user_id: If provided, filter to this user's sessions only
    
    Returns:
        Dictionary with feedback statistics
    """
    base_query = db.query(SessionFeedback)
    sessions_query = db.query(InterviewSession)
    
    if user_id:
        base_query = base_query.filter(SessionFeedback.user_id == user_id)
        sessions_query = sessions_query.filter(InterviewSession.user_id == user_id)
    
    # Count totals
    total_sessions = sessions_query.count()
    sessions_with_feedback = base_query.count()
    
    # Average rating
    avg_result = base_query.with_entities(func.avg(SessionFeedback.rating)).scalar()
    average_rating = round(float(avg_result), 2) if avg_result else None
    
    # Rating distribution
    rating_counts = (
        base_query
        .with_entities(SessionFeedback.rating, func.count(SessionFeedback.id))
        .group_by(SessionFeedback.rating)
        .all()
    )
    rating_distribution = {i: 0 for i in range(1, 6)}
    for rating, count in rating_counts:
        rating_distribution[rating] = count
    
    # Thumbs counts
    thumbs_up = base_query.filter(SessionFeedback.thumbs == "up").count()
    thumbs_down = base_query.filter(SessionFeedback.thumbs == "down").count()
    
    return {
        "total_sessions": total_sessions,
        "sessions_with_feedback": sessions_with_feedback,
        "average_rating": average_rating,
        "rating_distribution": rating_distribution,
        "thumbs_up_count": thumbs_up,
        "thumbs_down_count": thumbs_down,
    }


def get_highly_rated_sessions(
    db: Session,
    min_rating: int = 4,
    limit: int = 100
) -> list[int]:
    """Get session IDs with high ratings (for RAG candidate selection)."""
    results = (
        db.query(SessionFeedback.session_id)
        .filter(SessionFeedback.rating >= min_rating)
        .order_by(SessionFeedback.rating.desc(), SessionFeedback.created_at.desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in results]
