"""
Question Selection Module for Interview Engine.

Handles question type classification, difficulty selection, and main/technical/behavioral question picking.
"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud import session_question as session_question_crud
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.models.user_question_seen import UserQuestionSeen
from app.services.interview_engine_followups import InterviewEngineFollowups


class InterviewEngineQuestions(InterviewEngineFollowups):
    """Question selection and type classification methods."""

    def _question_type(self, q: Question) -> str:
        """
        Normalize question type for selection logic.
        Priority: explicit question_type (if set) else tags/track inference.
        """
        raw = getattr(q, "question_type", None)
        qt = str(raw).strip().lower() if raw else ""
        if qt and qt != "coding":
            return qt

        try:
            tags = {t.strip().lower() for t in (q.tags() or []) if str(t).strip()}
        except Exception:
            tags = set()

        if self._is_behavioral(q) or "behavioral" in tags or (q.track or "") == "behavioral":
            return "behavioral"
        if tags & self._SYSTEM_DESIGN_TAGS:
            return "system_design"
        if tags & self._CONCEPTUAL_TAGS:
            return "conceptual"
        return "coding"

    def _is_conceptual_question(self, q: Question) -> bool:
        if self._is_behavioral(q):
            return False
        qt = self._question_type(q)
        if qt and qt != "coding":
            return qt == "conceptual"
        prompt = (getattr(q, "prompt", None) or "").strip().lower()
        if not prompt:
            return False
        prefixes = (
            "explain",
            "define",
            "what is",
            "what's",
            "why",
            "describe",
            "compare",
            "difference between",
            "when would you",
            "when should you",
            "how would you handle",
            "how do you",
        )
        if not prompt.startswith(prefixes):
            return False
        exclude = (
            "implement",
            "write",
            "code",
            "solve",
            "return",
            "given",
            "design",
            "build",
            "create",
            "compute",
            "find",
        )
        return not any(k in prompt for k in exclude)

    def _matches_desired_type(self, q: Question, desired_type: str | None) -> bool:
        if not desired_type:
            return True
        target = (desired_type or "").strip().lower()
        if not target:
            return True
        qt = self._question_type(q)
        if target == "coding":
            return qt in ("coding", "conceptual")
        return qt == target

    def _effective_difficulty(self, session: InterviewSession) -> str:
        selected = (getattr(session, "difficulty", None) or "easy").strip().lower()
        current = (getattr(session, "difficulty_current", None) or "").strip().lower()
        if selected in ("easy", "medium", "hard"):
            return selected
        if current in ("easy", "medium", "hard"):
            return current
        return "easy"

    def _seen_question_subquery(self, session: InterviewSession):
        return select(UserQuestionSeen.question_id).where(UserQuestionSeen.user_id == session.user_id)

    def _pick_next_behavioral_question(
        self, db: Session, session: InterviewSession, asked_ids: set[int] | None = None
    ) -> Question | None:
        asked_ids = asked_ids or set()
        company = (session.company_style or "").strip().lower() or "general"
        track = (session.track or "").strip()
        diff = self._effective_difficulty(session)
        tracks = {track, "behavioral"} if track else {"behavioral"}

        def _query(company_style: str, difficulty: str | None) -> Question | None:
            base = db.query(Question).filter(
                Question.company_style == company_style,
                Question.track.in_(tracks),
                or_(Question.tags_csv.ilike("%behavioral%"), Question.question_type == "behavioral"),
            )
            if difficulty:
                base = base.filter(Question.difficulty == difficulty)
            if asked_ids:
                base = base.filter(~Question.id.in_(asked_ids))
            seen = self._seen_question_subquery(session)
            unseen = base.filter(~Question.id.in_(seen)).order_by(func.random()).first()
            if unseen:
                return unseen
            return base.order_by(func.random()).first()

        # Prefer company + same difficulty, then company any difficulty,
        # then general + same difficulty, then general any difficulty.
        for company_style, difficulty in (
            (company, diff),
            (company, None),
            ("general", diff) if company != "general" else (None, None),
            ("general", None) if company != "general" else (None, None),
        ):
            if not company_style:
                continue
            q = _query(company_style, difficulty)
            if q:
                return q
        return None

    def _pick_next_technical_question(
        self,
        db: Session,
        session: InterviewSession,
        asked_ids: set[int],
        seen_ids: set[int],
        focus: dict[str, Any] | None,
        desired_type: str | None = None,
    ) -> Question | None:
        diff = self._effective_difficulty(session)
        company = (session.company_style or "").strip().lower() or "general"

        base = db.query(Question).filter(
            Question.track == session.track,
            Question.company_style == company,
            Question.difficulty == diff,
            ~Question.tags_csv.ilike("%behavioral%"),
            Question.question_type != "behavioral",
        )
        if asked_ids:
            base = base.filter(~Question.id.in_(asked_ids))
        if seen_ids:
            base = base.filter(~Question.id.in_(seen_ids))

        candidates = base.order_by(func.random()).limit(120).all()
        if desired_type:
            candidates = [c for c in candidates if self._matches_desired_type(c, desired_type)]
        if not candidates:
            return None

        focus_tags = set((focus or {}).get("tags") or [])
        asked_tags: set[str] = set()
        if asked_ids:
            asked = db.query(Question).filter(Question.id.in_(asked_ids)).all()
            for q in asked:
                asked_tags.update({t.strip().lower() for t in (q.tags() or []) if t})

        # Phase 5: Get rubric gaps to target weak areas
        rubric_gaps = self._critical_rubric_gaps(session, threshold=5)

        best = None
        best_score = -10_000
        for q in candidates:
            tags = {t.strip().lower() for t in (q.tags() or []) if t}
            overlap = len(tags & focus_tags) if focus_tags else 0
            penalty = len(tags & asked_tags) if asked_tags else 0
            weak_score = self._weakness_score(q, self._weakness_keywords(self._weakest_dimension(session)))
            rubric_score = self._question_rubric_alignment_score(q, rubric_gaps)
            # Phase 5: Heavily weight rubric alignment (+20 boost)
            score = (overlap * 5) + weak_score + rubric_score - penalty
            if best is None or score > best_score:
                best = q
                best_score = score
        return best or candidates[0]

    def _pick_next_main_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        seen_ids = set(user_question_seen_crud.list_seen_question_ids(db, session.user_id))

        behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
        behavioral_asked = 0
        if asked_ids:
            asked_questions = db.query(Question).filter(Question.id.in_(asked_ids)).all()
            behavioral_asked = sum(1 for q in asked_questions if self._is_behavioral(q))

        questions_asked = int(session.questions_asked_count or 0)
        questions_remaining = max(0, int(session.max_questions or 0) - questions_asked)
        behavioral_remaining = max(0, behavioral_target - behavioral_asked)

        focus = {"tags": list(self._focus_tags(session))}

        if behavioral_remaining > 0:
            # If all remaining slots must be behavioral, do it now.
            if behavioral_remaining >= questions_remaining:
                q = self._pick_next_behavioral_question(db, session, asked_ids)
                if q:
                    return q
            # Otherwise, prefer technical first, then behavioral.
            q = self._pick_next_technical_question(db, session, asked_ids, seen_ids, focus, desired_type="coding")
            if q:
                return q
            return self._pick_next_behavioral_question(db, session, asked_ids)

        # Behavioral target already satisfied: only technical questions.
        q = self._pick_next_technical_question(db, session, asked_ids, seen_ids, focus, desired_type="coding")
        if q:
            return q
        return None
