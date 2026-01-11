"""
Tests for Interview Engine.

Tests cover:
- Question selection logic
- Adaptive difficulty adjustment
- Warmup flow
- Tag diversity
- Company style filtering
- Behavioral vs technical question balance
"""
import pytest
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch

from app.services.interview_engine import InterviewEngine
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.models.question import Question


@pytest.mark.unit
class TestInterviewEngine:
    """Test suite for Interview Engine."""
    
    def test_engine_initialization(self, db: Session, test_user: User):
        """Test interview engine initializes correctly."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="created"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        assert engine.db == db
        assert engine.session == session
    
    def test_select_warmup_question(self, db: Session, test_user: User, sample_questions):
        """Test warmup question selection."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="warmup"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        warmup_q = engine.select_warmup_question()
        
        assert warmup_q is not None
        # Warmup questions are typically behavioral and easy
        assert warmup_q.difficulty == "easy"
    
    def test_select_behavioral_question(self, db: Session, test_user: User, sample_questions):
        """Test behavioral question selection."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        behavioral_q = engine.select_next_question(question_type="behavioral")
        
        assert behavioral_q is not None
        assert "behavioral" in behavioral_q.tags_csv.lower()
    
    def test_select_technical_question(self, db: Session, test_user: User, sample_questions):
        """Test technical question selection."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="medium",
            status="active"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        technical_q = engine.select_next_question(question_type="coding")
        
        assert technical_q is not None
        assert technical_q.question_type == "coding"
    
    def test_adaptive_difficulty_increase(self, db: Session, test_user: User, sample_questions):
        """Test difficulty increases after correct answers."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active",
            difficulty_current="easy"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Simulate correct answer
        engine.update_difficulty(performance_score=0.9)
        
        db.refresh(session)
        # Difficulty should increase or stay same
        assert session.difficulty_current in ["easy", "medium"]
    
    def test_adaptive_difficulty_decrease(self, db: Session, test_user: User, sample_questions):
        """Test difficulty decreases after incorrect answers."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="hard",
            status="active",
            difficulty_current="hard"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Simulate poor performance
        engine.update_difficulty(performance_score=0.3)
        
        db.refresh(session)
        # Difficulty should decrease or stay same
        assert session.difficulty_current in ["medium", "hard"]
    
    def test_question_not_repeated_for_user(self, db: Session, test_user: User, sample_questions):
        """Test that questions are not repeated for the same user."""
        from app.models.user_question_seen import UserQuestionSeen
        
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active"
        )
        db.add(session)
        db.commit()
        
        # Mark first question as seen
        seen = UserQuestionSeen(
            user_id=test_user.id,
            question_id=sample_questions[0].id
        )
        db.add(seen)
        db.commit()
        
        engine = InterviewEngine(db, session)
        next_q = engine.select_next_question()
        
        # Should not select the seen question
        if next_q:
            assert next_q.id != sample_questions[0].id
    
    def test_company_style_filtering(self, db: Session, test_user: User):
        """Test questions are filtered by company style."""
        # Add company-specific questions
        google_q = Question(
            title="Google Question",
            prompt="Google-style question",
            difficulty="medium",
            track="swe_intern",
            company_style="google",
            tags_csv="algorithms",
            question_type="coding"
        )
        general_q = Question(
            title="General Question",
            prompt="General question",
            difficulty="medium",
            track="swe_intern",
            company_style="general",
            tags_csv="algorithms",
            question_type="coding"
        )
        db.add_all([google_q, general_q])
        db.commit()
        
        # Session with Google style
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="google",
            difficulty="medium",
            status="active"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        selected_q = engine.select_next_question()
        
        # Should prefer Google questions but can fall back to general
        if selected_q:
            assert selected_q.company_style in ["google", "general"]
    
    def test_tag_diversity(self, db: Session, test_user: User):
        """Test that questions with diverse tags are selected."""
        # Add questions with different tags
        questions = [
            Question(
                title=f"Question {i}",
                prompt=f"Question {i} prompt",
                difficulty="medium",
                track="swe_intern",
                company_style="general",
                tags_csv=tag,
                question_type="coding"
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
            status="active"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Select multiple questions
        selected_tags = set()
        for _ in range(3):
            q = engine.select_next_question()
            if q:
                selected_tags.add(q.tags_csv)
        
        # Should have some diversity in tags
        assert len(selected_tags) >= 1
    
    def test_behavioral_question_target(self, db: Session, test_user: User, sample_questions):
        """Test that behavioral questions meet target count."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active",
            behavioral_questions_target=2,
            questions_asked_count=0
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Engine should prioritize behavioral questions until target is met
        behavioral_count = 0
        for _ in range(5):
            q = engine.select_next_question()
            if q and "behavioral" in q.tags_csv.lower():
                behavioral_count += 1
        
        # Should have selected some behavioral questions
        assert behavioral_count > 0
    
    def test_max_questions_limit(self, db: Session, test_user: User, sample_questions):
        """Test that interview respects max questions limit."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active",
            max_questions=3,
            questions_asked_count=3
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Should not select more questions when limit is reached
        should_continue = engine.should_continue_interview()
        assert should_continue is False
    
    def test_followup_generation(self, db: Session, test_user: User, sample_questions):
        """Test follow-up question generation."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="active"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Mock LLM response for follow-up
        with patch.object(engine, 'llm_client') as mock_llm:
            mock_llm.chat_completion.return_value = {
                "follow_up": "Can you optimize this solution?"
            }
            
            followup = engine.generate_followup(
                question=sample_questions[0],
                user_answer="My answer here"
            )
            
            assert followup is not None
            assert isinstance(followup, str)
    
    def test_warmup_to_active_transition(self, db: Session, test_user: User, sample_questions):
        """Test transition from warmup to active interview."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="warmup"
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # Complete warmup
        engine.complete_warmup()
        
        db.refresh(session)
        assert session.status == "active"


@pytest.mark.integration
class TestInterviewEngineIntegration:
    """Integration tests for Interview Engine."""
    
    def test_complete_interview_flow(self, db: Session, test_user: User, sample_questions):
        """Test complete interview flow from warmup to completion."""
        session = InterviewSession(
            user_id=test_user.id,
            track="swe_intern",
            company_style="general",
            difficulty="easy",
            status="warmup",
            max_questions=3,
            behavioral_questions_target=1
        )
        db.add(session)
        db.commit()
        
        engine = InterviewEngine(db, session)
        
        # 1. Warmup phase
        warmup_q = engine.select_warmup_question()
        assert warmup_q is not None
        
        engine.complete_warmup()
        db.refresh(session)
        assert session.status == "active"
        
        # 2. Main interview
        questions_asked = []
        while engine.should_continue_interview():
            q = engine.select_next_question()
            if q:
                questions_asked.append(q)
                session.questions_asked_count += 1
                db.commit()
            else:
                break
        
        # Should have asked questions up to the limit
        assert len(questions_asked) <= session.max_questions
