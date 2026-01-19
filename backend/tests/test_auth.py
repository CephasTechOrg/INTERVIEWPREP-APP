"""
Tests for authentication and authorization.

Tests cover:
- User signup
- Email verification
- Login and JWT token generation
- Password hashing and verification
- Token validation
- Protected endpoint access
"""

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import pending_signup as pending_signup_crud
from app.crud import user as user_crud


# Helper function for decoding tokens (since it doesn't exist in security.py)
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        return None


# Helper function for hashing (alias)
def get_password_hash(password: str) -> str:
    return hash_password(password)


@pytest.mark.unit
@pytest.mark.auth
class TestAuthentication:
    """Test suite for authentication functionality."""

    def test_signup_success(self, client: TestClient, db: Session):
        """Test successful user signup."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "newuser@example.com", "password": "SecurePass123!", "full_name": "New User"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "message" in data
        pending = pending_signup_crud.get_by_email(db, "newuser@example.com")
        assert pending is not None

    def test_signup_duplicate_email(self, client: TestClient, test_user):
        """Test signup with duplicate email fails."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": test_user.email, "password": "AnotherPass123!", "full_name": "Duplicate User"},
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_weak_password(self, client: TestClient):
        """Test signup accepts weak password (no validation enforced)."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "weak@example.com", "password": "123", "full_name": "Weak Password User"},  # Too short
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_signup_invalid_email(self, client: TestClient):
        """Test signup with invalid email fails."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "SecurePass123!", "full_name": "Invalid Email User"},
        )

        assert response.status_code == 422  # Validation error

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post("/api/v1/auth/login", json={"email": test_user.email, "password": "TestPassword123!"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password fails."""
        response = client.post("/api/v1/auth/login", json={"email": test_user.email, "password": "WrongPassword123!"})

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "SomePassword123!"}
        )

        assert response.status_code == 401

    def test_login_unverified_user(self, client: TestClient, db: Session):
        """Test login with unverified user."""
        user_crud.create_user(
            db=db,
            email="unverified@example.com",
            password="SecurePass123!",
            full_name="Unverified User",
            is_verified=False,
        )

        # Try to login
        response = client.post(
            "/api/v1/auth/login", json={"email": "unverified@example.com", "password": "SecurePass123!"}
        )

        # Should fail or return specific message about verification
        assert response.status_code == 403

    def test_password_hashing(self):
        """Test password is properly hashed."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_jwt_token_creation_and_validation(self, test_user):
        """Test JWT token creation and validation."""
        token = create_access_token(subject=test_user.email)

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.get("sub") == test_user.email

    def test_jwt_token_expiration(self):
        """Test JWT token expiration."""
        # Create token with very short expiration (using expires_minutes parameter)
        token = create_access_token(subject="test@example.com", expires_minutes=-1)  # Already expired

        # Should fail to decode expired token
        payload = decode_access_token(token)
        assert payload is None

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/api/v1/sessions")

        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token fails."""
        response = client.get("/api/v1/sessions", headers={"Authorization": "Bearer invalid_token"})

        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client: TestClient, auth_headers):
        """Test accessing protected endpoint with valid token succeeds."""
        response = client.get("/api/v1/sessions", headers=auth_headers)

        assert response.status_code == 200

    def test_verify_email_success(self, client: TestClient, db: Session):
        """Test email verification success."""
        # Create user
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "verify@example.com", "password": "SecurePass123!", "full_name": "Verify User"},
        )
        assert response.status_code == 200

        pending = pending_signup_crud.get_by_email(db, "verify@example.com")
        assert pending is not None
        assert pending.verification_code is not None

        # Verify email
        response = client.post(
            "/api/v1/auth/verify", json={"email": "verify@example.com", "code": pending.verification_code}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # Check user is now verified
        user = user_crud.get_by_email(db, "verify@example.com")
        assert user is not None
        assert user.is_verified is True

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test email verification with invalid token fails."""
        response = client.post("/api/v1/auth/verify", json={"email": "nope@example.com", "code": "000000"})

        assert response.status_code == 400

    def test_token_refresh(self, client: TestClient, test_user_token):
        """Test token refresh functionality if implemented."""
        # This test assumes a refresh endpoint exists
        # Adjust based on actual implementation
        pass

    def test_logout(self, client: TestClient, auth_headers):
        """Test logout functionality if implemented."""
        # This test assumes a logout endpoint exists
        # Adjust based on actual implementation
        pass


@pytest.mark.integration
@pytest.mark.auth
class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""

    def test_complete_signup_verify_login_flow(self, client: TestClient, db: Session):
        """Test complete authentication flow: signup -> verify -> login."""
        email = "complete@example.com"
        password = "CompleteFlow123!"

        # 1. Signup
        response = client.post(
            "/api/v1/auth/signup", json={"email": email, "password": password, "full_name": "Complete Flow User"}
        )
        assert response.status_code == 200

        # 2. Get verification token
        pending = pending_signup_crud.get_by_email(db, email)
        assert pending is not None
        token = pending.verification_code

        # 3. Verify email
        response = client.post("/api/v1/auth/verify", json={"email": email, "code": token})
        assert response.status_code == 200

        # 4. Login
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # 5. Access protected endpoint
        response = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert response.status_code == 200
