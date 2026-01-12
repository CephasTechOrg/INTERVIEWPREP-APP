from datetime import datetime

from pydantic import BaseModel


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
