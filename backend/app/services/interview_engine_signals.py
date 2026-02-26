"""
Interview Engine Signals Module

Signal detection for candidate responses including:
- Question type classification (behavioral, coding, conceptual, system_design)
- Response content signals (code, complexity, edge cases, etc.)
- Response quality assessment (thin, vague, off-topic)
- Behavioral STAR element detection

This module depends on InterviewEngineUtils for text processing utilities.
"""

from app.models.question import Question
from app.services.interview_engine_utils import InterviewEngineUtils


class InterviewEngineSignals(InterviewEngineUtils):
    """Signal detection methods for interview responses and questions."""

    def _is_behavioral(self, q: Question) -> bool:
        """Check if question is behavioral."""
        try:
            if str(getattr(q, "question_type", "")).strip().lower() == "behavioral":
                return True
            return "behavioral" in set(q.tags())
        except Exception:
            return False

    def _is_system_design_question(self, q: Question) -> bool:
        """Check if question is system design."""
        try:
            tags = {t.strip().lower() for t in (q.tags() or []) if str(t).strip()}
            return bool(tags & self._SYSTEM_DESIGN_TAGS)
        except Exception:
            return False

    def _is_coding_question(self, q: Question) -> bool:
        """Check if question is coding."""
        qt = self._question_type(q)
        return qt == "coding"

    def _is_off_topic(self, q: Question, text: str | None, signals: dict[str, bool]) -> bool:
        """Check if response is off-topic relative to question."""
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

    def _candidate_signals(self, text: str | None) -> dict[str, bool]:
        """Extract all signals from candidate response."""
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

    def _missing_focus_keys(self, q: Question, signals: dict[str, bool], behavioral_missing: list[str]) -> list[str]:
        """Determine what focus areas are missing from response."""
        if self._is_conceptual_question(q):
            return []
        if self._is_behavioral(q):
            missing = []
            if len(behavioral_missing) >= 3:
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
        """Extract focus keys from question evaluation_focus column."""
        raw = getattr(q, "evaluation_focus", None) or []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            key = self._normalize_focus_key(str(item))
            if key and key not in out:
                out.append(key)
        return out
