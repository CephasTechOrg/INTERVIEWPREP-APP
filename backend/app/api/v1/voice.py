from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.user_usage import check_tts_limit, increment_tts_usage
from app.services.tts.tts_service import generate_speech

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    interviewer_id: str | None = None


@router.post("/tts")
def tts(
    payload: TTSRequest | None = Body(None),
    text: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Returns audio when available (ElevenLabs primary, default fallback), otherwise JSON with the text.
    Accepts either JSON body {"text": "...", "interviewer_id": "cephas"} or a query/form "text=...".
    interviewer_id selects the per-interviewer ElevenLabs voice (cephas|mason|erica|maya).
    
    If user's monthly TTS character limit is exceeded, returns text-only response for browser TTS.
    """
    content = (payload.text if payload else None) or text
    interviewer_id = (payload.interviewer_id if payload else None)

    if not content or not str(content).strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "text is required"},
        )
    
    user_id = getattr(_user, "id", None)
    is_admin = getattr(_user, "is_admin", False)
    char_count = len(content)
    
    # Check TTS character limit before calling ElevenLabs (skip for admins)
    tts_allowed = True
    remaining = 0
    limit = 0
    if user_id and not is_admin:
        tts_allowed, remaining, limit = check_tts_limit(db, user_id, char_count)
    
    if not tts_allowed:
        # Return text-only response for browser TTS fallback
        return JSONResponse(
            status_code=200,
            content={
                "mode": "text",
                "text": content,
                "tts_provider": "browser",
                "limit_exceeded": True,
                "message": "Voice limit reached. Using browser voice instead. Resets next month. Premium version coming soon!",
                "remaining_chars": remaining,
                "monthly_limit": limit,
            },
        )

    audio, content_type, provider = generate_speech(content, interviewer_id=interviewer_id)

    if audio and content_type:
        # Only count characters if ElevenLabs was used successfully (skip for admins)
        if user_id and not is_admin and provider == "elevenlabs":
            increment_tts_usage(db, user_id, char_count)
        
        return Response(
            content=audio,
            media_type=content_type,
            headers={"X-TTS-Provider": provider},
        )

    return JSONResponse(
        status_code=200,
        content={
            "mode": "text",
            "text": content,
            "tts_provider": provider,
        },
    )
