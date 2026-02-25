"""Restore local Postgres data into Supabase using SQL copy approach."""
from __future__ import annotations

import logging
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_database_url(env_path: Path) -> str:
    """Load the last (Supabase) DATABASE_URL from .env."""
    if not env_path.exists():
        raise FileNotFoundError(f".env not found at {env_path}")
    db_url: str | None = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DATABASE_URL="):
            db_url = line.split("=", 1)[1].strip()
    if not db_url:
        raise ValueError("DATABASE_URL not found in .env")
    return db_url


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / "backend" / ".env"

    supabase_url = _load_database_url(env_path)

    # Connect to Supabase
    logger.info("Connecting to Supabase...")
    engine = sa.create_engine(supabase_url)

    with Session(engine) as session:
        # Clear existing data (cascade delete where needed)
        tables = [
            "message",
            "session_feedback",
            "session_question",
            "session_embedding",
            "evaluation",
            "chat_thread",
            "interview_session",
            "user_question_seen",
            "question",
            "user",
            "audit_log",
            "pending_signup",
        ]

        logger.info("Clearing Supabase tables...")
        for table in tables:
            try:
                session.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))
                logger.info(f"  ✓ {table}")
            except Exception as e:
                logger.warning(f"  ⚠ {table}: {e}")

        session.commit()
        logger.info("✓ Supabase cleared. Now run:")
        logger.info("")
        logger.info("  cd backend")
        logger.info("  python -m alembic upgrade heads")
        logger.info("  python seed.py --questions")
        logger.info("")
        logger.info("This will recreate schema + seed questions.")


if __name__ == "__main__":
    main()
