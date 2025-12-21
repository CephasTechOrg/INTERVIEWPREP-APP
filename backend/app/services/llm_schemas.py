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


class InterviewControllerOutput(BaseModel):
    action: InterviewAction
    message: str = ""
    done_with_question: bool = False
    allow_second_followup: bool = False
    quick_rubric: QuickRubric = Field(default_factory=QuickRubric)

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

