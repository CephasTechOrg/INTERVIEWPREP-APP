import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db.init_db import load_questions_from_folder
from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.question import Question
from app.models.session_question import SessionQuestion
from app.models.user import User
from app.models.user_question_seen import UserQuestionSeen
from app.services.interview_engine import InterviewEngine


def cleanup(db, user_id: int | None, session_id: int | None) -> None:
    if session_id:
        db.query(Message).filter(Message.session_id == session_id).delete(synchronize_session=False)
        db.query(SessionQuestion).filter(SessionQuestion.session_id == session_id).delete(synchronize_session=False)
    if user_id:
        db.query(UserQuestionSeen).filter(UserQuestionSeen.user_id == user_id).delete(synchronize_session=False)
        db.query(InterviewSession).filter(InterviewSession.user_id == user_id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = None
    session = None

    try:
        load_questions_from_folder(db, str(ROOT / "data" / "questions"))

        user = User(
            email="diversity_regression@example.com",
            full_name="Diversity Regression",
            password_hash="x",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        q_last = (
            db.query(Question)
            .filter(
                Question.track == "swe_intern",
                Question.company_style == "general",
                Question.difficulty == "easy",
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            .first()
        )
        if not q_last:
            raise AssertionError("No technical question found for swe_intern/general/easy")

        session = InterviewSession(
            user_id=user.id,
            role="SWE Intern",
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            difficulty_current="easy",
            stage="candidate_solution",
            questions_asked_count=1,
            followups_used=0,
            max_questions=7,
            max_followups_per_question=2,
            behavioral_questions_target=2,
            skill_state={},
            current_question_id=q_last.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(SessionQuestion(session_id=session.id, question_id=q_last.id))
        db.commit()

        engine_obj = InterviewEngine()
        asked_ids, _asked_questions, used_tags, _behavioral_used = engine_obj._session_asked_state(db, session)
        next_q = engine_obj._pick_next_technical_question(db, session, asked_ids, used_tags)
        if not next_q:
            raise AssertionError("No next technical question found")

        last_tags = engine_obj._last_asked_technical_tags(db, session)
        if not last_tags:
            raise AssertionError("Last technical question has no tags")

        pool = []
        for diff in engine_obj._adaptive_difficulty_try_order(session):
            base = db.query(Question).filter(
                Question.track == session.track,
                Question.company_style == session.company_style,
                Question.difficulty == diff,
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            if asked_ids:
                base = base.filter(~Question.id.in_(asked_ids))
            pool = base.all()
            if pool:
                break

        if not pool:
            raise AssertionError("No candidate pool found for tag diversity check")

        def tag_set(q: Question) -> set[str]:
            return {t.strip().lower() for t in (q.tags() or []) if str(t).strip()}

        overlaps = [len(tag_set(c) & last_tags) for c in pool]
        min_overlap = min(overlaps) if overlaps else 0
        chosen_overlap = len(tag_set(next_q) & last_tags)
        if chosen_overlap != min_overlap:
            raise AssertionError("Tag diversity pick did not minimize overlap")

        return 0
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"Tag diversity regression failed: {exc}")
        return 1
    finally:
        try:
            cleanup(db, user.id if user else None, session.id if session else None)
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
