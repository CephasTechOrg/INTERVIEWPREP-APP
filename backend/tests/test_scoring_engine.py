"""
Tests for Scoring Engine.

Tests cover:
- Rubric loading
- Score calculation
- Summary generation
- Strengths and weaknesses identification
- Fallback behavior when LLM unavailable
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.user import User
from app.services.scoring_engine import ScoringEngine


@pytest.mark.unit
class TestScoringEngine:
    """Test suite for Scoring Engine."""

    def test_engine_initialization(self, db: Session, test_user: User):
        """Test scoring engine initializes correctly."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)
        assert engine.db == db
        assert engine.session == session

    def test_load_rubric(self, db: Session, test_user: User):
        """Test rubric loading for different tracks."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)
        rubric = engine.load_rubric()

        assert rubric is not None
        assert isinstance(rubric, dict)

    def test_calculate_scores_with_llm(self, db: Session, test_user: User):
        """Test score calculation using LLM."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        # Add some messages
        messages = [
            Message(session_id=session.id, role="assistant", content="Question 1"),
            Message(session_id=session.id, role="user", content="Answer 1"),
            Message(session_id=session.id, role="assistant", content="Question 2"),
            Message(session_id=session.id, role="user", content="Answer 2"),
        ]
        db.add_all(messages)
        db.commit()

        engine = ScoringEngine(db, session)

        # Mock LLM response
        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "overall_score": 85,
                "technical_score": 80,
                "communication_score": 90,
                "problem_solving_score": 85,
                "strengths": ["Good communication", "Clear thinking"],
                "weaknesses": ["Could improve optimization"],
                "summary": "Strong performance overall",
            }

            scores = engine.calculate_scores()

            assert scores is not None
            assert "overall_score" in scores
            assert scores["overall_score"] == 85
            assert "strengths" in scores
            assert len(scores["strengths"]) > 0

    def test_calculate_scores_fallback(self, db: Session, test_user: User):
        """Test score calculation fallback when LLM unavailable."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        # Add messages
        messages = [
            Message(session_id=session.id, role="assistant", content="Question"),
            Message(session_id=session.id, role="user", content="Answer"),
        ]
        db.add_all(messages)
        db.commit()

        engine = ScoringEngine(db, session)

        # Mock LLM failure
        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = None

            scores = engine.calculate_scores()

            # Should return fallback scores
            assert scores is not None
            assert "overall_score" in scores
            assert isinstance(scores["overall_score"], (int, float))

    def test_generate_summary(self, db: Session, test_user: User):
        """Test summary generation."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        # Add messages
        messages = [
            Message(session_id=session.id, role="assistant", content="Tell me about yourself"),
            Message(session_id=session.id, role="user", content="I am a software engineer..."),
        ]
        db.add_all(messages)
        db.commit()

        engine = ScoringEngine(db, session)

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "summary": "Candidate showed good communication skills and technical knowledge."
            }

            summary = engine.generate_summary()

            assert summary is not None
            assert isinstance(summary, str)
            assert len(summary) > 0

    def test_identify_strengths(self, db: Session, test_user: User):
        """Test strengths identification."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "strengths": ["Excellent problem-solving approach", "Clear communication", "Good code structure"]
            }

            strengths = engine.identify_strengths()

            assert strengths is not None
            assert isinstance(strengths, list)
            assert len(strengths) > 0

    def test_identify_weaknesses(self, db: Session, test_user: User):
        """Test weaknesses identification."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "weaknesses": ["Could improve time complexity analysis", "Needs more practice with edge cases"]
            }

            weaknesses = engine.identify_weaknesses()

            assert weaknesses is not None
            assert isinstance(weaknesses, list)
            assert len(weaknesses) > 0

    def test_rubric_score_calculation(self, db: Session, test_user: User):
        """Test individual rubric criteria scoring."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "rubric_scores": {"clarity": 9, "correctness": 8, "efficiency": 7, "communication": 9}
            }

            rubric_scores = engine.calculate_rubric_scores()

            assert rubric_scores is not None
            assert isinstance(rubric_scores, dict)
            assert "clarity" in rubric_scores
            assert rubric_scores["clarity"] == 9

    def test_score_normalization(self, db: Session, test_user: User):
        """Test score normalization to 0-100 range."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        engine = ScoringEngine(db, session)

        # Test normalization
        normalized = engine.normalize_score(8, max_score=10)
        assert normalized == 80

        normalized = engine.normalize_score(5, max_score=5)
        assert normalized == 100

    def test_empty_transcript_handling(self, db: Session, test_user: User):
        """Test handling of empty interview transcript."""
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="easy", status="completed"
        )
        db.add(session)
        db.commit()

        # No messages added
        engine = ScoringEngine(db, session)
        scores = engine.calculate_scores()

        # Should handle gracefully
        assert scores is not None
        assert "overall_score" in scores


@pytest.mark.integration
class TestScoringEngineIntegration:
    """Integration tests for Scoring Engine."""

    def test_complete_scoring_flow(self, db: Session, test_user: User):
        """Test complete scoring flow from transcript to evaluation."""
        # Create completed session with messages
        session = InterviewSession(
            user_id=test_user.id, track="swe_intern", company_style="general", difficulty="medium", status="completed"
        )
        db.add(session)
        db.commit()

        # Add interview transcript
        messages = [
            Message(session_id=session.id, role="assistant", content="Tell me about yourself"),
            Message(session_id=session.id, role="user", content="I'm a CS student with 2 years experience..."),
            Message(session_id=session.id, role="assistant", content="Solve two sum problem"),
            Message(session_id=session.id, role="user", content="I would use a hash map..."),
            Message(session_id=session.id, role="assistant", content="What's the time complexity?"),
            Message(session_id=session.id, role="user", content="O(n) time and O(n) space"),
        ]
        db.add_all(messages)
        db.commit()

        # Score the interview
        engine = ScoringEngine(db, session)

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.chat_completion.return_value = {
                "overall_score": 82,
                "technical_score": 80,
                "communication_score": 85,
                "problem_solving_score": 80,
                "strengths": [
                    "Good understanding of data structures",
                    "Clear communication",
                    "Correct complexity analysis",
                ],
                "weaknesses": ["Could provide more detailed explanations", "Consider edge cases earlier"],
                "summary": "Solid performance with good technical knowledge and communication skills.",
                "rubric_scores": {"clarity": 8, "correctness": 9, "efficiency": 7, "communication": 8},
            }

            evaluation = engine.generate_evaluation()

            assert evaluation is not None
            assert evaluation["overall_score"] == 82
            assert len(evaluation["strengths"]) == 3
            assert len(evaluation["weaknesses"]) == 2
            assert "summary" in evaluation
            assert "rubric_scores" in evaluation

    def test_scoring_different_tracks(self, db: Session, test_user: User):
        """Test scoring works for different interview tracks."""
        tracks = ["swe_intern", "swe_engineer", "behavioral"]

        for track in tracks:
            session = InterviewSession(
                user_id=test_user.id, track=track, company_style="general", difficulty="easy", status="completed"
            )
            db.add(session)
            db.commit()

            # Add sample message
            message = Message(session_id=session.id, role="user", content="Sample answer")
            db.add(message)
            db.commit()

            engine = ScoringEngine(db, session)
            rubric = engine.load_rubric()

            assert rubric is not None
            assert isinstance(rubric, dict)
