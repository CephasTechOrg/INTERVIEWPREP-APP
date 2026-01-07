import argparse
import json
import sys
from pathlib import Path


ALLOWED_TRACKS = {"behavioral", "swe_intern", "swe_engineer"}
ALLOWED_COMPANIES = {"general", "amazon", "apple", "google", "microsoft", "meta"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_QUESTION_TYPES = {"coding", "system_design", "behavioral", "conceptual"}


def _path_hints(base: Path, file: Path):
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


def _as_str(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def validate_file(path: Path, base: Path, seen):
    errors = []
    warnings = []
    count = 0

    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        errors.append(f"{path}: failed to read file ({exc})")
        return errors, warnings, count

    if not raw:
        errors.append(f"{path}: empty file")
        return errors, warnings, count

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON ({exc})")
        return errors, warnings, count

    if not isinstance(payload, dict):
        errors.append(f"{path}: expected JSON object at root")
        return errors, warnings, count

    track = _as_str(payload.get("track")).lower()
    company = _as_str(payload.get("company_style")).lower()
    difficulty = _as_str(payload.get("difficulty")).lower()
    questions = payload.get("questions")

    if not track:
        errors.append(f"{path}: missing 'track'")
    if not company:
        errors.append(f"{path}: missing 'company_style'")
    if not difficulty:
        errors.append(f"{path}: missing 'difficulty'")
    if not isinstance(questions, list):
        errors.append(f"{path}: 'questions' must be a list")
        questions = []
    if isinstance(questions, list) and not questions:
        errors.append(f"{path}: no questions found")

    if track and track not in ALLOWED_TRACKS:
        warnings.append(f"{path}: unknown track '{track}'")
    if company and company not in ALLOWED_COMPANIES:
        warnings.append(f"{path}: unknown company_style '{company}'")
    if difficulty and difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(f"{path}: invalid difficulty '{difficulty}'")

    track_hint, company_hint, difficulty_hint = _path_hints(base, path)
    if track_hint and track and track != track_hint:
        errors.append(f"{path}: track '{track}' does not match path '{track_hint}'")
    if company_hint and company and company != company_hint:
        errors.append(f"{path}: company_style '{company}' does not match path '{company_hint}'")
    if difficulty_hint and difficulty and difficulty != difficulty_hint:
        errors.append(f"{path}: difficulty '{difficulty}' does not match file name '{path.name}'")

    seen_titles = seen.get("titles", set())
    seen_prompts = seen.get("prompts", set())

    for idx, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            errors.append(f"{path}: question {idx} is not an object")
            continue

        title = _as_str(q.get("title"))
        prompt = _as_str(q.get("prompt"))
        if not title:
            errors.append(f"{path}: question {idx} missing title")
        if not prompt:
            errors.append(f"{path}: question {idx} missing prompt")

        tags = q.get("tags", [])
        if tags is None:
            errors.append(f"{path}: question {idx} missing tags")
            tags = []
        if not isinstance(tags, list):
            errors.append(f"{path}: question {idx} tags must be a list")
            tags = []
        if isinstance(tags, list) and not [t for t in tags if _as_str(t)]:
            errors.append(f"{path}: question {idx} has no valid tags")
        else:
            for t in tags:
                if not _as_str(t):
                    errors.append(f"{path}: question {idx} has empty tag")
                elif str(t).strip() != str(t).strip().lower():
                    warnings.append(f"{path}: question {idx} tag '{t}' should be lowercase")

        followups = q.get("followups", [])
        if followups is None:
            followups = []
        if not isinstance(followups, list):
            warnings.append(f"{path}: question {idx} followups should be a list")
            followups = []
        else:
            for f in followups:
                if not _as_str(f):
                    warnings.append(f"{path}: question {idx} has empty followup")

        q_type = _as_str(q.get("question_type") or q.get("type")).lower()
        if q_type and q_type not in ALLOWED_QUESTION_TYPES:
            warnings.append(f"{path}: question {idx} unknown question_type '{q_type}'")
        if track == "behavioral" and q_type and q_type != "behavioral":
            warnings.append(f"{path}: question {idx} behavioral track but question_type='{q_type}'")

        expected_topics = q.get("expected_topics")
        if expected_topics is not None:
            if not isinstance(expected_topics, list):
                warnings.append(f"{path}: question {idx} expected_topics should be a list")
            elif not [t for t in expected_topics if _as_str(t)]:
                warnings.append(f"{path}: question {idx} expected_topics is empty")

        evaluation_focus = q.get("evaluation_focus")
        if evaluation_focus is not None:
            if not isinstance(evaluation_focus, list):
                warnings.append(f"{path}: question {idx} evaluation_focus should be a list")
            elif not [t for t in evaluation_focus if _as_str(t)]:
                warnings.append(f"{path}: question {idx} evaluation_focus is empty")

        company_bar = q.get("company_bar")
        if company_bar is not None and not _as_str(company_bar):
            warnings.append(f"{path}: question {idx} company_bar is empty")

        if track == "behavioral":
            tag_set = {str(t).strip().lower() for t in tags if _as_str(t)}
            if "behavioral" not in tag_set:
                warnings.append(f"{path}: question {idx} is behavioral track but missing 'behavioral' tag")

        if title and track and company and difficulty:
            key = (track, company, difficulty, title.lower())
            if key in seen_titles:
                warnings.append(f"{path}: duplicate title '{title}' for track/company/difficulty")
            else:
                seen_titles.add(key)

        if prompt and track and company and difficulty:
            prompt_key = (track, company, difficulty, _normalize_text(prompt).lower())
            if prompt_key in seen_prompts:
                warnings.append(f"{path}: duplicate prompt for track/company/difficulty")
            else:
                seen_prompts.add(prompt_key)

        count += 1

    seen["titles"] = seen_titles
    seen["prompts"] = seen_prompts
    return errors, warnings, count


def main():
    parser = argparse.ArgumentParser(description="Validate question JSON files.")
    parser.add_argument(
        "--root",
        default="data/questions",
        help="Root folder containing question JSON files.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit code).",
    )
    args = parser.parse_args()

    base = Path(args.root)
    if not base.exists():
        print(f"Root not found: {base}")
        return 2

    files = sorted(base.rglob("*.json"))
    if not files:
        print(f"No JSON files found under {base}")
        return 2

    all_errors = []
    all_warnings = []
    total_questions = 0
    seen = {"titles": set(), "prompts": set()}

    for path in files:
        errors, warnings, count = validate_file(path, base, seen)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        total_questions += count

    for msg in all_errors:
        print(f"[ERROR] {msg}")
    for msg in all_warnings:
        print(f"[WARN]  {msg}")

    print(f"\nChecked {len(files)} files, {total_questions} questions.")
    print(f"Errors: {len(all_errors)}  Warnings: {len(all_warnings)}")

    if all_errors or (args.strict and all_warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
