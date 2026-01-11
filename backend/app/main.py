from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.db.session import SessionLocal
from app.db.init_db import load_questions_from_folder
from app.models.question import Question
from sqlalchemy import text

# Import models so SQLAlchemy sees them before create_all
from app.models.user import User  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.question import Question  # noqa: F401
from app.models.interview_session import InterviewSession  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.evaluation import Evaluation  # noqa: F401
from app.models.session_question import SessionQuestion  # noqa: F401
from app.models.user_question_seen import UserQuestionSeen  # noqa: F401
from app.models.pending_signup import PendingSignup  # noqa: F401
from app.core.constants import ALLOWED_COMPANY_STYLES, ALLOWED_DIFFICULTIES, ALLOWED_TRACKS

app = FastAPI(title=settings.APP_NAME)

# For local dev (simple frontend on another port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.on_event("startup")
def _startup_init_db() -> None:
    # Create tables (MVP). Later replace with Alembic migrations.
    # Keep this in startup so imports don't crash if DB isn't ready yet.
    Base.metadata.create_all(bind=engine)

    # Minimal schema upgrades for dev (since we use create_all instead of migrations).
    # Safe to run repeatedly.
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE IF EXISTS interview_sessions
                      ADD COLUMN IF NOT EXISTS questions_asked_count INTEGER NOT NULL DEFAULT 0,
                      ADD COLUMN IF NOT EXISTS followups_used INTEGER NOT NULL DEFAULT 0,
                      ADD COLUMN IF NOT EXISTS max_questions INTEGER NOT NULL DEFAULT 7,
                      ADD COLUMN IF NOT EXISTS max_followups_per_question INTEGER NOT NULL DEFAULT 2,
                      ADD COLUMN IF NOT EXISTS behavioral_questions_target INTEGER NOT NULL DEFAULT 2,
                      ADD COLUMN IF NOT EXISTS difficulty_current VARCHAR(20) NOT NULL DEFAULT 'easy',
                      ADD COLUMN IF NOT EXISTS skill_state JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE IF EXISTS questions
                      ADD COLUMN IF NOT EXISTS followups JSONB NOT NULL DEFAULT '[]'::jsonb,
                      ADD COLUMN IF NOT EXISTS question_type VARCHAR(50) NOT NULL DEFAULT 'coding',
                      ADD COLUMN IF NOT EXISTS meta JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS session_questions (
                      id SERIAL PRIMARY KEY,
                      session_id INTEGER NOT NULL,
                      question_id INTEGER NOT NULL,
                      created_at TIMESTAMPTZ DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS ix_session_questions_session_id ON session_questions(session_id);
                    CREATE INDEX IF NOT EXISTS ix_session_questions_question_id ON session_questions(question_id);
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS user_questions_seen (
                      id SERIAL PRIMARY KEY,
                      user_id INTEGER NOT NULL,
                      question_id INTEGER NOT NULL,
                      created_at TIMESTAMPTZ DEFAULT now()
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_user_questions_seen_user_question
                      ON user_questions_seen(user_id, question_id);
                    CREATE INDEX IF NOT EXISTS ix_user_questions_seen_user_id ON user_questions_seen(user_id);
                    CREATE INDEX IF NOT EXISTS ix_user_questions_seen_question_id ON user_questions_seen(question_id);
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE IF EXISTS users
                      ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false,
                      ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255),
                      ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255),
                      ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMPTZ,
                      ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                      id SERIAL PRIMARY KEY,
                      user_id INTEGER,
                      action VARCHAR(100) NOT NULL,
                      ip VARCHAR(64),
                      user_agent VARCHAR(255),
                      meta JSONB NOT NULL DEFAULT '{}'::jsonb,
                      created_at TIMESTAMPTZ DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
                    CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
                    """
                )
            )

            allowed_companies = ", ".join([f"'{c}'" for c in sorted(ALLOWED_COMPANY_STYLES)])
            allowed_tracks = ", ".join([f"'{t}'" for t in sorted(ALLOWED_TRACKS)])
            allowed_difficulties = ", ".join([f"'{d}'" for d in sorted(ALLOWED_DIFFICULTIES)])

            def _scalar(stmt: str) -> int:
                try:
                    return int(conn.execute(text(stmt)).scalar() or 0)
                except Exception:
                    return 0

            invalid_title = _scalar("SELECT COUNT(*) FROM questions WHERE btrim(title) = ''")
            invalid_prompt = _scalar("SELECT COUNT(*) FROM questions WHERE btrim(prompt) = ''")
            invalid_tags = _scalar("SELECT COUNT(*) FROM questions WHERE tags_csv IS NULL OR btrim(tags_csv) = ''")
            invalid_q_company = _scalar(
                f"SELECT COUNT(*) FROM questions WHERE company_style NOT IN ({allowed_companies})"
            )
            invalid_q_track = _scalar(
                f"SELECT COUNT(*) FROM questions WHERE track NOT IN ({allowed_tracks})"
            )
            invalid_q_diff = _scalar(
                f"SELECT COUNT(*) FROM questions WHERE difficulty NOT IN ({allowed_difficulties})"
            )
            invalid_s_company = _scalar(
                f"SELECT COUNT(*) FROM interview_sessions WHERE company_style NOT IN ({allowed_companies})"
            )
            invalid_s_track = _scalar(
                f"SELECT COUNT(*) FROM interview_sessions WHERE track NOT IN ({allowed_tracks})"
            )
            invalid_s_diff = _scalar(
                f"SELECT COUNT(*) FROM interview_sessions WHERE difficulty NOT IN ({allowed_difficulties})"
            )

            if invalid_title == 0:
                conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_title_nonempty') THEN
                            ALTER TABLE questions ADD CONSTRAINT ck_questions_title_nonempty CHECK (btrim(title) <> '');
                          END IF;
                        END $$;
                        """
                    )
                )
            if invalid_prompt == 0:
                conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_prompt_nonempty') THEN
                            ALTER TABLE questions ADD CONSTRAINT ck_questions_prompt_nonempty CHECK (btrim(prompt) <> '');
                          END IF;
                        END $$;
                        """
                    )
                )
            if invalid_tags == 0:
                conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_tags_nonempty') THEN
                            ALTER TABLE questions ADD CONSTRAINT ck_questions_tags_nonempty CHECK (btrim(tags_csv) <> '');
                          END IF;
                        END $$;
                        """
                    )
                )

            statements: list[str] = []
            if invalid_q_company == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_company_style') THEN
                      ALTER TABLE questions ADD CONSTRAINT ck_questions_company_style CHECK (company_style IN ({allowed_companies}));
                    END IF;
                    """
                )
            if invalid_q_track == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_track') THEN
                      ALTER TABLE questions ADD CONSTRAINT ck_questions_track CHECK (track IN ({allowed_tracks}));
                    END IF;
                    """
                )
            if invalid_q_diff == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_questions_difficulty') THEN
                      ALTER TABLE questions ADD CONSTRAINT ck_questions_difficulty CHECK (difficulty IN ({allowed_difficulties}));
                    END IF;
                    """
                )
            if invalid_s_company == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sessions_company_style') THEN
                      ALTER TABLE interview_sessions ADD CONSTRAINT ck_sessions_company_style CHECK (company_style IN ({allowed_companies}));
                    END IF;
                    """
                )
            if invalid_s_track == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sessions_track') THEN
                      ALTER TABLE interview_sessions ADD CONSTRAINT ck_sessions_track CHECK (track IN ({allowed_tracks}));
                    END IF;
                    """
                )
            if invalid_s_diff == 0:
                statements.append(
                    f"""
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sessions_difficulty') THEN
                      ALTER TABLE interview_sessions ADD CONSTRAINT ck_sessions_difficulty CHECK (difficulty IN ({allowed_difficulties}));
                    END IF;
                    """
                )

            if statements:
                conn.execute(
                    text(
                        "DO $$\nBEGIN\n" + "\n".join(statements) + "\nEND $$;"
                    )
                )
    except Exception as e:
        if settings.ENV == "dev":
            print(f"Schema upgrade skipped: {e}")

    # Dev convenience: auto-load questions from `data/questions` when DB is empty.
    # This does not affect auth flows; it just ensures the interview has content.
    try:
        db = SessionLocal()
        folder = str(Path(__file__).resolve().parents[2] / "data" / "questions")
        inserted = load_questions_from_folder(db, folder)
        if settings.ENV == "dev":
            print(f"Questions loaded: +{inserted}")
    except Exception as e:
        # Never crash startup because of seeding; the API should still run.
        if settings.ENV == "dev":
            print(f"Question seeding skipped: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass


@app.get("/health")
def health():
    return {"status": "ok"}
