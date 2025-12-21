from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.question import Question
from app.crud.session_question import list_asked_question_ids


def list_questions(db: Session, track: str | None, company_style: str | None, difficulty: str | None) -> list[Question]:
    q = db.query(Question)
    conditions = []
    if track:
        conditions.append(Question.track == track)
    if company_style:
        conditions.append(Question.company_style == company_style)
    if difficulty:
        conditions.append(Question.difficulty == difficulty)
    if conditions:
        q = q.filter(and_(*conditions))
    return q.order_by(Question.id.asc()).all()


def get_question(db: Session, question_id: int) -> Question | None:
    return db.query(Question).filter(Question.id == question_id).first()


def pick_next_question(db: Session, track: str, company_style: str, difficulty: str) -> Question | None:
    # Simple strategy: return first matching question. Upgrade later to random / adaptive selection.
    return (
        db.query(Question)
        .filter(
            Question.track == track,
            Question.company_style == company_style,
            Question.difficulty == difficulty,
        )
        .order_by(Question.id.asc())
        .first()
    )


def pick_next_unseen_question(
    db: Session,
    session_id: int,
    track: str,
    company_style: str,
    difficulty: str,
) -> Question | None:
    asked_ids = set(list_asked_question_ids(db, session_id))
    q = (
        db.query(Question)
        .filter(
            Question.track == track,
            Question.company_style == company_style,
            Question.difficulty == difficulty,
        )
    )
    if asked_ids:
        q = q.filter(~Question.id.in_(asked_ids))
    # Postgres random ordering
    return q.order_by(func.random()).first()


def count_questions(
    db: Session,
    track: str,
    company_style: str,
    difficulty: str,
    exclude_behavioral: bool = False,
) -> int:
    q = db.query(func.count(Question.id)).filter(
        Question.track == track,
        Question.company_style == company_style,
        Question.difficulty == difficulty,
    )
    if exclude_behavioral:
        q = q.filter(~Question.tags_csv.ilike("%behavioral%"))
    return int(q.scalar() or 0)
