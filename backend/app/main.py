import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.init_db import load_questions_from_folder
from app.db.session import SessionLocal
from app.models.question import Question

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _startup_init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]


origins = _parse_origins(settings.FRONTEND_ORIGINS)
origin_regex = None
if settings.ENV == "dev":
    # Allow any localhost/127.0.0.1 port in dev so preflights don't 400.
    origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if settings.ENV == "dev" and request.method == "OPTIONS":
        origin = request.headers.get("origin", "*")
        req_method = request.headers.get("access-control-request-method", "*")
        req_headers = request.headers.get("access-control-request-headers", "*")
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": req_method,
            "Access-Control-Allow-Headers": req_headers,
            "Access-Control-Max-Age": "86400",
            "Vary": "Origin",
        }
        return Response(status_code=204, headers=headers)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
    if settings.ENV != "dev":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

app.include_router(v1_router)


def _startup_init_db() -> None:
    """
    Startup hook: Load questions from data/questions/ (insert-only, dev).

    Note: Database schema is now managed by Alembic migrations.
    Run 'alembic upgrade head' before starting the application.
    """
    if settings.ENV != "dev" and not settings.SEED_QUESTIONS_ON_START:
        return
    # Auto-load questions from `data/questions` (insert-only).
    # In production, this only runs when the DB is empty and the flag is enabled.
    try:
        db = SessionLocal()
        if settings.ENV != "dev":
            existing = db.query(Question).count()
            if existing > 0:
                return
        folder = str(Path(__file__).resolve().parents[2] / "data" / "questions")
        inserted = load_questions_from_folder(db, folder)
        if settings.ENV == "dev" and inserted > 0:
            logger.info(f"Questions loaded: +{inserted}")
    except Exception as e:
        # Never crash startup because of seeding; the API should still run.
        if settings.ENV == "dev":
            logger.warning(f"Question seeding skipped: {e}")
    finally:
        with suppress(Exception):
            db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
