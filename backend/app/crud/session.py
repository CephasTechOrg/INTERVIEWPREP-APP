from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.interview_session import InterviewSession
from app.crud import user_question_seen as user_question_seen_crud
from app.models.message import Message
from app.models.evaluation import Evaluation
from app.models.session_question import SessionQuestion


def _initial_difficulty_current(difficulty: str) -> str:
    d = (difficulty or "").strip().lower()
    if d in ("easy", "medium", "hard"):
        return d
    return "easy"


def create_session(
    db: Session,
    user_id: int,
    role: str,
    track: str,
    company_style: str,
    difficulty: str,
    behavioral_questions_target: int = 2,
) -> InterviewSession:
    # Ensure historical sessions contribute to "seen questions" so new sessions
    # don't repeatedly start with the same prompt.
    try:
        user_question_seen_crud.backfill_user_seen_questions(db, user_id=user_id)
    except Exception:
        pass

    behavioral_target = max(0, min(int(behavioral_questions_target or 0), 3))

    s = InterviewSession(
        user_id=user_id,
        role=role,
        track=track,
        company_style=company_style,
        difficulty=difficulty,
        difficulty_current=_initial_difficulty_current(difficulty),
        stage="intro",
        questions_asked_count=0,
        followups_used=0,
        max_questions=7,
        max_followups_per_question=2,
        behavioral_questions_target=behavioral_target,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_session(db: Session, session_id: int) -> InterviewSession | None:
    return db.query(InterviewSession).filter(InterviewSession.id == session_id).first()


def list_sessions(db: Session, user_id: int, limit: int = 50) -> list[InterviewSession]:
    limit = max(1, min(int(limit or 50), 200))
    return (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(desc(InterviewSession.created_at), desc(InterviewSession.id))
        .limit(limit)
        .all()
    )


def delete_session(db: Session, session: InterviewSession) -> None:
    """
    Deletes a session and its related rows (messages, evaluation, asked-question links).
    Does NOT touch per-user `user_questions_seen` (keeps the no-repeat behavior stable).
    """
    session_id = session.id
    db.query(Message).filter(Message.session_id == session_id).delete(synchronize_session=False)
    db.query(Evaluation).filter(Evaluation.session_id == session_id).delete(synchronize_session=False)
    db.query(SessionQuestion).filter(SessionQuestion.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()


def update_stage(db: Session, session: InterviewSession, stage: str) -> InterviewSession:
    session.stage = stage
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def set_current_question(db: Session, session: InterviewSession, question_id: int) -> InterviewSession:
    session.current_question_id = question_id
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
