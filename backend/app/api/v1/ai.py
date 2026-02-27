from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.rate_limit import rate_limit
from app.crud.user_usage import check_chat_limit, increment_chat_usage
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
async def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    user_id = getattr(_user, "id", None)
    is_admin = getattr(_user, "is_admin", False)
    
    # Check daily chat limit (skip for anonymous users and admins)
    if user_id and not is_admin:
        allowed, remaining, limit = check_chat_limit(db, user_id)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "You've reached your daily chat limit. Resets at midnight UTC. Premium version coming soon!",
                    "limit": limit,
                    "remaining": 0,
                    "resets": "midnight UTC",
                },
            )
    
    # Per-minute rate limiting (burst protection)
    rate_limit(request, key=f"ai_chat:{user_id or 'anon'}", max_calls=30, window_sec=60)
    
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
        
        # Increment usage counter on successful response (skip for admins)
        if user_id and not is_admin:
            increment_chat_usage(db, user_id)
        
        return ChatResponse(reply=reply, mode="live")
    except LLMClientError:
        fallback = (
            "AI is currently offline. Set DEEPSEEK_API_KEY in backend/.env and restart the server "
            "to enable chat responses."
        )
        return ChatResponse(reply=fallback, mode="fallback")


class UsageLimits(BaseModel):
    """Response model for usage limits."""
    chat_messages_today: int
    chat_limit_daily: int
    chat_remaining: int
    tts_characters_month: int
    tts_limit_monthly: int
    tts_remaining: int


@router.get("/usage", response_model=UsageLimits)
def get_usage(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get current user's usage and remaining limits."""
    from app.core.config import settings
    from app.crud.user_usage import get_all_usage
    
    user_id = getattr(_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    usage = get_all_usage(db, user_id)
    
    chat_limit = settings.FREE_CHAT_LIMIT_DAILY
    tts_limit = settings.FREE_TTS_LIMIT_MONTHLY
    
    return UsageLimits(
        chat_messages_today=usage["chat_messages_today"],
        chat_limit_daily=chat_limit,
        chat_remaining=max(0, chat_limit - usage["chat_messages_today"]),
        tts_characters_month=usage["tts_characters_month"],
        tts_limit_monthly=tts_limit,
        tts_remaining=max(0, tts_limit - usage["tts_characters_month"]),
    )
