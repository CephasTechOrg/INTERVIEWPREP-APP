import asyncio
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
from app.services.llm_client import LLMClientError


class StubLLM:
    async def chat(self, *_args, **_kwargs):
        raise LLMClientError("stub")

    async def chat_json(self, *_args, **_kwargs):
        raise LLMClientError("stub")


def cleanup(db, user_id: int | None, session_id: int | None) -> None:
    if session_id:
        db.query(Message).filter(Message.session_id == session_id).delete(synchronize_session=False)
        db.query(SessionQuestion).filter(SessionQuestion.session_id == session_id).delete(synchronize_session=False)
    if user_id:
        db.query(UserQuestionSeen).filter(UserQuestionSeen.user_id == user_id).delete(synchronize_session=False)
        db.query(InterviewSession).filter(InterviewSession.user_id == user_id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle.lower() not in text.lower():
        raise AssertionError(f"{label} missing '{needle}'")


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = None
    session = None

    try:
        load_questions_from_folder(db, str(ROOT / "data" / "questions"))

        user = User(
            email="warmup_regression@example.com",
            full_name="Warmup Regression",
            password_hash="x",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = InterviewSession(
            user_id=user.id,
            role="SWE Intern",
            track="swe_intern",
            company_style="amazon",
            difficulty="medium",
            difficulty_current="easy",
            stage="intro",
            questions_asked_count=0,
            followups_used=0,
            max_questions=7,
            max_followups_per_question=2,
            behavioral_questions_target=2,
            skill_state={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        engine_obj = InterviewEngine()
        engine_obj.llm = StubLLM()

        msg1 = asyncio.run(engine_obj.ensure_question_and_intro(db, session, user_name=user.full_name))
        assert_contains(msg1, "how are you", "greeting")

        msg2 = asyncio.run(engine_obj.handle_student_message(db, session, "I am fine.", user_name=user.full_name))
        assert_contains(msg2, "i am doing well", "warmup reply")
        assert_contains(msg2, "your interviewer", "warmup reply")
        assert_contains(msg2, "behavioral question", "warmup question")

        db.refresh(session)
        warm = session.skill_state.get("warmup") if isinstance(session.skill_state, dict) else {}
        warm_id = warm.get("behavioral_question_id") if isinstance(warm, dict) else None
        if warm_id is None:
            raise AssertionError("warmup behavioral question id missing from state")

        asked_ids = [row[0] for row in db.query(SessionQuestion.question_id).filter(SessionQuestion.session_id == session.id).all()]
        if int(warm_id) not in asked_ids:
            raise AssertionError("warmup behavioral question not marked as asked")

        msg3 = asyncio.run(
            engine_obj.handle_student_message(db, session, "Because I want to grow as an engineer.", user_name=user.full_name)
        )
        assert_contains(msg3, "resta", "technical transition")

        db.refresh(session)
        if not session.current_question_id:
            raise AssertionError("technical question was not selected")
        q = db.query(Question).filter(Question.id == session.current_question_id).first()
        if not q:
            raise AssertionError("technical question not found in db")
        if "behavioral" in (q.tags_csv or "").lower():
            raise AssertionError("technical question should not be behavioral")

        return 0
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"Warmup regression failed: {exc}")
        return 1
    finally:
        try:
            cleanup(db, user.id if user else None, session.id if session else None)
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
