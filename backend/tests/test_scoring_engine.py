"""
Tests for Scoring Engine.

Tests cover:
- Finalize uses LLM output when available
- Finalize falls back on LLM errors
- Evaluation persistence
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from app.crud import evaluation as evaluation_crud
from app.models.interview_session import InterviewSession
from app.models.message import Message
from app.models.user import User
from app.services.llm_client import LLMClientError
from app.services.scoring_engine import ScoringEngine


def _create_session(db: Session, user_id: int, track: str = "swe_intern") -> InterviewSession:
    session = InterviewSession(
        user_id=user_id,
        track=track,
        company_style="general",
        difficulty="easy",
        difficulty_current="easy",
        stage="question",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _add_messages(db: Session, session_id: int) -> None:
    db.add_all(
        [
            Message(session_id=session_id, role="interviewer", content="Question 1"),
            Message(session_id=session_id, role="student", content="Answer 1"),
        ]
    )
    db.commit()


@pytest.mark.unit
class TestScoringEngine:
    """Test suite for Scoring Engine."""

    @pytest.mark.asyncio
    async def test_finalize_with_llm(self, db: Session, test_user: User):
        """Test finalize uses LLM output and stores evaluation."""
        session = _create_session(db, test_user.id)
        _add_messages(db, session.id)

        engine = ScoringEngine()
        llm_payload = {
            "overall_score": 82,
            "rubric": {
                "communication": 7,
                "problem_solving": 8,
                "correctness_reasoning": 7,
                "complexity": 6,
                "edge_cases": 6,
            },
            "strengths": ["Clear explanation"],
            "weaknesses": ["Missed an edge case"],
            "next_steps": ["Discuss trade-offs earlier"],
        }

        with patch.object(engine.llm, "chat_json", new=AsyncMock(return_value=llm_payload)):
            result = await engine.finalize(db, session.id)

        assert result["overall_score"] == 82
        assert result["rubric"]["communication"] == 7
        assert result["summary"]["strengths"] == ["Clear explanation"]

        stored = evaluation_crud.get_evaluation(db, session.id)
        assert stored is not None
        assert stored.overall_score == 82

    @pytest.mark.asyncio
    async def test_finalize_fallback(self, db: Session, test_user: User):
        """Test finalize falls back when LLM fails."""
        session = _create_session(db, test_user.id)
        _add_messages(db, session.id)

        engine = ScoringEngine()
        with patch.object(engine.llm, "chat_json", new=AsyncMock(side_effect=LLMClientError("boom"))):
            result = await engine.finalize(db, session.id)

        assert result["overall_score"] == 50
        assert "rubric" in result
        assert "summary" in result

        stored = evaluation_crud.get_evaluation(db, session.id)
        assert stored is not None
        assert stored.overall_score == 50

    @pytest.mark.asyncio
    async def test_finalize_empty_transcript(self, db: Session, test_user: User):
        """Test finalize handles empty transcript gracefully."""
        session = _create_session(db, test_user.id)

        engine = ScoringEngine()
        with patch.object(engine.llm, "chat_json", new=AsyncMock(side_effect=LLMClientError("boom"))):
            result = await engine.finalize(db, session.id)

        assert "overall_score" in result
        assert "summary" in result
