"""
CRUD operations for interview level outcomes.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.interview_level_outcome import InterviewLevelOutcome


def create_level_outcome(
    db: Session,
    session_id: str,
    outcome_data: dict,
) -> InterviewLevelOutcome:
    """Create a new interview level outcome record."""
    db_outcome = InterviewLevelOutcome(
        session_id=session_id,
        role=outcome_data.get("role"),
        company_tier=outcome_data.get("company_tier"),
        estimated_level=outcome_data.get("estimated_level"),
        estimated_level_display=outcome_data.get("estimated_level_display"),
        readiness_percent=outcome_data.get("readiness_percent", 0),
        confidence=outcome_data.get("confidence", "medium"),
        next_level=outcome_data.get("next_level"),
        strengths=outcome_data.get("strengths", []),
        gaps=outcome_data.get("gaps", []),
        next_actions=outcome_data.get("next_actions", []),
        rubric_scores_used=outcome_data.get("rubric_scores_used", {}),
    )
    db.add(db_outcome)
    db.commit()
    db.refresh(db_outcome)
    return db_outcome


def get_level_outcome_by_session(
    db: Session, session_id: str
) -> InterviewLevelOutcome | None:
    """Get the level outcome for a specific interview session."""
    return db.query(InterviewLevelOutcome).filter(
        InterviewLevelOutcome.session_id == session_id
    ).first()


def get_level_outcomes_by_role(
    db: Session, role: str, limit: int = 10
) -> list[InterviewLevelOutcome]:
    """Get recent level outcomes for a specific role."""
    return (
        db.query(InterviewLevelOutcome)
        .filter(InterviewLevelOutcome.role == role)
        .order_by(desc(InterviewLevelOutcome.created_at))
        .limit(limit)
        .all()
    )


def get_level_outcomes_by_tier(
    db: Session, company_tier: str, limit: int = 10
) -> list[InterviewLevelOutcome]:
    """Get recent level outcomes for a specific company tier."""
    return (
        db.query(InterviewLevelOutcome)
        .filter(InterviewLevelOutcome.company_tier == company_tier)
        .order_by(desc(InterviewLevelOutcome.created_at))
        .limit(limit)
        .all()
    )


def update_level_outcome(
    db: Session,
    session_id: str,
    outcome_data: dict,
) -> InterviewLevelOutcome | None:
    """Update an existing interview level outcome."""
    db_outcome = get_level_outcome_by_session(db, session_id)
    if not db_outcome:
        return None
    
    for key, value in outcome_data.items():
        if hasattr(db_outcome, key):
            setattr(db_outcome, key, value)
    
    db.commit()
    db.refresh(db_outcome)
    return db_outcome


def delete_level_outcome(db: Session, session_id: str) -> bool:
    """Delete an interview level outcome."""
    db_outcome = get_level_outcome_by_session(db, session_id)
    if not db_outcome:
        return False
    
    db.delete(db_outcome)
    db.commit()
    return True
