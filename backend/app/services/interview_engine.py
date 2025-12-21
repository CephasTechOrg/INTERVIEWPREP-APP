import random
import re
from typing import Any

from sqlalchemy import func, select
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
from app.services.llm_client import DeepSeekClient, LLMClientError
from app.services.llm_schemas import InterviewControllerOutput
from app.services import interview_warmup
from app.services.prompt_templates import (
    interviewer_controller_system_prompt,
    interviewer_controller_user_prompt,
    interviewer_system_prompt,
    warmup_system_prompt,
    warmup_prompt_user_prompt,
    warmup_reply_user_prompt,
)


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

    def _clamp_int(self, value: Any, default: int, lo: int, hi: int) -> int:
        try:
            n = int(value)
        except Exception:
            n = int(default)
        return max(lo, min(hi, n))

    def _coerce_quick_rubric(self, raw: Any) -> dict:
        raw_dict = raw if isinstance(raw, dict) else {}
        return {k: self._clamp_int(raw_dict.get(k), default=5, lo=0, hi=10) for k in self._RUBRIC_KEYS}

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
        streak = state.get("streak") if isinstance(state.get("streak"), dict) else {}

        n_prev = self._clamp_int(state.get("n"), default=0, lo=0, hi=10_000)
        sum_prev = state.get("sum") if isinstance(state.get("sum"), dict) else {}

        last = self._coerce_quick_rubric(quick_rubric_raw)
        sums: dict[str, int] = {}
        for k in self._RUBRIC_KEYS:
            sums[k] = self._clamp_int(sum_prev.get(k), default=0, lo=0, hi=1_000_000) + int(last[k])

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
            "streak": {"good": good_prev, "weak": weak_prev},
        }
        if warm:
            new_state["warmup"] = warm
        if focus:
            new_state["focus"] = focus
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
        Which technical difficulties to try, in order, bounded by the user's selected cap.

        We start from `difficulty_current`, try easier fallbacks, then (if needed) try
        harder values up to the cap (to avoid "no questions found" when a dataset is sparse).
        """
        cap_rank = self._difficulty_rank(getattr(session, "difficulty", "easy"))
        cur_rank = self._difficulty_rank(getattr(session, "difficulty_current", "easy"))
        cur_rank = min(cur_rank, cap_rank)

        ranks: list[int] = [cur_rank]
        for r in range(cur_rank - 1, -1, -1):
            ranks.append(r)
        for r in range(cur_rank + 1, cap_rank + 1):
            ranks.append(r)

        seen: set[int] = set()
        out: list[str] = []
        for r in ranks:
            if r in seen:
                continue
            seen.add(r)
            out.append(self._rank_to_difficulty(r))
        return out

    def _skill_last_overall(self, session: InterviewSession) -> float | None:
        state = session.skill_state if isinstance(getattr(session, "skill_state", None), dict) else None
        if not state:
            return None
        last = state.get("last")
        if not isinstance(last, dict):
            return None

        vals: list[int] = []
        for k in self._RUBRIC_KEYS:
            try:
                vals.append(int(last.get(k)))
            except Exception:
                pass
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
        Adaptive difficulty: start at easy, increase on strong streaks, decrease after repeated struggles.
        """
        cap_rank = self._difficulty_rank(getattr(session, "difficulty", "easy"))
        cur_rank = self._difficulty_rank(getattr(session, "difficulty_current", "easy"))
        cur_rank = min(cur_rank, cap_rank)
        if session.current_question_id:
            try:
                q_prev = question_crud.get_question(db, session.current_question_id)
            except Exception:
                q_prev = None
            if q_prev and self._is_behavioral(q_prev):
                return
        last_overall = self._skill_last_overall(session)
        if last_overall is None:
            return

        good_streak, weak_streak = self._skill_streaks(session)
        new_rank = cur_rank
        if weak_streak >= 2 and cur_rank > 0:
            new_rank = cur_rank - 1
        elif good_streak >= 2:
            if cur_rank == 0 and cap_rank >= 1 and last_overall >= 8.0:
                new_rank = 1
            elif cur_rank == 1 and cap_rank >= 2 and last_overall >= 9.0:
                new_rank = 2

        if new_rank != cur_rank:
            session.difficulty_current = self._rank_to_difficulty(new_rank)
            self._reset_streaks(session)
            db.add(session)
            db.commit()
            db.refresh(session)

    def _is_behavioral(self, q: Question) -> bool:
        try:
            return "behavioral" in set(q.tags())
        except Exception:
            return False

    def _company_name(self, company_style: str) -> str:
        if not company_style or company_style == "general":
            return "this company"
        return company_style[:1].upper() + company_style[1:]

    def _render_text(self, session: InterviewSession, text: str) -> str:
        company = self._company_name(session.company_style)
        return (
            (text or "")
            .replace("{company}", company)
            .replace("X company", company)
            .replace("X Company", company)
        )

    def _render_question(self, session: InterviewSession, q: Question) -> tuple[str, str]:
        return self._render_text(session, q.title), self._render_text(session, q.prompt)

    def _user_name_safe(self, name: str | None) -> str:
        if not name:
            return ""
        return name.strip()

    def _is_move_on(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = ["move on", "next question", "skip", "pass", "go next", "next please", "next pls"]
        return any(k in t for k in keywords)

    def _is_dont_know(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = ["don't know", "dont know", "do not know", "no idea", "not sure", "i dunno", "unsure"]
        return any(k in t for k in keywords)

    def _is_non_informative(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return True
        short = {"ok", "okay", "k", "kk", "sure", "yeah", "yep", "alright", "cool", "fine", "thanks"}
        return t in short or len(t.split()) <= 2

    def _is_vague(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return True
        words = t.split()
        return len(words) < 6

    def _normalize_text(self, text: str | None) -> str:
        return " ".join((text or "").lower().split())

    def _sanitize_ai_text(self, text: str | None) -> str:
        if not text:
            return ""
        replacements = {
            "\u2019": "'",
            "\u2018": "'",
            "\u201c": "\"",
            "\u201d": "\"",
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
            ["approach", "algorithm", "strategy", "plan", "idea", "i would", "we can", "i will", "i can", "use a", "use an"],
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

    def _prioritize_missing_focus(self, missing: list[str], session: InterviewSession) -> list[str]:
        if not missing:
            return []
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
        elif weakest == "problem_solving":
            prefer = "approach"
        elif weakest == "communication":
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

        bridge = "Let's move to the next question."
        if focus_line:
            return f"{lead} {focus_line} {bridge}"
        return f"{lead} {bridge}"

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
            if t.endswith(("?", ".", "!", ":")):
                return f"{t} {p}"
            return f"{t}. {p}"
        return t or p

    def _pick_warmup_behavioral_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        warmup_id = self._warmup_behavioral_question_id(session)
        if warmup_id:
            asked_ids.add(warmup_id)
        seen = self._seen_question_subquery(session)

        def choose(company_style: str, track: str) -> Question | None:
            base = db.query(Question).filter(
                Question.company_style == company_style,
                Question.track == track,
                Question.tags_csv.ilike("%behavioral%"),
            )
            if asked_ids:
                base = base.filter(~Question.id.in_(asked_ids))
            unseen = base.filter(~Question.id.in_(seen)).order_by(func.random()).first()
            if unseen:
                return unseen
            return base.order_by(func.random()).first()

        company = (session.company_style or "").strip().lower() or "general"
        track = (session.track or "").strip()
        choices: list[tuple[str, str]] = []
        if company != "general":
            if track:
                choices.append((company, track))
            choices.append((company, "behavioral"))
            if track:
                choices.append(("general", track))
        choices.append(("general", "behavioral"))

        for company_style, track_val in choices:
            if not track_val:
                continue
            q = choose(company_style, track_val)
            if q:
                return q

        base = db.query(Question).filter(Question.tags_csv.ilike("%behavioral%"))
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
            try:
                self._set_warmup_behavioral_question_id(db, session, q.id)
            except Exception:
                pass
            title, prompt = self._render_question(session, q)
            return self._combine_question_text(title, prompt), q.id

        return self._fallback_warmup_behavioral_question(session), None

    def _warmup_behavioral_reply(self, session: InterviewSession, focus: dict[str, Any], question_text: str) -> str:
        focus_line = self._warmup_focus_line(focus)
        question = question_text or self._fallback_warmup_behavioral_question(session)
        parts = ["I am doing well.", "Today I am your interviewer."]
        if focus_line:
            parts.append(focus_line)
        parts.append(f"Let's start with a quick behavioral question: {question}")
        return " ".join(parts).strip()

    def _warmup_behavioral_ack(self, student_text: str | None = None) -> str:
        if student_text and student_text.strip():
            return "Thanks for sharing. Let's move into the technical interview."
        return "Thanks. Let's move into the technical interview."

    def _mark_warmup_behavioral_asked(self, db: Session, session: InterviewSession, question_id: int | None = None) -> None:
        qid = question_id or self._warmup_behavioral_question_id(session)
        if not qid:
            return
        try:
            session_question_crud.mark_question_asked(db, session.id, int(qid))
        except Exception:
            pass
        try:
            user_question_seen_crud.mark_question_seen(db, session.user_id, int(qid))
        except Exception:
            pass

    def _last_interviewer_message(self, db: Session, session_id: int) -> str | None:
        msgs = message_crud.list_messages(db, session_id, limit=200)
        for m in reversed(msgs):
            if m.role == "interviewer":
                return m.content
        return None

    async def _warmup_prompt(self, session: InterviewSession, user_name: str | None = None) -> str:
        sys = warmup_system_prompt(session.company_style, session.role)
        user = warmup_prompt_user_prompt(user_name)
        try:
            reply = await self.llm.chat(sys, user)
        except LLMClientError:
            reply = interview_warmup.prompt_for_step(0, user_name=user_name) or "Hi! Ready to begin?"
        return self._sanitize_ai_text(reply)

    async def _warmup_reply(
        self,
        session: InterviewSession,
        student_text: str,
        user_name: str | None,
        focus: dict[str, Any],
        db: Session,
    ) -> str:
        sys = warmup_system_prompt(session.company_style, session.role)
        focus_line = self._warmup_focus_line(focus) or None
        behavioral_question, qid = self._warmup_behavioral_question(db, session)
        user = warmup_reply_user_prompt(
            candidate_text=student_text,
            user_name=user_name,
            behavioral_question=behavioral_question,
            focus_line=focus_line,
        )
        try:
            reply = await self.llm.chat(sys, user)
            reply = self._sanitize_ai_text(reply)
        except LLMClientError:
            reply = ""

        if not reply:
            self._mark_warmup_behavioral_asked(db, session, qid)
            return self._warmup_behavioral_reply(session, focus, behavioral_question)

        lower = reply.lower()
        has_doing_well = "i am doing well" in lower
        has_interviewer = "today i am your interviewer" in lower
        has_question = behavioral_question.lower() in lower
        if not (has_doing_well and has_interviewer and has_question):
            self._mark_warmup_behavioral_asked(db, session, qid)
            return self._warmup_behavioral_reply(session, focus, behavioral_question)
        self._mark_warmup_behavioral_asked(db, session, qid)
        return reply

    def _behavioral_target(self, session: InterviewSession) -> int:
        try:
            raw = int(getattr(session, "behavioral_questions_target", 2) or 0)
        except Exception:
            raw = 2
        return max(0, min(3, raw))

    def _behavioral_slots(self, max_questions: int, target: int) -> set[int]:
        """
        Pick which question numbers (1-indexed) should be behavioral.

        Design goals:
        - Never ask behavioral as Q1.
        - For target=2 (default), keep the familiar Q3/Q5 pattern.
        - For target=3, place them early enough to usually fit within 5 questions.
        """
        target = max(0, min(3, int(target or 0)))
        max_questions = max(1, int(max_questions or 7))
        if target == 0 or max_questions < 2:
            return set()

        if target == 1:
            preferred = [3, 4, 2, 5, 6, 7]
        elif target == 2:
            preferred = [3, 5, 2, 4, 6, 7]
        else:
            preferred = [2, 4, 5, 3, 6, 7]

        slots: list[int] = []
        for pos in preferred:
            if 2 <= pos <= max_questions and pos not in slots:
                slots.append(pos)
            if len(slots) >= target:
                break

        if len(slots) < target:
            for pos in range(2, max_questions + 1):
                if pos not in slots:
                    slots.append(pos)
                if len(slots) >= target:
                    break

        return set(slots)

    def _seen_question_subquery(self, session: InterviewSession):
        return select(UserQuestionSeen.question_id).where(UserQuestionSeen.user_id == session.user_id)

    def _offline_intro(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        followup = ""
        if isinstance(getattr(q, "followups", None), list) and q.followups:
            followup = f"\n\nFollow-up: {q.followups[0]}"
        greeting = f"Hi {user_name}," if user_name else "Hi!"
        if self._is_behavioral(q):
            body = (
                f"{greeting} I'm your interviewer.\n\n"
                "We'll start with a behavioral question.\n\n"
                f"{q.title}. {q.prompt}\n\n"
                "Answer using STAR (Situation, Task, Action, Result)."
                f"{followup}"
            )
            if preface:
                return f"{preface}\n\n{body}"
            return body

        body = (
            f"{greeting} I'm your interviewer.\n\n"
            "Please restate the problem and clarify constraints. Start with a brief plan and key steps, then share "
            "complexity, edge cases, and how you'd validate correctness.\n\n"
            f"{q.title}. {q.prompt}"
            f"{followup}"
        )
        if preface:
            return f"{preface}\n\n{body}"
        return body

    def _offline_next_question(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        followup = ""
        if isinstance(getattr(q, "followups", None), list) and q.followups:
            followup = f"\n\nFollow-up: {q.followups[0]}"
        name_part = f"{user_name}, " if user_name else ""
        if self._is_behavioral(q):
            body = (
                f"Alright {name_part}let's do a behavioral question.\n\n"
                f"{q.title}. {q.prompt}\n\n"
                "Answer using STAR (Situation, Task, Action, Result)."
                f"{followup}"
            )
            if preface:
                return f"{preface}\n\n{body}"
            return body

        body = (
            f"Alright {name_part}let's move to the next question.\n\n"
            "Please restate the problem and clarify constraints. Start with a brief plan and key steps, then share "
            "complexity, edge cases, and how you'd validate correctness.\n\n"
            f"{q.title}. {q.prompt}"
            f"{followup}"
        )
        if preface:
            return f"{preface}\n\n{body}"
        return body

    def _reset_for_new_question(self, db: Session, session: InterviewSession, question_id: int) -> None:
        session_crud.set_current_question(db, session, question_id)
        session.followups_used = 0
        session.stage = "question"
        db.add(session)
        db.commit()
        db.refresh(session)

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
        return int(session.questions_asked_count or 0) >= int(session.max_questions or 3)

    def _max_followups_reached(self, session: InterviewSession) -> bool:
        return int(session.followups_used or 0) >= int(session.max_followups_per_question or 2)

    def _session_asked_state(self, db: Session, session: InterviewSession) -> tuple[set[int], list[Question], set[str], int]:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        warmup_id = self._warmup_behavioral_question_id(session)
        if warmup_id:
            asked_ids.add(warmup_id)
        asked_questions: list[Question] = []
        used_tags: set[str] = set()
        behavioral_used = 0

        if asked_ids:
            asked_questions = db.query(Question).filter(Question.id.in_(asked_ids)).all()
            for aq in asked_questions:
                tags = self._tag_set(aq)
                used_tags.update(tags)
                if "behavioral" in tags and aq.id != warmup_id:
                    behavioral_used += 1

        return asked_ids, asked_questions, used_tags, behavioral_used

    def _tag_set(self, q: Question) -> set[str]:
        try:
            tags = q.tags()
        except Exception:
            tags = []
        return {str(t).strip().lower() for t in tags if str(t).strip()}

    def _last_asked_technical_tags(self, db: Session, session: InterviewSession) -> set[str]:
        rows = (
            db.query(Question)
            .join(SessionQuestion, SessionQuestion.question_id == Question.id)
            .filter(SessionQuestion.session_id == session.id)
            .order_by(SessionQuestion.id.desc())
            .limit(10)
            .all()
        )
        for q in rows:
            tags = self._tag_set(q)
            if "behavioral" in tags:
                continue
            if tags:
                return tags
        return set()

    def _pick_next_behavioral_question(self, db: Session, session: InterviewSession, asked_ids: set[int]) -> Question | None:
        base = db.query(Question).filter(
            Question.tags_csv.ilike("%behavioral%"),
            Question.company_style.in_([session.company_style, "general"]),
            Question.track.in_([session.track, "behavioral"]),
        )
        if asked_ids:
            base = base.filter(~Question.id.in_(asked_ids))
        # No difficulty filter for behavioral.
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
        used_tags: set[str],
    ) -> Question | None:
        seen = self._seen_question_subquery(session)
        weakness = self._weakest_dimension(session)
        weakness_keywords = self._weakness_keywords(weakness)
        focus_tags = self._focus_tags(session)
        last_tags = self._last_asked_technical_tags(db, session)

        def choose_from_pool(pool: list[Question]) -> Question:
            if not pool:
                raise ValueError("empty pool")

            # For the first question, pick uniformly at random for variety.
            if not asked_ids:
                return random.choice(pool)

            weak_scores = {cand.id: self._weakness_score(cand, weakness_keywords) for cand in pool} if weakness_keywords else {}
            best_weak = max(weak_scores.values(), default=0)
            targeted = [c for c in pool if weak_scores.get(c.id, 0) == best_weak] if best_weak > 0 else pool

            if focus_tags:
                focus_scores = {}
                for cand in targeted:
                    cand_tags = self._tag_set(cand)
                    focus_scores[cand.id] = len(cand_tags & focus_tags)
                best_focus = max(focus_scores.values(), default=0)
                if best_focus > 0:
                    targeted = [c for c in targeted if focus_scores.get(c.id, 0) == best_focus]

            if last_tags:
                overlap_scores = {}
                for cand in targeted:
                    cand_tags = self._tag_set(cand)
                    overlap_scores[cand.id] = len(cand_tags & last_tags)
                min_overlap = min(overlap_scores.values(), default=0)
                filtered = [c for c in targeted if overlap_scores.get(c.id, 0) == min_overlap]
                if filtered:
                    targeted = filtered

            best_div = -1
            best: list[Question] = []
            for cand in targeted:
                cand_tags = self._tag_set(cand)
                div = len(cand_tags - used_tags)
                if div > best_div:
                    best_div = div
                    best = [cand]
                elif div == best_div:
                    best.append(cand)
            return random.choice(best) if best else random.choice(targeted)

        # Try company-specific first, with adaptive difficulty order.
        for diff in self._adaptive_difficulty_try_order(session):
            base = db.query(Question).filter(
                Question.track == session.track,
                Question.company_style == session.company_style,
                Question.difficulty == diff,
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            if asked_ids:
                base = base.filter(~Question.id.in_(asked_ids))

            pool = base.filter(~Question.id.in_(seen)).all()
            if not pool:
                # Fall back to allowing repeats across sessions (still no repeats within this session).
                pool = base.all()
            if pool:
                return choose_from_pool(pool)

        # Fallback to general style for technical questions (still prefer unseen for this user)
        for diff in self._adaptive_difficulty_try_order(session):
            base2 = db.query(Question).filter(
                Question.track == session.track,
                Question.company_style == "general",
                Question.difficulty == diff,
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            if asked_ids:
                base2 = base2.filter(~Question.id.in_(asked_ids))
            q2 = base2.filter(~Question.id.in_(seen)).order_by(func.random()).first()
            if q2:
                return q2
            q2b = base2.order_by(func.random()).first()
            if q2b:
                return q2b

        return None

    def _pick_next_main_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids, _asked_questions, used_tags, behavioral_used = self._session_asked_state(db, session)

        behavioral_target = self._behavioral_target(session)
        next_num = int(session.questions_asked_count or 0) + 1
        behavioral_slots = self._behavioral_slots(int(session.max_questions or 7), behavioral_target)
        behavioral_slot = next_num in behavioral_slots

        if behavioral_slot and behavioral_used < behavioral_target:
            q_b = self._pick_next_behavioral_question(db, session, asked_ids)
            if q_b:
                return q_b

        q_t = self._pick_next_technical_question(db, session, asked_ids, used_tags)
        if q_t:
            return q_t

        # If technical pool is empty, try behavioral as a fallback (even if target is 0)
        # so the interview doesn't stall due to missing datasets.
        q_b2 = self._pick_next_behavioral_question(db, session, asked_ids)
        if q_b2:
            return q_b2

        diff = getattr(session, "difficulty_current", None) or session.difficulty
        return question_crud.pick_next_question(db, session.track, session.company_style, diff)

    async def _ask_new_main_question(
        self,
        db: Session,
        session: InterviewSession,
        q: Question,
        history: list[dict],
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        sys = interviewer_system_prompt(session.company_style, session.role)
        title, prompt = self._render_question(session, q)
        name_hint = user_name or "name unavailable"
        if self._is_behavioral(q):
            user = f"""
Move to the next question.
This is a behavioral question. Ask it clearly and ask the candidate to answer using STAR (Situation, Task, Action, Result).
Greet the candidate by name if provided ({name_hint}).
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {title}. {prompt}
""".strip()
        else:
            user = f"""
Move to the next question.
Briefly introduce the problem and ask the candidate to clarify constraints.
Ask for a brief plan and key steps, then complexity, edge cases, and how they would validate correctness.
Greet the candidate by name if provided ({name_hint}).
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {title}. {prompt}
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
        try:
            self._maybe_bump_difficulty_current(db, session)
        except Exception:
            pass

        next_q = self._pick_next_main_question(db, session)
        if not next_q:
            wrap = "No more questions available. Click Finalize to get your score."
            message_crud.add_message(db, session.id, "interviewer", wrap)
            session_crud.update_stage(db, session, "wrapup")
            return wrap

        self._reset_for_new_question(db, session, next_q.id)
        session_question_crud.mark_question_asked(db, session.id, next_q.id)
        try:
            user_question_seen_crud.mark_question_seen(db, session.user_id, next_q.id)
        except Exception:
            pass
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
            msg = self._warmup_behavioral_reply(session, focus, question_text)
            message_crud.add_message(db, session.id, "interviewer", msg)
            self._mark_warmup_behavioral_asked(db, session, qid)
            return msg

        # Warmup greeting (only when at intro/warmup stage)
        if not warm_done and (stage in (None, "", "intro", "warmup")) and stage != "warmup_done":
            if warm_step <= 0:
                msg = None
                try:
                    msg = await self._warmup_prompt(session, user_name=user_name)
                except Exception:
                    msg = None
                if not msg:
                    msg = interview_warmup.prompt_for_step(0, user_name=user_name)
                if msg:
                    message_crud.add_message(db, session.id, "interviewer", msg)
                    interview_warmup.set_state(db, session, 1, False)
                    session_crud.update_stage(db, session, "warmup")
                    return msg

            last = self._last_interviewer_message(db, session.id)
            if last:
                return last

        if session.questions_asked_count == 0 or session.current_question_id is None:
            q = self._pick_next_main_question(db, session)
            if not q:
                msg = "No questions found for this track/style/difficulty. Please ask admin to load questions."
                message_crud.add_message(db, session.id, "system", msg)
                return msg

            self._reset_for_new_question(db, session, q.id)
            session_question_crud.mark_question_asked(db, session.id, q.id)
            try:
                user_question_seen_crud.mark_question_seen(db, session.user_id, q.id)
            except Exception:
                pass
            self._increment_questions_asked(db, session)

            sys = interviewer_system_prompt(session.company_style, session.role)
            title, prompt = self._render_question(session, q)
            if self._is_behavioral(q):
                user = f"""
Start the interview with a short greeting.
Transition into the first behavioral question. Greet the candidate by name if available ({user_name or "name unavailable"}).
Ask the candidate to answer using STAR (Situation, Task, Action, Result). Keep it conversational and concise.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {title}. {prompt}
""".strip()
            else:
                user = f"""
Start the interview with a short greeting.
Ask the candidate to restate the problem and clarify constraints, then start with a brief plan and key steps.
Ask them to cover complexity, edge cases, and how they would validate correctness.
Greet the candidate by name if available ({user_name or "name unavailable"}). Keep it concise and friendly.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {title}. {prompt}
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
        message_crud.add_message(db, session.id, "interviewer", reply)
        session_crud.update_stage(db, session, "candidate_solution")
        return reply

    async def handle_student_message(self, db: Session, session: InterviewSession, student_text: str, user_name: str | None = None) -> str:
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
        if stage == "warmup_behavioral" and not warm_done:
            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                try:
                    self._store_focus(db, session, focus)
                except Exception:
                    pass
            preface = self._warmup_behavioral_ack(student_text)
            interview_warmup.set_state(db, session, max(warm_step, 2), True)
            session_crud.update_stage(db, session, "warmup_done")
            return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=preface)

        if not warm_done and (stage in (None, "", "intro", "warmup")) and stage != "warmup_done":
            # Warmup flow: greet, then ask one behavioral question before the technical interview.
            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                try:
                    self._store_focus(db, session, focus)
                except Exception:
                    pass

            if warm_step <= 0:
                msg = await self._warmup_prompt(session, user_name=user_name)
                message_crud.add_message(db, session.id, "interviewer", msg)
                interview_warmup.set_state(db, session, 1, False)
                session_crud.update_stage(db, session, "warmup")
                return msg

            msg = await self._warmup_reply(
                session=session,
                student_text=student_text,
                user_name=user_name,
                focus=focus,
                db=db,
            )
            message_crud.add_message(db, session.id, "interviewer", msg)
            interview_warmup.set_state(db, session, max(warm_step, 2), False)
            session_crud.update_stage(db, session, "warmup_behavioral")
            return msg

        q = question_crud.get_question(db, session.current_question_id) if session.current_question_id else None
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

        sys = interviewer_system_prompt(session.company_style, session.role)

        stage = session.stage or "intro"
        max_followups = int(session.max_followups_per_question or 2)
        max_questions = int(session.max_questions or 7)
        min_questions = 5

        if not q:
            return await self.ensure_question_and_intro(db, session, user_name=user_name)

        if stage in ("followups", "candidate_solution") and self._max_followups_reached(session):
            stage = "next_question"

        # Human-like handling before invoking the controller
        if self._is_move_on(student_text) or self._is_dont_know(student_text):
            reason = "move_on" if self._is_move_on(student_text) else "dont_know"
            preface = self._transition_preface(session, reason=reason)
            session_crud.update_stage(db, session, "next_question")
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        if self._is_non_informative(student_text):
            reply = "I'll need a fuller response. Please outline your approach, key steps, and any assumptions."
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if self._is_vague(student_text):
            reply = "Can you add more detail on your approach, complexity, and edge cases? A few sentences would help."
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if stage == "next_question":
            preface = self._transition_preface(session)
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        signals = self._candidate_signals(student_text)
        behavioral_missing = self._behavioral_missing_parts(student_text) if self._is_behavioral(q) else []
        missing_keys = self._missing_focus_keys(q, signals, behavioral_missing)
        missing_keys = self._prioritize_missing_focus(missing_keys, session)
        last_overall = self._skill_last_overall(session)
        if (
            last_overall is not None
            and last_overall >= 8.0
            and not self._is_behavioral(q)
            and "tradeoffs" not in missing_keys
            and not signals.get("mentions_tradeoffs")
        ):
            missing_keys = ["tradeoffs"] + missing_keys

        missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)
        signal_summary = self._signal_summary(signals, missing_keys, behavioral_missing)
        skill_summary = self._skill_summary(session)

        if int(session.followups_used or 0) == 0 and not self._max_followups_reached(session):
            targeted = None
            if self._is_behavioral(q) and behavioral_missing:
                targeted = self._missing_focus_question("star", behavioral_missing)
            elif signals.get("has_code") and not signals.get("mentions_approach"):
                targeted = "Thanks for the code. Walk me through your approach and key steps."
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

        ctrl_sys = interviewer_controller_system_prompt(session.company_style, session.role)
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
            is_behavioral=self._is_behavioral(q),
        )

        try:
            data = await self.llm.chat_json(ctrl_sys, ctrl_user, history=history)
            ctrl = InterviewControllerOutput.model_validate(data)
            action = ctrl.action
            message = self._sanitize_ai_text((ctrl.message or "").strip())
            done_with_question = bool(ctrl.done_with_question)
            allow_second_followup = bool(ctrl.allow_second_followup)
            quick_rubric_raw = ctrl.quick_rubric.model_dump()
        except Exception:
            action = ""
            message = ""
            done_with_question = False
            allow_second_followup = False
            quick_rubric_raw = None

        # Store rolling rubric (used later for adaptive difficulty and weakness targeting).
        if student_text and student_text.strip():
            try:
                self._update_skill_state(db, session, quick_rubric_raw, is_behavioral=self._is_behavioral(q))
            except Exception:
                pass

        if not message:
            if isinstance(getattr(q, "followups", None), list) and q.followups:
                idx = int(session.followups_used or 0)
                if 0 <= idx < len(q.followups):
                    message = self._render_text(session, str(q.followups[idx]).strip())

        if not message:
            message = self._phase_followup(
                q,
                signals,
                session,
                int(session.followups_used or 0),
            ) or ""

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

        if done_with_question and action not in ("WRAP_UP",):
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
