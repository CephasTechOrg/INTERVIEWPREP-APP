from sqlalchemy.orm import Session

from app.models.interview_session import InterviewSession
from app.models.session_question import SessionQuestion
from app.models.user_question_seen import UserQuestionSeen


def mark_question_seen(db: Session, user_id: int, question_id: int) -> UserQuestionSeen:
    existing = (
        db.query(UserQuestionSeen)
        .filter(UserQuestionSeen.user_id == user_id, UserQuestionSeen.question_id == question_id)
        .first()
    )
    if existing:
        return existing

    row = UserQuestionSeen(user_id=user_id, question_id=question_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_seen_question_ids(db: Session, user_id: int) -> list[int]:
    rows = db.query(UserQuestionSeen.question_id).filter(UserQuestionSeen.user_id == user_id).all()
    return [r[0] for r in rows]


def backfill_user_seen_questions(db: Session, user_id: int, limit: int = 5000) -> int:
    """
    Populate `user_questions_seen` from historical `session_questions` so new sessions
    avoid repeating questions the user has already seen in prior sessions.

    Safe to call repeatedly.
    """
    existing_rows = db.query(UserQuestionSeen.question_id).filter(UserQuestionSeen.user_id == user_id).all()
    existing = {r[0] for r in existing_rows}

    rows = (
        db.query(SessionQuestion.question_id)
        .join(InterviewSession, InterviewSession.id == SessionQuestion.session_id)
        .filter(InterviewSession.user_id == user_id)
        .distinct()
        .limit(max(1, min(int(limit or 5000), 20000)))
        .all()
    )
    missing = [qid for (qid,) in rows if qid not in existing]
    if not missing:
        return 0

    db.add_all([UserQuestionSeen(user_id=user_id, question_id=qid) for qid in missing])
    db.commit()
    return len(missing)
