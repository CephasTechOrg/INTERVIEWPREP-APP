import contextlib
import logging
import random
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud import message as message_crud
from app.crud import question as question_crud
from app.crud import session as session_crud
from app.crud import session_question as session_question_crud
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.models.session_question import SessionQuestion
from app.models.user_question_seen import UserQuestionSeen
from app.services import interview_warmup
from app.services.llm_client import DeepSeekClient, LLMClientError
from app.services.llm_schemas import InterviewControllerOutput, UserIntentClassification, WarmupSmalltalkProfile, WarmupToneProfile
from app.services.prompt_templates import (
    interviewer_controller_system_prompt,
    interviewer_controller_user_prompt,
    interviewer_system_prompt,
    user_intent_classifier_system_prompt,
    user_intent_classifier_user_prompt,
    warmup_prompt_user_prompt,
    warmup_reply_user_prompt,
    warmup_system_prompt,
    warmup_smalltalk_system_prompt,
    warmup_smalltalk_user_prompt,
    warmup_tone_classifier_system_prompt,
    warmup_tone_classifier_user_prompt,
)

_engine_logger = logging.getLogger(__name__)


def _get_rag_context_for_interview(db: Session, session_id: int) -> str | None:
    """
    Safely get RAG context for live interview.
    Returns None if RAG is unavailable or not enough data.
    """
    try:
        from app.services.rag_service import get_rag_context_for_session
        context = get_rag_context_for_session(db, session_id)
        if context:
            _engine_logger.debug("RAG context available for session_id=%s", session_id)
        return context
    except Exception:
        return None


