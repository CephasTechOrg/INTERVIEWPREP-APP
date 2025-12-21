import json
from json import JSONDecodeError
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.question import Question
from app.core.constants import ALLOWED_COMPANY_STYLES, ALLOWED_DIFFICULTIES, ALLOWED_TRACKS


def _path_hints(base: Path, file: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract (track, company, difficulty) hints from the nested path:
    data/questions/<track>/<company>/<difficulty>.json
    """
    try:
        rel = file.relative_to(base)
    except Exception:
        return None, None, None

    parts = rel.parts
    track_hint = parts[0] if len(parts) >= 3 else None
    company_hint = parts[1] if len(parts) >= 3 else None
    difficulty_hint = None
    stem = file.stem.lower()
    if "easy" in stem:
        difficulty_hint = "easy"
    elif "medium" in stem:
        difficulty_hint = "medium"
    elif "hard" in stem:
        difficulty_hint = "hard"
    return track_hint, company_hint, difficulty_hint


def load_questions_from_folder(db: Session, folder: str) -> int:
    """
    Loads questions from data/questions into Postgres.
    Supports nested structure: data/questions/<track>/<company>/<difficulty>.json
    (falls back to flat files for backward compatibility).

    Expected JSON shape:
    {
      "track": "swe_intern",
      "company_style": "apple",
      "difficulty": "easy",
      "questions": [
        {"title": "...", "prompt": "...", "tags": ["arrays","hashmap"]}
      ]
    }
    """
    base = Path(folder)
    if not base.exists():
        return 0

    inserted = 0
    # Walk all JSON files (nested or flat)
    for file in base.rglob("*.json"):
        raw = file.read_text(encoding="utf-8").strip()
        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except JSONDecodeError:
            continue

        track_hint, company_hint, difficulty_hint = _path_hints(base, file)
        track = payload.get("track") or track_hint
        company_style = payload.get("company_style") or company_hint
        difficulty = payload.get("difficulty") or difficulty_hint
        questions = payload.get("questions", [])

        if not track or not company_style or not difficulty or not isinstance(questions, list):
            continue
        track = str(track).strip().lower()
        company_style = str(company_style).strip().lower()
        difficulty = str(difficulty).strip().lower()
        if track not in ALLOWED_TRACKS:
            continue
        if company_style not in ALLOWED_COMPANY_STYLES:
            continue
        if difficulty not in ALLOWED_DIFFICULTIES:
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
                continue
            title = (q.get("title") or "").strip()
            prompt = (q.get("prompt") or "").strip()
            if not title or not prompt:
                continue
            tags = q.get("tags", [])
            if not isinstance(tags, list) or not [t for t in tags if t and str(t).strip()]:
                continue
            tags_csv = ",".join([t.strip() for t in tags if t and str(t).strip()])
            followups = q.get("followups", [])
            if not isinstance(followups, list):
                followups = []

            # Avoid duplicates: track+company+diff+title
            exists = (
                db.query(Question)
                .filter(
                    Question.track == track,
                    Question.company_style == company_style,
                    Question.difficulty == difficulty,
                    Question.title == title,
                )
                .first()
            )
            if exists:
                continue

            db.add(
                Question(
                    track=track,
                    company_style=company_style,
                    difficulty=difficulty,
                    title=title,
                    prompt=prompt,
                    tags_csv=tags_csv,
                    followups=followups,
                )
            )
            inserted += 1

    db.commit()
    return inserted
