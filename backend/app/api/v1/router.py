from fastapi import APIRouter

from app.api.v1 import ai, analytics, auth, chat_threads, embeddings, feedback, questions, sessions, users, voice

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, tags=["auth"])
router.include_router(questions.router, tags=["questions"])
router.include_router(sessions.router, tags=["sessions"])
router.include_router(analytics.router, tags=["analytics"])
router.include_router(ai.router, tags=["ai"])
router.include_router(chat_threads.router, tags=["chat_threads"])
router.include_router(voice.router, tags=["voice"])
router.include_router(users.router, tags=["users"])
router.include_router(feedback.router, tags=["feedback"])
router.include_router(embeddings.router, tags=["embeddings"])
