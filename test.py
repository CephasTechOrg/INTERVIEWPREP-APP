#!/usr/bin/env python3
"""
Minimal backend smoke test.

Usage:
    python test.py
"""

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import inspect, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.crud.evaluation import upsert_evaluation  # noqa: E402
from app.crud.message import add_message  # noqa: E402
from app.crud.session import create_session, delete_session  # noqa: E402
from app.crud.user import create_user, get_by_email  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402

REQUIRED_TABLES = {
    "alembic_version",
    "audit_logs",
    "evaluations",
    "interview_sessions",
    "messages",
    "pending_signups",
    "questions",
    "session_questions",
    "user_questions_seen",
    "users",
}


def _fail(msg: str) -> int:
    print(f"[ERROR] {msg}")
    return 1


def main() -> int:
    if not settings.DATABASE_URL:
        return _fail("DATABASE_URL is not set.")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return _fail(f"Database connection failed: {exc}")

    tables = set(inspect(engine).get_table_names())
    missing = REQUIRED_TABLES - tables
    if missing:
        return _fail(f"Missing tables: {', '.join(sorted(missing))}. Run: alembic upgrade head")

    user_cols = {c["name"] for c in inspect(engine).get_columns("users")}
    required_user_cols = {"role_pref", "profile"}
    missing_cols = required_user_cols - user_cols
    if missing_cols:
        return _fail(f"Missing users columns: {', '.join(sorted(missing_cols))}. Run: alembic upgrade head")

    db = SessionLocal()
    user = None
    session = None
    try:
        email = f"smoke_{uuid.uuid4().hex[:10]}@example.com"
        user = create_user(db, email, "SmokeTest123!", "Smoke Test")
        user.is_verified = True
        db.add(user)
        db.commit()
        db.refresh(user)

        if not get_by_email(db, email):
            return _fail("User lookup failed after create.")

        session = create_session(
            db=db,
            user_id=user.id,
            role="SWE Intern",
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            behavioral_questions_target=0,
        )

        add_message(db, session.id, "student", "Smoke test message.")
        upsert_evaluation(
            db,
            session.id,
            80,
            {
                "communication": 7,
                "problem_solving": 7,
                "correctness_reasoning": 7,
                "complexity": 7,
                "edge_cases": 6,
            },
            {
                "strengths": ["Clear structure"],
                "weaknesses": ["Minor gaps"],
                "next_steps": ["Practice edge cases"],
            },
        )
    except Exception as exc:
        return _fail(f"Smoke test failed: {exc}")
    finally:
        try:
            if session is not None:
                delete_session(db, session)
            if user is not None:
                db.delete(user)
                db.commit()
        except Exception:
            pass
        db.close()

    print("[OK] Smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
