# InterviewPrep-App Test Suite

Comprehensive test suite for the InterviewPrep-App backend, covering authentication, LLM integration, interview engine, scoring, CRUD operations, API endpoints, and TTS services.

## 📋 Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Test Coverage](#test-coverage)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)
- [CI Integration](#ci-integration)

---

## Overview

This test suite provides comprehensive coverage of the InterviewPrep-App backend:

| Test File | Coverage | Lines | Description |
|-----------|----------|-------|-------------|
| `test_auth.py` | Authentication & Authorization | 300+ | Signup, login, JWT, verification |
| `test_llm_client.py` | LLM Integration | 350+ | DeepSeek API, retries, fallbacks |
| `test_interview_engine.py` | Interview Logic | 400+ | Question selection, adaptive difficulty |
| `test_scoring_engine.py` | Evaluation | 300+ | Rubric scoring, strengths/weaknesses |
| `test_crud.py` | Database Operations | 400+ | Users, sessions, questions, messages |
| `test_api_endpoints.py` | REST API | 350+ | All major endpoints |
| `test_tts.py` | Text-to-Speech | 300+ | ElevenLabs, fallback handling |

**Total: 100+ test cases, 2,500+ lines of test code**

---

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements-dev.txt
```

This installs:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking utilities
- `pytest-cov` - Coverage reporting
- `httpx` - HTTP client for testing
- `respx` - HTTP mocking
- `ruff`, `black`, `mypy` - Code quality tools

### 2. Database Configuration

Tests use **SQLite in-memory database** by default (no setup required).

For PostgreSQL testing (optional):
```bash
# Set in .env or environment
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
```

### 3. Verify Setup

```bash
pytest --version
pytest --collect-only  # List all tests without running
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with extra verbose output
pytest -vv

# Run and show print statements
pytest -s
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=app

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux

# Generate XML coverage report (for CI)
pytest --cov=app --cov-report=xml
```

### Run by Test Markers

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Authentication tests
pytest -m auth

# LLM client tests
pytest -m llm

# TTS service tests
pytest -m tts

# Database CRUD tests
pytest -m crud

# Slow-running tests
pytest -m slow
```

### Run Specific Tests

```bash
# Run specific test file
pytest tests/test_auth.py

# Run specific test class
pytest tests/test_auth.py::TestAuthentication

# Run specific test function
pytest tests/test_auth.py::TestAuthentication::test_login_success

# Run tests matching pattern
pytest -k "login"
pytest -k "test_llm"
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4
```

### Stop on First Failure

```bash
pytest -x  # Stop on first failure
pytest --maxfail=3  # Stop after 3 failures
```

---

## Test Structure

### Directory Layout

```
backend/tests/
├── __init__.py              # Package initialization
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_llm_client.py       # LLM client tests
├── test_interview_engine.py # Interview engine tests
├── test_scoring_engine.py   # Scoring engine tests
├── test_crud.py             # CRUD operation tests
├── test_api_endpoints.py    # API endpoint tests
└── test_tts.py              # TTS service tests
```

### Fixtures (conftest.py)

Common fixtures available to all tests:

#### Database Fixtures
- `db` - Fresh SQLite in-memory database session for each test
- `sample_questions` - Pre-populated sample questions

#### Authentication Fixtures
- `test_user` - Pre-created verified user
- `test_user_token` - JWT token for test user
- `auth_headers` - Authorization headers with Bearer token

#### Client Fixtures
- `client` - FastAPI TestClient with database override

#### Mock Fixtures
- `mock_llm_response` - Mock LLM API response
- `mock_tts_response` - Mock TTS audio data

### Test Markers

Tests are organized with pytest markers for selective execution:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Integration tests (DB, external services)
@pytest.mark.auth          # Authentication tests
@pytest.mark.llm           # LLM client tests
@pytest.mark.tts           # TTS service tests
@pytest.mark.crud          # Database CRUD tests
@pytest.mark.slow          # Long-running tests
@pytest.mark.asyncio       # Async tests (auto-applied)
```

---

## Test Coverage

### Coverage Goals by Component

| Component | Target | Priority |
|-----------|--------|----------|
| Authentication | 80%+ | Critical (security) |
| LLM Client | 70%+ | High (error handling) |
| Interview Engine | 70%+ | High (core logic) |
| Scoring Engine | 65%+ | High (evaluation) |
| CRUD Operations | 75%+ | High (data integrity) |
| API Endpoints | 60%+ | Medium (integration) |
| TTS Services | 60%+ | Medium (fallbacks) |

**Overall Target: 65-70% code coverage**

### Current Coverage

Run to see current coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

### Coverage by Test File

- **test_auth.py**: Authentication flows, JWT, password hashing
- **test_llm_client.py**: API calls, retries, timeouts, fallbacks, health tracking
- **test_interview_engine.py**: Question selection, difficulty adaptation, warmup
- **test_scoring_engine.py**: Rubric scoring, evaluation generation
- **test_crud.py**: Database operations for all models
- **test_api_endpoints.py**: REST API endpoints, error handling
- **test_tts.py**: TTS services, ElevenLabs integration, fallbacks

---

## Writing New Tests

### Guidelines

1. **Use appropriate markers**: `@pytest.mark.unit` or `@pytest.mark.integration`
2. **Descriptive test names**: `test_<action>_<expected_result>`
3. **Follow AAA pattern**: Arrange, Act, Assert
4. **Mock external services**: Use `respx` for HTTP, `patch` for functions
5. **Test both success and failure cases**
6. **Keep tests isolated**: Each test should be independent
7. **Use fixtures**: Leverage existing fixtures from `conftest.py`

### Example: Unit Test

```python
import pytest
from app.services.some_service import SomeService

@pytest.mark.unit
def test_service_processes_data_correctly():
    """Test that service processes data as expected."""
    # Arrange
    service = SomeService()
    input_data = {"key": "value"}
    
    # Act
    result = service.process(input_data)
    
    # Assert
    assert result["status"] == "success"
    assert "processed" in result
```

### Example: Integration Test with Database

```python
import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.crud.user import create_user
from app.schemas.user import UserCreate

@pytest.mark.integration
@pytest.mark.crud
def test_create_user_in_database(db: Session):
    """Test creating a user in the database."""
    # Arrange
    user_data = UserCreate(
        email="test@example.com",
        password="SecurePass123!",
        full_name="Test User"
    )
    
    # Act
    user = create_user(db, user_data)
    
    # Assert
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.hashed_password != "SecurePass123!"
```

### Example: API Test

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_api_endpoint_returns_data(client: TestClient, auth_headers):
    """Test API endpoint returns expected data."""
    # Act
    response = client.get("/api/v1/sessions", headers=auth_headers)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### Example: Async Test with Mocking

```python
import pytest
import respx
from httpx import Response

@pytest.mark.unit
@pytest.mark.llm
@pytest.mark.asyncio
async def test_llm_client_handles_timeout():
    """Test LLM client handles timeout gracefully."""
    import httpx
    from app.services.llm_client import DeepSeekClient, LLMClientError
    
    # Arrange
    respx.post("https://api.deepseek.com/chat/completions").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )
    
    client = DeepSeekClient()
    
    # Act & Assert
    with pytest.raises(LLMClientError):
        await client.chat_completion(messages=[{"role": "user", "content": "test"}])
