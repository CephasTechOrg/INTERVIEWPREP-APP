# Interview Prep AI - Complete End-to-End Project Understanding

**Last Updated:** February 23, 2026  
**Project Type:** Full-Stack Web Application  
**Technology Stack:** Python/FastAPI Backend + Next.js/TypeScript Frontend + PostgreSQL

---

## 📋 Executive Summary

**Interview Prep AI** is a full-stack mock interview platform that helps candidates practice technical and behavioral interviews with AI-driven follow-ups and comprehensive scoring. The system uses DeepSeek LLM for intelligent interviewing with fallback mechanisms, comprehensive session tracking, and rubric-based evaluation.

**Key Value Proposition:**

- Realistic interview simulation with adaptive difficulty
- AI-powered dynamic follow-ups
- Comprehensive performance analytics
- Local deployment with PostgreSQL backend
- JWT authentication with email verification

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (Next.js Frontend App)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Pages: Login, Signup, Dashboard, Interview, Results      │   │
│  │ Components: ChatUI, QuestionDisplay, Timer, Analytics    │   │
│  │ State: Zustand (auth, session, UI)                       │   │
│  │ API Client: Axios with token interceptor                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────────────────┘
                        │ HTTPS/HTTPS
                        │ Bearer Token Auth
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│              FastAPI Backend (Python)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ /api/v1/                                                 │   │
│  │  ├─ auth/ (signup, login, verify, password-reset)       │   │
│  │  ├─ sessions/ (CRUD, messages, finalize)                │   │
│  │  ├─ questions/ (retrieve by ID)                          │   │
│  │  ├─ analytics/ (performance, results)                    │   │
│  │  ├─ ai/ (LLM status)                                     │   │
│  │  ├─ voice/ (TTS generation)                              │   │
│  │  └─ users/ (profile management)                          │   │
│  │                                                           │   │
│  │ Core Services:                                            │   │
│  │  ├─ InterviewEngine: Question selection, flow control    │   │
│  │  ├─ ScoringEngine: Evaluation & rubric scoring           │   │
│  │  ├─ DeepSeekClient: LLM API integration                  │   │
│  │  ├─ TTS Service: Audio generation                        │   │
│  │  └─ RAG Service: Semantic knowledge base                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────────────────┘
                        │ SQL Queries
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│         PostgreSQL Database (Docker Container)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Tables:                                                   │   │
│  │  ├─ users: Authentication & profiles                     │   │
│  │  ├─ interview_sessions: Session metadata & state         │   │
│  │  ├─ questions: Question bank                             │   │
│  │  ├─ messages: Chat history                               │   │
│  │  ├─ evaluations: Scoring & rubrics                       │   │
│  │  ├─ session_questions: Session→Question mapping          │   │
│  │  ├─ session_feedback: User ratings                       │   │
│  │  └─ (more: embeddings, audit_log, etc)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Technology Stack Details

### Backend (Python/FastAPI)

- **Framework:** FastAPI 0.115.6 (async Python web framework)
- **Database:** PostgreSQL 16 + SQLAlchemy 2.0 ORM + Alembic migrations
- **Async Runtime:** Uvicorn 0.34.0
- **Authentication:** PyJWT + Argon2 password hashing
- **LLM Integration:** DeepSeek API via httpx (async HTTP client)
- **Text-to-Speech:** ElevenLabs + custom fallback
- **Embeddings:** Sentence-transformers (for RAG/semantic search)
- **Email:** SMTP support (SendGrid or custom)
- **Testing:** Pytest + pytest-asyncio
- **Code Quality:** Black, Ruff, MyPy

### Frontend (Next.js/TypeScript)

- **Framework:** Next.js 16.1.6 with React 19.2.3
- **Language:** TypeScript 5
- **State Management:** Zustand 5.0.11 (lightweight Jotai alternative)
- **HTTP Client:** Axios 1.13.4 with interceptors
- **API Query:** TanStack React Query 5.90.20
- **Styling:** Tailwind CSS 3.4.17
- **Testing:** Vitest 4.0.18 + React Testing Library
- **Build Tool:** Next.js built-in (Webpack)

### Infrastructure

- **Containerization:** Docker + Docker Compose
- **Database Container:** PostgreSQL:16
- **Port Mapping:** Backend (8000), Frontend (3000), DB (5432)

---

