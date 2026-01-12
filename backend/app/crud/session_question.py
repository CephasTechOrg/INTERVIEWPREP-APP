from sqlalchemy.orm import Session

from app.models.session_question import SessionQuestion


def mark_question_asked(db: Session, session_id: int, question_id: int) -> SessionQuestion:
    existing = (
        db.query(SessionQuestion)
        .filter(SessionQuestion.session_id == session_id, SessionQuestion.question_id == question_id)
        .first()
    )
    if existing:
        return existing

    sq = SessionQuestion(session_id=session_id, question_id=question_id)
    db.add(sq)
    db.commit()
    db.refresh(sq)
    return sq


def list_asked_question_ids(db: Session, session_id: int) -> list[int]:
    rows = db.query(SessionQuestion.question_id).filter(SessionQuestion.session_id == session_id).all()
    return [r[0] for r in rows]
