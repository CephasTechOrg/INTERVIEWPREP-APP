"""Schemas for session feedback API."""

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for submitting feedback after an interview session."""
    
    session_id: int
    rating: int = Field(..., ge=1, le=5, description="Overall rating 1-5 stars")
    thumbs: str | None = Field(None, pattern="^(up|down)$", description="Quick thumbs up/down")
    comment: str | None = Field(None, max_length=2000, description="Optional written feedback")
    
    # Optional detailed ratings
    rating_questions: int | None = Field(None, ge=1, le=5, description="Rate question quality")
    rating_feedback: int | None = Field(None, ge=1, le=5, description="Rate AI feedback quality")
    rating_difficulty: int | None = Field(None, ge=1, le=5, description="Rate difficulty appropriateness")


class FeedbackOut(BaseModel):
    """Schema for returning feedback data."""
    
    id: int
    session_id: int
    rating: int
    thumbs: str | None
    comment: str | None
    rating_questions: int | None
    rating_feedback: int | None
    rating_difficulty: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics."""
    
    total_sessions: int
    sessions_with_feedback: int
    average_rating: float | None
    rating_distribution: dict[int, int]  # {1: count, 2: count, ...}
    thumbs_up_count: int
    thumbs_down_count: int
