from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.tts.tts_service import generate_speech

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    interviewer_id: str | None = None


@router.post("/tts")
def tts(payload: TTSRequest | None = Body(None), text: str | None = None, _user=Depends(get_current_user)):
    """
    Returns audio when available (ElevenLabs primary, default fallback), otherwise JSON with the text.
    Accepts either JSON body {"text": "...", "interviewer_id": "cephas"} or a query/form "text=...".
    interviewer_id selects the per-interviewer ElevenLabs voice (cephas|mason|erica|maya).
    """
    content = (payload.text if payload else None) or text
    interviewer_id = (payload.interviewer_id if payload else None)

    if not content or not str(content).strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "text is required"},
        )

    audio, content_type, provider = generate_speech(content, interviewer_id=interviewer_id)

    if audio and content_type:
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