## 🔄 Core Data Models & Relationships

### User Model

```python
- id (PK)
- email (unique, indexed)
- full_name
- role_pref (e.g., "SWE Intern")
- profile (JSON - preferences)
- password_hash
- is_verified
- verification_token
- reset_token
- created_at
```

### InterviewSession Model

```python
- id (PK)
- user_id (FK → User)
- role, track, company_style, difficulty
- difficulty_current (adaptive)
- stage (intro|question|followups|evaluation|done)
- questions_asked_count
- followups_used
- max_questions (default: 7)
- max_followups_per_question (default: 2)
- behavioral_questions_target (default: 2)
- skill_state (JSON - running rubric scores)
- current_question_id
- created_at
```

### Question Model

```python
- id (PK)
- track (e.g., "swe_intern")
- company_style (e.g., "google")
- difficulty (easy|medium|hard)
- title, prompt (text)
- tags_csv (comma-separated: "arrays,sorting,medium")
- followups (JSON - optional dataset-driven followups)
- question_type (coding|system_design|behavioral|conceptual)
- meta (JSON - additional metadata)
```

### Message Model

```python
- id (PK)
- session_id (FK → InterviewSession)
- role (interviewer|student|system)
- content (text)
- created_at
```

### Evaluation Model

```python
- id (PK)
- session_id (FK → InterviewSession, unique)
- overall_score (0-100)
- rubric (JSON - {communication, problem_solving, correctness, complexity, edge_cases})
- summary (JSON - {strengths, weaknesses, next_steps})
- created_at
```

---

## 🎯 Interview Flow - Complete End-to-End Workflow

### 1. User Authentication (Session Initiation)

**Frontend:**

```
User types email/password → Click "Sign Up"
↓
POST /api/v1/auth/signup
↓
Backend creates pending_signup row, sends verification code
↓
Frontend enters 6-digit code → Click "Verify"
↓
POST /api/v1/auth/verify
↓
Backend creates User, returns JWT token
↓
Frontend stores token in localStorage, redirects to dashboard
```

**Backend auth flow:**

- `hash_password()` - Argon2 hashing for storage
- `create_access_token()` - JWT creation with email claim
- Rate limiting on signup (6 calls/min per IP+email)
- Email verification code sent via SMTP or logged to console

### 2. Session Creation & Configuration

**Frontend:**

```
User selects role, track, company, difficulty
↓
POST /api/v1/sessions
  {
    "track": "swe_intern",
    "company_style": "google",
    "difficulty": "medium",
    "behavioral_questions_target": 2
  }
↓
Backend validates inputs, creates InterviewSession row
↓
Response: SessionOut with session.id
```

**Backend:**

- `_validate_session_inputs()` - Validates against ALLOWED_TRACKS, etc.
- Creates session with `stage=intro` and `difficulty_current=easy` (adaptive)
- Sets up skill_state tracking structure

### 3. Warmup Phase (First Message)

**Frontend:**

```
POST /api/v1/sessions/{id}/start
↓
Backend generates warmup greeting
↓
Response: First interviewer message
```

**Backend (InterviewEngine.warmup_greeting):**

- Creates personalized interviewer profile (name, gender, company style)
- Returns greeting: "Hi, I'm [Name]. I work at [Company]. How are you?"
- Stores interviewer profile in session.skill_state
- Updates stage to "question"

**Example Output:**

```
"Hi, I'm Sarah, and I'll be your interviewer from Google today.
Let's get started! How are you doing?"
```

### 4. Main Interview Loop (Question & Answer)

**Iteration (5-7 questions typically):**

#### Step 4a: Get Current Question

```
Backend InterviewEngine picks next question:
1. Determine pool: questions matching track/company/current_difficulty
2. Filter by already_seen (UserQuestionSeen)
3. Apply tag diversity: prefer new tags, avoid duplicates
4. Select behavioral vs technical based on target
5. Return question to frontend
```

**Question Selection Algorithm:**

- **Difficulty Adaptation:** Start easy, adjust based on performance
- **Tag Diversity:** Track tags_seen, prefer new domains
- **Behavioral Mix:** Track behavioral_questions_asked vs target
- **Company Style:** Match company_style (google, apple, general)

#### Step 4b: User Answers

