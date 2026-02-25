#!/usr/bin/env python
"""
Seed utility for InterviewPrep backend.

Usage (from backend/):
  python seed.py
  python seed.py --reset
  python seed.py --questions
  python seed.py --migrate --questions
  python seed.py --questions --no-upsert

Default (no flags): runs migrations + upserts questions from data/questions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.db import init_db as qinit  # noqa: E402
from app.models.question import Question  # noqa: E402


def run_migrations() -> None:
    """Run alembic upgrade head."""
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def reset_all_tables(db) -> None:
    """
    Truncate all app tables (destructive).
    Uses CASCADE when available; falls back to ordered deletes.
    """
    tables = [
        "messages",
        "session_questions",
        "evaluations",
        "session_feedback",
        "session_embeddings",
        "response_examples",
        "question_embeddings",
        "user_questions_seen",
        "pending_signups",
        "audit_logs",
        "interview_sessions",
        "users",
        "questions",
    ]

    try:
        db.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE;"))
        db.commit()
        return
    except Exception:
        db.rollback()

    # Fallback for non-Postgres
    for table in tables:
        db.execute(text(f"DELETE FROM {table};"))
    db.commit()


def _load_json(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _upsert_question(
    db, q_data: dict, track: str, company_style: str, difficulty: str, allow_update: bool
) -> str:
    title = (q_data.get("title") or "").strip()
    prompt = (q_data.get("prompt") or "").strip()
    if not title or not prompt:
        return "skipped"

    tags = q_data.get("tags", [])
    if not isinstance(tags, list) or not [t for t in tags if t and str(t).strip()]:
        return "skipped"

    tags_clean = [str(t).strip() for t in tags if t and str(t).strip()]
    tags_csv = ",".join(tags_clean)
    followups = q_data.get("followups", [])
    if not isinstance(followups, list):
        followups = []

    question_type = qinit._normalize_question_type(q_data.get("question_type"), tags_clean, track)
    expected_topics = qinit._clean_list(q_data.get("expected_topics"))
    evaluation_focus = qinit._clean_list(q_data.get("evaluation_focus"))
    
    meta: dict = {}
    company_bar = str(q_data.get("company_bar") or "").strip()
    if company_bar:
        meta["company_bar"] = company_bar

    existing = (
        db.query(Question)
        .filter(
            Question.track == track,
            Question.company_style == company_style,
            Question.difficulty == difficulty,
            Question.title == title,
        )
        .first()
    )
    if existing:
        if not allow_update:
            return "skipped"
        existing.prompt = prompt
        existing.tags_csv = tags_csv
        existing.followups = followups
        existing.question_type = question_type
        existing.expected_topics = expected_topics
        existing.evaluation_focus = evaluation_focus
        existing.meta = meta
        db.add(existing)
        return "updated"

    db.add(
        Question(
            track=track,
            company_style=company_style,
            difficulty=difficulty,
            title=title,
            prompt=prompt,
            tags_csv=tags_csv,
            followups=followups,
            question_type=question_type,
            expected_topics=expected_topics,
            evaluation_focus=evaluation_focus,
            meta=meta,
        )
    )
    return "inserted"


def sync_questions_from_folder(db, folder: str, allow_update: bool) -> dict:
    base = Path(folder)
    if not base.exists():
        return {"inserted": 0, "updated": 0, "skipped": 0}

    inserted = updated = skipped = 0
    for file in base.rglob("*.json"):
        payload = _load_json(file)
        if not payload:
            continue

        track_hint, company_hint, difficulty_hint = qinit._path_hints(base, file)
        track = payload.get("track") or track_hint
        company_style = payload.get("company_style") or company_hint
        difficulty = payload.get("difficulty") or difficulty_hint
        questions = payload.get("questions", [])

        if not track or not company_style or not difficulty or not isinstance(questions, list):
            continue
        track = str(track).strip().lower()
        company_style = str(company_style).strip().lower()
        difficulty = str(difficulty).strip().lower()

        if track not in qinit.ALLOWED_TRACKS:
            continue
        if company_style not in qinit.ALLOWED_COMPANY_STYLES:
            continue
        if difficulty not in qinit.ALLOWED_DIFFICULTIES:
            continue

        # Enforce path/content consistency when hints exist.
        if track_hint and track != track_hint:
            continue
        if company_hint and company_style != company_hint:
            continue
        if difficulty_hint and difficulty != difficulty_hint:
            continue

        for q in questions:
            if not isinstance(q, dict):
                skipped += 1
                continue
            outcome = _upsert_question(db, q, track, company_style, difficulty, allow_update)
            if outcome == "inserted":
                inserted += 1
            elif outcome == "updated":
                updated += 1
            else:
                skipped += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed InterviewPrep database.")
    parser.add_argument("--migrate", action="store_true", help="Run alembic upgrade head before seeding.")
    parser.add_argument("--reset", action="store_true", help="Delete all rows from all tables before seeding.")
    parser.add_argument("--questions", action="store_true", help="Sync questions from data/questions.")
    parser.add_argument("--no-upsert", action="store_true", help="Insert only; do not update existing questions.")
    parser.add_argument(
        "--folder",
        default=str(ROOT.parent / "data" / "questions"),
        help="Path to questions folder (default: ../data/questions).",
    )

    args = parser.parse_args()

    if args.no_upsert and not args.questions:
        args.questions = True

    # Default behavior: migrate + questions upsert
    if not any([args.migrate, args.reset, args.questions, args.no_upsert]):
        args.migrate = True
        args.questions = True

    if args.migrate:
        run_migrations()

    db = SessionLocal()
    try:
        if args.reset:
            reset_all_tables(db)

        if args.questions:
            stats = sync_questions_from_folder(db, args.folder, allow_update=not args.no_upsert)
            print(
                "Questions synced:",
                f"inserted={stats['inserted']}",
                f"updated={stats['updated']}",
                f"skipped={stats['skipped']}",
            )
        else:
            print("No seed actions selected. Use --questions or run without flags.")
    finally:
        db.close()


if __name__ == "__main__":
    def _safe_db_url(raw: str) -> str:
        if not raw:
            return ""
        try:
            parts = urlsplit(raw)
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            if parts.username:
                host = f"{parts.username}:***@{host}"
            return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
        except Exception:
            return "<redacted>"

    safe_db = _safe_db_url(settings.DATABASE_URL)
    if safe_db:
        print(f"[seed] ENV={settings.ENV} DB={safe_db}")
    else:
        print(f"[seed] ENV={settings.ENV}")
    main()
