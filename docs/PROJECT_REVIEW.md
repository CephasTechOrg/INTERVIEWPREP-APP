# Interview Prep AI - Comprehensive Project Review

**Date:** February 11, 2026  
**Full-Stack Application:** Python FastAPI Backend + Next.js (TypeScript/React) Frontend

---

## 🎯 Project Overview

**Interview Prep AI** is a full-stack mock interview web application designed to help candidates practice technical and behavioral interviews with AI-driven follow-ups and comprehensive scoring.

### Key Features

- Real-time interview flow with adaptive difficulty
- Dynamic question selection based on company style, role, and difficulty
- AI-powered interviewer (DeepSeek integration) with fallback mode
- Interview scoring using rubric-based evaluation
- Session history and analytics
- Voice input/output support (TTS)
- Authentication with JWT tokens
- Chat-based interview UI with code input support

---

## 📊 Architecture Overview

### Technology Stack

**Backend:**

- **Framework:** FastAPI (Python 3.x)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Migrations:** Alembic
- **LLM:** DeepSeek API with fallback to rule-based system
- **Task Queue:** Not visible in structure
- **TTS:** ElevenLabs + custom default TTS

**Frontend:**

- **Framework:** Next.js 16 (React 19, TypeScript)
- **State Management:** Zustand
- **API Client:** Axios with interceptors
- **Styling:** Tailwind CSS
- **Testing:** Vitest
- **Data Fetching:** TanStack React Query (installed but usage TBD)

**Infrastructure:**

- Docker & Docker Compose (local PostgreSQL)
- Environment configuration via .env files

---

## 🏗️ Backend Architecture

### Entry Point: `backend/app/main.py`

```
FastAPI Application
├── CORS Middleware (configurable by ENV)
├── Security Headers Middleware
├── Startup Hook: Question Seeding (dev mode only)
└── V1 Router
```

**Key Features:**

- CORS setup: Permissive in dev, regex-based for localhost/127.0.0.1
- Auto-loads questions from `data/questions/` on startup (insert-only)
- Health check endpoint: `GET /health`
- Custom security headers (X-Content-Type-Options, X-Frame-Options, CSP)

### API Routes Structure (`app/api/v1/`)

```
/api/v1/
├── /auth           (signup, login, token verification, password reset)
├── /questions      (get question by ID, list)
├── /sessions       (create, list, get messages, send message, finalize, delete)
├── /analytics      (user performance, session results)
├── /ai             (LLM status endpoint)
├── /chat_threads   (chat thread management for future features)
├── /voice          (TTS generation)
├── /users          (user profile management)
├── /feedback       (session feedback/ratings)
└── /embeddings     (RAG-related functionality)
```

### Database Models (`app/models/`)

| Model                | Purpose                                               |
| -------------------- | ----------------------------------------------------- |
| **User**             | Authentication, profile, role                         |
| **InterviewSession** | Session metadata, stage tracking, adaptive difficulty |
| **Question**         | Interview question dataset                            |
| **SessionQuestion**  | Questions assigned to specific sessions               |
| **Message**          | Chat messages (user + AI)                             |
| **Evaluation**       | Final scoring/rubric results                          |
| **SessionFeedback**  | User feedback on sessions                             |
| **ChatThread**       | Future feature for multi-turn conversations           |
| **PendingSignup**    | Email verification tokens                             |
| **UserQuestionSeen** | Track viewed questions to avoid repeats               |
| **SessionEmbedding** | RAG embeddings for sessions                           |
| **AuditLog**         | System audit trail                                    |

### Core Services (`app/services/`)

#### 1. **InterviewEngine** (`interview_engine.py`)