```
Frontend:
User types/speaks answer → Click "Send"
↓
POST /api/v1/sessions/{id}/message
  {
    "input_mode": "text|voice|code",
    "content": "I would use a HashMap..."
  }
↓
Backend:
1. Quick rubric score user response (0-10 on each dimension)
2. Update skill_state running average
3. Call LLM to generate AI follow-up (or use fallback)
4. Return AI message
↓
Frontend renders AI message in chat
```

**Backend Processing (POST /sessions/{id}/message):**

1. **Input Validation:**
   - Trim & check length (max 5000 chars)
   - Handle code blocks, voice transcription

2. **Quick Rubric Scoring:**
   - LLM or heuristic scores: communication, problem_solving, correctness, complexity, edge_cases
   - Each 0-10, clamped
   - Example: `{"communication": 7, "problem_solving": 6, ...}`

3. **Skill State Tracking:**

   ```json
   skill_state: {
     "n": 3,  // number of responses scored
     "sum": {"communication": 20, ...},  // cumulative scores
     "last": {"communication": 6, ...}   // last response scores
   }
   ```

4. **Follow-up Generation:**
   - Check if user said "I don't know" or "move on" → use fallback follow-up
   - Check if response too vague → prompt for detail
   - Check if reanchoring needed (went off topic) → redirect
   - Call LLM with system prompt + context
   - Store follow-up as interviewer message

#### Step 4c: Follow-ups (Max 2 per question)

```
If followups_used < max_followups_per_question:
  User can ask for clarification or request follow-up
  ↓
  Backend generates and stores follow-up message
  ↓
  Next iteration: check if max followups reached

If followups_used >= max or user ready:
  Move to next question
```

### 5. Finalization & Scoring

**When all questions complete (questions_asked_count >= max_questions):**

```
Frontend:
POST /api/v1/sessions/{id}/finalize
↓
Backend (ScoringEngine):
1. Retrieve all messages (transcript)
2. Detect which questions were asked (from session_questions)
3. Build rubric context (include behavioral rubric if applicable)
4. Optionally retrieve RAG context from similar sessions
5. Call LLM: "Score this interview using the rubric..."
6. Parse response: {overall_score, rubric, strengths, weaknesses, next_steps}
7. Store Evaluation row
8. Trigger embedding generation for future RAG
↓
Response: Evaluation with score (0-100) + detailed breakdown
```

**Scoring Rubric:**

```json
{
  "overall_score": 72,
  "rubric": {
    "communication": 7,
    "problem_solving": 7,
    "correctness_reasoning": 6,
    "complexity": 8,
    "edge_cases": 5
  },
  "strengths": [
    "Clear explanation of approach",
    "Considered edge cases early",
    "Good communication of tradeoffs"
  ],
  "weaknesses": [
    "Could have optimized space complexity",
    "Didn't discuss follow-up improvements",
    "Minor syntax errors in pseudocode"
  ],
  "next_steps": [
    "Practice space optimization techniques",
    "Work on system design at scale",
    "Review common edge cases in similar problems"
  ]
}
```

### 6. Results & Analytics (Post-Interview)

**Frontend:**

```
GET /api/v1/analytics/sessions/{id}/results
↓
Backend returns: full evaluation, session metadata, performance trends
↓
Frontend displays: score, rubric breakdown, feedback, comparison to prior sessions
```

---

## 📁 Project Directory Structure

### Backend Directory (`backend/`)

