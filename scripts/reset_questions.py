from pathlib import Path
import sys

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from app.db.session import SessionLocal
from scripts.reseed_questions import reseed_questions


def reset_questions(db) -> None:
    db.execute(text("DELETE FROM session_questions"))
    db.execute(text("DELETE FROM user_questions_seen"))
    db.execute(text("DELETE FROM questions"))
    db.execute(text("UPDATE interview_sessions SET current_question_id = NULL"))
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        reset_questions(db)
        inserted, updated = reseed_questions(db, ROOT / "data" / "questions")
    finally:
        db.close()
    print(f"Questions reset and reseeded. inserted={inserted} updated={updated}")


if __name__ == "__main__":
    main()
