"""
Pytest configuration and fixtures for InterviewPrep-App tests.

This module provides shared fixtures for database setup, test client,
authentication, and common test data.
"""

import contextlib
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.db.base import Base
from app.main import app
from app.models.question import Question
from app.models.user import User

# Use SQLite in-memory database for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.

    Yields:
        Session: SQLAlchemy database session
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database dependency override.

    Args:
        db: Database session fixture

    Yields:
        TestClient: FastAPI test client
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """
    Create a test user in the database.

    Args:
        db: Database session fixture

    Returns:
        User: Created test user
    """
    user = user_crud.create_user(db=db, email="test@example.com", password="TestPassword123!", full_name="Test User")
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """
    Generate JWT token for test user.

    Args:
        test_user: Test user fixture

    Returns:
        str: JWT access token
    """
    return create_access_token(subject=test_user.email)


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """
    Create authorization headers with test user token.

    Args:
        test_user_token: JWT token fixture

    Returns:
        dict: Headers dictionary with Authorization
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def sample_questions(db: Session) -> list[Question]:
    """
    Create sample questions for testing.

    Args:
        db: Database session fixture

    Returns:
        list[Question]: List of created questions
    """
    questions_data = [
        {
            "title": "Two Sum",
            "prompt": "Given an array of integers, return indices of two numbers that add up to target.",
            "difficulty": "easy",
            "track": "swe_intern",
            "company_style": "general",
            "tags_csv": "array,hash-table",
            "question_type": "coding",
            "followups": [],
            "meta": {},
        },
        {
            "title": "Binary Tree Traversal",
            "prompt": "Implement inorder traversal of a binary tree.",
            "difficulty": "medium",
            "track": "swe_intern",
            "company_style": "general",
            "tags_csv": "tree,dfs",
            "question_type": "coding",
            "followups": [],
            "meta": {},
        },
        {
            "title": "Tell me about yourself",
            "prompt": "Describe your background and experience.",
            "difficulty": "easy",
            "track": "swe_intern",
            "company_style": "general",
            "tags_csv": "behavioral,introduction",
            "question_type": "behavioral",
            "followups": [],
            "meta": {},
        },
    ]

    questions = []
    for q_data in questions_data:
        question = Question(**q_data)
        db.add(question)
        questions.append(question)

    db.commit()
    for q in questions:
        db.refresh(q)

    return questions


@pytest.fixture
def mock_llm_response():
    """
    Provide a mock LLM response for testing.

    Returns:
        dict: Mock LLM API response
    """
    return {
        "choices": [
            {"message": {"content": '{"response": "This is a test response", "follow_up": "Can you explain more?"}'}}
        ]
    }


@pytest.fixture
def mock_tts_response():
    """
    Provide a mock TTS response for testing.

    Returns:
        bytes: Mock audio data
    """
    return b"mock_audio_data"


# Cleanup test database file after all tests
def pytest_sessionfinish(session, exitstatus):
    """Clean up test database file after test session."""
    if os.path.exists("./test.db"):
        with contextlib.suppress(Exception):
            engine.dispose()
        with contextlib.suppress(PermissionError):
            os.remove("./test.db")