```
backend/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
├── alembic.ini                      # Alembic config
├── seed.py                          # Data seeding script
├── create_test_user.py              # Test user creation
│
├── alembic/                         # Database migrations
│   ├── env.py                       # Migration environment
│   ├── script.py.mako               # Migration template
│   └── versions/                    # Migration files (*.py)
│
├── app/
│   ├── main.py                      # FastAPI setup, middleware, lifespan
│   │
│   ├── api/v1/
│   │   ├── router.py                # Main V1 router
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── sessions.py              # Interview session endpoints
│   │   ├── questions.py             # Question retrieval endpoints
│   │   ├── analytics.py             # Analytics endpoints
│   │   ├── ai.py                    # LLM status endpoint
│   │   ├── voice.py                 # TTS endpoints
│   │   ├── users.py                 # User profile endpoints
│   │   ├── feedback.py              # Session feedback endpoints
│   │   ├── embeddings.py            # RAG embeddings endpoints
│   │   └── chat_threads.py          # Chat thread endpoints (future)
│   │
│   ├── models/                      # SQLAlchemy models
│   │   ├── user.py
│   │   ├── interview_session.py
│   │   ├── question.py
│   │   ├── message.py
│   │   ├── evaluation.py
│   │   ├── session_question.py
│   │   ├── session_feedback.py
│   │   ├── session_embedding.py
│   │   ├── chat_thread.py
│   │   ├── audit_log.py
│   │   ├── pending_signup.py
│   │   ├── user_question_seen.py
│   │   └── (others...)
│   │
│   ├── schemas/                     # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── question.py
│   │   ├── evaluation.py
│   │   └── (others...)
│   │
│   ├── crud/                        # Database CRUD operations
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── question.py
│   │   ├── message.py
│   │   ├── evaluation.py
│   │   └── (others...)
│   │
│   ├── services/                    # Business logic
│   │   ├── interview_engine.py      # Core interview flow & Q selection
│   │   ├── interview_warmup.py      # Warmup logic
│   │   ├── scoring_engine.py        # Evaluation & scoring
│   │   ├── llm_client.py            # DeepSeek API client
│   │   ├── llm_schemas.py           # LLM response schemas
│   │   ├── prompt_templates.py      # System/user prompts for LLM
│   │   ├── rubric_loader.py         # Rubric context building
│   │   ├── rag_service.py           # Semantic search service
│   │   ├── session_embedder.py      # Embedding generation
│   │   └── tts/                     # Text-to-speech
│   │       ├── tts_service.py
│   │       ├── elevenlabs_tts.py
│   │       └── default_tts.py
│   │
│   ├── core/                        # Configuration & utilities
│   │   ├── config.py                # Settings (env vars)
│   │   ├── security.py              # JWT, hashing, auth logic
│   │   ├── email.py                 # Email sending
│   │   ├── constants.py             # Constants (allowed tracks, etc)
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   ├── session.py               # Database session management
│   │   ├── init_db.py               # Database initialization
│   │   └── (others...)
│   │
│   ├── utils/
│   │   ├── audit.py                 # Audit logging
│   │   └── (others...)
│   │
│   └── api/deps.py                  # Dependency injection (get_db, get_current_user)
│
├── tests/                           # Pytest test suite
│   ├── test_auth.py
│   ├── test_sessions.py
│   ├── test_interview_engine.py
│   └── (others...)
│
├── scripts/                         # Utility scripts
│   ├── init_migrations.py
│   ├── reset_db.py
│   └── (others...)
│
└── htmlcov/                         # Coverage reports
```

### Frontend Directory (`frontend-next/`)

```
frontend-next/
├── package.json                     # Dependencies
├── tsconfig.json                    # TypeScript config
├── vitest.config.ts                 # Test config
├── next.config.ts                   # Next.js config
├── tailwind.config.js               # Tailwind config
├── postcss.config.mjs               # PostCSS config
│
├── src/
│   ├── app/                         # Next.js App Router
│   │   ├── layout.tsx               # Root layout
│   │   ├── page.tsx                 # Home/dashboard page
│   │   ├── globals.css              # Global styles
│   │   ├── favicon.ico
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx             # Login page
│   │   ├── signup/
│   │   │   └── page.tsx             # Signup page
│   │   ├── verify/
│   │   │   └── page.tsx             # Email verification page
│   │   ├── forgot-password/
│   │   ├── reset-password/
│   │   └── (other pages...)
│   │
│   ├── components/
│   │   ├── layout/                  # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── (others...)
│   │   │
│   │   ├── sections/                # Full-page sections
│   │   │   ├── DashboardSection.tsx # Session list & creation
│   │   │   ├── InterviewSection.tsx # Main interview UI
│   │   │   ├── ChatSection.tsx      # Chat message display
│   │   │   ├── ResultsSection.tsx   # Post-interview results
│   │   │   ├── HistorySection.tsx   # Session history
│   │   │   ├── PerformanceSection.tsx # Analytics
│   │   │   └── (others...)
│   │   │
│   │   ├── modals/
│   │   │   ├── CreateSessionModal.tsx
│   │   │   └── (others...)
│   │   │
│   │   ├── ui/                      # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Spinner.tsx
│   │   │   └── (others...)
│   │   │
│   │   ├── providers/
│   │   │   └── Providers.tsx        # App-level providers (Zustand, Query)
│   │   │
│   │   └── (other components...)
│   │
│   ├── lib/
│   │   ├── api.ts                   # Axios instance & base API client
│   │   │
│   │   ├── services/
│   │   │   ├── authService.ts       # Auth API calls
│   │   │   ├── sessionService.ts    # Session API calls
│   │   │   ├── questionService.ts   # Question API calls
│   │   │   ├── chatService.ts       # Chat/message API calls
│   │   │   ├── analyticsService.ts  # Analytics API calls
│   │   │   └── aiService.ts         # AI status API calls
│   │   │
│   │   ├── stores/
│   │   │   ├── authStore.ts         # Zustand: Auth state
│   │   │   ├── sessionStore.ts      # Zustand: Interview session state
│   │   │   └── uiStore.ts           # Zustand: UI state (modals, toasts)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts           # Auth context hook
│   │   │   ├── useSession.ts        # Session context hook
│   │   │   └── (others...)
│   │   │
│   │   └── utils/
│   │       ├── formatters.ts        # Date, number formatting
│   │       └── (others...)
│   │
│   ├── types/
│   │   ├── api.ts                   # API request/response types
│   │   ├── session.ts               # Session-related types
│   │   └── (others...)
│   │
│   ├── __tests__/
│   │   ├── components/
│   │   └── lib/
│   │
│   └── public/                      # Static assets
│       ├── (icons, images, etc)
│
└── .env.local                       # Local environment variables
```

