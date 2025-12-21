from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation


def upsert_evaluation(db: Session, session_id: int, overall_score: int, rubric: dict, summary: dict) -> Evaluation:
    existing = db.query(Evaluation).filter(Evaluation.session_id == session_id).first()
    if existing:
        existing.overall_score = overall_score
        existing.rubric = rubric
        existing.summary = summary
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    e = Evaluation(session_id=session_id, overall_score=overall_score, rubric=rubric, summary=summary)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def get_evaluation(db: Session, session_id: int) -> Evaluation | None:
    return db.query(Evaluation).filter(Evaluation.session_id == session_id).first()
