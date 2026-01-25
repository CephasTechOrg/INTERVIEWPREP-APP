from datetime import datetime

from pydantic import BaseModel, Field


class InterviewerProfile(BaseModel):
    id: str
    name: str
    gender: str | None = None
    image_url: str | None = None


class CreateSessionRequest(BaseModel):
    role: str = "SWE Intern"
    track: str = "swe_intern"
    company_style: str = "general"
    difficulty: str = "easy"
    behavioral_questions_target: int = Field(default=2, ge=0, le=10)
    interviewer: InterviewerProfile | None = None


class SessionOut(BaseModel):
    id: int
    role: str
    track: str
    company_style: str
    difficulty: str
    stage: str
    current_question_id: int | None = None
    interviewer: InterviewerProfile | None = None


class SessionSummaryOut(BaseModel):
    id: int
    role: str
    track: str
    company_style: str
    difficulty: str
    stage: str
    current_question_id: int | None = None
    questions_asked_count: int = 0
    max_questions: int = 7
    behavioral_questions_target: int = 2
    overall_score: int | None = None
    created_at: datetime | None = None
    interviewer: InterviewerProfile | None = None
