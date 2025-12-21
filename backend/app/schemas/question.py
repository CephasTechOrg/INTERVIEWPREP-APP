from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: int
    track: str
    company_style: str
    difficulty: str
    title: str
    prompt: str
    tags: list[str]


class QuestionCoverageOut(BaseModel):
    track: str
    company_style: str
    difficulty: str
    count: int
    fallback_general: int = 0
