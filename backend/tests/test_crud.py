"""
Tests for CRUD operations.

Tests cover:
- User CRUD operations
- Session CRUD operations
- Question CRUD operations
- Message CRUD operations
- Evaluation CRUD operations
"""

import pytest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.evaluation import get_evaluation, upsert_evaluation
from app.crud.message import add_message, list_messages
from app.crud.question import get_question as get_question_by_id
from app.crud.question import list_questions
from app.crud.session import create_session, get_session, update_stage
from app.crud.user import create_user, get_by_email
from app.models.interview_session import InterviewSession
from app.models.user import User


# Helper functions to match test expectations (aliases for actual CRUD functions)
def get_user_by_email(db, email: str):
    """Alias for get_by_email."""
    return get_by_email(db, email)


def get_user_by_id(db, user_id: int):
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


# Define test-specific schemas that don't exist in the actual app
class UserCreate(BaseModel):
    """Test schema for creating users."""

    email: str
    password: str
    full_name: str | None = None


class SessionCreate(BaseModel):
    """Test schema for creating sessions."""

    track: str
    company_style: str
    difficulty: str


class MessageCreate(BaseModel):
    """Test schema for creating messages."""

    role: str
    content: str


class EvaluationCreate(BaseModel):
    """Test schema for creating evaluations."""

    overall_score: int
    rubric: dict
    summary: dict


def create_user_from_data(db, user_data):
    """Adapter for create_user using test schema."""
    return create_user(db, user_data.email, user_data.password, user_data.full_name)


def create_session_from_data(db, session_data, user_id: int):
    """Adapter for create_session using test schema."""
    return create_session(
        db=db,
        user_id=user_id,
        role="SWE Intern",
        track=session_data.track,
        company_style=session_data.company_style,
        difficulty=session_data.difficulty,
    )


# Helper aliases for message CRUD to match test expectations
def create_message(db, message_data, session_id):
    """Alias for add_message that accepts MessageCreate schema."""
    return add_message(db, session_id, message_data.role, message_data.content)


def get_session_messages(db, session_id):
    """Alias for list_messages."""
    return list_messages(db, session_id)


# Helper aliases for evaluation CRUD to match test expectations
def create_evaluation(db, evaluation_data, session_id):
    """Alias for upsert_evaluation that accepts EvaluationCreate schema."""
    return upsert_evaluation(db, session_id, evaluation_data.overall_score, evaluation_data.rubric, evaluation_data.summary)


def get_evaluation_by_session(db, session_id):
    """Alias for get_evaluation."""
    return get_evaluation(db, session_id)


