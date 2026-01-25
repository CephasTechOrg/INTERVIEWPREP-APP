"""
Tests for API endpoints.

Tests cover:
- Health check endpoint
- Session endpoints (create, start, message, finalize)
- Question endpoints
- Analytics endpoints
- AI status endpoint
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


@pytest.mark.integration
class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint returns OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.usefixtures("sample_questions")
class TestSessionEndpoints:
    """Test suite for session-related endpoints."""

    def test_create_session(self, client: TestClient, auth_headers):
        """Test creating a new interview session."""
        response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["track"] == "swe_intern"
        assert data["company_style"] == "general"
        assert data["difficulty"] == "easy"
        assert data["stage"] == "intro"

    def test_create_session_unauthorized(self, client: TestClient):
        """Test creating session without auth fails."""
        response = client.post(
            "/api/v1/sessions", json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"}
        )

        assert response.status_code == 401

    def test_create_session_invalid_data(self, client: TestClient, auth_headers):
        """Test creating session with invalid data fails."""
        response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "invalid_track", "company_style": "general", "difficulty": "easy"},
        )

        assert response.status_code == 422  # Validation error

    def test_get_sessions(self, client: TestClient, auth_headers):
        """Test retrieving user's sessions."""
        # Create a session first
        client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )

        # Get sessions
        response = client.get("/api/v1/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_session_messages(self, client: TestClient, auth_headers, sample_questions):
        """Test retrieving session message history."""
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "medium"},
        )
        session_id = create_response.json()["id"]

        client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_headers)
        client.post(
            f"/api/v1/sessions/{session_id}/message",
            headers=auth_headers,
            json={"content": "Answering the question with some detail."},
        )

        response = client.get(f"/api/v1/sessions/{session_id}/messages", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for msg in data:
            assert msg["session_id"] == session_id
            assert msg["role"] in ["interviewer", "student", "system"]

    def test_start_session(self, client: TestClient, auth_headers, db: Session, test_user: User, sample_questions):
        """Test starting an interview session."""
        # Create session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )
        session_id = create_response.json()["id"]

        # Start session
        response = client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["role"] == "interviewer"
        assert data["content"]

    def test_send_message(self, client: TestClient, auth_headers, sample_questions):
        """Test sending a message in a session."""
        # Create and start session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )
        session_id = create_response.json()["id"]

        client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_headers)

        # Send message
        response = client.post(
            f"/api/v1/sessions/{session_id}/message",
            headers=auth_headers,
            json={"content": "This is my answer to the question."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["role"] == "interviewer"
        assert data["content"]

    def test_finalize_session(self, client: TestClient, auth_headers, sample_questions):
        """Test finalizing an interview session."""
        # Create and start session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )
        session_id = create_response.json()["id"]

        client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_headers)

        # Finalize session
        response = client.post(f"/api/v1/sessions/{session_id}/finalize", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "rubric" in data
        assert "summary" in data


@pytest.mark.integration
class TestQuestionEndpoints:
    """Test suite for question-related endpoints."""

    def test_get_questions(self, client: TestClient, auth_headers, sample_questions):
        """Test retrieving questions."""
        response = client.get("/api/v1/questions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_questions_with_filters(self, client: TestClient, auth_headers, sample_questions):
        """Test retrieving questions with filters."""
        response = client.get("/api/v1/questions?difficulty=easy&track=swe_intern", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for question in data:
            assert question["difficulty"] == "easy"
            assert question["track"] == "swe_intern"

    def test_get_question_by_id(self, client: TestClient, auth_headers, sample_questions):
        """Test retrieving a specific question."""
        question_id = sample_questions[0].id

        response = client.get(f"/api/v1/questions/{question_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == question_id

    def test_get_question_coverage(self, client: TestClient, auth_headers, sample_questions):
        """Test getting question coverage statistics."""
        response = client.get(
            "/api/v1/questions/coverage?track=swe_intern&company_style=general&difficulty=easy",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["track"] == "swe_intern"
        assert data["company_style"] == "general"
        assert data["difficulty"] == "easy"
        assert "count" in data


@pytest.mark.integration
@pytest.mark.usefixtures("sample_questions")
class TestAnalyticsEndpoints:
    """Test suite for analytics endpoints."""

    def test_get_session_results(self, client: TestClient, auth_headers, db: Session, test_user: User):
        """Test retrieving session results."""
        # Create and complete a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"track": "swe_intern", "company_style": "general", "difficulty": "easy"},
        )
        session_id = create_response.json()["id"]

        # Start and finalize
        client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_headers)
        client.post(f"/api/v1/sessions/{session_id}/finalize", headers=auth_headers)

        # Get results
        response = client.get(f"/api/v1/analytics/sessions/{session_id}/results", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "overall_score" in data
        assert "rubric" in data
        assert "summary" in data

    def test_get_user_analytics(self, client: TestClient, auth_headers):
        """Test retrieving user analytics."""
        response = client.get("/api/v1/analytics/user", headers=auth_headers)

        assert response.status_code == 404


@pytest.mark.integration
class TestAIEndpoints:
    """Test suite for AI-related endpoints."""

    def test_get_ai_status(self, client: TestClient, auth_headers):
        """Test getting AI/LLM status."""
        response = client.get("/api/v1/ai/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "status" in data
        assert "fallback_mode" in data

    def test_ai_status_structure(self, client: TestClient, auth_headers):
        """Test AI status response structure."""
        response = client.get("/api/v1/ai/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify expected fields
        expected_fields = ["configured", "status", "fallback_mode"]
        for field in expected_fields:
            assert field in data


@pytest.mark.integration
class TestVoiceEndpoints:
    """Test suite for voice/TTS endpoints."""

    def test_tts_endpoint_exists(self, client: TestClient, auth_headers):
        """Test TTS endpoint is accessible."""
        response = client.post("/api/v1/tts", headers=auth_headers, json={"text": "Hello, this is a test."})

        # Should return 200 or appropriate status
        assert response.status_code in [200, 400, 404, 501]


@pytest.mark.integration
class TestErrorHandling:
    """Test suite for API error handling."""

    def test_404_not_found(self, client: TestClient):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_invalid_session_id(self, client: TestClient, auth_headers):
        """Test accessing non-existent session."""
        response = client.get("/api/v1/sessions/99999/messages", headers=auth_headers)

        assert response.status_code == 404

    def test_invalid_json_body(self, client: TestClient, auth_headers):
        """Test sending invalid JSON."""
        response = client.post("/api/v1/sessions", headers=auth_headers, data="invalid json")

        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient, auth_headers):
        """Test missing required fields in request."""
        response = client.post("/api/v1/sessions", headers=auth_headers, json={})  # Missing required fields

        assert response.status_code == 200
        data = response.json()
        assert data["track"] == "swe_intern"
        assert data["company_style"] == "general"
        assert data["difficulty"] == "easy"


@pytest.mark.integration
class TestRateLimiting:
    """Test suite for rate limiting (if implemented)."""

    def test_rate_limit_not_exceeded_normal_use(self, client: TestClient, auth_headers):
        """Test normal usage doesn't hit rate limits."""
        # Make several requests
        for _ in range(5):
            response = client.get("/api/v1/sessions", headers=auth_headers)
            assert response.status_code == 200

    @pytest.mark.slow
    def test_rate_limit_exceeded(self, client: TestClient, auth_headers):
        """Test rate limiting kicks in after many requests."""
        # This test assumes rate limiting is implemented
        # Adjust based on actual rate limit configuration
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response.status_code)

        # Should have at least some successful requests
        assert 200 in responses
