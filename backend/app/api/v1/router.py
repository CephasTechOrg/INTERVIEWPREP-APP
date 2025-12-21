from fastapi import APIRouter

from app.api.v1 import ai, analytics, auth, questions, sessions, voice

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, tags=["auth"])
router.include_router(questions.router, tags=["questions"])
router.include_router(sessions.router, tags=["sessions"])
router.include_router(analytics.router, tags=["analytics"])
router.include_router(ai.router, tags=["ai"])
router.include_router(voice.router, tags=["voice"])
