import asyncio
import secrets
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.user import User
from app.services.scoring_engine import ScoringEngine


def cleanup_smoke_rows(db) -> None:
    users = db.query(User).filter(User.email.startswith("smoke_")).all()
    if not users:
        return
    user_ids = [u.id for u in users]
    session_ids = [s[0] for s in db.query(InterviewSession.id).filter(InterviewSession.user_id.in_(user_ids)).all()]
    if session_ids:
        db.query(Message).filter(Message.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(Evaluation).filter(Evaluation.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(InterviewSession).filter(InterviewSession.id.in_(session_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = None
    session = None

    try:
        cleanup_smoke_rows(db)
        token = secrets.token_urlsafe(8).replace("-", "").replace("_", "")
        email = f"smoke_{token.lower()}@example.com"

        user = User(
            email=email,
            full_name="Smoke Test",
            password_hash="smoke-hash",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = InterviewSession(
            user_id=user.id,
            role="Software Engineer",
            track="swe_engineer",
            company_style="general",
            difficulty="medium",
            difficulty_current="medium",
            stage="candidate_solution",
            questions_asked_count=1,
            followups_used=0,
            max_questions=7,
            max_followups_per_question=2,
            behavioral_questions_target=1,
            skill_state={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add_all(
            [
                Message(
                    session_id=session.id,
                    role="interviewer",
                    content="Describe a system design approach for a URL shortener.",
                ),
                Message(
                    session_id=session.id,
                    role="student",
                    content="I would start with requirements, then define APIs, data model, and scaling plan.",
                ),
                Message(
                    session_id=session.id,
                    role="interviewer",
                    content="What are the main trade-offs in your storage design?",
                ),
            ]
        )
        db.commit()

        scorer = ScoringEngine()
        result = asyncio.run(scorer.finalize(db, session.id))
        print("Finalize result:")
        print(result)
        return 0
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"Smoke finalize failed: {exc}")
        return 1
    finally:
        try:
            if session:
                db.query(Message).filter(Message.session_id == session.id).delete(synchronize_session=False)
                db.query(Evaluation).filter(Evaluation.session_id == session.id).delete(synchronize_session=False)
                db.query(InterviewSession).filter(InterviewSession.id == session.id).delete(synchronize_session=False)
            if user:
                db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
