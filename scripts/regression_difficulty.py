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
            email="difficulty_regression@example.com",
            full_name="Difficulty Regression",
            password_hash="x",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        q = (
            db.query(Question)
            .filter(
                Question.track == "swe_intern",
                Question.company_style == "general",
                Question.difficulty == "easy",
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            .first()
        )
        if not q:
            raise AssertionError("No technical question found for swe_intern/general/easy")

        session = InterviewSession(
            user_id=user.id,
            role="SWE Intern",
            track="swe_intern",
            company_style="general",
            difficulty="hard",
            difficulty_current="easy",
            stage="candidate_solution",
            questions_asked_count=1,
            followups_used=0,
            max_questions=7,
            max_followups_per_question=2,
            behavioral_questions_target=2,
            skill_state={},
            current_question_id=q.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        engine_obj = InterviewEngine()
        strong = {k: 9 for k in engine_obj._RUBRIC_KEYS}
        weak = {k: 2 for k in engine_obj._RUBRIC_KEYS}

        engine_obj._update_skill_state(db, session, strong, is_behavioral=False)
        engine_obj._update_skill_state(db, session, strong, is_behavioral=False)
        engine_obj._maybe_bump_difficulty_current(db, session)
        db.refresh(session)
        if session.difficulty_current != "medium":
            raise AssertionError(f"Expected bump to medium, got {session.difficulty_current}")

        engine_obj._update_skill_state(db, session, strong, is_behavioral=False)
        engine_obj._update_skill_state(db, session, strong, is_behavioral=False)
        engine_obj._maybe_bump_difficulty_current(db, session)
        db.refresh(session)
        if session.difficulty_current != "hard":
            raise AssertionError(f"Expected bump to hard, got {session.difficulty_current}")

        engine_obj._update_skill_state(db, session, weak, is_behavioral=False)
        engine_obj._update_skill_state(db, session, weak, is_behavioral=False)
        engine_obj._maybe_bump_difficulty_current(db, session)
        db.refresh(session)
        if session.difficulty_current != "medium":
            raise AssertionError(f"Expected drop to medium, got {session.difficulty_current}")

        engine_obj._update_skill_state(db, session, weak, is_behavioral=False)
        engine_obj._update_skill_state(db, session, weak, is_behavioral=False)
        engine_obj._maybe_bump_difficulty_current(db, session)
        db.refresh(session)
        if session.difficulty_current != "easy":
            raise AssertionError(f"Expected drop to easy, got {session.difficulty_current}")

        return 0
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"Difficulty regression failed: {exc}")
        return 1
    finally:
        try:
            cleanup(db, user.id if user else None, session.id if session else None)
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