### Data Directory (`data/`)

```
data/
├── questions/
│   ├── swe_intern/
│   │   ├── behavioral.json
│   │   ├── coding_easy.json
│   │   ├── coding_medium.json
│   │   ├── coding_hard.json
│   │   └── (other categories)
│   │
│   ├── swe_engineer/
│   ├── data_science/
│   ├── devops_cloud/
│   ├── product_management/
│   ├── cybersecurity/
│   └── (other tracks...)
│
└── rubrics/
    ├── behavioral_rubric.json
    ├── technical_rubric.json
    └── (other rubric definitions)
```

---

## 🔐 Authentication & Security Flow

### Signup Process

```
1. User submits email + password + name
   ↓
2. Backend generates 6-digit verification code, stores in pending_signup
   ↓
3. Email sent (or logged to console if SMTP unavailable)
   ↓
4. User enters code in verification form
   ↓
5. Backend validates code, creates User row, marks is_verified=True
   ↓
6. JWT token generated and returned
   ↓
7. Frontend stores token in localStorage["access_token"]
```

### Request Authentication

```
Frontend sends every API request with:
  Authorization: Bearer <JWT_TOKEN>
  ↓
Backend (get_current_user dependency):
  1. Extract token from header
  2. Decode JWT using SECRET_KEY
  3. Extract email from payload
  4. Query User by email
  5. Attach User to request context
  ↓
If token invalid/expired: 401 Unauthorized
If user not found: 401 Unauthorized
```

### Token Structure

```
JWT Payload: {
  "sub": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567000
}
```

---

## 📊 Key Backend Services

### InterviewEngine (interview_engine.py)

**Responsibilities:**

- Question selection algorithm (adaptive difficulty, tag diversity)
- Warmup greeting generation
- Follow-up generation (LLM or fallback)
- Conversational quality rules (handle "move on", vague answers, off-topic)
- Running skill state tracking

**Key Methods:**

- `warmup_greeting(session)` → First AI message
- `pick_next_question(db, session)` → Select next question
- `generate_ai_response(db, session, user_message)` → Full LLM response + follow-up
- `should_prompt_for_detail(message)` → Detect vague answers
- `_update_skill_state(db, session, scores)` → Track running averages

**Fallback Mechanisms:**

- If DeepSeek unavailable: Use deterministic follow-ups from question.followups JSON
- If no LLM response: Return conservative follow-ups like "Can you elaborate?"
- If skill_state unavailable: Default to "easy" difficulty

### ScoringEngine (scoring_engine.py)

**Responsibilities:**

- Transcript compilation from messages
- Rubric context building
- LLM evaluation call
- Score calibration and validation
- Evaluation storage

**Key Methods:**

- `finalize(db, session_id)` → Async scoring
- `_fallback_evaluation_data()` → Conservative fallback scores
- `_calibrate_overall_score()` → Adjust based on rubric signals

