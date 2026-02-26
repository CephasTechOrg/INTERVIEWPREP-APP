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
from app.services.interview_engine_main import InterviewEngineMain


class InterviewEngine(InterviewEngineMain):
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
        super().__init__()
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

    def _interviewer_id(self, session: InterviewSession) -> str | None:
        profile = self._interviewer_profile(session)
        id_ = str(profile.get("id") or "").strip().lower()
        return id_ or None

    def _interviewer_intro_line(self, session: InterviewSession) -> str | None:
        name = self._interviewer_name(session)
        if not name:
            return None
        return f"Hi, I'm {name}, and I'll be your interviewer today."

    def _intro_used(self, session: InterviewSession) -> bool:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            return False
        return bool(state.get("intro_used"))

    def _set_intro_used(self, db: Session, session: InterviewSession) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        state["intro_used"] = True
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

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

    def _critical_rubric_gaps(self, session: InterviewSession, threshold: int = 5) -> list[str]:
        """
        Phase 4: Extract critical rubric gaps (score < threshold) to guide follow-ups.
        
        Maps rubric dimensions to missing focus keys for targeted follow-ups.
        """
        state = session.skill_state if isinstance(getattr(session, "skill_state", None), dict) else None
        if not state:
            return []

        last = state.get("last")
        if not isinstance(last, dict):
            return []

        gaps: list[str] = []
        # Map rubric dimensions to focus keys
        dim_to_focus = {
            "correctness_reasoning": "correctness",
            "problem_solving": "approach",
            "complexity": "complexity",
            "edge_cases": "edge_cases",
            "communication": "approach",  # fallback for communication issues
        }

        for dim, focus_key in dim_to_focus.items():
            try:
                score = int(last.get(dim))
            except (ValueError, TypeError):
                continue
            if score < threshold and focus_key not in gaps:
                gaps.append(focus_key)

        return gaps

    def _question_rubric_alignment_score(self, q: Question, rubric_gaps: list[str]) -> int:
        """
        Phase 5: Score how well a question targets the candidate's rubric gaps.

        Questions with evaluation_focus matching rubric gaps get higher scores.
        """
        if not rubric_gaps:
            return 0

        eval_focus = getattr(q, "evaluation_focus", None) or []
        if not isinstance(eval_focus, list):
            return 0

        focus_keys = {self._normalize_focus_key(str(f)) for f in eval_focus}
        focus_keys.discard(None)
        
        # Score: +10 for each gap the question targets
        matching_gaps = sum(1 for gap in rubric_gaps if gap in focus_keys)
        return matching_gaps * 10

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
        If adaptive difficulty is disabled, lock to user's selected value.
        If enabled, allow difficulty_current to move toward the selected cap based on performance.
        """
        selected = (getattr(session, "difficulty", None) or "easy").strip().lower()
        if selected not in ("easy", "medium", "hard"):
            selected = "easy"
        adaptive_enabled = bool(getattr(session, "adaptive_difficulty_enabled", False))
        if not adaptive_enabled:
            if getattr(session, "difficulty_current", None) != selected:
                session.difficulty_current = selected
                db.add(session)
                db.commit()
                db.refresh(session)
            return

        current = (getattr(session, "difficulty_current", None) or selected).strip().lower()
        if current not in ("easy", "medium", "hard"):
            current = selected

        cap_rank = self._difficulty_rank(selected)
        current_rank = self._difficulty_rank(current)
        last_overall = self._skill_last_overall(session)
        good_streak, weak_streak = self._skill_streaks(session)

        bumped = current_rank
        if last_overall is not None and good_streak >= 2 and last_overall >= 7.5:
            bumped = min(cap_rank, current_rank + 1)
        elif last_overall is not None and weak_streak >= 2 and last_overall <= 4.5:
            bumped = max(0, current_rank - 1)

        if bumped != current_rank:
            session.difficulty_current = self._rank_to_difficulty(bumped)
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

    def _company_name(self, company_style: str) -> str:
        if not company_style or company_style == "general":
            return "this company"
        return company_style[:1].upper() + company_style[1:]

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
        is_conceptual: bool = False,
    ) -> bool:
        """Check if response lacks substance - but allow clarifications."""
        # Don't flag clarification requests as thin
        if self._is_clarification_request(text or ""):
            return False
        
        tokens = self._clean_tokens(text)
        if not tokens:
            return True

        if is_conceptual:
            return len(tokens) < 8
        
        # Short responses with technical content are acceptable
        if len(tokens) >= 3:
            t_lower = (text or "").lower()
            technical_patterns = ["array", "hash", "map", "dict", "list", "tree", "graph",
                                 "o(n)", "o(1)", "o(log", "time", "space", "algorithm"]
            if any(pattern in t_lower for pattern in technical_patterns):
                return False  # Has technical content, not thin
        
        if is_behavioral:
            return len(behavioral_missing) >= 3
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

    def _mentions_tests(self, text: str | None) -> bool:
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            [
                "test",
                "tests",
                "unit test",
                "unit tests",
                "example",
                "examples",
                "cases",
                "test case",
                "test cases",
                "validate",
                "verification",
                "assert",
            ],
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
            "mentions_tests": self._mentions_tests(text),
        }

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

