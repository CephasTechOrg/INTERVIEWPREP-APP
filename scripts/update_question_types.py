import json
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "questions"

ALLOWED_QUESTION_TYPES = {"coding", "system_design", "behavioral", "conceptual"}
SYSTEM_DESIGN_TAGS = {
    "system-design",
    "distributed-systems",
    "system-thinking",
    "scalability",
    "reliability",
    "architecture",
    "observability",
    "databases",
    "api",
}
CONCEPTUAL_TAGS = {"fundamentals", "concepts", "oop"}


def _path_hints(base: Path, file: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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


def _normalize_question_type(raw, tags: list[str], track: str) -> str:
    val = str(raw).strip().lower() if raw is not None else ""
    if val in ALLOWED_QUESTION_TYPES:
        return val

    tag_set = {t.strip().lower() for t in tags if t and str(t).strip()}
    if track == "behavioral" or "behavioral" in tag_set:
        return "behavioral"
    if tag_set & SYSTEM_DESIGN_TAGS:
        return "system_design"
    if tag_set & CONCEPTUAL_TAGS:
        return "conceptual"
    return "coding"


def update_file(file_path: Path) -> tuple[int, int]:
    raw = file_path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return 0, 0

    payload = json.loads(raw)
    questions = payload.get("questions", [])
    if not isinstance(questions, list):
        return 0, 0

    track_hint, _company_hint, _difficulty_hint = _path_hints(DATA_DIR, file_path)
    track = str(payload.get("track") or track_hint or "").strip().lower()

    updated = 0
    total = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        total += 1
        tags = q.get("tags", [])
        tags_clean = [str(t).strip() for t in tags if t and str(t).strip()] if isinstance(tags, list) else []
        inferred = _normalize_question_type(q.get("question_type"), tags_clean, track)
        if q.get("question_type") != inferred:
            q["question_type"] = inferred
            updated += 1

    if updated:
        file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return total, updated


def main() -> None:
    if not DATA_DIR.exists():
        print("No data/questions directory found.")
        return

    total_questions = 0
    total_updated = 0
    files = list(DATA_DIR.rglob("*.json"))
    for file in files:
        total, updated = update_file(file)
        total_questions += total
        total_updated += updated

    print(f"Updated question_type in {total_updated} questions across {len(files)} files (total questions: {total_questions}).")


if __name__ == "__main__":
    main()
