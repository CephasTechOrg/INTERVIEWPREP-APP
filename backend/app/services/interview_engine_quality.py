"""
Quality Assessment Module for Interview Engine.

Handles response evaluation, weakness detection, and skill/signal summaries.
"""

from app.models.interview_session import InterviewSession
from app.services.interview_engine_rubric import InterviewEngineRubric


class InterviewEngineQuality(InterviewEngineRubric):
    """Quality assessment and response evaluation methods."""

    def _response_quality(
        self,
        text: str | None,
        signals: dict[str, bool],
        is_behavioral: bool,
        behavioral_missing: list[str],
        is_conceptual: bool = False,
    ) -> str:
        """Assess response quality - but don't penalize clarifications."""
        # Clarification requests are neutral quality
        if self._is_clarification_request(text or ""):
            return "ok"
        
        tokens = self._clean_tokens(text)
        if is_conceptual:
            if len(tokens) < 8:
                return "weak"
            if len(tokens) >= 25:
                return "strong"
            return "ok"
        if len(tokens) < 8:
            return "weak"
        if is_behavioral:
            if len(behavioral_missing) >= 3:
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

    def _signal_summary(self, signals: dict[str, bool], missing: list[str], behavioral_missing: list[str]) -> str:
        """Generate a summary of signals and missing focus items."""
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
            f"mentions_tests={signals.get('mentions_tests', False)}",
        ]
        summary = "; ".join(bits)
        missing_summary = self._missing_focus_summary(missing, behavioral_missing)
        if missing_summary:
            summary = f"{summary}; missing={missing_summary}"
        return summary

    def _skill_summary(self, session: InterviewSession) -> str:
        """Generate a summary of current skill state and focus."""
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
