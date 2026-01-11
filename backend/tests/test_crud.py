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
from sqlalchemy.orm import Session
from datetime import datetime

from app.crud.user import create_user, get_by_email
from app.crud import user as user_crud


# Helper functions to match test expectations (aliases for actual CRUD functions)
def get_user_by_email(db, email: str):
    """Alias for get_by_email."""
    return get_by_email(db, email)


def get_user_by_id(db, user_id: int):
    """Get user by ID."""
    from app.models.user import User
    return db.query(User).filter(User.id == user_id).first()
from app.crud.session import create_session, get_session, update_stage
from app.crud.question import list_questions, get_question as get_question_by_id
from app.crud.message import create_message, get_session_messages
from app.crud.evaluation import create_evaluation, get_evaluation_by_session
from app.schemas.user import UserCreate
from app.schemas.session import SessionCreate
from app.schemas.message import MessageCreate
from app.schemas.evaluation import EvaluationCreate
from app.models.user import User
from app.models.interview_session import InterviewSession
from app.models.question import Question


@pytest.mark.unit
@pytest.mark.crud
class TestUserCRUD:
    """Test suite for User CRUD operations."""
    
    def test_create_user(self, db: Session):
        """Test creating a new user."""
        user_data = UserCreate(
            email="crud@example.com",
            password="CrudTest123!",
            full_name="CRUD Test User"
        )
        
        user = create_user(db, user_data)
        
        assert user.id is not None
        assert user.email == "crud@example.com"
        assert user.full_name == "CRUD Test User"
        assert user.hashed_password != "CrudTest123!"  # Should be hashed
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
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        
        session = create_session(db, session_data, test_user.id)
        
        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.track == "swe_intern"
        assert session.company_style == "general"
        assert session.difficulty == "easy"
        assert session.status == "created"
    
    def test_get_session(self, db: Session, test_user: User):
        """Test retrieving a session by ID."""
        # Create session
        session_data = SessionCreate(
            track="swe_intern",
            company_style="google",
            difficulty="medium"
        )
        created_session = create_session(db, session_data, test_user.id)
        
        # Retrieve session
        retrieved_session = get_session(db, created_session.id)
        
        assert retrieved_session is not None
        assert retrieved_session.id == created_session.id
        assert retrieved_session.company_style == "google"
    
    def test_update_session_status(self, db: Session, test_user: User):
        """Test updating session status."""
        # Create session
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Update stage
        updated_session = update_stage(db, session, "active")
        
        assert updated_session.stage == "active"
    
    def test_get_user_sessions(self, db: Session, test_user: User):
        """Test retrieving all sessions for a user."""
        # Create multiple sessions
        for i in range(3):
            session_data = SessionCreate(
                track="swe_intern",
                company_style="general",
                difficulty="easy"
            )
            create_session(db, session_data, test_user.id)
        
        # Get all sessions for user
        sessions = db.query(InterviewSession).filter(
            InterviewSession.user_id == test_user.id
        ).all()
        
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
        questions = list_questions(
            db,
            track="swe_intern",
            company_style=None,
            difficulty="easy"
        )
        
        assert len(questions) > 0
        for q in questions:
            assert q.track == "swe_intern"
            assert q.difficulty == "easy"
    
    def test_get_questions_by_company_style(self, db: Session, sample_questions):
        """Test filtering questions by company style."""
        questions = list_questions(
            db,
            track=None,
            company_style="general"
            ,
            difficulty=None
        )
        
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
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Create message
        message_data = MessageCreate(
            role="user",
            content="This is a test message"
        )
        message = create_message(db, message_data, session.id)
        
        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == "user"
        assert message.content == "This is a test message"
        assert message.created_at is not None
    
    def test_get_session_messages(self, db: Session, test_user: User):
        """Test retrieving all messages for a session."""
        # Create session
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Create multiple messages
        messages_data = [
            MessageCreate(role="user", content="Message 1"),
            MessageCreate(role="assistant", content="Message 2"),
            MessageCreate(role="user", content="Message 3")
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
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Create messages
        for i in range(5):
            message_data = MessageCreate(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
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
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Create evaluation
        evaluation_data = EvaluationCreate(
            overall_score=85,
            technical_score=80,
            communication_score=90,
            problem_solving_score=85,
            strengths=["Good communication", "Clear thinking"],
            weaknesses=["Could improve time complexity analysis"],
            summary="Overall good performance",
            rubric_scores={"clarity": 9, "correctness": 8}
        )
        evaluation = create_evaluation(db, evaluation_data, session.id)
        
        assert evaluation.id is not None
        assert evaluation.session_id == session.id
        assert evaluation.overall_score == 85
        assert evaluation.technical_score == 80
        assert len(evaluation.strengths) == 2
        assert len(evaluation.weaknesses) == 1
    
    def test_get_evaluation_by_session(self, db: Session, test_user: User):
        """Test retrieving evaluation by session ID."""
        # Create session
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        
        # Create evaluation
        evaluation_data = EvaluationCreate(
            overall_score=75,
            technical_score=70,
            communication_score=80,
            problem_solving_score=75,
            strengths=["Good effort"],
            weaknesses=["Needs practice"],
            summary="Decent performance",
            rubric_scores={}
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
        session_data = SessionCreate(
            track="swe_intern",
            company_style="general",
            difficulty="easy"
        )
        session = create_session(db, session_data, test_user.id)
        assert session.id is not None
        
        # 2. Add messages
        messages_data = [
            MessageCreate(role="assistant", content="Hello! Let's start the interview."),
            MessageCreate(role="user", content="I'm ready!"),
            MessageCreate(role="assistant", content="Great! Here's your first question...")
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
            technical_score=85,
            communication_score=90,
            problem_solving_score=88,
            strengths=["Excellent communication", "Strong problem-solving"],
            weaknesses=["Could optimize solutions better"],
            summary="Strong performance overall",
            rubric_scores={"clarity": 9, "correctness": 8, "efficiency": 7}
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
