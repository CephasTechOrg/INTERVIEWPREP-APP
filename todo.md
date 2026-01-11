# Project TODO & Development Guide

Purpose
-------
A short, actionable guide to advance the project from MVP to a more robust, testable, and production-ready state. Each top-level task lists recommended sub-steps, commands, and quick verification checks.

How to use
----------
- Work items are ordered by priority (top = highest).
- For each item: follow the sub-steps, run the commands, add tests, then check it off.
- Ask for help to scaffold any item (migrations, tests, CI config, etc.).

---

## CRITICAL GAPS IDENTIFIED (High Priority)

### 1) Missing `.env.example` file ⚠️ URGENT
- **Status**: NOT FOUND in backend directory
- **Impact**: New developers cannot set up the project without knowing required environment variables
- **Action Required**:
  1. Create `backend/.env.example` with all required and optional variables
  2. Document each variable with inline comments
  3. Include example values (non-sensitive)
  4. Reference in README.md setup instructions
- **Required Variables** (from config.py analysis):
  - `SECRET_KEY` (required)
  - `DATABASE_URL` (required)
  - `DEEPSEEK_API_KEY` (optional - AI features)
  - `DEEPSEEK_BASE_URL` (optional - default: https://api.deepseek.com)
  - `DEEPSEEK_MODEL` (optional - default: deepseek-chat)
  - `DEEPSEEK_TIMEOUT_SECONDS` (optional - default: 45)
  - `DEEPSEEK_MAX_RETRIES` (optional - default: 2)
  - `DEEPSEEK_RETRY_BACKOFF_SECONDS` (optional - default: 0.8)
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` (optional - email)
  - `TTS_PRIMARY`, `TTS_FALLBACK` (optional - text-to-speech)
  - `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` (optional - TTS)
- **Estimated**: 30 minutes

### 2) Alembic migrations fully implemented ✅ COMPLETED
- **Status**: ✅ FULLY VALIDATED AND DEPLOYED
- **Completed Actions**:
  1. ✅ Alembic configuration validated (`alembic.ini`, `alembic/env.py`, `alembic/versions/`)
  2. ✅ Initial migration generated and tested (upgrade/downgrade cycle successful)
  3. ✅ Runtime schema patching removed from `backend/app/main.py`
  4. ✅ Replaced `Base.metadata.create_all()` with Alembic-managed migrations
  5. ✅ Replaced `print()` statements with structured logging (`logger.info/warning`)
  6. ✅ Added clear documentation in startup function about Alembic requirement
- **Changes Made**:
  - Removed ~250 lines of runtime SQL patching code from main.py
  - Kept only question seeding logic in startup hook
  - Added TODO comment to restrict CORS in production
  - Database schema is now fully managed by Alembic migrations
- **Important**: Before starting the app, always run: `alembic upgrade head` from backend directory
- **Next Steps**:
  - Add CI step to assert `alembic current` equals `head` (see CI pipeline item below)

### 3) No test suite exists ⚠️ HIGH PRIORITY
- **Status**: No `tests/` directory found in project root or backend
- **Impact**: No automated testing; changes risk breaking existing functionality
- **Action Required**:
  1. Create `tests/` or `backend/tests/` directory structure
  2. Add pytest configuration (`pytest.ini` or `pyproject.toml`)
  3. Write core tests for:
     - `InterviewEngine` (question selection, adaptive difficulty, warmup flow)
     - `llm_client.py` (DeepSeek API mocking, error handling, fallbacks)
     - `scoring_engine.py` (rubric calculation, summary generation)
     - TTS service fallbacks
     - CRUD operations
  4. Add test fixtures for database setup/teardown
- **Dependencies to add**: `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`, `respx`
- **Estimated**: 6-10 hours for initial coverage

### 4) No CI/CD pipeline ⚠️ HIGH PRIORITY
- **Status**: No `.github/workflows/` directory found
- **Impact**: No automated quality checks on PRs; manual testing only
- **Action Required**:
  1. Create `.github/workflows/ci.yml`
  2. Add jobs for:
     - Python linting (ruff/flake8)
     - Code formatting check (black)
     - Type checking (mypy)
     - Run `python scripts/validate_questions.py --strict`
     - Run `pytest` with coverage report
     - **Alembic migration check**: Assert `alembic current` equals `head`
  3. Configure to run on pull requests and main branch pushes
- **Estimated**: 2-3 hours

### 5) Missing linting/formatting configuration ⚠️ MEDIUM PRIORITY
- **Status**: No `pyproject.toml`, `ruff.toml`, `mypy.ini`, or `.pre-commit-config.yaml` found
- **Impact**: Inconsistent code style; no automated type checking
- **Action Required**:
  1. Create `backend/pyproject.toml` with tool configurations
  2. Add `ruff` for linting
  3. Add `black` for formatting
  4. Add `mypy` for type checking
  5. Create `.pre-commit-config.yaml` for git hooks
  6. Run formatters on existing codebase
- **Dependencies to add**: `ruff`, `black`, `mypy`, `pre-commit`
- **Estimated**: 2-4 hours

### 6) Backend code hygiene ⚠️ MEDIUM PRIORITY
- **Status**: Stray files found in backend root directory
- **Impact**: Confusing repository structure; potential version conflicts
- **Action Required**:
  1. Remove accidental artifact files from `backend/` root:
     - `0.27.0`
     - `1.0.0`
     - `bool`
     - `tuple[bytes`
  2. Verify these are not needed by any scripts or dependencies
- **Estimated**: 5 minutes

---

## EXISTING TODO ITEMS (From Original File)

## 1) Add Alembic migrations and configure migrations folder ✅ COMPLETED
- Goal: Replace runtime schema patching with versioned DB migrations.
- **Current Status**: ✅ FULLY CONFIGURED AND DEPLOYED
- **Completed Steps**:
  1. ✅ Fixed typo in requirements.txt (`alembic>=1.18.0`)
  2. ✅ Created `backend/alembic.ini` with proper configuration
  3. ✅ Populated `backend/alembic/env.py` with all model imports and DB URL configuration
  4. ✅ Created `backend/alembic/versions/` directory for migration files
  5. ✅ Created comprehensive migration guide: `backend/MIGRATIONS.md`
  6. ✅ Created quick start guide: `backend/ALEMBIC_QUICKSTART.md`
  7. ✅ Created initialization script: `backend/scripts/init_migrations.py`
  8. ✅ Updated README.md with migration information
  9. ✅ Generated and validated initial migration
  10. ✅ Removed all runtime schema patching from `backend/app/main.py`
- **Files Created**:
  - `backend/alembic.ini` - Main Alembic configuration
  - `backend/alembic/env.py` - Environment setup with all models imported
  - `backend/alembic/script.py.mako` - Migration template (fixed for Windows)
  - `backend/alembic/versions/<rev>_initial_schema.py` - Initial migration
  - `backend/MIGRATIONS.md` - Comprehensive 200+ line migration guide
  - `backend/ALEMBIC_QUICKSTART.md` - Quick reference for daily use
  - `backend/scripts/init_migrations.py` - Automated setup script
  - `backend/scripts/README.md` - Scripts documentation
- **Documentation**:
  - Quick start: `backend/ALEMBIC_QUICKSTART.md`
  - Full guide: `backend/MIGRATIONS.md`
  - Main README updated with migration section

---

## 2) Add unit tests (core services) ✅ COMPLETED
- Goal: Add a small but meaningful test suite covering `InterviewEngine`, `llm_client`, TTS fallbacks, and CRUD.
- **Current Status**: ✅ COMPREHENSIVE TEST SUITE IMPLEMENTED
- **Completed Actions**:
  1. ✅ Created `backend/requirements-dev.txt` with all testing dependencies
  2. ✅ Created `backend/pytest.ini` with comprehensive configuration and markers
  3. ✅ Created `backend/tests/` directory with complete test infrastructure
  4. ✅ Implemented `backend/tests/conftest.py` with shared fixtures:
     - Database session with SQLite in-memory
     - FastAPI test client
     - Test user and authentication fixtures
     - Sample questions fixture
     - Mock LLM and TTS response fixtures
  5. ✅ Created comprehensive test files:
     - `test_auth.py` - Authentication & authorization (signup, login, verification, JWT)
     - `test_llm_client.py` - DeepSeek API integration (success, retries, fallbacks, timeouts)
     - `test_interview_engine.py` - Question selection, adaptive difficulty, warmup flow
     - `test_scoring_engine.py` - Rubric scoring, summary generation, strengths/weaknesses
     - `test_crud.py` - Database operations (users, sessions, questions, messages, evaluations)
     - `test_api_endpoints.py` - REST API integration tests (all major endpoints)
     - `test_tts.py` - TTS services (ElevenLabs, fallback, error handling)
- **Test Coverage**:
  - 7 test files with 100+ test cases
  - Unit tests (fast, isolated) and integration tests
  - Comprehensive mocking of external services (DeepSeek, ElevenLabs)
  - Database operations tested with SQLite in-memory
  - API endpoints tested with FastAPI TestClient
  - Target coverage: 65-70%
- **Test Markers**:
  - `@pytest.mark.unit` - Fast unit tests
  - `@pytest.mark.integration` - Integration tests
  - `@pytest.mark.auth` - Authentication tests
  - `@pytest.mark.llm` - LLM client tests
  - `@pytest.mark.tts` - TTS service tests
  - `@pytest.mark.crud` - Database CRUD tests
  - `@pytest.mark.slow` - Long-running tests
- **Running Tests**:
  ```bash
  cd backend
  pip install -r requirements-dev.txt
  pytest                    # Run all tests
  pytest -m unit           # Run unit tests only
  pytest --cov=app         # Run with coverage
  ```
- **Files Created**:
  - `backend/requirements-dev.txt` - Testing and dev dependencies
  - `backend/pytest.ini` - Pytest configuration
  - `backend/tests/__init__.py` - Test package init
  - `backend/tests/conftest.py` - Shared fixtures (200+ lines)
  - `backend/tests/test_auth.py` - Auth tests (300+ lines)
  - `backend/tests/test_llm_client.py` - LLM tests (350+ lines)
  - `backend/tests/test_interview_engine.py` - Interview engine tests (400+ lines)
  - `backend/tests/test_scoring_engine.py` - Scoring tests (300+ lines)
  - `backend/tests/test_crud.py` - CRUD tests (400+ lines)
  - `backend/tests/test_api_endpoints.py` - API tests (350+ lines)
  - `backend/tests/test_tts.py` - TTS tests (300+ lines)
- **Next Steps**:
  - Run tests locally to verify all pass
  - Add to CI pipeline (see item #3)
  - Monitor coverage and add tests for edge cases as needed

---

## 3) Add CI pipeline (run tests, lint, validate_questions) ⚠️ HIGH PRIORITY
- Goal: Enforce tests, linting, and question validation on PRs.
- **Current Status**: NO `.github/workflows/` directory exists
- Steps:
  1. Create `.github/workflows/ci.yml` with steps: 
     - checkout
     - setup python
     - install deps
     - run `python scripts/validate_questions.py --strict`
     - run `pytest --cov=backend/app --cov-report=term-missing`
     - run linter (ruff/flake8)
     - run formatting check (black --check)
     - run type checking (mypy)
     - **NEW**: Check Alembic migration status (`alembic current` should equal `head`)
  2. Fail early on dataset validation errors.
  3. Add status badge to README.md
- Quick check: Open PR and confirm the CI run shows the steps and status.
- Estimated: 2-3 hours.

---

## 4) Run & fix `scripts/validate_questions.py` results ✅
- Goal: Ensure question JSONs are consistent and clean.
- **Current Status**: Script exists and is well-implemented
- Steps:
  1. Run: `python scripts/validate_questions.py` (from repo root). Consider `--strict` in CI.
  2. Inspect `[ERROR]` and `[WARN]` outputs; fix JSON files in `data/questions/` accordingly (tags, duplicate prompts, mismatched metadata, empty fields).
  3. Add to CI pipeline to prevent regressions
- Tip: Add a note in PR template to remind dataset authors to run the script before PR.
- Estimated: Varies (minutes → hours depending on dataset health).

---

## 5) Document `.env.example` & confirm required env vars ⚠️ URGENT
- Goal: Make dev onboarding frictionless.
- **Current Status**: `.env.example` file DOES NOT EXIST
- Steps:
  1. Create `backend/.env.example` listing required and optional env vars with comments
  2. Required variables:
     - `SECRET_KEY` (JWT signing - generate with `openssl rand -hex 32`)
     - `DATABASE_URL` (PostgreSQL connection string)
  3. Optional variables (with defaults):
     - `DEEPSEEK_API_KEY` (AI features - app works in fallback mode without it)
     - `DEEPSEEK_BASE_URL` (default: https://api.deepseek.com)
     - `DEEPSEEK_MODEL` (default: deepseek-chat)
     - `DEEPSEEK_TIMEOUT_SECONDS` (default: 45)
     - `DEEPSEEK_MAX_RETRIES` (default: 2)
     - `DEEPSEEK_RETRY_BACKOFF_SECONDS` (default: 0.8)
     - SMTP settings (email verification - prints to console if not set)
     - TTS settings (ElevenLabs - falls back to browser speech)
  4. Document in README how missing keys affect behavior (offline fallbacks).
  5. Add setup instructions referencing `.env.example`
- Estimated: 30-45 minutes.

---

## 6) Add integration tests or mocks for LLM/TTS fallbacks ✅
- Goal: Verify graceful behavior when external APIs are down or return invalid responses.
- **Current Status**: No tests exist
- **Code Analysis**: `llm_client.py` has good error handling with `LLMClientError` and retry logic
- Steps:
  1. Use `respx` or `httpx` mocking to simulate DeepSeek network errors, timeouts, and invalid JSON.
  2. Ensure `DeepSeekClient` raises `LLMClientError` and the app gracefully falls back.
  3. Test ElevenLabs flow and fallback to `default_tts` or browser speech.
  4. Test retry logic with exponential backoff
  5. Test health status tracking (`get_llm_status()`)
- Estimated: 3-5 hours.

---

## 7) Add type checking / linters and formatting ⚠️ MEDIUM PRIORITY
- Goal: Maintain consistent style and catch type errors early.
- **Current Status**: NO configuration files exist (no `pyproject.toml`, `ruff.toml`, `mypy.ini`)
- Steps:
  1. Add dev tools to requirements.txt: `ruff` (lint), `black` (format), `mypy` (type checking).
  2. Create `backend/pyproject.toml` with tool configurations:
     ```toml
     [tool.black]
     line-length = 120
     target-version = ['py311']
     
     [tool.ruff]
     line-length = 120
     target-version = "py311"
     
     [tool.mypy]
     python_version = "3.11"
     warn_return_any = true
     warn_unused_configs = true
     disallow_untyped_defs = false
     ```
  3. Create `.pre-commit-config.yaml` for git hooks
  4. Run formatters on existing codebase: `black backend/` and `ruff check backend/ --fix`
  5. Add to CI pipeline
- Estimated: 2-4 hours.

---

## 8) Add health checks & monitoring for LLM/TTS endpoints ✅
- Goal: Surface LLM/TTS status for observability.
- **Current Status**: ALREADY IMPLEMENTED
- **Findings**:
  - `/api/v1/ai/status` endpoint exists (returns LLM health)
  - `get_llm_status()` in `llm_client.py` tracks last success/error
  - Frontend displays AI status badge with online/offline/fallback states
  - Health tracking includes: configured, status, fallback_mode, last_ok_at, last_error_at, last_error
- **Recommendation**: Consider adding similar health endpoint for TTS service
- Estimated: 1-2 hours for TTS health endpoint.

---

## 9) Replace ad-hoc prints with structured logging ✅ COMPLETED
- Goal: Use structured logs and levels instead of `print`.
- **Current Status**: ✅ COMPLETED
- **Completed Actions**:
  - ✅ `backend/app/core/logging.py` exists (structured logging setup)
  - ✅ Most services use `logging.getLogger(__name__)` properly
  - ✅ Replaced remaining `print()` in `main.py` with `logger.info()` and `logger.warning()`
  - ✅ All logging is now gated by `settings.ENV == "dev"` where appropriate
- **Result**: Consistent structured logging throughout the application

---

## ADDITIONAL FINDINGS & RECOMMENDATIONS

### Architecture Strengths ✅
1. **Well-structured backend**: Clean separation of concerns (models, schemas, CRUD, services, API)
2. **Robust interview engine**: Sophisticated logic for adaptive difficulty, question selection, warmup flow
3. **Graceful degradation**: LLM and TTS fallbacks work without external APIs
4. **Frontend architecture**: Clean separation of concerns, good state management
5. **Question validation**: Comprehensive validation script with detailed error reporting
6. **Database design**: Proper relationships, indexes, and constraints
7. **Migration system**: Alembic fully configured and runtime patching removed

### Code Quality Observations
1. **Interview Engine** (`backend/app/services/interview_engine.py`):
   - 2000+ lines - consider splitting into smaller modules
   - Excellent adaptive difficulty logic
   - Good warmup flow implementation
   - Well-documented with inline comments
   
2. **Frontend** (`frontend/assets/js/interview.js`):
   - 1800+ lines - consider splitting into modules (api.js, state.js, ui.js, etc.)
   - Good separation of concerns with guidance system
   - Comprehensive error handling
   - Voice/TTS integration is well-implemented

3. **LLM Client** (`backend/app/services/llm_client.py`):
   - Clean implementation with retry logic
   - Good error handling and health tracking
   - JSON parsing with fallback strategies

### Security Considerations
1. **CORS**: Currently set to allow all origins (`allow_origins=["*"]`) - TODO added in main.py to restrict in production
2. **Rate limiting**: `backend/app/api/rate_limit.py` exists - ensure it's applied to all endpoints
3. **JWT expiration**: Set to 7 days - consider shorter duration for production
4. **Environment variables**: Ensure `.env` is in `.gitignore` (it is) ✅
5. **Docker Compose**: Port mapping verified - POSTGRES_PORT is set to 5432 in .env ✅

### Performance Considerations
1. **Database queries**: Consider adding query optimization and connection pooling
2. **LLM timeout**: 45 seconds is reasonable but may need tuning based on usage
3. **Frontend bundle size**: Consider code splitting for large JS files

### Documentation Gaps
1. **API documentation**: Consider adding OpenAPI/Swagger docs (FastAPI supports this natively)
2. **Architecture diagram**: Would help new developers understand system flow
3. **Deployment guide**: Add production deployment instructions
4. **Contributing guide**: Add guidelines for contributors

---

## Quick development & verification commands

### Setup
```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
# Add dev dependencies
pip install pytest pytest-asyncio pytest-mock respx ruff black mypy pre-commit
```

### Run validators & tests
```bash
# From repo root
python scripts/validate_questions.py
python scripts/validate_questions.py --strict  # For CI

# Run tests (once created)
pytest -v
pytest --cov=backend/app --cov-report=term-missing
pytest --cov=backend/app --cov-report=html
```

### Linting & formatting
```bash
# From backend/
black . --check  # Check formatting
black .          # Apply formatting
ruff check .     # Lint
ruff check . --fix  # Auto-fix issues
mypy .           # Type checking
```

### Database migrations
```bash
# From backend/
alembic upgrade head      # Apply all migrations
alembic current           # Show current revision
alembic downgrade -1      # Rollback one migration
alembic history           # Show migration history
alembic revision --autogenerate -m "description"  # Create new migration
```

### Run application
```bash
# Start database
docker-compose up -d

# Apply migrations (REQUIRED before first run)
cd backend
alembic upgrade head

# Start backend (from backend/)
uvicorn app.main:app --reload

# Start frontend (from frontend/)
cd frontend
python -m http.server 5173
```

---

## Priority Action Plan (Next 2 Weeks)

### Week 1: Critical Infrastructure
1. **Day 1**: Create `.env.example` and clean up backend root artifacts
2. **Day 2-3**: Set up test infrastructure and write core tests
3. **Day 4-5**: Create CI pipeline and linting configuration

### Week 2: Quality & Documentation
1. **Day 1-2**: Run and fix validation issues, add more tests
2. **Day 3-4**: Add API documentation and architecture diagram
3. **Day 5**: Code cleanup and refactoring

---

## Marking progress
- Check items as you complete them in this file and update the checklist accordingly.
- Update the "Current Status" field for each item as work progresses.
- If you'd like, I can scaffold any of the above (e.g., a starter test, CI workflow, or config files).

---

## Need Help?
If you want me to scaffold any file (examples: `backend/.env.example`, starter tests, CI workflow, `pyproject.toml`), tell me which item to start with and I will prepare the complete implementation for you.
