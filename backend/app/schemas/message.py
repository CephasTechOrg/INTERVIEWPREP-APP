from pydantic import BaseModel
from datetime import datetime


class SendMessageRequest(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    current_question_id: int | None = None


class MessageHistoryOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime | None = None
