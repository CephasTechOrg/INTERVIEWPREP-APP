"""
Follow-up Logic Module for Interview Engine.

Handles follow-up decision making, focus identification, and follow-up question generation.
"""

from app.models.question import Question
from app.models.interview_session import InterviewSession
from app.services.interview_engine_quality import InterviewEngineQuality


class InterviewEngineFollowups(InterviewEngineQuality):
    """Follow-up decision and generation logic."""

    def _missing_focus_keys(self, q: Question, signals: dict[str, bool], behavioral_missing: list[str]) -> list[str]:
        """Identify which focus areas are missing from the response."""
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
        """Extract focus areas from question metadata."""
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
        """Prioritize missing focus areas by importance and session state."""
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
        """Generate a summary of missing focus areas."""
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
        """Categorize missing focus into critical and optional tiers."""
        if not missing:
            return ([], [])
        if is_behavioral:
            critical = [k for k in missing if k == "star"] if len(behavioral_missing) >= 3 else []
            optional = [k for k in missing if k not in critical]
            return (critical, optional)
        critical = [k for k in missing if k in ("approach", "correctness")]
        optional = [k for k in missing if k not in critical]
        return (critical, optional)

    def _missing_from_coverage(self, coverage: dict, is_behavioral: bool) -> list[str]:
        """Extract missing items from coverage dict."""
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
        """Normalize free-form focus key to canonical form."""
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
        """Generate a gentle prompt asking the candidate to elaborate on missing focus."""
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
        """Generate a targeted follow-up question for a specific missing focus area."""
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
        """Generate a phase-based follow-up prompt based on response signals."""
        if self._is_behavioral(q) or self._is_conceptual_question(q):
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
        if signals.get("has_code") and not signals.get("mentions_tests"):
            return "What tests would you run to validate your solution?"
        if not signals.get("mentions_correctness"):
            return "Why is your approach correct? Any invariant you rely on?"

        return None
