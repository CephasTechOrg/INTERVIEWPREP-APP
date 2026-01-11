from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.init_db import load_questions_from_folder

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# For local dev (simple frontend on another port)
# TODO: Restrict CORS origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.on_event("startup")
def _startup_init_db() -> None:
    """
    Startup hook: Load questions from data/questions/ if DB is empty.
    
    Note: Database schema is now managed by Alembic migrations.
    Run 'alembic upgrade head' before starting the application.
    """
    # Dev convenience: auto-load questions from `data/questions` when DB is empty.
    # This does not affect auth flows; it just ensures the interview has content.
    try:
        db = SessionLocal()
        folder = str(Path(__file__).resolve().parents[2] / "data" / "questions")
        inserted = load_questions_from_folder(db, folder)
        if settings.ENV == "dev" and inserted > 0:
            logger.info(f"Questions loaded: +{inserted}")
    except Exception as e:
        # Never crash startup because of seeding; the API should still run.
        if settings.ENV == "dev":
            logger.warning(f"Question seeding skipped: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass


@app.get("/health")
def health():
    return {"status": "ok"}