class InterviewEngine:
    """
    Controls interview flow and conversational quality.

    Responsibilities:
    - Pick questions (adaptive difficulty, behavioral mix).
    - Manage stages and counters (questions asked, followups used).
    - Route AI calls and apply fallbacks.
    - Enforce human-like rules: handle "move on"/"don't know", prompt for detail
      on vague/non-informative answers, keep followups short, and personalize greetings.
    """

    def __init__(self) -> None:
        self.llm = DeepSeekClient()

    _RUBRIC_KEYS: tuple[str, ...] = (
        "communication",
        "problem_solving",
        "correctness_reasoning",
        "complexity",
        "edge_cases",
    )
    _SYSTEM_DESIGN_TAGS: set[str] = {
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
    _CONCEPTUAL_TAGS: set[str] = {"fundamentals", "concepts", "oop"}

    def _clamp_int(self, value: Any, default: int, lo: int, hi: int) -> int:
        try:
            n = int(value)
        except Exception:
            n = int(default)
        return max(lo, min(hi, n))

    def _coerce_quick_rubric(self, raw: Any) -> dict:
        raw_dict = raw if isinstance(raw, dict) else {}
        return {k: self._clamp_int(raw_dict.get(k), default=5, lo=0, hi=10) for k in self._RUBRIC_KEYS}

    def _pool_state(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        pool = state.get("pool")
        return pool if isinstance(pool, dict) else {}

    def _interviewer_profile(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        raw = state.get("interviewer")
        return raw if isinstance(raw, dict) else {}

    def _interviewer_name(self, session: InterviewSession) -> str | None:
        profile = self._interviewer_profile(session)
        name = str(profile.get("name") or "").strip()
        return name or None

    def _interviewer_intro_line(self, session: InterviewSession) -> str | None:
        name = self._interviewer_name(session)
        if not name:
            return None
        return f"Hi, I'm {name}, and I'll be your interviewer today."

    def _reanchor_state(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        raw = state.get("reanchor")
        return raw if isinstance(raw, dict) else {}

    def _get_reanchor_count(self, session: InterviewSession, question_id: int | None) -> int:
        if not question_id:
            return 0
        state = self._reanchor_state(session)
        try:
            qid = int(state.get("qid") or 0)
        except Exception:
            qid = 0
        if qid != int(question_id):
            return 0
        try:
            return max(0, int(state.get("count") or 0))
        except Exception:
            return 0

    def _set_reanchor_count(self, db: Session, session: InterviewSession, question_id: int, count: int) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        state["reanchor"] = {"qid": int(question_id), "count": max(0, int(count))}
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _clarify_state(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        raw = state.get("clarify")
        return raw if isinstance(raw, dict) else {}

    def _get_clarify_attempts(self, session: InterviewSession, question_id: int | None) -> int:
        if not question_id:
            return 0
        state = self._clarify_state(session)
        try:
            qid = int(state.get("qid") or 0)
        except Exception:
            qid = 0
        if qid != int(question_id):
            return 0
        try:
            return max(0, int(state.get("attempts") or 0))
        except Exception:
            return 0

    def _get_clarify_missing(self, session: InterviewSession, question_id: int | None) -> list[str]:
        if not question_id:
            return []
        state = self._clarify_state(session)
        try:
            qid = int(state.get("qid") or 0)
        except Exception:
            qid = 0
        if qid != int(question_id):
            return []
        raw = state.get("missing")
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            nk = self._normalize_focus_key(item)
            if nk and nk not in out:
                out.append(nk)
        return out

    def _set_clarify_state(
        self,
        db: Session,
        session: InterviewSession,
        question_id: int,
        attempts: int,
        missing: list[str] | None,
    ) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        clean_missing: list[str] = []
        for item in (missing or []):
            nk = self._normalize_focus_key(item)
            if nk and nk not in clean_missing:
                clean_missing.append(nk)
        state["clarify"] = {
            "qid": int(question_id),
            "attempts": max(0, int(attempts)),
            "missing": clean_missing,
        }
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _update_clarify_tracking(
        self,
        db: Session,
        session: InterviewSession,
        question_id: int,
        critical_missing: list[str],
    ) -> tuple[int, bool]:
        prev_missing = self._get_clarify_missing(session, question_id)
        prev_attempts = self._get_clarify_attempts(session, question_id)
        if not critical_missing:
            if prev_attempts or prev_missing:
                self._set_clarify_state(db, session, question_id, 0, [])
            return 0, True

        improved = False
        if prev_missing:
            improved = len(critical_missing) < len(prev_missing)

        attempts = 0 if improved else prev_attempts + 1
        self._set_clarify_state(db, session, question_id, attempts, critical_missing)
        return attempts, improved

    def _pool_allowed_difficulties(self, session: InterviewSession) -> list[str]:
        pool = self._pool_state(session)
        raw = pool.get("available_difficulties")
        if not isinstance(raw, list):
            return []
        allowed: list[str] = []
        for item in raw:
            diff = str(item).strip().lower()
            if diff in ("easy", "medium", "hard") and diff not in allowed:
                allowed.append(diff)
        return allowed

    def _pool_cap_override(self, session: InterviewSession) -> str | None:
        pool = self._pool_state(session)
        raw = pool.get("difficulty_cap_override")
        if not raw:
            return None
        diff = str(raw).strip().lower()
        if diff in ("easy", "medium", "hard"):
            return diff
        return None

    def _effective_company_style(self, session: InterviewSession) -> str:
        return (session.company_style or "general").strip().lower() or "general"

    def _update_skill_state(
        self,
        db: Session,
        session: InterviewSession,
        quick_rubric_raw: Any,
        is_behavioral: bool = False,
    ) -> None:
        """
        Persist rolling rubric state used for adaptive difficulty + weakness targeting.

        Structure:
          {"n": int, "sum": {k:int...}, "last": {k:int...}, "streak": {"good": int, "weak": int}}
        """
        try:
            state: dict = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else None
        focus = state.get("focus") if isinstance(state.get("focus"), dict) else None
        pool = state.get("pool") if isinstance(state.get("pool"), dict) else None
        reanchor = state.get("reanchor") if isinstance(state.get("reanchor"), dict) else None
        clarify = state.get("clarify") if isinstance(state.get("clarify"), dict) else None
        interviewer = state.get("interviewer") if isinstance(state.get("interviewer"), dict) else None
        plan = state.get("plan") if isinstance(state.get("plan"), dict) else None
        streak = state.get("streak") if isinstance(state.get("streak"), dict) else {}

        n_prev = self._clamp_int(state.get("n"), default=0, lo=0, hi=10_000)
        sum_prev = state.get("sum") if isinstance(state.get("sum"), dict) else {}
        ema_prev = state.get("ema") if isinstance(state.get("ema"), dict) else {}

        last = self._coerce_quick_rubric(quick_rubric_raw)
        sums: dict[str, int] = {}
        for k in self._RUBRIC_KEYS:
            sums[k] = self._clamp_int(sum_prev.get(k), default=0, lo=0, hi=1_000_000) + int(last[k])

        alpha = 0.35
        ema: dict[str, float] = {}
        for k in self._RUBRIC_KEYS:
            try:
                prev_val = float(ema_prev.get(k))
            except Exception:
                prev_val = float(last[k])
            ema[k] = (alpha * float(last[k])) + ((1.0 - alpha) * prev_val)

        good_prev = self._clamp_int(streak.get("good"), default=0, lo=0, hi=10_000)
        weak_prev = self._clamp_int(streak.get("weak"), default=0, lo=0, hi=10_000)
        if is_behavioral:
            good_prev = 0
            weak_prev = 0
        else:
            vals = [int(last.get(k)) for k in self._RUBRIC_KEYS if isinstance(last.get(k), int)]
            last_overall = (sum(vals) / len(vals)) if vals else 0.0
            strong = last_overall >= 8.0
            weak = last_overall <= 4.0
            if strong:
                good_prev += 1
                weak_prev = 0
            elif weak:
                weak_prev += 1
                good_prev = 0
            else:
                good_prev = 0
                weak_prev = 0

        new_state: dict[str, Any] = {
            "n": n_prev + 1,
            "sum": sums,
            "last": last,
            "ema": ema,
            "streak": {"good": good_prev, "weak": weak_prev},
        }
        if warm:
            new_state["warmup"] = warm
        if focus:
            new_state["focus"] = focus
        if pool:
            new_state["pool"] = pool
        if reanchor:
            new_state["reanchor"] = reanchor
        if clarify:
            new_state["clarify"] = clarify
        if interviewer:
            new_state["interviewer"] = interviewer
        if plan:
            new_state["plan"] = plan
        session.skill_state = new_state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _difficulty_rank(self, difficulty: str | None) -> int:
        d = (difficulty or "").strip().lower()
        if d == "hard":
            return 2
        if d == "medium":
            return 1
        return 0

    def _rank_to_difficulty(self, rank: int) -> str:
        if rank >= 2:
            return "hard"
        if rank == 1:
            return "medium"
        return "easy"

    def _adaptive_difficulty_try_order(self, session: InterviewSession) -> list[str]:
        """
        Use only the user's selected difficulty (no cross-difficulty fallback).
        """
        diff = (getattr(session, "difficulty", None) or "easy").strip().lower()
        if diff not in ("easy", "medium", "hard"):
            diff = "easy"
        return [diff]

    def _skill_last_overall(self, session: InterviewSession) -> float | None:
        state = session.skill_state if isinstance(getattr(session, "skill_state", None), dict) else None
        if not state:
            return None
        last = state.get("last")
        if not isinstance(last, dict):
            return None

        vals: list[int] = []
        for k in self._RUBRIC_KEYS:
            with contextlib.suppress(Exception):
                vals.append(int(last.get(k)))
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _skill_streaks(self, session: InterviewSession) -> tuple[int, int]:
        state = session.skill_state if isinstance(getattr(session, "skill_state", None), dict) else None
        if not state:
            return 0, 0
        streak = state.get("streak")
        if not isinstance(streak, dict):
            return 0, 0
        good = self._clamp_int(streak.get("good"), default=0, lo=0, hi=10_000)
        weak = self._clamp_int(streak.get("weak"), default=0, lo=0, hi=10_000)
        return good, weak

    def _reset_streaks(self, session: InterviewSession) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        streak = state.get("streak")
        if not isinstance(streak, dict):
            return
        state = dict(state)
        streak = dict(streak)
        streak["good"] = 0
        streak["weak"] = 0
        state["streak"] = streak
        session.skill_state = state

    def _weakest_dimension(self, session: InterviewSession) -> str | None:
        state = session.skill_state if isinstance(getattr(session, "skill_state", None), dict) else None
        if not state:
            return None

        ema = state.get("ema") if isinstance(state.get("ema"), dict) else None
        if ema:
            weakest: str | None = None
            weakest_avg: float | None = None
            for k in self._RUBRIC_KEYS:
                try:
                    avg = float(ema.get(k))
                except Exception:
                    continue
                if weakest_avg is None or avg < weakest_avg:
                    weakest_avg = avg
                    weakest = k
            if weakest:
                return weakest

        try:
            n = int(state.get("n") or 0)
        except Exception:
            n = 0
        sums = state.get("sum")
        if n <= 0 or not isinstance(sums, dict):
            return None

        weakest: str | None = None
        weakest_avg: float | None = None
        for k in self._RUBRIC_KEYS:
            try:
                avg = float(int(sums.get(k) or 0)) / float(n)
            except Exception:
                continue
            if weakest_avg is None or avg < weakest_avg:
                weakest_avg = avg
                weakest = k
        return weakest

    def _weakness_keywords(self, dimension: str | None) -> list[str]:
        dim = (dimension or "").strip().lower()
        if dim == "edge_cases":
            return ["edge case", "corner case", "boundary", "empty", "null", "off-by-one", "constraints"]
        if dim == "complexity":
            return ["time complexity", "space complexity", "big-o", "complexity", "optimize", "runtime", "amortized"]
        if dim == "correctness_reasoning":
            return ["prove", "correct", "invariant", "why", "reason", "ensure", "guarantee"]
        if dim == "problem_solving":
            return ["approach", "algorithm", "design", "strategy", "trade-off", "plan"]
        if dim == "communication":
            return ["explain", "walk through", "clarify", "describe", "communicate"]
        return []

    def _weakness_score(self, q: Question, keywords: list[str]) -> int:
        if not keywords:
            return 0
        followups = getattr(q, "followups", None)
        followup_text = " ".join([str(x) for x in followups]) if isinstance(followups, list) else ""
        hay = f"{q.title}\n{q.prompt}\n{followup_text}\n{q.tags_csv}".lower()
        score = 0
        for kw in keywords:
            if kw and kw in hay:
                score += 1
        return score

    def _maybe_bump_difficulty_current(self, db: Session, session: InterviewSession) -> None:
        """
        Difficulty is locked to the user's selected value for the entire session.
        """
        selected = (getattr(session, "difficulty", None) or "easy").strip().lower()
        if selected not in ("easy", "medium", "hard"):
            selected = "easy"
        if getattr(session, "difficulty_current", None) != selected:
            session.difficulty_current = selected
            db.add(session)
            db.commit()
            db.refresh(session)
        return

    def _is_behavioral(self, q: Question) -> bool:
        try:
            if str(getattr(q, "question_type", "")).strip().lower() == "behavioral":
                return True
            return "behavioral" in set(q.tags())
        except Exception:
            return False

    def _question_type(self, q: Question) -> str:
        """
        Normalize question type for selection logic.
        Priority: explicit question_type (if set) else tags/track inference.
        """
        raw = getattr(q, "question_type", None)
        qt = str(raw).strip().lower() if raw else ""
        if qt and qt != "coding":
            return qt

        try:
            tags = {t.strip().lower() for t in (q.tags() or []) if str(t).strip()}
        except Exception:
            tags = set()

        if self._is_behavioral(q) or "behavioral" in tags or (q.track or "") == "behavioral":
            return "behavioral"
        if tags & self._SYSTEM_DESIGN_TAGS:
            return "system_design"
        if tags & self._CONCEPTUAL_TAGS:
            return "conceptual"
        return "coding"

    def _matches_desired_type(self, q: Question, desired_type: str | None) -> bool:
        if not desired_type:
            return True
        target = (desired_type or "").strip().lower()
        if not target:
            return True
        qt = self._question_type(q)
        if target == "coding":
            return qt in ("coding", "conceptual")
        return qt == target

    def _company_name(self, company_style: str) -> str:
        if not company_style or company_style == "general":
            return "this company"
        return company_style[:1].upper() + company_style[1:]

    def _effective_difficulty(self, session: InterviewSession) -> str:
        selected = (getattr(session, "difficulty", None) or "easy").strip().lower()
        current = (getattr(session, "difficulty_current", None) or "").strip().lower()
        if selected in ("easy", "medium", "hard"):
            return selected
        if current in ("easy", "medium", "hard"):
            return current
        return "easy"

    def _render_text(self, session: InterviewSession, text: str) -> str:
        company = self._company_name(session.company_style)
        return (text or "").replace("{company}", company).replace("X company", company).replace("X Company", company)

    def _render_question(self, session: InterviewSession, q: Question) -> tuple[str, str]:
        return self._render_text(session, q.title), self._render_text(session, q.prompt)

    def _user_name_safe(self, name: str | None) -> str:
        if not name:
            return ""
        return name.strip()

    def _is_clarification_request(self, text: str) -> bool:
        """Check if user is asking for question clarification/repetition."""
        t = (text or "").strip().lower()
        if not t:
            return False
        # Clarification keywords
        clarify_keywords = [
            "repeat", "again", "clarify", "explain", "rephrase", "restate",
            "what was", "what is", "can you repeat", "say that again",
            "didn't catch", "didnt catch", "missed that", "understand the question",
            "what's the question", "whats the question", "confus", "unclear",
            "elaborate", "more detail", "tell me more about", "what do you mean"
        ]
        return any(k in t for k in clarify_keywords)

    def _is_move_on(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        # Only match explicit move-on requests
        keywords = ["move on", "next question", "skip", "pass", "go next", "next please", "next pls"]
        # Ensure these aren't part of a longer sentence asking for help
        if self._is_clarification_request(text):
            return False
        return any(k in t for k in keywords)

    def _is_dont_know(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = ["don't know", "dont know", "do not know", "no idea", "i dunno"]
        # Allow "not sure" and "unsure" only if they're not part of a longer reasoning
        tokens_count = len(self._clean_tokens(text))
        if tokens_count > 10:  # If it's a longer response, they're probably thinking through it
            return False
        if "not sure" in t or "unsure" in t:
            return tokens_count <= 5  # Only flag if very short
        return any(k in t for k in keywords)

    def _is_non_informative(self, text: str) -> bool:
        """Check if response is too short to be meaningful."""
        tokens = self._clean_tokens(text)
        if not tokens:
            return True
        # Single word responses
        if len(tokens) == 1:
            return True
        # Very short non-substantive responses
        short = {
            "ok", "okay", "k", "kk", "sure", "yes", "yeah", "yep", "yup",
            "alright", "cool", "fine", "thanks", "thank", "no", "nah"
        }
        # Only flag if 2 tokens or less AND all are filler words
        if len(tokens) <= 2 and all(t in short for t in tokens):
            return True
        return False

    def _is_vague(self, text: str) -> bool:
        """Check if response is too vague/short to be useful."""
        tokens = self._clean_tokens(text)
        if not tokens:
            return True
        # Very short responses (less than 5 words) are vague
        # But allow them if they contain technical terms or questions
        if len(tokens) < 5:
            # Check for clarification requests
            if self._is_clarification_request(text):
                return False
            # Check for technical keywords (user might be answering concisely)
            technical_patterns = ["array", "hash", "map", "list", "tree", "graph", "stack", "queue",
                                 "o(", "time", "space", "complexity", "algorithm", "function",
                                 "class", "object", "pointer", "node", "edge", "vertex"]
            t_lower = text.lower()
            if any(pattern in t_lower for pattern in technical_patterns):
                return False  # Technical response, even if short
            return True
        return False

    def _normalize_text(self, text: str | None) -> str:
        return " ".join((text or "").lower().split())

    def _clean_tokens(self, text: str | None) -> list[str]:
        raw = (text or "").lower().replace("```", " ")
        tokens = [re.sub(r"[^a-z0-9']+", "", w) for w in raw.split()]
        return [t for t in tokens if t]

    def _keyword_tokens(self, text: str | None) -> set[str]:
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "for",
            "in",
            "on",
            "with",
            "without",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "it",
            "this",
            "that",
            "as",
            "by",
            "from",
            "at",
            "you",
            "your",
            "i",
            "we",
            "they",
            "he",
            "she",
            "them",
            "our",
            "their",
            "can",
            "could",
            "should",
            "would",
            "about",
            "into",
            "over",
            "under",
            "than",
            "then",
            "if",
            "else",
            "when",
            "while",
        }
        tokens = self._clean_tokens(text)
        return {t for t in tokens if len(t) > 2 and t not in stop}

    def _overlap_ratio(self, base: set[str], text: str | None) -> float:
        if not base:
            return 0.0
        other = self._keyword_tokens(text)
        if not other:
            return 0.0
        return len(base & other) / float(len(base))

    def _is_off_topic(self, q: Question, text: str | None, signals: dict[str, bool]) -> bool:
        if self._is_behavioral(q):
            return False
        if signals.get("has_code") or signals.get("mentions_approach") or signals.get("mentions_correctness"):
            return False
        q_text = f"{q.title}\n{q.prompt}\n{q.tags_csv or ''}"
        base = self._keyword_tokens(q_text)
        if len(base) < 6:
            return False
        ratio = self._overlap_ratio(base, text)
        return ratio < 0.05

    def _is_thin_response(
        self,
        text: str | None,
        signals: dict[str, bool],
        is_behavioral: bool,
        behavioral_missing: list[str],
    ) -> bool:
        """Check if response lacks substance - but allow clarifications."""
        # Don't flag clarification requests as thin
        if self._is_clarification_request(text or ""):
            return False
        
        tokens = self._clean_tokens(text)
        if not tokens:
            return True
        
        # Short responses with technical content are acceptable
        if len(tokens) >= 3:
            t_lower = (text or "").lower()
            technical_patterns = ["array", "hash", "map", "dict", "list", "tree", "graph",
                                 "o(n)", "o(1)", "o(log", "time", "space", "algorithm"]
            if any(pattern in t_lower for pattern in technical_patterns):
                return False  # Has technical content, not thin
        
        if is_behavioral:
            return len(behavioral_missing) >= 2
        if signals.get("has_code") and not signals.get("mentions_approach"):
            return True
        content_signals = [
            "mentions_approach",
            "mentions_constraints",
            "mentions_correctness",
            "mentions_complexity",
            "mentions_edge_cases",
            "mentions_tradeoffs",
        ]
        return not any(signals.get(k) for k in content_signals)

    def _response_quality(
        self,
        text: str | None,
        signals: dict[str, bool],
        is_behavioral: bool,
        behavioral_missing: list[str],
    ) -> str:
        """Assess response quality - but don't penalize clarifications."""
        # Clarification requests are neutral quality
        if self._is_clarification_request(text or ""):
            return "ok"
        
        tokens = self._clean_tokens(text)
        if len(tokens) < 8:
            return "weak"
        if is_behavioral:
            if len(behavioral_missing) >= 2:
                return "weak"
            if not behavioral_missing and len(tokens) >= 25:
                return "strong"
            return "ok"
        if signals.get("has_code") and not signals.get("mentions_approach"):
            return "weak"
        if not signals.get("mentions_approach"):
            return "weak"
        coverage = 0
        for key in (
            "mentions_constraints",
            "mentions_correctness",
            "mentions_complexity",
            "mentions_edge_cases",
            "mentions_tradeoffs",
        ):
            if signals.get(key):
                coverage += 1
        if coverage >= 3:
            return "strong"
        if coverage >= 1 or len(tokens) >= 20:
            return "ok"
        return "weak"

    def _sanitize_ai_text(self, text: str | None) -> str:
        if not text:
            return ""
        replacements = {
            "\u2019": "'",
            "\u2018": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2014": "--",
            "\u2013": "-",
            "\u2026": "...",
            "\u2022": "-",
            "\u00b7": "-",
            "\u00a0": " ",
        }
        cleaned = "".join(replacements.get(ch, ch) for ch in text)
        cleaned = cleaned.replace("```", "")
        cleaned = "".join(ch if ord(ch) < 128 else "" for ch in cleaned)

        title = ""
        prompt = ""
        lines: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.replace("**", "").replace("__", "").replace("`", "")
            line = re.sub(r"^[-*]\s+", "", line)
            line = re.sub(r"^\d+\.\s+", "", line)

            lower = line.lower()
            if lower.startswith("title:"):
                title = line.split(":", 1)[1].strip()
                continue
            if lower.startswith("prompt:"):
                prompt = line.split(":", 1)[1].strip()
                continue

            lines.append(line)

        if title or prompt:
            question = " ".join([part for part in [title, prompt] if part])
            if lines:
                lines.append(question)
                return "\n\n".join(lines).strip()
            return question.strip()

        return "\n\n".join(lines).strip()

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(k in text for k in keywords)

    def _has_code_block(self, text: str | None) -> bool:
        raw = text or ""
        if "```" in raw:
            return True
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "function ", "public ", "private ")):
                return True
            if stripped.startswith(("for ", "while ", "if ", "else ", "elif ")):
                return True
            if stripped.endswith(";") and ("=" in stripped or "return" in stripped):
                return True
        return False

    def _mentions_complexity(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return "o(" in t or self._contains_any(
            t,
            ["big o", "time complexity", "space complexity", "complexity", "runtime", "amortized"],
        )

    def _mentions_edge_cases(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["edge case", "corner case", "boundary", "empty", "null", "none", "zero", "negative", "overflow"],
        )

    def _mentions_constraints(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["constraint", "constraints", "limit", "bounds", "input size", "range", "assumption"],
        )

    def _mentions_approach(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            [
                "approach",
                "algorithm",
                "strategy",
                "plan",
                "idea",
                "i would",
                "we can",
                "i will",
                "i can",
                "use a",
                "use an",
            ],
        )

    def _mentions_tradeoffs(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["trade-off", "tradeoff", "versus", " vs ", "pros", "cons", "alternative", "option"],
        )

    def _mentions_correctness(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["correct", "proof", "invariant", "why it works", "guarantee"],
        )

    def _behavioral_missing_parts(self, text: str | None) -> list[str]:
        t = self._normalize_text(text)
        if "star" in t:
            return []
        parts = {
            "situation": ["situation", "context", "background"],
            "task": ["task", "goal", "responsibility"],
            "action": ["action", "implemented", "built", "led", "drove", "executed", "delivered"],
            "result": ["result", "impact", "outcome", "metric", "learned", "improved", "increased", "decreased"],
        }
        missing = []
        for name, keywords in parts.items():
            if not self._contains_any(t, keywords):
                missing.append(name)
        return missing

    def _candidate_signals(self, text: str | None) -> dict[str, bool]:
        return {
            "has_code": self._has_code_block(text),
            "mentions_complexity": self._mentions_complexity(text),
            "mentions_edge_cases": self._mentions_edge_cases(text),
            "mentions_constraints": self._mentions_constraints(text),
            "mentions_approach": self._mentions_approach(text),
            "mentions_tradeoffs": self._mentions_tradeoffs(text),
            "mentions_correctness": self._mentions_correctness(text),
        }

    def _missing_focus_keys(self, q: Question, signals: dict[str, bool], behavioral_missing: list[str]) -> list[str]:
        if self._is_behavioral(q):
            missing = []
            if behavioral_missing:
                missing.append("star")
            if "result" in behavioral_missing:
                missing.append("impact")
            return missing

        missing = []
        if not signals.get("mentions_approach"):
            missing.append("approach")
        if not signals.get("mentions_constraints"):
            missing.append("constraints")
        if not signals.get("mentions_correctness"):
            missing.append("correctness")
        if not signals.get("mentions_complexity"):
            missing.append("complexity")
        if not signals.get("mentions_edge_cases"):
            missing.append("edge_cases")
        if not signals.get("mentions_tradeoffs"):
            missing.append("tradeoffs")
        return missing

    def _question_focus_keys(self, q: Question) -> list[str]:
        meta = getattr(q, "meta", None)
        if not isinstance(meta, dict):
            return []
        raw = meta.get("evaluation_focus")
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            key = self._normalize_focus_key(str(item))
            if key and key not in out:
                out.append(key)
        return out

    def _prioritize_missing_focus(
        self,
        missing: list[str],
        session: InterviewSession,
        prefer: list[str] | None = None,
    ) -> list[str]:
        if not missing:
            return []
        if prefer:
            ordered = [p for p in prefer if p in missing]
            if ordered:
                return ordered + [m for m in missing if m not in ordered]
        focus_key = self._dimension_to_missing_key(self._focus_dimension(session))
        if focus_key and focus_key in missing:
            return [focus_key] + [m for m in missing if m != focus_key]
        weakest = self._weakest_dimension(session)
        prefer = None
        if weakest == "edge_cases":
            prefer = "edge_cases"
        elif weakest == "complexity":
            prefer = "complexity"
        elif weakest == "correctness_reasoning":
            prefer = "correctness"
        elif weakest == "problem_solving" or weakest == "communication":
            prefer = "approach"
        if prefer and prefer in missing:
            return [prefer] + [m for m in missing if m != prefer]
        return missing

    def _missing_focus_summary(self, missing: list[str], behavioral_missing: list[str]) -> str:
        if not missing:
            return ""
        if "star" in missing and behavioral_missing:
            parts = ", ".join(behavioral_missing)
            return f"STAR parts missing: {parts}"
        return ", ".join(missing)

    def _missing_focus_tiers(
        self,
        missing: list[str],
        is_behavioral: bool,
        behavioral_missing: list[str],
    ) -> tuple[list[str], list[str]]:
        if not missing:
            return ([], [])
        if is_behavioral:
            critical = [k for k in missing if k == "star"] if len(behavioral_missing) >= 2 else []
            optional = [k for k in missing if k not in critical]
            return (critical, optional)
        critical = [k for k in missing if k in ("approach", "correctness")]
        optional = [k for k in missing if k not in critical]
        return (critical, optional)

    def _missing_from_coverage(self, coverage: dict, is_behavioral: bool) -> list[str]:
        if not coverage or not isinstance(coverage, dict):
            return []
        if is_behavioral:
            keys = ["star", "impact"]
        else:
            keys = ["approach", "constraints", "correctness", "complexity", "edge_cases", "tradeoffs"]
        missing: list[str] = []
        for key in keys:
            if coverage.get(key) is False:
                missing.append(key)
        return missing

    def _normalize_focus_key(self, key: str | None) -> str | None:
        k = (key or "").strip().lower()
        if not k:
            return None
        mapping = {
            "edge case": "edge_cases",
            "edge cases": "edge_cases",
            "edge": "edge_cases",
            "edges": "edge_cases",
            "complexity": "complexity",
            "runtime": "complexity",
            "big o": "complexity",
            "correctness": "correctness",
            "proof": "correctness",
            "invariant": "correctness",
            "trade-off": "tradeoffs",
            "tradeoff": "tradeoffs",
            "tradeoffs": "tradeoffs",
            "approach": "approach",
            "plan": "approach",
            "constraints": "constraints",
            "assumptions": "constraints",
            "star": "star",
            "impact": "impact",
            "outcome": "impact",
        }
        if k in mapping:
            return mapping[k]
        if k in {"approach", "constraints", "correctness", "complexity", "edge_cases", "tradeoffs", "star", "impact"}:
            return k
        return None

    def _soft_nudge_prompt(
        self,
        is_behavioral: bool,
        missing_keys: list[str],
        behavioral_missing: list[str],
    ) -> str:
        if is_behavioral:
            if behavioral_missing:
                parts = ", ".join(behavioral_missing[:2])
                return "I want to make sure I understood. Can you briefly add the " f"{parts} and the outcome?"
            return "Can you frame that with STAR (Situation, Task, Action, Result) and the outcome?"

        focus_bits = []
        if "approach" in missing_keys:
            focus_bits.append("your approach")
        if "constraints" in missing_keys:
            focus_bits.append("constraints")
        if "correctness" in missing_keys:
            focus_bits.append("why it works")
        if "complexity" in missing_keys:
            focus_bits.append("complexity")
        if "edge_cases" in missing_keys:
            focus_bits.append("edge cases")
        if "tradeoffs" in missing_keys:
            focus_bits.append("trade-offs")

        if focus_bits:
            focus_line = ", ".join(focus_bits[:3])
            return f"I might be missing your core idea. Can you restate it and cover {focus_line}?"

        return "I might be missing your core idea. Can you restate the problem and outline your plan and constraints?"

    def _missing_focus_question(self, key: str, behavioral_missing: list[str]) -> str | None:
        if key == "star":
            if behavioral_missing:
                return "Could you structure that using STAR and include the outcome or impact?"
            return "Could you structure that using STAR (Situation, Task, Action, Result)?"
        if key == "impact":
            return "What was the outcome or impact of your actions?"
        if key == "approach":
            return "Start with a brief plan and the key steps. What is your high-level approach?"
        if key == "constraints":
            return "What constraints or assumptions are you making?"
        if key == "correctness":
            return "Why is your approach correct? Any invariant you rely on?"
        if key == "complexity":
            return "What is the time and space complexity of your solution?"
        if key == "edge_cases":
            return "What edge cases would you test or handle?"
        if key == "tradeoffs":
            return "What trade-offs did you consider, and why did you choose this approach?"
        return None

    def _phase_followup(
        self,
        q: Question,
        signals: dict[str, bool],
        session: InterviewSession,
        followups_used: int,
    ) -> str | None:
        if self._is_behavioral(q):
            return None

        if followups_used <= 0:
            focus_dims = self._focus_dimensions(session)
            if "complexity" in focus_dims and "edge_cases" in focus_dims:
                return "What is the time and space complexity, and what edge cases would you test?"
            if not signals.get("mentions_approach"):
                return "Start with a brief plan and the key steps. What is your high-level approach?"
            if not signals.get("mentions_constraints"):
                return "What constraints or assumptions are you making?"

        if not signals.get("mentions_complexity"):
            return "What is the time and space complexity of your solution? Any optimizations?"
        if not signals.get("mentions_tradeoffs"):
            return "What trade-offs did you consider, and why did you choose this approach?"

        if not signals.get("mentions_edge_cases") and not signals.get("mentions_correctness"):
            return "How would you validate correctness and edge cases for this solution?"
        if not signals.get("mentions_edge_cases"):
            return "What edge cases would you test or handle?"
        if not signals.get("mentions_correctness"):
            return "Why is your approach correct? Any invariant you rely on?"

        return None

    def _signal_summary(self, signals: dict[str, bool], missing: list[str], behavioral_missing: list[str]) -> str:
        if not signals and not missing:
            return ""
        bits = [
            f"has_code={signals.get('has_code', False)}",
            f"mentions_approach={signals.get('mentions_approach', False)}",
            f"mentions_constraints={signals.get('mentions_constraints', False)}",
            f"mentions_correctness={signals.get('mentions_correctness', False)}",
            f"mentions_complexity={signals.get('mentions_complexity', False)}",
            f"mentions_edge_cases={signals.get('mentions_edge_cases', False)}",
            f"mentions_tradeoffs={signals.get('mentions_tradeoffs', False)}",
        ]
        summary = "; ".join(bits)
        missing_summary = self._missing_focus_summary(missing, behavioral_missing)
        if missing_summary:
            summary = f"{summary}; missing={missing_summary}"
        return summary

    def _skill_summary(self, session: InterviewSession) -> str:
        last_overall = self._skill_last_overall(session)
        weakest = self._weakest_dimension(session)
        focus_dim = self._focus_dimension(session)
        focus_tags = self._focus_tags(session)

        parts: list[str] = []
        if last_overall is not None:
            parts.append(f"last_overall={last_overall:.1f}/10")
        if weakest:
            parts.append(f"weakest={weakest}")
        if focus_dim:
            parts.append(f"focus={focus_dim}")
        if focus_tags:
            short = ", ".join(sorted(focus_tags)[:3])
            parts.append(f"focus_tags={short}")
        return "; ".join(parts)

    def _extract_focus(self, text: str | None) -> dict[str, Any]:
        raw = (text or "").strip()
        t = self._normalize_text(raw)
        if not t:
            return {"raw": raw, "dimensions": [], "tags": []}

        dim_map = {
            "communication": ["communicat", "clarity", "explain", "articulate", "confidence", "presentation"],
            "problem_solving": ["problem", "approach", "algorithm", "strategy", "design", "plan", "solution"],
            "correctness_reasoning": ["correct", "proof", "reasoning", "invariant", "why it works"],
            "complexity": ["complexity", "optimize", "performance", "runtime", "big o", "space"],
            "edge_cases": ["edge case", "corner", "boundary", "test", "constraints"],
        }
        tag_map = {
            "arrays": ["array", "arrays"],
            "hashmap": ["hashmap", "hash map", "dictionary"],
            "linked-list": ["linked list", "linked-list"],
            "graphs": ["graph", "graphs"],
            "trees": ["tree", "trees", "binary tree", "bst"],
            "dp": ["dynamic programming", "dp"],
            "greedy": ["greedy"],
            "stack": ["stack"],
            "queue": ["queue"],
            "heap": ["heap", "priority queue"],
            "two-pointers": ["two pointers", "two-pointer"],
            "binary search": ["binary search", "bisect"],
            "sliding window": ["sliding window"],
            "system design": ["system design", "scalable", "architecture", "distributed"],
            "behavioral": ["behavioral", "story", "star", "leadership", "teamwork", "conflict"],
        }

        dims = [dim for dim, kws in dim_map.items() if self._contains_any(t, kws)]
        tags = [tag for tag, kws in tag_map.items() if self._contains_any(t, kws)]
        return {"raw": raw, "dimensions": dims, "tags": tags}

    def _store_focus(self, db: Session, session: InterviewSession, focus: dict[str, Any]) -> None:
        try:
            state: dict = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else None

        state["focus"] = {
            "raw": str(focus.get("raw") or "").strip(),
            "dimensions": list(focus.get("dimensions") or []),
            "tags": list(focus.get("tags") or []),
        }
        if warm:
            state["warmup"] = warm
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _focus_dimension(self, session: InterviewSession) -> str | None:
        dims = self._focus_dimensions(session)
        return dims[0] if dims else None

    def _focus_dimensions(self, session: InterviewSession) -> list[str]:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            return []
        focus = state.get("focus") if isinstance(state.get("focus"), dict) else None
        if not focus:
            return []
        dims = focus.get("dimensions")
        if not isinstance(dims, list):
            return []
        out: list[str] = []
        for dim in dims:
            d = str(dim).strip().lower()
            if d in self._RUBRIC_KEYS and d not in out:
                out.append(d)
        return out

    def _focus_tags(self, session: InterviewSession) -> set[str]:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            return set()
        focus = state.get("focus") if isinstance(state.get("focus"), dict) else None
        if not focus:
            return set()
        tags = focus.get("tags")
        if not isinstance(tags, list):
            return set()
        return {str(t).strip().lower() for t in tags if str(t).strip()}

    def _focus_summary(self, focus: dict[str, Any]) -> str:
        dims = focus.get("dimensions") or []
        tags = focus.get("tags") or []
        parts = []
        if dims:
            parts.append("dimensions=" + ", ".join(dims))
        if tags:
            parts.append("tags=" + ", ".join(tags))
        return "; ".join(parts)

    def _is_ready_to_start(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        if not t:
            return False
        keywords = ["ready", "let's start", "lets start", "start interview", "go ahead", "begin", "start now"]
        return self._contains_any(t, keywords)

    def _dimension_to_missing_key(self, dimension: str | None) -> str | None:
        if dimension == "edge_cases":
            return "edge_cases"
        if dimension == "complexity":
            return "complexity"
        if dimension == "correctness_reasoning":
            return "correctness"
        if dimension == "problem_solving":
            return "approach"
        if dimension == "communication":
            return "approach"
        return None

    def _transition_preface(self, session: InterviewSession, reason: str | None = None) -> str:
        focus_dims = self._focus_dimensions(session)
        focus_line = ""
        if "complexity" in focus_dims and "edge_cases" in focus_dims:
            focus_line = "I'll keep an eye on complexity and edge cases."
        elif focus_dims:
            focus_line = f"I'll focus on {focus_dims[0].replace('_', ' ')}."

        if reason == "move_on":
            lead = "Understood."
        elif reason == "dont_know":
            lead = "No worries."
        else:
            lead = "Thanks."

        bridges = ["Let's continue.", "Let's keep going.", "Let's move on."]
        idx = int(session.questions_asked_count or 0) % len(bridges)
        bridge = bridges[idx]
        if focus_line:
            return f"{lead} {focus_line} {bridge}"
        return f"{lead} {bridge}"

    def _clean_next_question_reply(self, text: str | None, user_name: str | None = None) -> str:
        if not text:
            return ""
        cleaned = text.strip()

        name = (user_name or "").strip()
        if name:
            cleaned = re.sub(
                rf"^(?:hi|hello|hey)(?:\s+there)?\s+{re.escape(name)}[\s,!.:-]*",
                "",
                cleaned,
                flags=re.I,
            )
        cleaned = re.sub(r"^(?:hi|hello|hey)(?:\s+there)?[\s,!.:-]*", "", cleaned, flags=re.I)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
        if not paragraphs:
            return cleaned

        transition_re = re.compile(r"\b(move to the next question|next question)\b", re.I)
        greeting_re = re.compile(r"^(hi|hello|hey)\b", re.I)
        seen: set[str] = set()
        cleaned_paragraphs: list[str] = []
        for para in paragraphs:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            kept: list[str] = []
            for sent in sentences:
                s = sent.strip()
                if not s:
                    continue
                if "?" not in s and greeting_re.search(s):
                    continue
                if "?" not in s and transition_re.search(s):
                    continue
                norm = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
                if norm and norm in seen:
                    continue
                if norm:
                    seen.add(norm)
                kept.append(s)
            if kept:
                cleaned_paragraphs.append(" ".join(kept))

        if not cleaned_paragraphs:
            return cleaned
        cleaned = "\n\n".join(cleaned_paragraphs).strip()
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()

    def _warmup_focus_line(self, focus: dict[str, Any]) -> str:
        dims = focus.get("dimensions") or []
        if "complexity" in dims and "edge_cases" in dims:
            return "I'll keep an eye on complexity and edge cases."
        if dims:
            return f"I'll focus on {dims[0].replace('_', ' ')}."
        return ""

    def _warmup_behavioral_question_id(self, session: InterviewSession) -> int | None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        raw = warm.get("behavioral_question_id")
        try:
            return int(raw) if raw is not None else None
        except Exception:
            return None

    def _set_warmup_behavioral_question_id(self, db: Session, session: InterviewSession, question_id: int) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        warm = dict(warm)
        warm["behavioral_question_id"] = int(question_id)
        state["warmup"] = warm
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _combine_question_text(self, title: str | None, prompt: str | None) -> str:
        t = (title or "").strip()
        p = (prompt or "").strip()
        if t and p:
            t_norm = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
            p_norm = re.sub(r"[^a-z0-9]+", " ", p.lower()).strip()
            if t_norm and p_norm:
                if t_norm in p_norm:
                    return p
                if p_norm in t_norm:
                    return t
            if t.endswith(("?", ".", "!", ":")):
                return f"{t} {p}"
            return f"{t}. {p}"
        return t or p

    def _seen_question_subquery(self, session: InterviewSession):
        return select(UserQuestionSeen.question_id).where(UserQuestionSeen.user_id == session.user_id)

    def _increment_questions_asked(self, db: Session, session: InterviewSession) -> None:
        session.questions_asked_count = int(session.questions_asked_count or 0) + 1
        db.add(session)
        db.commit()
        db.refresh(session)

    def _increment_followups_used(self, db: Session, session: InterviewSession) -> None:
        session.followups_used = int(session.followups_used or 0) + 1
        db.add(session)
        db.commit()
        db.refresh(session)

    def _max_questions_reached(self, session: InterviewSession) -> bool:
        max_q = int(session.max_questions or 0)
        if max_q <= 0:
            return False
        return int(session.questions_asked_count or 0) >= max_q

    def _max_followups_reached(self, session: InterviewSession) -> bool:
        max_f = int(session.max_followups_per_question or 0)
        if max_f <= 0:
            return False
        return int(session.followups_used or 0) >= max_f

    def _reset_for_new_question(self, db: Session, session: InterviewSession, question_id: int) -> None:
        session.current_question_id = int(question_id)
        session.followups_used = 0
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        state.pop("reanchor", None)
        state.pop("clarify", None)
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _last_interviewer_message(self, db: Session, session_id: int) -> str | None:
        msgs = message_crud.list_messages(db, session_id, limit=200)
        for m in reversed(msgs):
            if m.role == "interviewer":
                return m.content
        return None

    def _offline_intro(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        name = self._user_name_safe(user_name)
        greeting = f"Hi {name}!" if name else "Hi!"
        question_text = self._combine_question_text(q.title, q.prompt)
        if self._is_behavioral(q):
            body = f"{question_text} Please answer using STAR (Situation, Task, Action, Result)."
        else:
            body = (
                f"{question_text} Start by restating the problem and clarifying constraints, "
                "then outline your approach and complexity."
            )
        parts = []
        if preface:
            parts.append(preface.strip())
        parts.append(f"{greeting} {body}".strip())
        return "\n\n".join([p for p in parts if p]).strip()

    def _offline_next_question(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        question_text = self._combine_question_text(q.title, q.prompt)
        if self._is_behavioral(q):
            body = f"{question_text} Please answer using STAR (Situation, Task, Action, Result)."
        else:
            body = (
                f"{question_text} Start with constraints and a brief plan, then share complexity and edge cases."
            )
        if preface:
            return f"{preface.strip()}\n\n{body}".strip()
        return body.strip()

    def _pick_next_behavioral_question(
        self, db: Session, session: InterviewSession, asked_ids: set[int] | None = None
    ) -> Question | None:
        asked_ids = asked_ids or set()
        company = (session.company_style or "").strip().lower() or "general"
        track = (session.track or "").strip()
        diff = self._effective_difficulty(session)
        tracks = {track, "behavioral"} if track else {"behavioral"}

        base = db.query(Question).filter(
            Question.company_style == company,
            Question.track.in_(tracks),
            Question.difficulty == diff,
            or_(Question.tags_csv.ilike("%behavioral%"), Question.question_type == "behavioral"),
        )
        if asked_ids:
            base = base.filter(~Question.id.in_(asked_ids))
        seen = self._seen_question_subquery(session)
        unseen = base.filter(~Question.id.in_(seen)).order_by(func.random()).first()
        if unseen:
            return unseen
        return base.order_by(func.random()).first()

    def _pick_next_technical_question(
        self,
        db: Session,
        session: InterviewSession,
        asked_ids: set[int],
        seen_ids: set[int],
        focus: dict[str, Any] | None,
        desired_type: str | None = None,
    ) -> Question | None:
        diff = self._effective_difficulty(session)
        company = (session.company_style or "").strip().lower() or "general"

        base = db.query(Question).filter(
            Question.track == session.track,
            Question.company_style == company,
            Question.difficulty == diff,
            ~Question.tags_csv.ilike("%behavioral%"),
            Question.question_type != "behavioral",
        )
        if asked_ids:
            base = base.filter(~Question.id.in_(asked_ids))
        if seen_ids:
            base = base.filter(~Question.id.in_(seen_ids))

        candidates = base.order_by(func.random()).limit(120).all()
        if desired_type:
            candidates = [c for c in candidates if self._matches_desired_type(c, desired_type)]
        if not candidates:
            return None

        focus_tags = set((focus or {}).get("tags") or [])
        asked_tags: set[str] = set()
        if asked_ids:
            asked = db.query(Question).filter(Question.id.in_(asked_ids)).all()
            for q in asked:
                asked_tags.update({t.strip().lower() for t in (q.tags() or []) if t})

        best = None
        best_score = -10_000
        for q in candidates:
            tags = {t.strip().lower() for t in (q.tags() or []) if t}
            overlap = len(tags & focus_tags) if focus_tags else 0
            penalty = len(tags & asked_tags) if asked_tags else 0
            weak_score = self._weakness_score(q, self._weakness_keywords(self._weakest_dimension(session)))
            score = (overlap * 5) + weak_score - penalty
            if best is None or score > best_score:
                best = q
                best_score = score
        return best or candidates[0]

    def _pick_next_main_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        seen_ids = set(user_question_seen_crud.list_seen_question_ids(db, session.user_id))

        behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
        behavioral_asked = 0
        if asked_ids:
            asked_questions = db.query(Question).filter(Question.id.in_(asked_ids)).all()
            behavioral_asked = sum(1 for q in asked_questions if self._is_behavioral(q))

        questions_asked = int(session.questions_asked_count or 0)
        questions_remaining = max(0, int(session.max_questions or 0) - questions_asked)
        behavioral_remaining = max(0, behavioral_target - behavioral_asked)

        focus = {"tags": list(self._focus_tags(session))}

        if behavioral_remaining > 0:
            # If all remaining slots must be behavioral, do it now.
            if behavioral_remaining >= questions_remaining:
                q = self._pick_next_behavioral_question(db, session, asked_ids)
                if q:
                    return q
            # Otherwise, prefer technical first, then behavioral.
            q = self._pick_next_technical_question(db, session, asked_ids, seen_ids, focus, desired_type="coding")
            if q:
                return q
            return self._pick_next_behavioral_question(db, session, asked_ids)

        # Behavioral target already satisfied: only technical questions.
        q = self._pick_next_technical_question(db, session, asked_ids, seen_ids, focus, desired_type="coding")
        if q:
            return q
        return None

    def _mark_warmup_behavioral_asked(self, db: Session, session: InterviewSession, question_id: int | None) -> None:
        if not question_id:
            return
        with contextlib.suppress(Exception):
            session_question_crud.mark_question_asked(db, session.id, int(question_id))
        with contextlib.suppress(Exception):
            user_question_seen_crud.mark_question_seen(db, session.user_id, int(question_id))

    def _warmup_behavioral_ack(self, student_text: str | None) -> str:
        return interview_warmup.warmup_ack(student_text)

    async def _warmup_prompt(self, session: InterviewSession, user_name: str | None = None) -> str:
        sys = warmup_system_prompt(session.company_style, session.role, self._interviewer_name(session))
        user = warmup_prompt_user_prompt(user_name, self._interviewer_name(session))
        if not getattr(self.llm, "api_key", None):
            return interview_warmup.prompt_for_step(0, user_name=user_name, interviewer_name=self._interviewer_name(session)) or ""
        try:
            reply = await self.llm.chat(sys, user)
            return self._sanitize_ai_text(reply)
        except Exception:
            return interview_warmup.prompt_for_step(0, user_name=user_name, interviewer_name=self._interviewer_name(session)) or ""

    async def _warmup_reply(
        self,
        session: InterviewSession,
        student_text: str,
        user_name: str | None,
        focus: dict[str, Any],
        db: Session,
        tone_line: str | None = None,
    ) -> str:
        question_text, qid = self._warmup_behavioral_question(db, session)
        focus_line = self._warmup_focus_line(focus) or None
        sys = warmup_system_prompt(session.company_style, session.role, self._interviewer_name(session))
        user = warmup_reply_user_prompt(student_text, user_name, question_text, focus_line=focus_line, tone_line=tone_line)

        if not getattr(self.llm, "api_key", None):
            msg = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)
            self._mark_warmup_behavioral_asked(db, session, qid)
            return msg

        try:
            reply = await self.llm.chat(sys, user)
            reply = self._sanitize_ai_text(reply)
        except Exception:
            reply = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)

        if not reply:
            reply = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)

        self._mark_warmup_behavioral_asked(db, session, qid)
        return reply

    def _pick_warmup_behavioral_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        warmup_id = self._warmup_behavioral_question_id(session)
        if warmup_id:
            asked_ids.add(warmup_id)
        seen = self._seen_question_subquery(session)
        company = (session.company_style or "").strip().lower() or "general"
        track = (session.track or "").strip()
        tracks = [track, "behavioral"] if track else ["behavioral"]
        diff = (session.difficulty or "easy").strip().lower()

        base = db.query(Question).filter(
            Question.company_style == company,
            Question.track.in_(tracks),
            Question.difficulty == diff,
            or_(Question.tags_csv.ilike("%behavioral%"), Question.question_type == "behavioral"),
        )
        if asked_ids:
            base = base.filter(~Question.id.in_(asked_ids))
        unseen = base.filter(~Question.id.in_(seen)).order_by(func.random()).first()
        if unseen:
            return unseen
        return base.order_by(func.random()).first()

    def _fallback_warmup_behavioral_question(self, session: InterviewSession) -> str:
        company = self._company_name(session.company_style)
        role = (session.role or "").strip().lower()
        if session.company_style == "general":
            if "intern" in role:
                return "Why are you interested in this internship?"
            return "Why are you interested in this role?"
        if "intern" in role:
            return f"Why do you want to intern at {company}?"
        return f"Why do you want to work at {company}?"

    def _warmup_behavioral_question(self, db: Session, session: InterviewSession) -> tuple[str, int | None]:
        stored_id = self._warmup_behavioral_question_id(session)
        if stored_id:
            q = question_crud.get_question(db, stored_id)
            if q:
                title, prompt = self._render_question(session, q)
                return self._combine_question_text(title, prompt), q.id

        q = self._pick_warmup_behavioral_question(db, session)
        if q:
            with contextlib.suppress(Exception):
                self._set_warmup_behavioral_question_id(db, session, q.id)
            title, prompt = self._render_question(session, q)
            return self._combine_question_text(title, prompt), q.id

        return self._fallback_warmup_behavioral_question(session), None

    def _warmup_state(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        warm = state.get("warmup")
        return warm if isinstance(warm, dict) else {}

    def _set_warmup_state(
        self,
        db: Session,
        session: InterviewSession,
        step: int,
        done: bool,
        **meta: Any,
    ) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        warm = dict(warm)
        for key, val in meta.items():
            if val is not None:
                warm[key] = val
        warm["step"] = int(step)
        warm["done"] = bool(done)
        state["warmup"] = warm
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _warmup_profile_from_state(self, session: InterviewSession) -> WarmupToneProfile | None:
        warm = self._warmup_state(session)
        tone = warm.get("tone")
        energy = warm.get("energy")
        confidence_raw = warm.get("tone_confidence")
        if not tone and not energy:
            return None
        try:
            if confidence_raw is None:
                confidence = 0.6
            else:
                confidence = float(confidence_raw)
            return WarmupToneProfile(
                tone=tone or "neutral",
                energy=energy or "medium",
                confidence=confidence,
            )
        except Exception:
            return None

    def _infer_smalltalk_topic(self, text: str) -> str:
        t = self._normalize_text(text)
        if not t:
            return ""
        if any(k in t for k in ("class", "classes", "school", "semester", "lecture", "exam", "homework")):
            return "school"
        if any(k in t for k in ("project", "feature", "build", "prototype", "assignment")):
            return "project"
        if any(k in t for k in ("work", "job", "office", "meeting", "deadline", "shift")):
            return "work"
        if "interview" in t or "prep" in t:
            return "interview_prep"
        if any(k in t for k in ("commute", "traffic", "train", "bus", "drive")):
            return "commute"
        if any(k in t for k in ("weekend", "tonight")):
            return "weekend"
        if "weather" in t:
            return "weather"
        if "day" in t or "today" in t:
            return "day"
        return ""

    def _greeting_ack(self, text: str | None) -> str | None:
        t = self._normalize_text(text)
        if not t:
            return None
        if any(
            phrase in t
            for phrase in (
                "how are you",
                "how are you doing",
                "how are you doing today",
                "how is it going",
                "hows it going",
                "how's it going",
            )
        ):
            return "I'm doing well, thanks for asking."
        return None

    def _clean_smalltalk_question(self, question: str | None) -> str:
        q = (question or "").strip()
        if not q:
            return ""
        q = " ".join(q.split())
        q = re.sub(r"^(question|q)[:\-\s]+", "", q, flags=re.IGNORECASE).strip()
        if "?" in q:
            q = q.split("?")[0].strip() + "?"
        else:
            q = q.rstrip(".!") + "?"
        if len(q) > 140:
            q = q[:140].rsplit(" ", 1)[0].rstrip(".!?") + "?"
        return q

    def _is_redundant_smalltalk(self, question: str) -> bool:
        normalized = self._normalize_text(question).rstrip("?").strip()
        return normalized in {
            "how are you",
            "how are you doing",
            "how are you doing today",
            "how is it going",
            "hows it going",
        }

    def _smalltalk_question_from_topic(self, topic: str) -> str | None:
        t = (topic or "").strip().lower()
        if t in ("work", "job"):
            return "What have you been working on today?"
        if t in ("school", "class", "classes"):
            return "How are classes going lately?"
        if t == "project":
            return "What kind of project have you been working on recently?"
        if t in ("interview_prep", "interview"):
            return "How has interview prep been going lately?"
        if t == "commute":
            return "How was your commute today?"
        if t == "weekend":
            return "Any nice plans for later today?"
        if t == "weather":
            return "How's the weather where you are?"
        if t == "day":
            return "How has your day been so far?"
        return None

    def _smalltalk_question(self, profile: WarmupSmalltalkProfile | None, text: str) -> str:
        if profile:
            q = self._clean_smalltalk_question(profile.smalltalk_question)
            if q and not self._is_redundant_smalltalk(q):
                return q
            topic = profile.topic or self._infer_smalltalk_topic(text)
        else:
            topic = self._infer_smalltalk_topic(text)

        by_topic = self._smalltalk_question_from_topic(topic)
        if by_topic:
            return by_topic

        if profile and profile.tone in ("excited", "positive"):
            return "What's been the highlight of your day so far?"
        if profile and profile.tone in ("stressed", "tired"):
            return "Has your day been pretty busy so far?"
        return "How has your day been so far?"

    def _warmup_smalltalk_line(self, profile: WarmupToneProfile | None) -> str:
        if not profile:
            return "Thanks for sharing."
        tone = profile.tone
        energy = profile.energy

        if tone == "excited":
            return "Love the energy."
        if tone == "positive":
            return "Great to hear."
        if tone == "stressed":
            return "Totally fair."
        if tone == "tired" or tone == "negative":
            return "Thanks for sharing."
        if energy == "high":
            return "Nice, sounds like a good rhythm."
        return "Thanks for sharing."

    def _warmup_transition_line(self, profile: WarmupToneProfile | None) -> str:
        if not profile:
            return "Thanks for sharing, let's get started."
        tone = profile.tone
        energy = profile.energy

        if tone == "excited":
            return "Love the energy, let's keep that momentum."
        if tone == "positive":
            if energy == "high":
                return "Great to hear, let's keep that momentum."
            if energy == "low":
                return "Great to hear, we'll keep a steady pace."
            return "Great to hear, let's dive in."
        if tone == "stressed":
            return "Totally fair, we'll take it step by step."
        if tone == "tired":
            return "Thanks for sharing, we'll keep the pace comfortable."
        if tone == "negative":
            return "Thanks for sharing, we'll keep it low pressure."
        if energy == "high":
            return "Thanks for sharing, let's use that momentum."
        if energy == "low":
            return "Thanks for sharing, we'll keep the pace comfortable."
        return "Thanks for sharing, let's get started."

    def _warmup_smalltalk_reply(self, ack_line: str | None, question: str) -> str:
        ack = (ack_line or "Thanks for sharing.").strip()
        if ack and ack[-1] not in ".!?":
            ack = f"{ack}."
        q = self._clean_smalltalk_question(question) or "How has your day been so far?"
        return f"{ack} {q}".strip()

    async def _classify_warmup_smalltalk(self, text: str) -> WarmupSmalltalkProfile | None:
        msg = (text or "").strip()
        if not msg:
            return None
        if not getattr(self.llm, "api_key", None):
            return None
        sys = warmup_smalltalk_system_prompt()
        user = warmup_smalltalk_user_prompt(msg)
        try:
            data = await self.llm.chat_json(sys, user)
            if isinstance(data, dict) and "smalltalk_question" not in data and "question" in data:
                data["smalltalk_question"] = data.get("question")
            return WarmupSmalltalkProfile.model_validate(data)
        except Exception:
            return None

    async def _classify_warmup_tone(self, text: str) -> WarmupToneProfile | None:
        msg = (text or "").strip()
        if not msg:
            return None
        if not getattr(self.llm, "api_key", None):
            return None
        sys = warmup_tone_classifier_system_prompt()
        user = warmup_tone_classifier_user_prompt(msg)
        try:
            data = await self.llm.chat_json(sys, user)
            return WarmupToneProfile.model_validate(data)
        except Exception:
            return None

    async def _classify_user_intent(self, text: str, question_context: str | None = None) -> UserIntentClassification | None:
        """
        AI-powered intent classification. Understands context like a human.
        Falls back to keyword heuristics if LLM unavailable.
        """
        if not text or not text.strip():
            return None
        
        # Try AI classification first
        sys = user_intent_classifier_system_prompt()
        user = user_intent_classifier_user_prompt(text, question_context)
        try:
            data = await self.llm.chat_json(sys, user)
            classification = UserIntentClassification.model_validate(data)
            _engine_logger.debug(
                "Intent classified: %s (%.2f confidence) - %s",
                classification.intent,
                classification.confidence,
                classification.reasoning
            )
            return classification
        except Exception as e:
            _engine_logger.debug("Intent classification unavailable, using heuristics: %s", e)
            # Fallback to keyword heuristics
            return self._classify_intent_heuristic(text)

    def _classify_intent_heuristic(self, text: str) -> UserIntentClassification:
        """Fallback keyword-based intent classification."""
        if self._is_clarification_request(text):
            return UserIntentClassification(intent="clarification", confidence=0.7, reasoning="Keyword match")
        if self._is_move_on(text):
            return UserIntentClassification(intent="move_on", confidence=0.8, reasoning="Keyword match")
        if self._is_dont_know(text):
            return UserIntentClassification(intent="dont_know", confidence=0.7, reasoning="Keyword match")
        # Default to answering
        return UserIntentClassification(intent="answering", confidence=0.5, reasoning="Default fallback")

    def _warmup_behavioral_reply(
        self,
        session: InterviewSession,
        focus: dict[str, Any],
        question_text: str,
        tone_line: str | None = None,
    ) -> str:
        focus_line = self._warmup_focus_line(focus)
        question = question_text or self._fallback_warmup_behavioral_question(session)
        # Ensure regression-friendly phrasing even when LLM is offline:
        # - contains "i am doing well"
        # - contains "your interviewer"
        # - contains "behavioral question"
        interviewer_name = self._interviewer_name(session)
        if interviewer_name:
            base_ack = tone_line or f"I am doing well -- I'm {interviewer_name}, your interviewer. Let's get started."
        else:
            base_ack = tone_line or "I am doing well -- I'm your interviewer. Let's get started."
        if base_ack and base_ack[-1] not in ".!?":
            base_ack = f"{base_ack}."
        parts = [base_ack]
        if focus_line:
            parts.append(focus_line)
        parts.append(f"Let's start with a quick behavioral question: {question}")
        return " ".join(parts).strip()

    async def _ask_new_main_question(
        self,
        db: Session,
        session: InterviewSession,
        q: Question,
        history: list[dict],
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session))
        title, prompt = self._render_question(session, q)
        question_context = self._combine_question_text(title, prompt)
        if self._is_behavioral(q):
            user = f"""
This is a behavioral question. Ask it clearly and ask the candidate to answer using STAR (Situation, Task, Action, Result).
Avoid extra greetings or transition phrases like "next question".
Do not repeat the question.
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {question_context}
""".strip()
        else:
            user = f"""
Briefly introduce the problem and ask the candidate to clarify constraints.
Ask for a brief plan and key steps, then share "
"complexity, edge cases, and how you'd validate correctness.
Avoid extra greetings or transition phrases like "next question".
Do not repeat the question.
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {question_context}
""".strip()

        try:
            reply = await self.llm.chat(sys, user, history=history)
            reply = self._sanitize_ai_text(reply)
        except LLMClientError:
            q_title, q_prompt = self._render_question(session, q)
            q2 = Question(
                id=q.id,
                track=q.track,
                company_style=q.company_style,
                difficulty=q.difficulty,
                title=q_title,
                prompt=q_prompt,
                tags_csv=q.tags_csv,
                followups=[self._render_text(session, str(x)) for x in (getattr(q, "followups", []) or [])],
            )
            reply = self._offline_next_question(q2, user_name=user_name, preface=preface)
        cleaned_reply = self._clean_next_question_reply(reply, user_name=user_name)
        if cleaned_reply:
            reply = cleaned_reply
        if preface:
            cleaned = preface.strip()
            if cleaned and cleaned.lower() not in (reply or "").lower():
                reply = f"{cleaned}\n\n{reply}"
        message_crud.add_message(db, session.id, "interviewer", reply)
        session_crud.update_stage(db, session, "candidate_solution")
        return reply

    async def _advance_to_next_question(
        self,
        db: Session,
        session: InterviewSession,
        history: list[dict],
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        if self._max_questions_reached(session):
            wrap = "Thanks - that's the end of the interview. When you're ready, click Finalize to get your score."
            message_crud.add_message(db, session.id, "interviewer", wrap)
            session_crud.update_stage(db, session, "wrapup")
            return wrap

        # Adaptive difficulty: adjust for the next technical question if appropriate.
        with contextlib.suppress(Exception):
            self._maybe_bump_difficulty_current(db, session)

        next_q = self._pick_next_main_question(db, session)
        if not next_q:
            wrap = "No more questions available. Click Finalize to get your score."
            message_crud.add_message(db, session.id, "interviewer", wrap)
            session_crud.update_stage(db, session, "wrapup")
            return wrap

        self._reset_for_new_question(db, session, next_q.id)
        session_question_crud.mark_question_asked(db, session.id, next_q.id)
        with contextlib.suppress(Exception):
            user_question_seen_crud.mark_question_seen(db, session.user_id, next_q.id)
        self._increment_questions_asked(db, session)
        if preface is None:
            preface = self._transition_preface(session)
        return await self._ask_new_main_question(db, session, next_q, history, user_name=user_name, preface=preface)

    async def ensure_question_and_intro(
        self,
        db: Session,
        session: InterviewSession,
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        """
        Start the interview with a greeting + main question for the first problem.
        If the LLM is unavailable, fall back to a dataset-driven message (no 502).
        """
        warm_step, warm_done = interview_warmup.get_state(session)
        stage = session.stage or "intro"

        if stage == "warmup_behavioral" and not warm_done:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            focus = {"dimensions": self._focus_dimensions(session), "tags": []}
            question_text, qid = self._warmup_behavioral_question(db, session)
            tone_line = self._warmup_transition_line(self._warmup_profile_from_state(session))
            msg = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)
            message_crud.add_message(db, session.id, "interviewer", msg)
            self._mark_warmup_behavioral_asked(db, session, qid)
            return msg

        if stage == "warmup_smalltalk" and not warm_done:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            warm = self._warmup_state(session)
            profile = self._warmup_profile_from_state(session)
            question = warm.get("smalltalk_question") or self._smalltalk_question(None, "")
            msg = self._warmup_smalltalk_reply(self._warmup_smalltalk_line(profile), question)
            message_crud.add_message(db, session.id, "interviewer", msg)
            return msg

        # Warmup greeting (only when at intro/warmup stage)
        if not warm_done and (stage in (None, "", "intro", "warmup", "warmup_smalltalk")) and stage != "warmup_done":
            if warm_step <= 0:
                msg = None
                try:
                    msg = await self._warmup_prompt(session, user_name=user_name)
                except Exception:
                    msg = None
                if not msg:
                    msg = interview_warmup.prompt_for_step(
                        0, user_name=user_name, interviewer_name=self._interviewer_name(session)
                    )
                if msg:
                    message_crud.add_message(db, session.id, "interviewer", msg)
                    self._set_warmup_state(db, session, 1, False)
                    session_crud.update_stage(db, session, "warmup")
                    return msg

            last = self._last_interviewer_message(db, session.id)
            if last:
                return last

        reply: str | None = None
        if session.questions_asked_count == 0 or session.current_question_id is None:
            q = self._pick_next_main_question(db, session)
            if not q:
                msg = "No questions found for this track/style/difficulty. Please ask admin to load questions."
                message_crud.add_message(db, session.id, "system", msg)
                return msg

            self._reset_for_new_question(db, session, q.id)
            session_question_crud.mark_question_asked(db, session.id, q.id)
            with contextlib.suppress(Exception):
                user_question_seen_crud.mark_question_seen(db, session.user_id, q.id)
            self._increment_questions_asked(db, session)

            if not preface:
                preface = self._interviewer_intro_line(session) or preface
            sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session))
            title, prompt = self._render_question(session, q)
            if self._is_behavioral(q):
                user = f"""
Start the interview with a short greeting.
Transition into the first behavioral question. Greet the candidate by name if available ({user_name or "name unavailable"}).
Ask the candidate to answer using STAR (Situation, Task, Action, Result). Keep it conversational and concise.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()
            else:
                user = f"""
Start the interview with a short greeting.
Ask the candidate to restate the problem and clarify constraints, then start with a brief plan and key steps.
Ask them to cover complexity, edge cases, and how they would validate correctness.
Greet the candidate by name if available ({user_name or "name unavailable"}). Keep it concise and friendly.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()

            try:
                reply = await self.llm.chat(sys, user)
                reply = self._sanitize_ai_text(reply)
            except LLMClientError:
                q_title, q_prompt = self._render_question(session, q)
                q2 = Question(
                    id=q.id,
                    track=q.track,
                    company_style=q.company_style,
                    difficulty=q.difficulty,
                    title=q_title,
                    prompt=q_prompt,
                    tags_csv=q.tags_csv,
                    followups=[self._render_text(session, str(x)) for x in (getattr(q, "followups", []) or [])],
                )
                reply = self._offline_intro(q2, user_name=user_name, preface=preface)
            if preface:
                cleaned = preface.strip()
                if cleaned and cleaned.lower() not in (reply or "").lower():
                    reply = f"{cleaned}\n\n{reply}"

        if reply is None:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            msg = "No interviewer message available. Please send a response or restart the session."
            message_crud.add_message(db, session.id, "system", msg)
            return msg

        message_crud.add_message(db, session.id, "interviewer", reply)
        session_crud.update_stage(db, session, "candidate_solution")
        return reply

    async def handle_student_message(
        self, db: Session, session: InterviewSession, student_text: str, user_name: str | None = None
    ) -> str:
        """
        Store student message and decide next interviewer reply.
        Order of operations:
        1) Persist student text.
        2) Apply quick human-like heuristics (move on / don't know / non-informative / vague).
        3) Delegate to controller LLM for structured action selection.
        4) Use dataset followups / safe defaults if the LLM is unavailable.
        """
        if student_text and student_text.strip():
            message_crud.add_message(db, session.id, "student", student_text.strip())

        warm_step, warm_done = interview_warmup.get_state(session)
        stage = session.stage or "intro"
        
        # Handle behavioral warmup stage with smart intent detection
        if stage == "warmup_behavioral" and not warm_done:
            # Check if user wants clarification/repetition
            intent_classification = await self._classify_user_intent(student_text, question_context="Behavioral warmup question")
            if intent_classification and intent_classification.confidence >= 0.6:
                if intent_classification.intent == "clarification":
                    # Repeat the behavioral question
                    msgs = message_crud.list_messages(db, session.id, limit=10)
                    behavioral_question = None
                    for m in reversed(msgs):
                        if m.role == "interviewer" and ("tell me about" in m.content.lower() or "describe a time" in m.content.lower()):
                            behavioral_question = m.content
                            break
                    if behavioral_question:
                        clarify_reply = f"Of course! Here's the question again:\n\n{behavioral_question}"
                        message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                        return clarify_reply
            
            # Normal flow: user answered behavioral, move on
            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                with contextlib.suppress(Exception):
                    self._store_focus(db, session, focus)
            preface = self._warmup_behavioral_ack(student_text)
            self._set_warmup_state(db, session, max(warm_step, 3), True)
            session_crud.update_stage(db, session, "warmup_done")
            return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=preface)

        if not warm_done and (stage in (None, "", "intro", "warmup", "warmup_smalltalk")) and stage != "warmup_done":
            # Warmup flow: greet, then a short small-talk question, then a behavioral warmup question.
            
            # SMART INTENT: Check if user is asking for clarification/repetition during warmup
            if warm_step > 0:  # After initial greeting
                intent_classification = await self._classify_user_intent(student_text, question_context="Warmup conversation")
                if intent_classification and intent_classification.confidence >= 0.6:
                    if intent_classification.intent == "clarification":
                        # User asking to repeat during warmup - use natural response
                        msgs = message_crud.list_messages(db, session.id, limit=5)
                        last_interviewer_msg = None
                        for m in reversed(msgs):
                            if m.role == "interviewer":
                                last_interviewer_msg = m.content
                                break
                        if last_interviewer_msg:
                            clarify_reply = f"Of course! I asked: {last_interviewer_msg}"
                            message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                            return clarify_reply
            
            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                with contextlib.suppress(Exception):
                    self._store_focus(db, session, focus)

            if warm_step <= 0:
                msg = await self._warmup_prompt(session, user_name=user_name)
                message_crud.add_message(db, session.id, "interviewer", msg)
                self._set_warmup_state(db, session, 1, False)
                session_crud.update_stage(db, session, "warmup")
                return msg

            if warm_step == 1:
                # Step 1: User responded to greeting, now continue conversation naturally
                # Check if user is asking about the interviewer (reciprocal question)
                t_lower = student_text.lower()
                is_reciprocal = any(phrase in t_lower for phrase in [
                    "how are you", "how about you", "what about you", "how is your",
                    "how's your", "and you", "yourself"
                ])
                
                if is_reciprocal:
                    # User asked about the interviewer - respond naturally then continue
                    reciprocal_response = "I'm doing well, thank you for asking! "
                    # Then add a smalltalk question
                    profile = await self._classify_warmup_smalltalk(student_text)
                    question = self._smalltalk_question(profile, student_text)
                    msg = reciprocal_response + question
                    meta: dict[str, Any] = {
                        "smalltalk_question": question,
                        "smalltalk_topic": (profile.topic if profile else None) or self._infer_smalltalk_topic(student_text),
                    }
                    if profile:
                        meta.update({
                            "tone": profile.tone,
                            "energy": profile.energy,
                            "tone_confidence": profile.confidence,
                        })
                    message_crud.add_message(db, session.id, "interviewer", msg)
                    self._set_warmup_state(db, session, 2, False, **meta)
                    session_crud.update_stage(db, session, "warmup_smalltalk")
                    return msg
                
                # Normal flow: classify and ask smalltalk
                profile = await self._classify_warmup_smalltalk(student_text)
                # If LLM is unavailable, still do a small-talk fallback before behavioral warmup.
                if not profile and not getattr(self.llm, "api_key", None):
                    question = self._smalltalk_question(None, student_text)
                    ack_line = self._greeting_ack(student_text) or self._warmup_smalltalk_line(None)
                    msg = self._warmup_smalltalk_reply(ack_line, question)
                    meta: dict[str, Any] = {
                        "smalltalk_question": question,
                        "smalltalk_topic": self._infer_smalltalk_topic(student_text),
                    }
                    message_crud.add_message(db, session.id, "interviewer", msg)
                    self._set_warmup_state(db, session, 2, False, **meta)
                    session_crud.update_stage(db, session, "warmup_smalltalk")
                    return msg

                question = self._smalltalk_question(profile, student_text)
                ack_line = self._greeting_ack(student_text) or self._warmup_smalltalk_line(profile)
                msg = self._warmup_smalltalk_reply(ack_line, question)
                meta: dict[str, Any] = {
                    "smalltalk_question": question,
                    "smalltalk_topic": (profile.topic if profile else None) or self._infer_smalltalk_topic(student_text),
                }
                if profile:
                    meta.update(
                        {
                            "tone": profile.tone,
                            "energy": profile.energy,
                            "tone_confidence": profile.confidence,
                        }
                    )
                message_crud.add_message(db, session.id, "interviewer", msg)
                self._set_warmup_state(db, session, 2, False, **meta)
                session_crud.update_stage(db, session, "warmup_smalltalk")
                return msg

            # Step 2+: User responded to smalltalk - check for reciprocal or continue to behavioral
            # Check if user is still engaging in conversation before moving to behavioral
            if warm_step == 2:
                t_lower = student_text.lower()
                is_reciprocal = any(phrase in t_lower for phrase in [
                    "how are you", "how about you", "what about you", "how is your",
                    "how's your", "and you", "yourself", "what about your", "asked you"
                ])
                
                if is_reciprocal:
                    # User is continuing conversation - respond naturally
                    natural_response = "I'm doing great, thanks for asking! "
                    # Now transition to behavioral
                    behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
                    if behavioral_target <= 0:
                        transition = "Let's dive into the interview."
                        self._set_warmup_state(db, session, 3, True)
                        session_crud.update_stage(db, session, "warmup_done")
                        preface = natural_response + transition
                        return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=preface)
                    else:
                        # Continue to behavioral with natural transition
                        transition = "Let's get started. "
                        question_text, qid = self._warmup_behavioral_question(db, session)
                        msg = natural_response + transition + question_text
                        message_crud.add_message(db, session.id, "interviewer", msg)
                        self._set_warmup_state(db, session, 3, False)
                        session_crud.update_stage(db, session, "warmup_behavioral")
                        self._mark_warmup_behavioral_asked(db, session, qid)
                        return msg
            
            # Normal flow: transition to behavioral question
            behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
            tone_line = self._warmup_transition_line(self._warmup_profile_from_state(session))
            if behavioral_target <= 0:
                # Skip behavioral warmup if none are requested.
                self._set_warmup_state(db, session, max(warm_step, 3), True)
                session_crud.update_stage(db, session, "warmup_done")
                return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=tone_line)

            msg = await self._warmup_reply(
                session=session,
                student_text=student_text,
                user_name=user_name,
                focus=focus,
                db=db,
                tone_line=tone_line,
            )
            message_crud.add_message(db, session.id, "interviewer", msg)
            self._set_warmup_state(db, session, max(warm_step, 3), False)
            session_crud.update_stage(db, session, "warmup_behavioral")
            return msg

        q = question_crud.get_question(db, session.current_question_id) if session.current_question_id else None
        if q:
            if self._is_behavioral(q):
                allowed_tracks = {session.track, "behavioral"}
                if q.track not in allowed_tracks:
                    q = None
            else:
                if q.track != session.track:
                    q = None
            if q:
                desired_diff = (session.difficulty or "easy").strip().lower()
                if (q.difficulty or "").strip().lower() != desired_diff:
                    q = None
            if q:
                allowed_company = (session.company_style or "").strip().lower() or "general"
                if (q.company_style or "").strip().lower() != allowed_company:
                    q = None

        if q:
            qt, qp = self._render_question(session, q)
            question_context = f"\nQuestion: {qt}\n{qp}\n"
        else:
            question_context = ""

        msgs = message_crud.list_messages(db, session.id, limit=30)
        history: list[dict] = []
        for m in msgs:
            if m.role == "student":
                history.append({"role": "user", "content": m.content})
            elif m.role == "interviewer":
                history.append({"role": "assistant", "content": m.content})

        sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session))

        stage = session.stage or "intro"
        max_followups = int(session.max_followups_per_question or 2)
        max_questions = int(session.max_questions or 7)
        min_questions = 5

        if not q:
            # Clear stale question so we can pick a new one.
            session.current_question_id = None
            db.add(session)
            db.commit()
            db.refresh(session)
            return await self.ensure_question_and_intro(db, session, user_name=user_name)

        if stage in ("followups", "candidate_solution") and self._max_followups_reached(session):
            stage = "next_question"

        # SMART INTENT DETECTION: Use AI to understand what user wants (like a human would)
        intent_classification = await self._classify_user_intent(student_text, question_context)
        
        if intent_classification and intent_classification.confidence >= 0.6:
            intent = intent_classification.intent
            
            # Handle clarification requests
            if intent == "clarification":
                qt, qp = self._render_question(session, q)
                clarify_reply = f"Of course! Let me restate the question:\n\n**{qt}**\n\n{qp}\n\nTake your time thinking through it."
                message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                # Don't increment followups for clarification requests
                return clarify_reply
            
            # Handle explicit move-on requests
            if intent == "move_on":
                reason = "move_on"
                preface = self._transition_preface(session, reason=reason)
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            
            # Handle "don't know" responses
            if intent == "dont_know":
                reason = "dont_know"
                preface = self._transition_preface(session, reason=reason)
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        # Fallback checks for very short/empty responses (keep as safety net)
        if self._is_non_informative(student_text):
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            reply = "I'll need a fuller response before we move on. Please outline your approach, key steps, and any assumptions."
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if self._is_vague(student_text):
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            reply = "Can you add more detail on your approach, complexity, and edge cases before we move on?"
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if stage == "next_question":
            preface = self._transition_preface(session)
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        signals = self._candidate_signals(student_text)
        is_behavioral = self._is_behavioral(q)
        behavioral_missing = self._behavioral_missing_parts(student_text) if is_behavioral else []
        missing_keys_all = self._missing_focus_keys(q, signals, behavioral_missing)
        focus_keys = self._question_focus_keys(q)
        missing_keys_all = self._prioritize_missing_focus(missing_keys_all, session, prefer=focus_keys)
        last_overall = self._skill_last_overall(session)
        if (
            last_overall is not None
            and last_overall >= 8.0
            and not is_behavioral
            and "tradeoffs" not in missing_keys_all
            and not signals.get("mentions_tradeoffs")
        ):
            missing_keys_all = ["tradeoffs"] + missing_keys_all

        response_quality = self._response_quality(
            student_text,
            signals,
            is_behavioral,
            behavioral_missing,
        )
        critical_missing, optional_missing = self._missing_focus_tiers(
            missing_keys_all,
            is_behavioral,
            behavioral_missing,
        )
        missing_keys = missing_keys_all
        if response_quality == "strong":
            missing_keys = critical_missing
        elif response_quality == "ok":
            missing_keys = []
            for key in critical_missing + optional_missing[:1]:
                if key not in missing_keys:
                    missing_keys.append(key)

        missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)
        signal_summary = self._signal_summary(signals, missing_keys, behavioral_missing)
        skill_summary = self._skill_summary(session)

        if self._is_off_topic(q, student_text, signals):
            reanchor_count = self._get_reanchor_count(session, q.id)
            if reanchor_count < 1 and not self._max_followups_reached(session):
                nudge = "I may be missing how that answers the question. Can you restate the problem and outline your approach?"
                message_crud.add_message(db, session.id, "interviewer", nudge)
                self._increment_followups_used(db, session)
                self._set_reanchor_count(db, session, q.id, reanchor_count + 1)
                session_crud.update_stage(db, session, "followups")
                return nudge
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please answer the next question directly."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        thin_response = self._is_thin_response(
            student_text,
            signals,
            is_behavioral,
            behavioral_missing,
        )

        if thin_response:
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            nudge = self._soft_nudge_prompt(is_behavioral, missing_keys, behavioral_missing)
            message_crud.add_message(db, session.id, "interviewer", nudge)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return nudge

        if int(session.followups_used or 0) == 0 and not self._max_followups_reached(session):
            force_followup = False
            if is_behavioral:
                force_followup = len(behavioral_missing) >= 2
            else:
                force_followup = "approach" in critical_missing or "correctness" in critical_missing
            if signals.get("has_code") and not signals.get("mentions_approach"):
                force_followup = True
            if force_followup:
                targeted = None
                if is_behavioral and behavioral_missing:
                    targeted = self._missing_focus_question("star", behavioral_missing)
                elif signals.get("has_code") and not signals.get("mentions_approach"):
                    targeted = "Walk me through your approach and key steps."
                else:
                    targeted = self._phase_followup(
                        q,
                        signals,
                        session,
                        int(session.followups_used or 0),
                    )
                    if not targeted and missing_keys:
                        targeted = self._missing_focus_question(missing_keys[0], behavioral_missing)

                if targeted:
                    message_crud.add_message(db, session.id, "interviewer", targeted)
                    self._increment_followups_used(db, session)
                    session_crud.update_stage(db, session, "followups")
                    return targeted

        # Get RAG context for smarter follow-ups (Phase 5)
        rag_context = _get_rag_context_for_interview(db, session.id)
        
        ctrl_sys = interviewer_controller_system_prompt(session.company_style, session.role, rag_context=rag_context)
        ctrl_user = interviewer_controller_user_prompt(
            stage=stage,
            question_title=self._render_text(session, q.title),
            question_prompt=self._render_text(session, q.prompt),
            candidate_latest=student_text,
            followups_used=int(session.followups_used or 0),
            max_followups=max_followups,
            questions_asked_count=int(session.questions_asked_count or 0),
            max_questions=max_questions,
            signal_summary=signal_summary or None,
            missing_focus=missing_focus or None,
            skill_summary=skill_summary or None,
            response_quality=response_quality,
            is_behavioral=is_behavioral,
        )

        intent = ""
        confidence = 0.6
        next_focus = None
        coverage = {}
        missing_focus_llm: list[str] = []
        try:
            data = await self.llm.chat_json(ctrl_sys, ctrl_user, history=history)
            ctrl = InterviewControllerOutput.model_validate(data)
            action = ctrl.action
            message = self._sanitize_ai_text((ctrl.message or "").strip())
            done_with_question = bool(ctrl.done_with_question)
            allow_second_followup = bool(ctrl.allow_second_followup)
            quick_rubric_raw = ctrl.quick_rubric.model_dump()
            intent = (ctrl.intent or "").strip().upper() if ctrl.intent else ""
            confidence = float(ctrl.confidence or 0.6)
            next_focus = ctrl.next_focus
            coverage = ctrl.coverage or {}
            missing_focus_llm = ctrl.missing_focus or []
        except Exception:
            action = ""
            message = ""
            done_with_question = False
            allow_second_followup = False
            quick_rubric_raw = None
            coverage = {}
            missing_focus_llm = []

        # Store rolling rubric (used later for adaptive difficulty and weakness targeting).
        if student_text and student_text.strip():
            with contextlib.suppress(Exception):
                self._update_skill_state(db, session, quick_rubric_raw, is_behavioral=self._is_behavioral(q))

        if intent == "WRAP_UP":
            action = "WRAP_UP"
        elif intent == "ADVANCE" and action == "FOLLOWUP":
            action = "MOVE_TO_NEXT_QUESTION"
        elif intent in ("CLARIFY", "DEEPEN", "CHALLENGE") and action in ("MOVE_TO_NEXT_QUESTION", "WRAP_UP"):
            action = "FOLLOWUP"

        if confidence < 0.5:
            allow_second_followup = False
        if confidence < 0.3 and action == "FOLLOWUP" and int(session.followups_used or 0) >= 1:
            action = "MOVE_TO_NEXT_QUESTION"

        if confidence >= 0.55:
            if missing_focus_llm:
                missing_keys = self._prioritize_missing_focus(missing_focus_llm, session, prefer=focus_keys)
                missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)
            elif coverage:
                inferred = self._missing_from_coverage(coverage, is_behavioral)
                if inferred:
                    missing_keys = self._prioritize_missing_focus(inferred, session, prefer=focus_keys)
                    missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)

        if response_quality in ("strong", "ok") and missing_keys:
            crit_after, opt_after = self._missing_focus_tiers(missing_keys, is_behavioral, behavioral_missing)
            if response_quality == "strong":
                missing_keys = crit_after
            else:
                limited: list[str] = []
                for key in crit_after + opt_after[:1]:
                    if key not in limited:
                        limited.append(key)
                missing_keys = limited
            missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)

        critical_missing, _ = self._missing_focus_tiers(missing_keys, is_behavioral, behavioral_missing)
        clarify_attempts, _ = self._update_clarify_tracking(db, session, q.id, critical_missing)
        if not critical_missing and response_quality in ("strong", "ok") and int(session.followups_used or 0) == 0:
            if action == "FOLLOWUP":
                action = "MOVE_TO_NEXT_QUESTION"

        force_clarify = (
            bool(critical_missing)
            and not self._max_followups_reached(session)
            and clarify_attempts < 2
        )
        if force_clarify:
            if action in ("MOVE_TO_NEXT_QUESTION", "WRAP_UP"):
                action = "FOLLOWUP"
            if int(session.followups_used or 0) >= 1:
                allow_second_followup = True
            if not message:
                message = self._missing_focus_question(critical_missing[0], behavioral_missing) or ""
        elif critical_missing and clarify_attempts >= 2 and action == "FOLLOWUP":
            action = "MOVE_TO_NEXT_QUESTION"

        if not message:
            focus_key = self._normalize_focus_key(next_focus)
            if focus_key:
                message = self._missing_focus_question(focus_key, behavioral_missing) or ""

        if not message and isinstance(getattr(q, "followups", None), list) and q.followups:
            idx = int(session.followups_used or 0)
            if 0 <= idx < len(q.followups):
                message = self._render_text(session, str(q.followups[idx]).strip())

        if not message:
            message = (
                self._phase_followup(
                    q,
                    signals,
                    session,
                    int(session.followups_used or 0),
                )
                or ""
            )

        if not message:
            missing_line = f"Missing focus: {missing_focus}" if missing_focus else ""
            user_prompt = f"""
Continue the interview.
{question_context}
Ask ONE follow-up question based on the candidate's latest response.
Prefer: constraints, approach clarity, complexity, edge cases, optimization.
{missing_line}
""".strip()
            try:
                message = await self.llm.chat(sys, user_prompt, history=history)
                message = self._sanitize_ai_text(message)
            except LLMClientError:
                if missing_keys:
                    message = self._missing_focus_question(missing_keys[0], behavioral_missing) or ""
                if not message:
                    if self._is_behavioral(q):
                        message = "What was the outcome, and what did you learn from that experience?"
                    else:
                        message = "What is the time complexity of your approach, and what edge cases would you test?"
            action = "FOLLOWUP"

        if action == "WRAP_UP" and int(session.questions_asked_count or 0) >= min_questions:
            message_crud.add_message(db, session.id, "interviewer", message)
            session_crud.update_stage(db, session, "wrapup")
            return message
        if action == "WRAP_UP" and int(session.questions_asked_count or 0) < min_questions:
            action = "MOVE_TO_NEXT_QUESTION"

        if done_with_question and action not in ("WRAP_UP",) and not force_clarify:
            action = "MOVE_TO_NEXT_QUESTION"

        # Followups are short by design: mostly 1; allow 2 only if explicitly requested.
        if action == "FOLLOWUP" and int(session.followups_used or 0) >= 1 and not allow_second_followup:
            action = "MOVE_TO_NEXT_QUESTION"

        if action == "MOVE_TO_NEXT_QUESTION" or self._max_followups_reached(session):
            session_crud.update_stage(db, session, "next_question")
            preface = self._transition_preface(session)
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        self._increment_followups_used(db, session)
        message_crud.add_message(db, session.id, "interviewer", message)
        session_crud.update_stage(db, session, "followups")
        return message