@pytest.mark.unit
@pytest.mark.crud
class TestUserCRUD:
    """Test suite for User CRUD operations."""

    def test_create_user(self, db: Session):
        """Test creating a new user."""
        user_data = UserCreate(email="crud@example.com", password="CrudTest123!", full_name="CRUD Test User")

        user = create_user_from_data(db, user_data)

        assert user.id is not None
        assert user.email == "crud@example.com"
        assert user.full_name == "CRUD Test User"
        assert user.password_hash != "CrudTest123!"  # Should be hashed
        assert user.is_verified is False  # Default

    def test_get_user_by_email(self, db: Session, test_user: User):
        """Test retrieving user by email."""
        user = get_user_by_email(db, test_user.email)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    def test_get_user_by_email_not_found(self, db: Session):
        """Test retrieving non-existent user returns None."""
        user = get_user_by_email(db, "nonexistent@example.com")

        assert user is None

    def test_get_user_by_id(self, db: Session, test_user: User):
        """Test retrieving user by ID."""
        user = get_user_by_id(db, test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    def test_get_user_by_id_not_found(self, db: Session):
        """Test retrieving non-existent user by ID returns None."""
        user = get_user_by_id(db, 99999)

        assert user is None


@pytest.mark.unit
@pytest.mark.crud
class TestSessionCRUD:
    """Test suite for Session CRUD operations."""

    def test_create_session(self, db: Session, test_user: User):
        """Test creating a new interview session."""
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")

        session = create_session_from_data(db, session_data, test_user.id)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.track == "swe_intern"
        assert session.company_style == "general"
        assert session.difficulty == "easy"
        assert session.stage == "intro"

    def test_get_session(self, db: Session, test_user: User):
        """Test retrieving a session by ID."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="google", difficulty="medium")
        created_session = create_session_from_data(db, session_data, test_user.id)

        # Retrieve session
        retrieved_session = get_session(db, created_session.id)

        assert retrieved_session is not None
        assert retrieved_session.id == created_session.id
        assert retrieved_session.company_style == "google"

    def test_update_session_status(self, db: Session, test_user: User):
        """Test updating session status."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Update stage
        updated_session = update_stage(db, session, "active")

        assert updated_session.stage == "active"

    def test_get_user_sessions(self, db: Session, test_user: User):
        """Test retrieving all sessions for a user."""
        # Create multiple sessions
        for _i in range(3):
            session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
            create_session_from_data(db, session_data, test_user.id)

        # Get all sessions for user
        sessions = db.query(InterviewSession).filter(InterviewSession.user_id == test_user.id).all()

        assert len(sessions) == 3


@pytest.mark.unit
@pytest.mark.crud
class TestQuestionCRUD:
    """Test suite for Question CRUD operations."""

    def test_get_question_by_id(self, db: Session, sample_questions):
        """Test retrieving a question by ID."""
        question = get_question_by_id(db, sample_questions[0].id)

        assert question is not None
        assert question.id == sample_questions[0].id
        assert question.title == sample_questions[0].title

    def test_get_questions_by_filters(self, db: Session, sample_questions):
        """Test filtering questions by various criteria."""
        questions = list_questions(db, track="swe_intern", company_style=None, difficulty="easy")

        assert len(questions) > 0
        for q in questions:
            assert q.track == "swe_intern"
            assert q.difficulty == "easy"

    def test_get_questions_by_company_style(self, db: Session, sample_questions):
        """Test filtering questions by company style."""
        questions = list_questions(db, track=None, company_style="general", difficulty=None)

        assert len(questions) > 0
        for q in questions:
            assert q.company_style == "general"

    def test_get_questions_by_tags(self, db: Session, sample_questions):
        """Test filtering questions by tags (in-memory filter as DB helper doesn't support tags)."""
        all_questions = list_questions(db, track=None, company_style=None, difficulty=None)
        questions = [q for q in all_questions if (q.tags_csv or "").lower().find("array") != -1]

        assert len(questions) > 0
        for q in questions:
            assert "array" in (q.tags_csv or "").lower()

    def test_get_behavioral_questions(self, db: Session, sample_questions):
        """Test filtering behavioral questions (in-memory based on tags)."""
        all_questions = list_questions(db, track=None, company_style=None, difficulty=None)
        questions = [q for q in all_questions if (q.tags_csv or "").lower().find("behavioral") != -1]

        assert len(questions) > 0
        for q in questions:
            assert "behavioral" in (q.tags_csv or "").lower()


@pytest.mark.unit
@pytest.mark.crud
class TestMessageCRUD:
    """Test suite for Message CRUD operations."""

    def test_create_message(self, db: Session, test_user: User):
        """Test creating a message."""
        # Create session first
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Create message
        message_data = MessageCreate(role="student", content="This is a test message")
        message = create_message(db, message_data, session.id)

        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == "student"
        assert message.content == "This is a test message"
        assert message.created_at is not None

    def test_get_session_messages(self, db: Session, test_user: User):
        """Test retrieving all messages for a session."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Create multiple messages
        messages_data = [
            MessageCreate(role="student", content="Message 1"),
            MessageCreate(role="interviewer", content="Message 2"),
            MessageCreate(role="student", content="Message 3"),
        ]

        for msg_data in messages_data:
            create_message(db, msg_data, session.id)

        # Retrieve messages
        messages = get_session_messages(db, session.id)

        assert len(messages) == 3
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Message 2"
        assert messages[2].content == "Message 3"

    def test_messages_ordered_by_timestamp(self, db: Session, test_user: User):
        """Test that messages are retrieved in chronological order."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Create messages
        for i in range(5):
            message_data = MessageCreate(role="student" if i % 2 == 0 else "interviewer", content=f"Message {i}")
            create_message(db, message_data, session.id)

        # Retrieve messages
        messages = get_session_messages(db, session.id)

        # Verify order
        for i in range(len(messages) - 1):
            assert messages[i].created_at <= messages[i + 1].created_at


@pytest.mark.unit
@pytest.mark.crud
class TestEvaluationCRUD:
    """Test suite for Evaluation CRUD operations."""

    def test_create_evaluation(self, db: Session, test_user: User):
        """Test creating an evaluation."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Create evaluation
        evaluation_data = EvaluationCreate(
            overall_score=85,
            rubric={"communication": 9, "problem_solving": 8},
            summary={
                "strengths": ["Good communication", "Clear thinking"],
                "weaknesses": ["Could improve time complexity analysis"],
                "next_steps": ["Discuss complexity trade-offs sooner"],
            },
        )
        evaluation = create_evaluation(db, evaluation_data, session.id)

        assert evaluation.id is not None
        assert evaluation.session_id == session.id
        assert evaluation.overall_score == 85
        assert evaluation.rubric.get("communication") == 9
        assert len(evaluation.summary.get("strengths", [])) == 2
        assert len(evaluation.summary.get("weaknesses", [])) == 1

    def test_get_evaluation_by_session(self, db: Session, test_user: User):
        """Test retrieving evaluation by session ID."""
        # Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)

        # Create evaluation
        evaluation_data = EvaluationCreate(
            overall_score=75,
            rubric={"communication": 8},
            summary={
                "strengths": ["Good effort"],
                "weaknesses": ["Needs practice"],
                "next_steps": ["Practice more mock interviews"],
            },
        )
        created_eval = create_evaluation(db, evaluation_data, session.id)

        # Retrieve evaluation
        retrieved_eval = get_evaluation_by_session(db, session.id)

        assert retrieved_eval is not None
        assert retrieved_eval.id == created_eval.id
        assert retrieved_eval.overall_score == 75


@pytest.mark.integration
@pytest.mark.crud
class TestCRUDIntegration:
    """Integration tests for CRUD operations."""

    def test_complete_interview_data_flow(self, db: Session, test_user: User, sample_questions):
        """Test complete data flow: user -> session -> messages -> evaluation."""
        # 1. Create session
        session_data = SessionCreate(track="swe_intern", company_style="general", difficulty="easy")
        session = create_session_from_data(db, session_data, test_user.id)
        assert session.id is not None

        # 2. Add messages
        messages_data = [
            MessageCreate(role="interviewer", content="Hello! Let's start the interview."),
            MessageCreate(role="student", content="I'm ready!"),
            MessageCreate(role="interviewer", content="Great! Here's your first question..."),
        ]

        for msg_data in messages_data:
            create_message(db, msg_data, session.id)

        messages = get_session_messages(db, session.id)
        assert len(messages) == 3

        # 3. Update session stage
        update_stage(db, session, "completed")
        updated_session = get_session(db, session.id)
        assert updated_session.stage == "completed"

        # 4. Create evaluation
        evaluation_data = EvaluationCreate(
            overall_score=88,
            rubric={"clarity": 9, "correctness": 8, "efficiency": 7},
            summary={
                "strengths": ["Excellent communication", "Strong problem-solving"],
                "weaknesses": ["Could optimize solutions better"],
                "next_steps": ["Practice explaining trade-offs earlier"],
            },
        )
        evaluation = create_evaluation(db, evaluation_data, session.id)
        assert evaluation.id is not None

        # 5. Verify complete data
        final_session = get_session(db, session.id)
        final_messages = get_session_messages(db, session.id)
        final_evaluation = get_evaluation_by_session(db, session.id)

        assert final_session.stage == "completed"
        assert len(final_messages) == 3
        assert final_evaluation.overall_score == 88
