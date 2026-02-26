"""
Interview Engine Rubric Module

Rubric scoring and skill state management including:
- Rolling EMA (exponential moving average) rubric tracking
- Difficulty ranking and adaptation
- Weakness detection and gap identification (Phase 4-5)
- Skill streak tracking for performance patterns

This module depends on InterviewEngineSignals for signal detection.
CRITICAL: Contains Phase 4 (smart follow-ups) and Phase 5 (weakness-targeted questions) logic.
"""

import contextlib
from typing import Any

from sqlalchemy.orm import Session

from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services.interview_engine_signals import InterviewEngineSignals


class InterviewEngineRubric(InterviewEngineSignals):
    """Rubric scoring and skill state management."""

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
        """Convert difficulty string to numeric rank."""
        d = (difficulty or "").strip().lower()
        if d == "hard":
            return 2
        if d == "medium":
            return 1
        return 0

    def _rank_to_difficulty(self, rank: int) -> str:
        """Convert numeric rank back to difficulty string."""
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
        """Get overall skill score from last assessment."""
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
        """Get current skill streak counts (good, weak)."""
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
        """Reset good/weak streaks to zero."""
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
        """Identify weakest rubric dimension using EMA or overall average."""
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
        Used by Phase 4 (smart follow-ups) to identify weak areas needing reinforcement.
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
        Used by Phase 5 (weakness-targeted questions) to steer toward weak areas.
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
        """Get keywords associated with a rubric weakness dimension."""
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
        """Score how well a question addresses weakness keywords."""
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
