from pydantic import BaseModel


class EvaluationOut(BaseModel):
    session_id: int
    overall_score: int
    rubric: dict
    summary: dict
