from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QuickRubric(BaseModel):
    communication: int = Field(default=5, ge=0, le=10)
    problem_solving: int = Field(default=5, ge=0, le=10)
    correctness_reasoning: int = Field(default=5, ge=0, le=10)
    complexity: int = Field(default=5, ge=0, le=10)
    edge_cases: int = Field(default=5, ge=0, le=10)

    @field_validator("*", mode="before")
    @classmethod
    def _clamp_score(cls, v):  # noqa: ANN001
        if v is None:
            n = 5
        else:
            try:
                n = int(float(v))
            except Exception:
                n = 5
        return max(0, min(10, n))


InterviewAction = Literal["ASK_MAIN_QUESTION", "FOLLOWUP", "MOVE_TO_NEXT_QUESTION", "WRAP_UP"]
InterviewIntent = Literal["CLARIFY", "DEEPEN", "CHALLENGE", "ADVANCE", "WRAP_UP"]

WarmupTone = Literal["positive", "neutral", "negative", "stressed", "excited", "tired"]
WarmupEnergy = Literal["low", "medium", "high"]


def _normalize_tone(raw) -> str:  # noqa: ANN001
    if raw is None:
        return "neutral"
    key = str(raw).strip().lower()
    if not key:
        return "neutral"
    mapping = {
        "positive": "positive",
        "happy": "positive",
        "good": "positive",
        "great": "positive",
        "neutral": "neutral",
        "ok": "neutral",
        "okay": "neutral",
        "fine": "neutral",
        "negative": "negative",
        "sad": "negative",
        "down": "negative",
        "upset": "negative",
        "stressed": "stressed",
        "anxious": "stressed",
        "nervous": "stressed",
        "overwhelmed": "stressed",
        "excited": "excited",
        "pumped": "excited",
        "energized": "excited",
        "tired": "tired",
        "sleepy": "tired",
        "exhausted": "tired",
    }
    return mapping.get(key, "neutral")


def _normalize_energy(raw) -> str:  # noqa: ANN001
    if raw is None:
        return "medium"
    key = str(raw).strip().lower()
    if not key:
        return "medium"
    mapping = {
        "low": "low",
        "low energy": "low",
        "tired": "low",
        "sleepy": "low",
        "medium": "medium",
        "mid": "medium",
        "moderate": "medium",
        "high": "high",
        "high energy": "high",
        "energetic": "high",
        "excited": "high",
        "pumped": "high",
    }
    return mapping.get(key, "medium")


class WarmupToneProfile(BaseModel):
    tone: WarmupTone = Field(default="neutral")
    energy: WarmupEnergy = Field(default="medium")
    confidence: float = Field(default=0.6, ge=0, le=1)

    @field_validator("tone", mode="before")
    @classmethod
    def _coerce_tone(cls, v):  # noqa: ANN001
        return _normalize_tone(v)

    @field_validator("energy", mode="before")
    @classmethod
    def _coerce_energy(cls, v):  # noqa: ANN001
        return _normalize_energy(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v):  # noqa: ANN001
        if v is None:
            return 0.6
        try:
            n = float(v)
        except Exception:
            return 0.6
        return max(0.0, min(1.0, n))


class WarmupSmalltalkProfile(WarmupToneProfile):
    topic: str = Field(default="")
    smalltalk_question: str = Field(default="")


UserIntent = Literal[
    "answering",           # User is providing an answer to the question
    "clarification",       # User wants question repeated/clarified
    "move_on",            # User wants to skip/move to next question
    "dont_know",          # User doesn't know the answer
    "thinking",           # User is thinking through the problem
    "greeting",           # User is greeting/small talk
]


class UserIntentClassification(BaseModel):
    """AI-powered classification of user's intent."""
    intent: UserIntent = Field(default="answering")
    confidence: float = Field(default=0.6, ge=0, le=1)
    reasoning: str = Field(default="")
    
    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v):  # noqa: ANN001
        if v is None:
            return 0.6
        try:
            n = float(v)
        except Exception:
            return 0.6
        return max(0.0, min(1.0, n))

    @field_validator("reasoning", mode="before")
    @classmethod
    def _coerce_reasoning(cls, v):  # noqa: ANN001
        if v is None:
            return ""
        return str(v).strip()


_FOCUS_KEYS = {
    "approach",
    "constraints",
    "correctness",
    "complexity",
    "edge_cases",
    "tradeoffs",
    "star",
    "impact",
}


def _normalize_focus_key(raw) -> str | None:  # noqa: ANN001
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if not key:
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
    if key in mapping:
        return mapping[key]
    if key in _FOCUS_KEYS:
        return key
    return None


class InterviewControllerOutput(BaseModel):
    action: InterviewAction
    message: str = ""
    done_with_question: bool = False
    allow_second_followup: bool = False
    quick_rubric: QuickRubric = Field(default_factory=QuickRubric)
    intent: str | None = None
    confidence: float = Field(default=0.6, ge=0, le=1)
    next_focus: str | None = None
    coverage: dict[str, bool] = Field(default_factory=dict)
    missing_focus: list[str] = Field(default_factory=list)

    @field_validator("action", mode="before")
    @classmethod
    def _normalize_action(cls, v):  # noqa: ANN001
        return str(v).strip().upper()

    @field_validator("message", mode="before")
    @classmethod
    def _coerce_message(cls, v):  # noqa: ANN001
        if v is None:
            return ""
        return str(v)

    @field_validator("intent", mode="before")
    @classmethod
    def _normalize_intent(cls, v):  # noqa: ANN001
        if v is None:
            return None
        raw = str(v).strip().upper()
        if raw in InterviewIntent.__args__:
            return raw
        return None

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v):  # noqa: ANN001
        if v is None:
            return 0.6
        try:
            n = float(v)
        except Exception:
            return 0.6
        return max(0.0, min(1.0, n))

    @field_validator("next_focus", mode="before")
    @classmethod
    def _coerce_next_focus(cls, v):  # noqa: ANN001
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("coverage", mode="before")
    @classmethod
    def _coerce_coverage(cls, v):  # noqa: ANN001
        if v is None:
            return {}
        if isinstance(v, dict):
            out: dict[str, bool] = {}
            for key, val in v.items():
                nk = _normalize_focus_key(key)
                if nk:
                    out[nk] = bool(val)
            return out
        if isinstance(v, list):
            out = {}
            for item in v:
                nk = _normalize_focus_key(item)
                if nk:
                    out[nk] = True
            return out
        if isinstance(v, str):
            nk = _normalize_focus_key(v)
            return {nk: True} if nk else {}
        return {}

    @field_validator("missing_focus", mode="before")
    @classmethod
    def _coerce_missing_focus(cls, v):  # noqa: ANN001
        if v is None:
            return []
        items = v if isinstance(v, list) else [v]
        out: list[str] = []
        for item in items:
            nk = _normalize_focus_key(item)
            if nk and nk not in out:
                out.append(nk)
        return out


class EvaluationOutput(BaseModel):
    overall_score: int = Field(default=50, ge=0, le=100)
    rubric: QuickRubric = Field(default_factory=QuickRubric)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

    @field_validator("overall_score", mode="before")
    @classmethod
    def _coerce_overall_score(cls, v):  # noqa: ANN001
        if v is None:
            n = 50
        else:
            try:
                n = int(float(v))
            except Exception:
                n = 50
        return max(0, min(100, n))

    @field_validator("strengths", "weaknesses", "next_steps", mode="before")
    @classmethod
    def _coerce_str_list(cls, v):  # noqa: ANN001
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            out: list[str] = []
            for item in v:
                s = str(item).strip()
                if s:
                    out.append(s)
            return out
        return []