- **2900+ lines** - Core interview logic
- **Responsibilities:**
  - Manage interview flow (intro → warmup → behavioral → technical → followups → evaluation → done)
  - Question selection with:
    - Adaptive difficulty (starts easy, scales based on performance)
    - Behavioral question mixing (target 2-3 behavioral questions)
    - Tag diversity (avoids repetitive topics)
    - Company-style specific questions
  - Warmup handling (greeting, small talk, tone detection)
  - Follow-up generation with LLM or fallback
  - User intent classification (move-on, don't-know, vague answer detection)
  - Skill state tracking with running rubric scores

**State Management:**

- Tracks `skill_state` (running averages of rubric scores)
- `questions_asked_count`, `followups_used`
- `current_question_id`, `stage` (state machine)
- Adaptive `difficulty_current` based on performance

#### 2. **ScoringEngine** (`scoring_engine.py`)

- Final evaluation after interview completion
- Summarizes transcript into:
  - Rubric scores (communication, problem-solving, correctness, complexity, edge-cases)
  - Strengths & weaknesses summary
- Uses LLM with fallback strategy
- Validates output with Pydantic schemas

#### 3. **LLMClient** (`llm_client.py`)

- DeepSeek API integration with:
  - Retry logic with exponential backoff
  - Timeout handling (45 seconds default)
  - Health status tracking
  - Fallback mode detection
- Error tracking for frontend badge display
- Dual chat methods:
  - `chat()` - For text responses
  - `chat_json()` - For structured output (evaluations)

#### 4. **InterviewWarmup** (`interview_warmup.py`)

- Greeting personalization
- Small-talk generation
- Tone detection (formal, casual, etc.)
- Establishes rapport before technical questions

#### 5. **RAGService** (`rag_service.py`)

- Retrieval-augmented generation for context
- Session embeddings storage
- Used for potential follow-up personalization

#### 6. **TTSService** (`tts/`)

- ElevenLabs integration
- Default fallback TTS
- Generates audio for interview replay

#### 7. **RubricLoader** (`rubric_loader.py`)

- Loads evaluation criteria from config
- Defines scoring dimensions

### CRUD Layer (`app/crud/`)

Standard SQLAlchemy CRUD operations:

- `session.py` - Interview session operations
- `message.py` - Message persistence
- `question.py` - Question lookup/filtering
- `user.py` - User account operations
- `evaluation.py` - Scoring data
- Others for supporting models

### Authentication Flow

```
1. Signup (POST /auth/signup)
   ├─ Create user with hashed password
   ├─ Generate verification token
   └─ Send email (or print to console in dev)

2. Verification (GET /auth/verify/{token})
   └─ Mark user as verified

3. Login (POST /auth/login)
   ├─ Validate credentials
   └─ Return JWT token (7-day expiry)

4. Protected Routes
   └─ `Authorization: Bearer <token>` required
```

**Config:** `app/core/config.py`

- `SECRET_KEY`: JWT signing key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 7 days default
- SMTP configuration (optional)
- DeepSeek API credentials

---

## 💾 Database Schema

### Key Tables

**users**

- id, username, email, hashed_password, is_verified, created_at, updated_at

**interview_sessions**

- id, user_id, role, track, company_style
- difficulty, difficulty_current (adaptive)
- stage ('intro'|'question'|'followups'|'evaluation'|'done')
- questions_asked_count, followups_used, max_questions (7), max_followups_per_question (2)
- behavioral_questions_target (2)
- skill_state (JSON: running rubric averages)
- current_question_id
- created_at

**messages**

- id, session_id, role ('user'|'ai'), content, created_at

**questions**

- id, text, type ('technical'|'behavioral'), difficulty ('easy'|'medium'|'hard')
- tags (JSON array), company_style, rubric_focus, sample_answer

**evaluations**

- id, session_id
- rubric (JSON: {communication, problem_solving, correctness_reasoning, complexity, edge_cases})
- strengths, weaknesses, feedback
- overall_score

**session_questions**

- id, session_id, question_id, order, num_followups_used

**user_questions_seen**

- id, user_id, question_id (prevents repetition)

### Migrations

- Managed by Alembic
- Located in `alembic/versions/`
- Usage: `alembic upgrade head`

---

## 🎨 Frontend Architecture

### File Structure

```
frontend-next/
├── src/
│   ├── app/
│   │   ├── layout.tsx (root layout)
│   │   ├── page.tsx (main page)
│   │   ├── globals.css (tailwind)
│   │   ├── login/ (login page)
│   │   ├── signup/ (signup page)
│   │   ├── verify/ (email verification)
│   │   ├── forgot-password/
│   │   └── reset-password/
│   ├── components/
│   │   ├── sections/ (major page sections)
│   │   │   ├── InterviewSection.tsx (main interview UI)
│   │   │   ├── DashboardSection.tsx (session creation)
│   │   │   ├── HistorySection.tsx (past sessions)
│   │   │   ├── ResultsSection.tsx (evaluation display)
│   │   │   ├── PerformanceSection.tsx (analytics/charts)
│   │   │   ├── SettingsSection.tsx
│   │   │   └── ChartsSection.tsx
│   │   ├── modals/ (reusable dialog components)
│   │   ├── layout/ (page layout components)
│   │   ├── providers/ (context/provider components)
│   │   └── ui/ (base UI components: buttons, cards, icons)
│   ├── lib/
│   │   ├── api.ts (axios client with interceptors)
│   │   ├── services/ (business logic)
│   │   │   ├── sessionService.ts (session CRUD)
│   │   │   ├── questionService.ts (question lookup)
│   │   │   ├── chatService.ts (message handling)
│   │   │   ├── authService.ts (auth flows)
│   │   │   ├── aiService.ts (AI status)
│   │   │   └── analyticsService.ts (metrics)
│   │   ├── stores/ (Zustand state management)
│   │   │   ├── authStore.ts (user auth state)
│   │   │   ├── sessionStore.ts (current interview state)
│   │   │   └── uiStore.ts (UI state: sidebar, modals)
│   │   └── hooks/ (custom React hooks)
│   └── types/
│       └── api.ts (TypeScript interfaces for API)
├── public/ (static assets)
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.js
└── vitest.config.ts
```

### State Management (Zustand)

#### **authStore.ts**

```typescript
{
  user: { id, email, username } | null
  token: string | null
  isLoading: boolean
  isVerified: boolean

  login(email, password)
  signup(data)
  verify(token)
  logout()
  setUser(user)
}
```

#### **sessionStore.ts**

```typescript
{
  currentSession: InterviewSession | null
  messages: Message[]
  evaluation: Evaluation | null
  error: string | null

  setCurrentSession(session)
  addMessage(message)
  setMessages(messages)
  setEvaluation(eval)
  clearSession()
}
```

#### **uiStore.ts**

```typescript
{
  currentPage: "dashboard" |
    "interview" |
    "history" |
    "results" |
    "performance" |
    "settings";
  voiceEnabled: boolean;
  sidebarCollapsed: boolean;

  setCurrentPage(page);
  setVoiceEnabled(bool);
  toggleSidebar();
}
```

### API Client (`lib/api.ts`)

Axios instance with:

- **Request interceptor:** Automatically adds JWT token from localStorage
- **Response interceptor:**
  - Handles 401 (unauthorized) by redirecting to /login
  - Redirects only on non-auth endpoints
- **Error parsing:** Extracts detail messages from backend responses
- **Timeout:** 30 seconds

### Services Layer (`lib/services/`)

#### **sessionService.ts**

```typescript
createSession(data: CreateSessionRequest)
  ├─ POST /sessions
  └─ Sets currentSession in store

listSessions()
  └─ GET /sessions (with pagination)

getMessages(sessionId)
  └─ GET /sessions/{id}/messages

startSession(sessionId)
  └─ POST /sessions/{id}/start (get initial AI greeting)

sendMessage(sessionId, payload)
  ├─ POST /sessions/{id}/message
  └─ Handles text, code, voice inputs

finalizeSession(sessionId)
  ├─ POST /sessions/{id}/finalize
  └─ Triggers scoring, returns evaluation

deleteSession(sessionId)
  └─ DELETE /sessions/{id}
```

#### **questionService.ts**

```typescript
getQuestion(questionId)
  └─ GET /questions/{id} (fetch question details)
```

#### **aiService.ts**

```typescript
getStatus()
  └─ GET /ai/status (returns {configured, status, fallback_mode})

generateSpeech(text)
  └─ POST /tts (returns audio blob)
```

#### **authService.ts**

```typescript
signup(data);
login(email, password);
verify(token);
logout();
resetPassword(token, newPassword);
```

#### **chatService.ts**

```typescript
formatMessage(message)
parseUserInput(text, mode: 'text'|'code'|'voice')
buildMessagePayload(text, mode, sessionState)
```

#### **analyticsService.ts**

```typescript
getUserStats();
getSessionResults(sessionId);
getPerformanceTrends();
```

### Main Components

#### **InterviewSection.tsx** (840+ lines)

**Purpose:** Main interview UI with multi-panel layout

**Features:**

- **Left Panel:** Current question display with difficulty badge
- **Right Panel:** Chat messages + input form
- **Header:** Timer, AI status badge, action buttons
- **Input Modes:**
  - Text (textarea with auto-resize)
  - Code (code block input)
  - Voice (Web Speech API recognition)

**State Tracking:**

```typescript
- inputMode: 'text' | 'code' | 'voice'
- messageText, codeText, voiceText
- loading: {messages, sending, finalizing, ending, replaying}
- aiStatus, question, elapsedSec
- voiceSupported, isListening
- audioUnlocked (for voice playback)
```

**Key Methods:**

- `loadMessages()` - Fetch chat history on mount
- `handleSendMessage()` - Validate, format, send to API
- `startSession()` - Request initial AI greeting
- `finalizeInterview()` - Complete session and get evaluation
- `playAudio()` - TTS replay of AI messages
- `setupVoiceRecognition()` - Initialize Web Speech API

**Keyboard Shortcuts:**

- Enter to send (Shift+Enter for newline)
- Voice toggle button

#### **DashboardSection.tsx**

Create new interview session with parameters:

- Role (SWE Intern, SWE Mid, etc.)
- Track (swe_intern, data_science, etc.)
- Company style (general, FAANG, startup)
- Difficulty (easy, medium, hard)

#### **HistorySection.tsx**

Display past sessions with:

- Session metadata
- Date, duration
- Final score
- Replay/delete actions

#### **ResultsSection.tsx**

Display evaluation after session:

- Rubric scores (radar chart)
- Strengths/weaknesses
- Feedback
- Full transcript

#### **PerformanceSection.tsx**

Analytics dashboard:

- Performance trends
- Difficulty progression
- Topic distribution
- Score history

### Type Definitions (`types/api.ts`)

Key interfaces:

```typescript
User {
  id: number
  email: string
  username: string
  is_verified: boolean
}

InterviewSession {
  id: number
  user_id: number
  role: string
  track: string
  company_style: string
  difficulty: string
  stage: 'intro'|'question'|'followups'|'evaluation'|'done'
  questions_asked_count: number
  current_question_id?: number
  skill_state: object
}

Message {
  id: string
  session_id: number
  role: 'user'|'ai'
  content: string
  created_at: string
}

Question {
  id: number
  text: string
  type: 'technical'|'behavioral'
  difficulty: string
  tags: string[]
  company_style: string
}

Evaluation {
  id: number
  session_id: number
  rubric: RubricScores
  strengths: string[]
  weaknesses: string[]
  feedback: string
  overall_score: number
}

AIStatusResponse {
  configured: boolean
  status: 'online'|'offline'
  fallback_mode: boolean
  reason?: string
}

ErrorResponse {
  message: string
  status: number
  details?: any
}
```

---

## 🔄 Interview Flow (End-to-End)

### Session Lifecycle

```
1. CREATE SESSION
   ├─ POST /sessions {role, track, company_style, difficulty}
   ├─ Creates InterviewSession in DB
   ├─ Initializes stage='intro'
   └─ Returns session metadata

2. LOAD INITIAL STATE
   ├─ GET /sessions/{id}/messages (empty initially)
   ├─ If 0 messages: POST /sessions/{id}/start
   └─ AI generates greeting + warmup question

3. INTERVIEW LOOP
   ├─ User sends message
   ├─ POST /sessions/{id}/message {text/code, mode}
   ├─ Backend processes:
   │  ├─ Store user message
   │  ├─ Classification: intent (answer/move-on/don't-know)
   │  ├─ If substantive: generate follow-up or next question
   │  ├─ Update skill_state with running rubric scores
   │  └─ Return AI response
   └─ Repeat until max questions or finalization

4. INTERVIEW STAGES
   ├─ intro: Greeting, warmup, tone detection
   ├─ question: Main technical/behavioral questions
   ├─ followups: Short follow-up questions (max 2 per question)
   ├─ evaluation: Finalize, compute scores
   └─ done: Return evaluation to frontend

5. FINALIZE
   ├─ POST /sessions/{id}/finalize
   ├─ ScoringEngine summarizes transcript
   ├─ Returns rubric scores + strengths/weaknesses
   └─ Stage transitions to 'done'

6. REVIEW (Optional)
   ├─ GET /sessions/{id} (full session data)
   ├─ Replay with TTS via POST /tts
   └─ DELETE /sessions/{id} (optional cleanup)
```

### State Machine

```
          START
            │
            ▼
        ┌─intro─┐
        │warmup │ AI greets, detects tone
        └───┬───┘
            │
            ▼
      ┌──question──┐
      │behavioral +│ Pick questions adaptively
      │technical   │ Based on difficulty, tags
      └───┬────────┘
            │
            ├─────────────────────┐
            │                     │
      answer with detail     vague/move-on
            │                     │
            ▼                     ▼
        followups?          next_question
            │                     │
      (max 2 per Q)              │
            │                     │
            ▼                     ▼
       max questions?            MAX
       or finalize?           QUESTIONS
            │                     │
      yes ──┴─────┬───────────────┘
              no  │
                  │
            ┌─────▼──────┐
            │ evaluation  │ Scoring engine
            └─────┬──────┘
                  │
            ┌─────▼────┐
            │   done    │
            └───────────┘
```

---

## 🔐 Key Implementation Details

### Question Selection Algorithm

1. **Behavioral Mix:**
   - Target 2-3 behavioral questions
   - Spread throughout interview

2. **Adaptive Difficulty:**
   - Start at user's selected difficulty
   - Adjust `difficulty_current` based on running rubric scores
   - Higher scores → harder questions
   - Lower scores → maintain or reduce difficulty

3. **Tag Diversity:**
   - Track used tags in session
   - Avoid repeating same topic (e.g., don't ask 3 hash-map questions)
   - Use question type + skill balance

4. **Company-Specific Filtering:**
   - FAANG style: system-design heavy, harder edge-cases
   - Startup: full-stack, rapid implementation
   - General: balanced mix

### Evaluation Rubric

**5-point scale per dimension (0-10):**

1. **Communication** - Clarity, explanation quality
2. **Problem-Solving** - Approach, thought process
3. **Correctness & Reasoning** - Accuracy, logic
4. **Complexity** - Trade-offs, optimization awareness
5. **Edge Cases** - Completeness, robustness

**Quick Rubric:** Computed after each response
**Final Evaluation:** Comprehensive LLM-based scoring

### LLM Integration

**Primary:** DeepSeek Chat API

- Timeout: 45 seconds
- Max retries: 2
- Backoff: 0.8 seconds exponential

**Fallback:** Rule-based generation

- Templates for generic follow-ups
- Hardcoded scoring if LLM unavailable

**Status Tracking:**

- Last OK time
- Last error time + message
- Exposed at `GET /ai/status` for frontend badge

---

## 📦 Key Files & Dependencies

### Backend

**Main Dependencies:**

```
fastapi
sqlalchemy
pydantic / pydantic-settings
psycopg2 (postgres driver)
httpx (async HTTP for LLM)
python-jose (JWT)
passlib (password hashing)
alembic (migrations)
pytest (testing)
```

**Config:** `backend/pyproject.toml`, `requirements.txt`

### Frontend

**Main Dependencies:**

```
next 16
react 19
zustand (state)
axios (HTTP)
tailwindcss (styling)
vitest (testing)
@tanstack/react-query (caching - installed, usage TBD)
```

**Config:** `frontend-next/package.json`

---

## 🚀 Development Workflow

### Backend Setup

```bash
# Install dependencies
cd backend
pip install -r requirements-dev.txt

# Setup database
docker-compose up -d  # Postgres
alembic upgrade head  # Apply migrations

# Run server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run tests
pytest tests/ -v --cov=app
```

### Frontend Setup

```bash
# Install dependencies
cd frontend-next
npm install

# Run dev server
npm run dev  # http://localhost:3000

# Run tests
npm run test:run

# Build for production
npm run build
npm start
```

### Environment Variables

**Backend (.env in root):**

```
SECRET_KEY=your-secret
DATABASE_URL=postgresql://user:pass@localhost/interview_db
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
ENV=dev
```

**Frontend (.env.local):**

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

---

## 🧪 Testing

### Backend Testing

- Location: `backend/tests/`
- Framework: pytest
- Coverage: htmlcov report available
- Key test files: CRUD, auth, interview engine, scoring

### Frontend Testing

- Location: `frontend-next/src/__tests__/`
- Framework: Vitest + React Testing Library
- MSW (Mock Service Worker) for API mocking

---

## 📋 Data Seeding

### Questions Dataset

**Location:** `data/questions/`

Questions stored as JSON, auto-loaded on startup (dev mode):

- Difficulty levels: easy, medium, hard
- Types: technical, behavioral
- Tags: topic categorization
- Company styles: general, FAANG, startup, etc.

**Seeding Process:**

1. App startup calls `load_questions_from_folder()`
2. Insert-only: No updates to existing questions
3. Non-blocking: Errors don't crash app

---

## 🔍 Architecture Highlights

### Strengths

1. **Modular Backend:**
   - Clear separation: models, CRUD, services, API routes
   - Service-oriented interview/scoring engines
   - Pluggable LLM (fallback mode)

2. **Robust Interview Logic:**
   - Adaptive difficulty
   - Smart question selection
   - User intent classification
   - Warmup personalization
   - Follow-up generation

3. **Clean Frontend:**
   - Next.js with type safety (TypeScript)
   - Centralized state (Zustand)
   - Service-based API layer
   - Component-driven UI

4. **Production-Ready Features:**
   - JWT authentication
   - Email verification
   - Audit logging
   - Error handling & health checks
   - CORS + security headers

5. **Scalability Considerations:**
   - RAG service (embedding-based context)
   - Session embeddings for future analytics
   - Async LLM calls with retry logic

### Areas for Monitoring

1. **LLM Dependency:** DeepSeek API required for full functionality
2. **Voice Support:** Browser-dependent (Speech Recognition API)
3. **Database Performance:** Large question datasets may need indexing
4. **Token Management:** 7-day JWT expiry; refresh token flow not explicitly visible

---

## 📚 Documentation References

Key docs in project:

- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - Detailed wiring
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Setup instructions
- [MIGRATIONS.md](backend/MIGRATIONS.md) - Database migration guide
- [RAG_SYSTEM.md](backend/RAG_SYSTEM.md) - Embedding/RAG details
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Test strategy
- [project-walkthrough.md](project-walkthrough.md) - Feature walkthrough

---

## 🎓 Summary for New Developers

### To Get Started:

1. **Understand the Core Loop:**
   - User creates session → API creates InterviewSession
   - Frontend polls `/messages` or listens to WebSocket
   - User sends message → backend processes through InterviewEngine
   - InterviewEngine routes to LLM or fallback
   - Response includes next question/follow-up
   - Loop until finalization

2. **Key Files to Read First:**
   - Backend: `app/main.py` → `app/services/interview_engine.py` → `app/api/v1/sessions.py`
   - Frontend: `src/components/sections/InterviewSection.tsx` → `src/lib/stores/sessionStore.ts` → `src/lib/services/sessionService.ts`

3. **Test Flows:**
   - Create session via dashboard
   - Send test message
   - Monitor AI status badge (confirms LLM online)
   - Complete interview and view results

4. **Debugging Tips:**
   - Backend: Check `app.log` or uvicorn console
   - Frontend: Browser DevTools → Network (API calls) → Console (JS errors)
   - AI Status: Hit `GET /api/v1/ai/status` endpoint
   - DB: Use `psql` to inspect tables

---

**Generated:** February 11, 2026  
**Project State:** Fully functional full-stack application with core interview flow, AI integration, and analytics