```

### Adding New Test Files

1. Create file: `tests/test_<component>.py`
2. Import pytest and required modules
3. Add test class (optional): `class Test<Component>:`
4. Write test functions: `def test_<scenario>():`
5. Add appropriate markers
6. Use fixtures from `conftest.py`

---

## Troubleshooting

### Common Issues

#### Issue: `ImportError: No module named 'app'`
**Solution**: Run tests from `backend/` directory or set PYTHONPATH:
```bash
cd backend
pytest
# OR
PYTHONPATH=backend pytest
```

#### Issue: Database connection errors
**Solution**: Tests use SQLite in-memory by default. If using PostgreSQL:
```bash
# Ensure PostgreSQL is running
docker-compose up -d

# Or use SQLite (default)
unset TEST_DATABASE_URL
```

#### Issue: Async tests failing
**Solution**: Ensure `pytest-asyncio` is installed and `asyncio_mode = auto` in pytest.ini:
```bash
pip install pytest-asyncio
```

#### Issue: Mock not working
**Solution**: Check import paths and use correct patch target:
```python
# Wrong
@patch('app.services.llm_client.httpx')

# Correct
@patch('httpx.AsyncClient.post')
```

#### Issue: Tests pass locally but fail in CI
**Solution**: Check for:
- Environment variables
- Database configuration
- File paths (use `Path` for cross-platform compatibility)
- Timezone differences

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show local variables on failure
pytest -l

# Show print statements
pytest -s

# Increase verbosity
pytest -vv
```

### Logging During Tests

```python
import logging

def test_with_logging(caplog):
    """Test with log capture."""
    with caplog.at_level(logging.INFO):
        # Your test code
        pass
    
    assert "expected log message" in caplog.text
```

---

## CI Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests with coverage
      run: |
        cd backend
        pytest --cov=app --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
```

### Pre-commit Hook

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

Install:
```bash
pip install pre-commit
pre-commit install
```

---

## Best Practices

### Do's ✅

- ✅ Write tests before fixing bugs (TDD)
- ✅ Keep tests simple and focused
- ✅ Use descriptive test names
- ✅ Test edge cases and error conditions
- ✅ Mock external dependencies
- ✅ Use fixtures for common setup
- ✅ Run tests before committing
- ✅ Maintain test coverage above 65%

### Don'ts ❌

- ❌ Don't test implementation details
- ❌ Don't write tests that depend on each other
- ❌ Don't use real external APIs in tests
- ❌ Don't commit failing tests
- ❌ Don't skip writing tests for "simple" code
- ❌ Don't test third-party library code
- ❌ Don't use sleep() for timing (use mocks)

---

## Quick Reference

### Most Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run unit tests only
pytest -m unit

# Run specific file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run in parallel
pytest -n 4
```

### Most Used Fixtures

```python
def test_example(db, client, test_user, auth_headers):
    """Example using common fixtures."""
    # db: Database session
    # client: FastAPI test client
    # test_user: Pre-created user
    # auth_headers: Auth headers with token
    pass
```

### Most Used Markers

```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test
@pytest.mark.asyncio       # Async test
@pytest.mark.parametrize   # Parameterized test
```

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [respx Documentation](https://lundberg.github.io/respx/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## Support

For questions or issues with the test suite:

1. Check this README
2. Review existing tests for examples
3. Check pytest documentation
4. Ask in project discussions

---

**Last Updated**: 2024
**Test Suite Version**: 1.0.0
**Target Coverage**: 65-70%
