"""
Tests for Interview Engine.

Focus:
- Question selection logic
- Static difficulty behavior
- Warmup flow transitions
- Tag diversity
- Company style filtering
- Behavioral vs technical question balance
"""

import asyncio

import pytest
from sqlalchemy.orm import Session

from app.crud import session_question as session_question_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.models.user import User
from app.models.user_question_seen import UserQuestionSeen
from app.services.interview_engine import InterviewEngine


@pytest.mark.unit
class TestInterviewEngine:
    """Test suite for Interview Engine."""

    def test_engine_initialization(self):
        """Test interview engine initializes correctly."""
        engine = InterviewEngine()
        assert engine.llm is not None

    def test_warmup_profile_keeps_zero_confidence(self):
        """Test warmup profile preserves 0.0 confidence values."""
        engine = InterviewEngine()
        session = InterviewSession(
            user_id=1,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
        )
        session.skill_state = {"warmup": {"tone": "neutral", "energy": "low", "tone_confidence": 0.0}}
        profile = engine._warmup_profile_from_state(session)
        assert profile is not None
        assert profile.confidence == 0.0

    def test_select_warmup_question(self, db: Session, test_user: User, sample_questions):
        """Test warmup question selection."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        warmup_q = engine._pick_warmup_behavioral_question(db, session)

        assert warmup_q is not None
        assert "behavioral" in (warmup_q.tags_csv or "").lower()

    def test_select_behavioral_question(self, db: Session, test_user: User, sample_questions):
        """Test behavioral question selection."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        behavioral_q = engine._pick_next_behavioral_question(db, session, asked_ids=set())

        assert behavioral_q is not None
        assert "behavioral" in (behavioral_q.tags_csv or "").lower()

    def test_select_technical_question(self, db: Session, test_user: User, sample_questions):
        """Test technical question selection."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="medium", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        technical_q = engine._pick_next_technical_question(db, session, set(), set(), {}, desired_type="coding")

        assert technical_q is not None
        assert technical_q.question_type == "coding"
        assert technical_q.difficulty == "medium"

    def test_adaptive_difficulty_increase(self, db: Session, test_user: User, sample_questions):
        """Test difficulty stays at the selected value (static behavior)."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
            difficulty_current="hard",
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        engine._maybe_bump_difficulty_current(db, session)

        db.refresh(session)
        assert session.difficulty_current == "easy"

    def test_adaptive_difficulty_decrease(self, db: Session, test_user: User, sample_questions):
        """Test difficulty stays at the selected value (static behavior)."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="hard",
            stage="intro",
            difficulty_current="easy",
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        engine._maybe_bump_difficulty_current(db, session)

        db.refresh(session)
        assert session.difficulty_current == "hard"

    def test_question_not_repeated_for_user(self, db: Session, test_user: User, sample_questions):
        """Test that questions are not repeated for the same user."""
        extra = Question(
            title="Extra Easy",
            prompt="Another easy question.",
            difficulty="easy",
            track="swe_intern",
            company_style="general",
            tags_csv="array,extra",
            question_type="coding",
        )
        db.add(extra)
        db.commit()

        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
            behavioral_questions_target=0,
        )
        db.add(session)
        db.commit()

        seen = UserQuestionSeen(user_id=test_user.id, question_id=sample_questions[0].id)
        db.add(seen)
        db.commit()

        engine = InterviewEngine()
        next_q = engine._pick_next_main_question(db, session)

        assert next_q is not None
        assert next_q.id != sample_questions[0].id

    def test_company_style_filtering(self, db: Session, test_user: User):
        """Test questions are filtered by company style."""
        google_q = Question(
            title="Google Question",
            prompt="Google-style question",
            difficulty="medium",
            track="swe_intern",
            company_style="google",
            tags_csv="algorithms",
            question_type="coding",
        )
        general_q = Question(
            title="General Question",
            prompt="General question",
            difficulty="medium",
            track="swe_intern",
            company_style="general",
            tags_csv="algorithms",
            question_type="coding",
        )
        db.add_all([google_q, general_q])
        db.commit()

        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="google", difficulty="medium", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        selected_q = engine._pick_next_technical_question(db, session, set(), set(), {}, desired_type="coding")

        assert selected_q is not None
        assert selected_q.company_style == "google"

    def test_tag_diversity(self, db: Session, test_user: User):
        """Test that questions with diverse tags are selected."""
        questions = [
            Question(
                title=f"Question {i}",
                prompt=f"Question {i} prompt",
                difficulty="medium",
                track="swe_intern",
                company_style="general",
                tags_csv=tag,
                question_type="coding",
            )
            for i, tag in enumerate(["array", "tree", "graph", "dp", "string"])
        ]
        db.add_all(questions)
        db.commit()

        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="medium",
            stage="intro",
            behavioral_questions_target=0,
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()

        selected_tags = set()
        for _ in range(3):
            q = engine._pick_next_main_question(db, session)
            assert q is not None
            selected_tags.add(q.tags_csv)
            session_question_crud.mark_question_asked(db, session.id, q.id)
            engine._increment_questions_asked(db, session)

        assert len(selected_tags) >= 2

    def test_behavioral_question_target(self, db: Session, test_user: User, sample_questions):
        """Test that behavioral questions meet target count."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
            behavioral_questions_target=2,
            max_questions=2,
            questions_asked_count=0,
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        q = engine._pick_next_main_question(db, session)

        assert q is not None
        assert "behavioral" in (q.tags_csv or "").lower()

    def test_max_questions_limit(self, db: Session, test_user: User, sample_questions):
        """Test that interview respects max questions limit."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
            max_questions=3,
            questions_asked_count=3,
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        assert engine._max_questions_reached(session) is True

    def test_followup_generation(self, db: Session, test_user: User, sample_questions):
        """Test follow-up generation heuristic."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        signals = engine._candidate_signals("def foo():\n    pass")
        followup = engine._phase_followup(sample_questions[0], signals, session, followups_used=0)

        assert followup is not None
        assert isinstance(followup, str)
        assert followup.strip()

    def test_warmup_to_active_transition(self, db: Session, test_user: User, sample_questions):
        """Test transition from warmup to active interview."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        engine.llm.api_key = None

        asyncio.run(engine.ensure_question_and_intro(db, session, user_name="Test User"))
        db.refresh(session)
        assert session.stage == "warmup"

        asyncio.run(engine.handle_student_message(db, session, "Doing well, thanks.", user_name="Test User"))
        db.refresh(session)
        assert session.stage == "warmup_smalltalk"

        asyncio.run(
            engine.handle_student_message(db, session, "Pretty good, just wrapped some work.", user_name="Test User")
        )
        db.refresh(session)
        assert session.stage == "warmup_behavioral"

        asyncio.run(engine.handle_student_message(db, session, "Situation task action result.", user_name="Test User"))
        db.refresh(session)
        assert session.stage == "candidate_solution"
        assert session.questions_asked_count == 1

    def test_warmup_smalltalk_fallback(self, db: Session, test_user: User, sample_questions):
        """Test small-talk fallback when the LLM is unavailable."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", stage="intro"
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()
        engine.llm.api_key = None

        asyncio.run(engine.ensure_question_and_intro(db, session, user_name="Test User"))
        db.refresh(session)
        assert session.stage == "warmup"

        msg = asyncio.run(engine.handle_student_message(db, session, "I'm doing okay.", user_name="Test User"))
        db.refresh(session)
        assert session.stage == "warmup_smalltalk"
        assert "?" in msg


@pytest.mark.integration
class TestInterviewEngineIntegration:
    """Integration tests for Interview Engine."""

    def test_complete_interview_flow(self, db: Session, test_user: User, sample_questions):
        """Test complete interview flow from question selection to completion."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            stage="intro",
            max_questions=3,
            behavioral_questions_target=1,
        )
        db.add(session)
        db.commit()

        engine = InterviewEngine()

        questions_asked = []
        while not engine._max_questions_reached(session):
            q = engine._pick_next_main_question(db, session)
            if q:
                questions_asked.append(q)
                session_question_crud.mark_question_asked(db, session.id, q.id)
                engine._increment_questions_asked(db, session)
            else:
                break

        assert len(questions_asked) <= session.max_questions
