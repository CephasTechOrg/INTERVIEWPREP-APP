from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.crud.session_question import list_asked_question_ids
from app.models.question import Question


def list_questions(db: Session, track: str | None, company_style: str | None, difficulty: str | None) -> list[Question]:
    q = db.query(Question)
    conditions = []
    if track:
        conditions.append(Question.track == track)
    if company_style:
        conditions.append(Question.company_style == company_style)
    if difficulty:
        conditions.append(Question.difficulty == difficulty)
    if conditions:
        q = q.filter(and_(*conditions))
    return q.order_by(Question.id.asc()).all()


def get_question(db: Session, question_id: int) -> Question | None:
    return db.query(Question).filter(Question.id == question_id).first()


def pick_next_question(db: Session, track: str, company_style: str, difficulty: str) -> Question | None:
    # Simple strategy: return first matching question. Upgrade later to random / adaptive selection.
    return (
        db.query(Question)
        .filter(
            Question.track == track,
            Question.company_style == company_style,
            Question.difficulty == difficulty,
        )
        .order_by(Question.id.asc())
        .first()
    )


def pick_next_unseen_question(
    db: Session,
    session_id: int,
    track: str,
    company_style: str,
    difficulty: str,
) -> Question | None:
    asked_ids = set(list_asked_question_ids(db, session_id))
    q = db.query(Question).filter(
        Question.track == track,
        Question.company_style == company_style,
        Question.difficulty == difficulty,
    )
    if asked_ids:
        q = q.filter(~Question.id.in_(asked_ids))
    # Postgres random ordering
    return q.order_by(func.random()).first()


def count_questions(
    db: Session,
    track: str,
    company_style: str,
    difficulty: str,
    exclude_behavioral: bool = False,
) -> int:
    q = db.query(func.count(Question.id)).filter(
        Question.track == track,
        Question.company_style == company_style,
        Question.difficulty == difficulty,
    )
    if exclude_behavioral:
        q = q.filter(~Question.tags_csv.ilike("%behavioral%"), Question.question_type != "behavioral")
    return int(q.scalar() or 0)


def count_behavioral_questions(db: Session, track: str, company_style: str, difficulty: str) -> int:
    q = db.query(func.count(Question.id)).filter(
        Question.company_style == company_style,
        Question.difficulty == difficulty,
        or_(Question.tags_csv.ilike("%behavioral%"), Question.question_type == "behavioral"),
    )
    # Allow role-specific behavioral banks (track == role) and generic behavioral (track == "behavioral").
    q = q.filter(Question.track.in_([track, "behavioral"]))
    return int(q.scalar() or 0)


def count_technical_questions(db: Session, track: str, company_style: str, difficulty: str) -> int:
    q = db.query(func.count(Question.id)).filter(
        Question.track == track,
        Question.company_style == company_style,
        Question.difficulty == difficulty,
        ~Question.tags_csv.ilike("%behavioral%"),
        Question.question_type != "behavioral",
    )
    return int(q.scalar() or 0)


DIFFICULTY_ORDER: tuple[str, ...] = ("easy", "medium", "hard")


def _difficulty_rank(value: str | None) -> int:
    diff = (value or "").strip().lower()
    try:
        return DIFFICULTY_ORDER.index(diff)
    except ValueError:
        return 0


def _choose_best_difficulty(candidates: list[str], requested_rank: int) -> str | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda d: (abs(_difficulty_rank(d) - requested_rank), _difficulty_rank(d)),
    )[0]


def preflight_question_pool(db: Session, track: str, company_style: str, difficulty: str) -> dict:
    """
    Inspect question availability and resolve a safe, effective pool for technical questions.
    This avoids mid-session "no questions found" errors by selecting a viable company/difficulty.
    """
    t = (track or "").strip().lower()
    c = (company_style or "").strip().lower()
    d = (difficulty or "").strip().lower()
    if not t or not c or not d:
        return {}

    company_counts = {}
    general_counts = {}
    for diff in DIFFICULTY_ORDER:
        company_counts[diff] = count_questions(db, t, c, diff, exclude_behavioral=True)
        general_counts[diff] = count_questions(db, t, "general", diff, exclude_behavioral=True)

    company_total = sum(company_counts.values())
    general_total = sum(general_counts.values())

    available_difficulties = [diff for diff in DIFFICULTY_ORDER if (company_counts[diff] + general_counts[diff]) > 0]

    requested_rank = _difficulty_rank(d)
    cap_rank = requested_rank

    company_within_cap = [
        diff for diff in DIFFICULTY_ORDER if company_counts[diff] > 0 and _difficulty_rank(diff) <= cap_rank
    ]
    general_within_cap = [
        diff for diff in DIFFICULTY_ORDER if general_counts[diff] > 0 and _difficulty_rank(diff) <= cap_rank
    ]
    company_any = [diff for diff in DIFFICULTY_ORDER if company_counts[diff] > 0]
    general_any = [diff for diff in DIFFICULTY_ORDER if general_counts[diff] > 0]

    effective_company = c
    effective_difficulty = d
    status = "exact"
    cap_override = None

    if company_counts.get(d, 0) > 0:
        effective_company = c
        effective_difficulty = d
        status = "exact"
    elif company_within_cap:
        effective_company = c
        effective_difficulty = _choose_best_difficulty(company_within_cap, requested_rank) or d
        status = "company_fallback"
    elif general_counts.get(d, 0) > 0:
        effective_company = "general"
        effective_difficulty = d
        status = "general_fallback"
    elif general_within_cap:
        effective_company = "general"
        effective_difficulty = _choose_best_difficulty(general_within_cap, requested_rank) or d
        status = "general_fallback"
    elif company_any:
        effective_company = c
        effective_difficulty = _choose_best_difficulty(company_any, requested_rank) or d
        status = "company_fallback_above_cap"
        cap_override = effective_difficulty
    elif general_any:
        effective_company = "general"
        effective_difficulty = _choose_best_difficulty(general_any, requested_rank) or d
        status = "general_fallback_above_cap"
        cap_override = effective_difficulty
    else:
        status = "empty"

    return {
        "requested": {"track": t, "company_style": c, "difficulty": d},
        "effective_company_style": effective_company,
        "effective_difficulty": effective_difficulty,
        "available_difficulties": available_difficulties,
        "difficulty_cap_override": cap_override,
        "status": status,
        "counts": {
            "company": {**company_counts, "total": company_total},
            "general": {**general_counts, "total": general_total},
        },
    }
