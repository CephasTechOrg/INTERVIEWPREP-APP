import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db.init_db import load_questions_from_folder
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.question import Question
from app.models.session_question import SessionQuestion
from app.models.user import User
from app.models.user_question_seen import UserQuestionSeen
from app.services import interview_engine as interview_engine_module
from app.services.interview_engine import InterviewEngine


def cleanup(db, user_id: int | None, session_id: int | None) -> None:
    if session_id:
        db.query(Message).filter(Message.session_id == session_id).delete(synchronize_session=False)
        db.query(SessionQuestion).filter(SessionQuestion.session_id == session_id).delete(synchronize_session=False)
    if user_id:
        db.query(UserQuestionSeen).filter(UserQuestionSeen.user_id == user_id).delete(synchronize_session=False)
        db.query(InterviewSession).filter(InterviewSession.user_id == user_id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = None
    session = None

    try:
        load_questions_from_folder(db, str(ROOT / "data" / "questions"))

        user = User(
            email="diversity_regression@example.com",
            full_name="Diversity Regression",
            password_hash="x",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        q_last = (
            db.query(Question)
            .filter(
                Question.track == "swe_intern",
                Question.company_style == "general",
                Question.difficulty == "easy",
                ~Question.tags_csv.ilike("%behavioral%"),
            )
            .first()
        )
        if not q_last:
            raise AssertionError("No technical question found for swe_intern/general/easy")

        session = InterviewSession(
            user_id=user.id,
            role="SWE Intern",
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            difficulty_current="easy",
            stage="candidate_solution",
            questions_asked_count=1,
            followups_used=0,
            max_questions=7,
            max_followups_per_question=2,
            behavioral_questions_target=2,
            skill_state={},
            current_question_id=q_last.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(SessionQuestion(session_id=session.id, question_id=q_last.id))
        db.commit()

        rng = random.Random(0)
        original_random = interview_engine_module.random
        interview_engine_module.random = rng

        try:
            engine_obj = InterviewEngine()
            asked_ids, _asked_questions, used_tags, _behavioral_used, tag_counts = engine_obj._session_asked_state(db, session)
            next_q = engine_obj._pick_next_technical_question(db, session, asked_ids, used_tags, tag_counts)
            if not next_q:
                raise AssertionError("No next technical question found")

            last_tags = engine_obj._last_asked_technical_tags(db, session)
            if not last_tags:
                raise AssertionError("Last technical question has no tags")

            seen = engine_obj._seen_question_subquery(session)

            def build_pool(company_style: str):
                for diff in engine_obj._adaptive_difficulty_try_order(session):
                    base = db.query(Question).filter(
                        Question.track == session.track,
                        Question.company_style == company_style,
                        Question.difficulty == diff,
                        ~Question.tags_csv.ilike("%behavioral%"),
                    )
                    if asked_ids:
                        base = base.filter(~Question.id.in_(asked_ids))

                    pool = base.filter(~Question.id.in_(seen)).all()
                    used_seen = False
                    if not pool:
                        pool = base.all()
                        used_seen = True
                    if pool:
                        return pool, used_seen
                return [], False

            company_style = engine_obj._effective_company_style(session)
            pool, used_seen = build_pool(company_style)
            if not pool and company_style != "general":
                pool, used_seen = build_pool("general")

            if not pool:
                raise AssertionError("No candidate pool found for tag diversity check")

            def tag_set(q: Question) -> set[str]:
                return {t.strip().lower() for t in (q.tags() or []) if str(t).strip()}

            weakness = engine_obj._weakest_dimension(session)
            weakness_keywords = engine_obj._weakness_keywords(weakness)
            focus_tags = engine_obj._focus_tags(session)
            seen_ids: set[int] = set()
            if used_seen:
                try:
                    seen_ids = set(user_question_seen_crud.list_seen_question_ids(db, session.user_id))
                except Exception:
                    seen_ids = set()

            rng_check = random.Random(0)

            def score_candidate(cand: Question) -> float:
                cand_tags = tag_set(cand)
                weakness_score = engine_obj._weakness_score(cand, weakness_keywords) if weakness_keywords else 0
                focus_overlap = len(cand_tags & focus_tags) if focus_tags else 0
                diversity_bonus = len(cand_tags - used_tags) if used_tags else len(cand_tags)
                last_overlap = len(cand_tags & last_tags) if last_tags else 0
                if cand_tags:
                    avg_freq = sum(tag_counts.get(t, 0) for t in cand_tags) / float(len(cand_tags))
                else:
                    avg_freq = 0.0
                rarity_bonus = 1.0 / (1.0 + avg_freq)
                seen_penalty = 1.4 if cand.id in seen_ids else 0.0

                score = (
                    (1.2 * weakness_score)
                    + (1.0 * focus_overlap)
                    + (0.8 * diversity_bonus)
                    + (0.6 * rarity_bonus)
                    - (0.8 * last_overlap)
                    - seen_penalty
                )
                return score + (rng_check.random() * 0.15)

            ranked = sorted(pool, key=score_candidate, reverse=True)
            if not ranked:
                raise AssertionError("No ranked candidates found")

            bucket_size = max(3, min(len(ranked), max(3, len(ranked) // 4)))
            bucket = ranked[:bucket_size]
            bucket_ids = {q.id for q in bucket}
            if next_q.id not in bucket_ids:
                raise AssertionError("Tag diversity pick not in top bucket")
        finally:
            interview_engine_module.random = original_random
        return 0
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"Tag diversity regression failed: {exc}")
        return 1
    finally:
        try:
            cleanup(db, user.id if user else None, session.id if session else None)
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
