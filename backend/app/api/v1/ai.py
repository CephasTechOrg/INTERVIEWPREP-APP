from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.api.rate_limit import rate_limit
from app.services.llm_client import DeepSeekClient, LLMClientError, get_llm_status

router = APIRouter(prefix="/ai")


@router.get("/status")
def ai_status(_user=Depends(get_current_user)):
    return get_llm_status()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(default="", max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    mode: str = "live"  # "live" | "fallback"


_CHAT_SYSTEM_PROMPT = (
    "You are InterviewPrep AI, a concise and helpful assistant for interview prep and general questions. "
    "Be clear, practical, and friendly. If something is unknown, say so. Keep responses under 200 words unless asked."
)
_CHAT_MAX_HISTORY = 20
_CHAT_CLIENT = DeepSeekClient()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, _user=Depends(get_current_user)):
    user_id = getattr(_user, "id", "anon")
    rate_limit(request, key=f"ai_chat:{user_id}", max_calls=30, window_sec=60)
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message is required.")

    history: list[dict] = []
    for item in payload.history[-_CHAT_MAX_HISTORY:]:
        role = (item.role or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (item.content or "").strip()
        if not content:
            continue
        history.append({"role": role, "content": content[:4000]})

    try:
        reply = await _CHAT_CLIENT.chat(_CHAT_SYSTEM_PROMPT, message, history=history)
        reply = (reply or "").strip() or "I couldn't generate a response. Please try again."
        return ChatResponse(reply=reply, mode="live")
    except LLMClientError:
        fallback = (
            "AI is currently offline. Set DEEPSEEK_API_KEY in backend/.env and restart the server "
            "to enable chat responses."
        )
        return ChatResponse(reply=fallback, mode="fallback")
