from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class CreateChatThreadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    messages: list[ChatMessageSchema] = Field(default_factory=list)


class UpdateChatThreadRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    messages: list[ChatMessageSchema] | None = None


class ChatThreadOut(BaseModel):
    id: int
    user_id: int
    title: str
    messages: list[ChatMessageSchema]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatThreadSummaryOut(BaseModel):
    id: int
    title: str
    message_count: int
    updated_at: datetime

    class Config:
        from_attributes = True
