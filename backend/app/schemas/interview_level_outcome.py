"""
Schemas for interview level outcome API responses.
"""

from pydantic import BaseModel
from datetime import datetime


class LevelOutcomeStrength(BaseModel):
    """Strength identified in the interview."""
    dimension: str
    actual_score: float
    threshold: float
    strength: str


class LevelOutcomeGap(BaseModel):
    """Gap or area for improvement."""
    dimension: str
    actual_score: float
    target_score: float
    gap: float
    interpretation: str


class InterviewLevelOutcomeOut(BaseModel):
    """Level calibration result response."""
    id: int
    session_id: int
    role: str
    company_tier: str
    estimated_level: str
    estimated_level_display: str
    readiness_percent: int
    confidence: str
    next_level: str | None
    strengths: list[LevelOutcomeStrength]
    gaps: list[LevelOutcomeGap]
    next_actions: list[str]
    rubric_scores_used: dict[str, float]
    created_at: datetime

    class Config:
        from_attributes = True