**Output Schema (EvaluationOutput):**

```json
{
  "overall_score": 72,
  "rubric": {
    "communication": 7,
    "problem_solving": 7,
    "correctness_reasoning": 6,
    "complexity": 8,
    "edge_cases": 5
  },
  "strengths": ["..."],
  "weaknesses": ["..."],
  "next_steps": ["..."]
}
```

### DeepSeekClient (llm_client.py)

**Responsibilities:**

- HTTP calls to DeepSeek API
- Retry logic with exponential backoff
- Request/response logging
- Health status tracking
- Error handling and fallback signaling

**Key Methods:**

- `chat(system_prompt, user_prompt, history)` → Text response
- `chat_json(system_prompt, user_prompt)` → JSON response (parsed)
- `_post_with_retries()` → HTTP with retry logic
- Exposed as `/api/v1/ai/status` for frontend badge

### TTS Service (tts/)

**Responsibilities:**

- Audio generation for interview playback
- ElevenLabs API integration with fallback
- Voice selection and caching

**Components:**

- `elevenlabs_tts.py` - Primary TTS provider
- `default_tts.py` - Fallback (gTTS or offline TTS)
- `tts_service.py` - Abstraction layer

---

## 💾 Database Design

### Schema Overview

**Core Tables:**

- `users` - User accounts
- `interview_sessions` - Interview instances
- `questions` - Question bank
- `messages` - Chat history
- `evaluations` - Scoring results
- `session_questions` - Session→Question mapping
- `user_question_seen` - Track which questions user has seen (prevent repeats)

**Supporting Tables:**

- `session_embedding` - Embeddings for RAG
- `chat_thread` - Multi-turn conversation threads (future)
- `session_feedback` - User ratings/feedback
- `audit_log` - Authentication audit trail
- `pending_signup` - Pending email verification

### Key Indexes

- `users(email)` - Fast login lookup
- `interview_sessions(user_id)` - Fast session listing
- `messages(session_id)` - Fast message retrieval
- `questions(track, company_style, difficulty)` - Fast question selection
- `user_question_seen(user_id, question_id)` - Prevent repeats

### Migrations (Alembic)

- Managed in `backend/alembic/versions/`
- Run `alembic upgrade head` to apply all pending migrations
- Run `alembic revision --autogenerate -m "description"` to create new migrations

---

## 🎬 How to Run Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+ (or Docker)

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (use .env.example as template)
# Set DATABASE_URL, SECRET_KEY, DEEPSEEK_API_KEY (optional)

# 5. Run migrations
alembic upgrade head

# 6. Seed questions (optional)
python seed.py --questions

# 7. Start backend
uvicorn app.main:app --reload
```

Backend will be available at `http://127.0.0.1:8000`

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend-next

# 2. Install dependencies
npm install

# 3. Create .env.local
# Set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1

# 4. Start dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

### Database Setup (Docker)

```bash
# From project root
docker-compose up -d

# Creates PostgreSQL container with environment variables from .env
```

---

## 🧪 Testing

### Backend Tests (Pytest)

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_sessions.py

# Run with verbose output
pytest -v
```

**Test Structure:**

- `tests/test_auth.py` - Authentication endpoints
- `tests/test_sessions.py` - Interview flow
- `tests/test_interview_engine.py` - Question selection
- `tests/test_scoring_engine.py` - Evaluation logic

### Frontend Tests (Vitest)

```bash
cd frontend-next

# Run all tests
npm run test

# Run with watch mode
npm run test

