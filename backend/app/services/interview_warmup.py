from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

WarmupState = dict[str, Any]


def _skill_state(session) -> dict:
    try:
        return session.skill_state if isinstance(session.skill_state, dict) else {}
    except Exception:
        return {}


def get_state(session) -> tuple[int, bool]:
    """
    Return (step, done) for warmup. Step starts at 0 when unsent.
    """
    state = _skill_state(session)
    warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
    try:
        step = int(warm.get("step") or 0)
    except Exception:
        step = 0
    step = max(0, min(step, 10))
    done = bool(warm.get("done"))
    return step, done


def set_state(db: Session, session, step: int, done: bool) -> None:
    """
    Persist warmup state while preserving other skill_state keys.
    """
    state = dict(_skill_state(session))
    warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
    warm = dict(warm)
    warm["step"] = int(step)
    warm["done"] = bool(done)
    state["warmup"] = warm
    session.skill_state = state
    db.add(session)
    db.commit()
    db.refresh(session)


def prompt_for_step(step: int, user_name: str | None = None, interviewer_name: str | None = None) -> str | None:
    """
    step=0 -> greeting
    step=1 -> small-talk follow-up handled by InterviewEngine
    step=2 -> behavioral warmup handled by InterviewEngine
    """
    name = (user_name or "").strip() or "there"
    if step <= 0:
        if interviewer_name:
            return f"Hi {name}! I'm {interviewer_name}, your interviewer today. How are you doing?"
        return f"Hi {name}! I'm your interviewer today. How are you doing?"
    if step == 1:
        return None
    return None


def warmup_ack(student_text: str | None = None) -> str:
    txt = (student_text or "").strip()
    if txt:
        return "Thanks for sharing. Let's get started."
    return "Great. Let's get started."


def choose_company_from_text(text: str) -> str | None:
    # Keep for future use; not used when the frontend already supplies company_style.
    t = (text or "").lower()
    if not t:
        return None
    if "amazon" in t:
        return "amazon"
    if "apple" in t:
        return "apple"
    if "google" in t:
        return "google"
    if "microsoft" in t or "ms" in t:
        return "microsoft"
    if "general" in t or "any" in t or "all" in t:
        return "general"
    return None