# Run with coverage
npm run test:coverage
```

---

## 📈 Deployment Considerations

### Production Checklist

1. **Environment Variables:**
   - `ENV=production` (disable CORS dev mode)
   - `SECRET_KEY` - Strong random value
   - `DATABASE_URL` - Production PostgreSQL instance
   - `DEEPSEEK_API_KEY` - API key for production
   - SMTP credentials for email

2. **Security:**
   - Enable HTTPS/TLS
   - Set `CORS` to production frontend domain only
   - Use strong database passwords
   - Rotate secrets regularly

3. **Database:**
   - Run migrations on production
   - Set up automated backups
   - Monitor query performance

4. **Monitoring:**
   - Log all errors to centralized logging
   - Monitor API response times
   - Alert on LLM failures

---

## 🔄 State Management

### Frontend State (Zustand)

**AuthStore:**

- `user` - Current authenticated user
- `token` - JWT access token
- `isAuthenticated` - Auth state
- Methods: `login()`, `logout()`, `setUser()`

**SessionStore:**

- `currentSession` - Active interview session
- `messages` - Chat messages
- `evaluation` - Final scoring
- Methods: `createSession()`, `addMessage()`, `finalize()`

**UIStore:**

- `isLoading` - Global loading state
- `toast` - Toast notifications
- `modals` - Modal visibility state
- Methods: `showToast()`, `openModal()`, `closeModal()`

---

## 🚀 Key Features & Advanced Flows

### 1. Adaptive Difficulty

- Start at `easy`
- Track running skill scores in `session.skill_state`
- Adjust `difficulty_current` based on performance
- Questions selected from matching difficulty tier

### 2. Tag Diversity

- Track `tags_seen` in skill_state
- Prefer questions with new tags
- Avoid repeated tag combinations
- Ensure coverage across domains

### 3. Behavioral Question Mix

- Target: 2 behavioral questions per session
- Track `behavioral_questions_asked` in skill_state
- Maintain mix even as difficulty increases

### 4. RAG (Retrieval-Augmented Generation)

- After session finalization, generate embeddings
- Store in `session_embedding` table
- Retrieve similar past sessions for scoring context
- Improves evaluation consistency

### 5. Session Embeddings & Knowledge Base

- `session_embedder.py` generates embeddings for:
  - Session transcripts (SessionEmbedding)
  - User responses (ResponseExample)
- Used to find similar past sessions for RAG
- Enables transfer learning across candidates

---

## 📋 Important Files Quick Reference

| File                                                         | Purpose              |
| ------------------------------------------------------------ | -------------------- |
| `backend/app/main.py`                                        | FastAPI app setup    |
| `backend/app/services/interview_engine.py`                   | Core interview logic |
| `backend/app/services/scoring_engine.py`                     | Evaluation scoring   |
| `backend/app/services/llm_client.py`                         | LLM integration      |
| `backend/app/api/v1/sessions.py`                             | Session endpoints    |
| `backend/app/models/`                                        | Database models      |
| `frontend-next/src/lib/api.ts`                               | API client           |
| `frontend-next/src/lib/stores/`                              | Zustand state        |
| `frontend-next/src/components/sections/InterviewSection.tsx` | Main interview UI    |
| `data/questions/`                                            | Question datasets    |

---

## 🐛 Known Limitations & TODO

See `EDGE_CASES_TODO.md` for tracked issues (31 edge cases across 4 phases):

**Phase 1 (Critical - Do First):**

- Finalize race conditions
- Session message locking
- Behavioral target validation

**Phase 2 (High Priority):**

- Message size limits
- Score validation
- Error recovery

**Phase 3 (Medium):**

- Cache optimization
- Database indexing
- Query performance

**Phase 4 (Backlog):**

- Advanced analytics
- Export features
- Integrations

---

## 🎓 Key Concepts to Understand

1. **JWT Authentication** - Stateless token-based auth
2. **SQLAlchemy ORM** - Python-to-SQL object mapping
3. **Async/await** - FastAPI async patterns with httpx
4. **Zustand** - Lightweight state management (vs Redux)
5. **LLM Integration** - Prompt engineering + fallback handling
6. **Adaptive Algorithms** - Dynamic difficulty + question selection
7. **RAG (Retrieval-Augmented Generation)** - Context-aware AI responses
8. **Event-Driven Architecture** - Session flows as state machines

---

## 📞 Support & Debugging

### Common Issues

**"Cannot connect to backend"**

- Check backend is running: `uvicorn app.main:app --reload`
- Verify DATABASE_URL and Postgres is running
- Check CORS settings in `backend/app/main.py`

**"Database migrations failed"**

- Run: `alembic upgrade head`
- Check Postgres connection string
- Verify user has permissions

**"LLM responses unavailable"**

- Check DEEPSEEK_API_KEY is set
- Verify DeepSeek API is accessible
- Check `/api/v1/ai/status` endpoint for health

**"Questions not loading"**

- Run: `python seed.py --questions`
- Check questions exist in `data/questions/`
- Verify database migrations have run

---

**This document provides a complete end-to-end understanding of the Interview Prep AI system.**
**For specific implementation details, refer to the source code files listed above.**
