# System Architecture Diagrams & Visual Reference

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Interview Prep AI - Complete Flow                    │
└─────────────────────────────────────────────────────────────────────────┘

                           USER BROWSER
                        ┌──────────────────┐
                        │   Next.js App    │
                        │  (React Router)  │
                        │   Zustand Store  │
                        └────────┬─────────┘
                                 │
                    HTTP + JSON  │
                  Authorization: │ Bearer {JWT}
                                 ▼
        ┌────────────────────────────────────────────────────┐
        │          INTERVIEW PREP AI BACKEND                 │
        │            (FastAPI + Python 3.11)                 │
        ├────────────────────────────────────────────────────┤
        │                                                     │
        │  ┌─────────────┐      ┌──────────────────┐        │
        │  │  Auth Layer │      │ Interview Engine │        │
        │  │             │      │                  │        │
        │  │ · Login     │      │ · Question Pick  │        │
        │  │ · Signup    │      │ · Stage Control  │        │
        │  │ · Verify    │      │ · Followups      │        │
        │  │ · JWT Gen   │      │ · Adaptive Level │        │
        │  └──────┬──────┘      └────────┬─────────┘        │
        │         │                      │                  │
        │  ┌──────▼──────────────────────▼──────┐           │
        │  │     LLM Integration Layer           │           │
        │  │                                     │           │
        │  │  ┌──────────────────────────────┐  │           │
        │  │  │  DeepSeek LLM Client         │  │           │
        │  │  │ (with fallback mode)         │  │           │
        │  │  │ • 45s timeout                │  │           │
        │  │  │ • 2x retry with backoff      │  │           │
        │  │  │ • Status health checks       │  │           │
        │  │  └──────────────────────────────┘  │           │
        │  └─────────────────────────────────────┘           │
        │         │                                          │
        │  ┌──────▼────────────────────────────┐            │
        │  │    Scoring & Evaluation Engine     │            │
        │  │                                    │            │
        │  │  • Transcript analysis             │            │
        │  │  • Rubric scoring (1-10 scale)    │            │
        │  │  • 5-skill evaluation              │            │
        │  │  • Feedback generation             │            │
        │  └──────────────────────────────────┘            │
        │         │                                         │
        │  ┌──────▼────────────────────────────┐           │
        │  │  Voice & TTS Integration           │           │
        │  │                                    │           │
        │  │  • ElevenLabs TTS (primary)       │           │
        │  │  • Fallback text response         │           │
        │  │  • Speech recognition (browser)  │           │
        │  └──────────────────────────────────┘           │
        │         │                                        │
        │  ┌──────▼──────────────────────────────────┐    │
        │  │      Database Layer (SQLAlchemy)        │    │
        │  │                                         │    │
        │  │  ┌───────────────────────────────────┐ │    │
        │  │  │      PostgreSQL Database          │ │    │
        │  │  │                                   │ │    │
        │  │  │  Tables:                          │ │    │
        │  │  │  • Users (auth, profiles)         │ │    │
        │  │  │  • InterviewSessions              │ │    │
        │  │  │  • Questions (immutable dataset)  │ │    │
        │  │  │  • Messages (transcript)          │ │    │
        │  │  │  • Evaluations (results)          │ │    │
        │  │  │  • SessionEmbeddings (RAG)        │ │    │
        │  │  │  • SessionFeedback (surveys)      │ │    │
        │  │  │  • [7 more tables]                │ │    │
        │  │  └───────────────────────────────────┘ │    │
        │  └─────────────────────────────────────────┘    │
        │                                                  │
        └────────────────────────────────────────────────┘
```

---

## 2. Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION FLOW                         │
└─────────────────────────────────────────────────────────────┘

USER SIGNUP:
─────────────
  User enters: email, password, name
        │
        ▼
  POST /auth/signup
        │
        ├─ Validate email not in use
        ├─ Hash password (Argon2)
        ├─ Generate 6-digit verification code
        ├─ Store in PendingSignup table
        └─ Send email with code
        │
        └─ Response: { ok: true, message: "Code sent" }

        │
        ▼
  User enters 6-digit code
        │
        ▼
  POST /auth/verify
        │
        ├─ Validate code
        ├─ Move to Users table (is_verified = true)
        ├─ Delete from PendingSignup
        └─ Generate JWT token
        │
        └─ Response: { access_token: "...", token_type: "bearer" }

        │
        ▼
  Frontend stores token in localStorage
        │
        └─ auth-storage JSON with: { token, user }


SUBSEQUENT LOGINS:
──────────────────
  User enters: email, password
        │
        ▼
  POST /auth/login
        │
        ├─ Hash password input
        ├─ Compare with stored hash
        ├─ If match: generate JWT
        │
        └─ Response: { access_token: "..." }

        │
        ▼
  Frontend stores token
        │
        └─ Used in all future requests: Authorization: Bearer {token}


TOKEN LIFECYCLE:
────────────────
  Generated  ──(7 days)──> Expires
  ├─ Payload: { sub: "email", exp: <timestamp> }
  ├─ Signed with: HS256 algorithm
  └─ Secret: settings.SECRET_KEY

  On request:
  ├─ Check expiry date
  ├─ If expired: 401 Unauthorized → redirect to /login
  └─ If valid: Extract email, load user, proceed
```

---

## 3. Interview Session State Machine

```
┌──────────────────────────────────────────────────────────────────┐
│          INTERVIEW SESSION STATE MACHINE (Stage Flow)             │
└──────────────────────────────────────────────────────────────────┘

User creates session:
  POST /sessions
  ├─ Input: { track, company_style, difficulty, behavioral_target }
  └─ → Session created in state: "intro"

        │
        ├─ ID: <session_id>
        ├─ Stage: "intro"
        ├─ Questions asked: 0
        └─ Followups used: 0

        ▼
    [INTRO STAGE] – Greeting & Setup
    ───────────────────────────────
    POST /sessions/{id}/message
    ├─ User: "Hello"
    ├─ AI: "Hi! I'm Alex, your interview coach. Let's start!"
    └─ Stage transitions to: "question"

        ▼
    [QUESTION STAGE] – Main Questions (loop)
    ────────────────────────────────────────
    POST /sessions/{id}/message
    ├─ AI selects question (adaptive difficulty)
    ├─ AI: "Let's start with: [question prompt]"
    ├─ User answers: "My approach would be..."
    ├─ AI evaluates response (quick rubric)
    ├─ If answer is vague/incomplete → followups
    │  └─ Move to: "followups"
    ├─ If answer is complete → next question
    │  └─ Increment questions_asked_count
    │  └─ If questions_asked_count < max: stay "question"
    │  └─ If questions_asked_count >= max: move to "evaluation"
    └─ Loop continues...

        ▼
    [FOLLOWUPS STAGE] – Depth Check
    ────────────────────────────────
    POST /sessions/{id}/message
    ├─ AI asks followup: "Can you explain the edge case?"
    ├─ User responds
    ├─ followups_used++
    ├─ If followups_used < max_followups_per_question:
    │  └─ Ask another followup OR move to next question
    └─ If followups_used >= max_followups_per_question:
       └─ Move to: "question" (next question)

        ▼
    [EVALUATION STAGE] – Final Scoring
    ──────────────────────────────────
    POST /sessions/{id}/finalize
    ├─ Collect full transcript
    ├─ Run LLM evaluator:
    │  ├─ Input: All messages + questions + user answers
    │  └─ Output: Rubric scores (communication, problem_solving, etc.)
    ├─ Calculate overall_score (0-100)
    ├─ Generate feedback (strengths, weaknesses, next steps)
    ├─ Store in Evaluations table
    └─ Stage transitions to: "done"

        ▼
    [DONE STAGE] – Complete
    ──────────────────────
    GET /analytics/sessions/{id}/results
    ├─ Return: { overall_score, rubric, summary }
    └─ User views Results page with:
       ├─ Score gauge visualization
       ├─ Rubric breakdown (5 skills)
       ├─ Strengths/weaknesses
       └─ Next steps for improvement
```

---

## 4. Question Selection & Adaptive Difficulty

```
┌──────────────────────────────────────────────────────────┐
│       QUESTION SELECTION & ADAPTIVE DIFFICULTY           │
└──────────────────────────────────────────────────────────┘

INITIAL SETUP:
───────────────
User selects:
  ├─ Track: "swe_intern" / "swe_engineer" / etc.
  ├─ Company: "google" / "amazon" / "general"
  ├─ Difficulty: "easy" / "medium" / "hard"
  └─ Behavioral target: 2 (out of 7 questions)

        │
        ▼
Database queries:
  ├─ Find all questions matching: track + company + difficulty
  ├─ If company-specific: limited pool, fallback to "general"
  └─ Example: Google medium SWE = 24 questions (15 general fallback)

        │
        ▼
Session created with:
  ├─ difficulty: "medium" (user's cap)
  ├─ difficulty_current: "medium" (starts same as cap)
  ├─ questions_asked_count: 0
  ├─ behavioral_questions_target: 2
  └─ skill_state: { n: 0, sum: {}, last: {} }


QUESTION PICKING (after each answer):
──────────────────────────────────────
For each question slot:

  1. Check if behavioral quota met:
     ├─ behavioral_asked < behavioral_target?
     └─ If yes: prioritize behavioral questions

  2. Select question avoiding repeats:
     ├─ Check user_question_seen table
     ├─ Remove already-seen questions
     └─ Randomly pick from remaining pool

  3. Adaptive difficulty adjustment:
     ├─ Last score: check skill_state.last rubric
     ├─ If score < 5: decrease difficulty (max to easy)
     ├─ If score > 7: increase difficulty (up to hard)
     ├─ If 5-7: keep difficulty same
     └─ Update session.difficulty_current

  4. Deliver question:
     ├─ AI presents prompt + context
     ├─ Store question in SessionQuestion (tracking)
     └─ User answers...

  5. Evaluate answer (quick rubric):
     ├─ LLM scores response 1-10 per skill
     ├─ Store in skill_state:
     │  ├─ n: count of evaluations
     │  ├─ sum: cumulative scores
     │  └─ last: most recent scores
     └─ Use for adaptive difficulty next round

REPEAT until questions_asked_count reaches max_questions


FINAL POOL STATE:
─────────────────
session.skill_state = {
  "n": 5,                          # 5 questions answered
  "sum": {
    "communication": 35,
    "problem_solving": 33,
    "correctness_reasoning": 36,
    "complexity": 28,
    "edge_cases": 23
  },
  "last": {                        # Most recent answer
    "communication": 7,
    "problem_solving": 7,
    "correctness_reasoning": 7,
    "complexity": 6,
    "edge_cases": 5
  },
  "interviewer": {                 # Personality/context
    "id": "1",
    "name": "Alex",
    "gender": "male",
    "image_url": "https://..."
  }
}
```

---

## 5. Message Flow (Question → Answer → Score)

```
┌────────────────────────────────────────────────────────┐
│   MESSAGE FLOW: Question Delivery & Response Cycle     │
└────────────────────────────────────────────────────────┘

CYCLE: User Answer → AI Evaluation → Score → Next Action


┌─ Request: POST /sessions/{id}/message
│  ├─ Body: { message: "I would use a hash map..." }
│  │
│  ▼
│  Backend processes:
│  ├─ Store message in Messages table:
│  │  └─ { session_id, role: "student", content: "...", created_at }
│  │
│  ├─ Call InterviewEngine.process_message():
│  │  ├─ Parse user intent (intent classifier)
│  │  ├─ Check for signals: "skip", "don't know", vague answers
│  │  ├─ Route to LLM:
│  │  │  ├─ Input: Current question + user answer + context
│  │  │  ├─ Prompt: interviewer_system_prompt + controller prompt
│  │  │  └─ LLM decides: followup? | next question? | evaluation?
│  │  │
│  │  ├─ Output: InterviewControllerOutput:
│  │  │  ├─ action: "ask_followup" | "next_question" | "finalize"
│  │  │  ├─ reply: "Great approach! But what about edge cases?"
│  │  │  └─ quick_rubric: { communication: 7, ... }
│  │  │
│  │  └─ Score response (quick rubric):
│  │     ├─ Run scoring_prompt through LLM
│  │     ├─ Extract 1-10 scores per skill
│  │     └─ Update session.skill_state
│  │
│  ├─ Store AI response:
│  │  └─ { session_id, role: "interviewer", content: "...", created_at }
│  │
│  ├─ Update session state:
│  │  ├─ If action == "next_question":
│  │  │  ├─ Increment questions_asked_count
│  │  │  ├─ Select next question
│  │  │  ├─ Update session.stage
│  │  │  └─ Check if max reached → transition to "evaluation"
│  │  │
│  │  ├─ If action == "ask_followup":
│  │  │  ├─ Increment followups_used
│  │  │  └─ Stay in "followups" stage
│  │  │
│  │  └─ If action == "finalize":
│  │     └─ Move to "evaluation" stage
│  │
│  └─ Check adaptive difficulty:
│     └─ Adjust difficulty_current based on scores
│
└─ Response: Message object
   ├─ { id: 2, session_id: 42, role: "interviewer", 
   │    content: "...", created_at: "..." }
   │
   └─ Frontend displays:
      ├─ User message bubble
      ├─ Thinking indicator
      └─ AI response bubble


REPEAT:
───────
Loop continues until:
  ├─ User chooses "end session", OR
  ├─ Max questions reached (default: 7), OR
  ├─ Time limit exceeded (if applicable)
  │
  └─ Then: POST /sessions/{id}/finalize
     └─ Full evaluation & scoring
```

---

## 6. API Endpoint Network Diagram

```
┌──────────────────────────────────────────────────────────────┐
│           API ENDPOINTS (27 Total Across 6 Routes)           │
└──────────────────────────────────────────────────────────────┘

                    [Frontend Client]
                     /    |    |    \
                    /     |    |     \
        ┌──────────────────────────────────────────┐
        │      HTTP Requests (JSON + JWT)          │
        └──────────────────────────────────────────┘
                    /    |    |    \
                   /     |    |     \


    ┌─ AUTH ROUTE ─────────┐
    │ POST   /signup        │  Create account + verify code
    │ POST   /login         │  Get access token
    │ POST   /verify        │  Confirm email with code
    │ POST   /resend-verify │  Resend code
    │ POST   /reset         │  Initiate password reset
    │ POST   /reset-perform │  Complete password reset
    └───────────────────────┘


    ┌─ SESSIONS ROUTE ─────────────┐
    │ GET    /                      │  List user's sessions
    │ POST   /                      │  Create new session
    │ GET    /{id}                  │  Get session details
    │ POST   /{id}/message          │  Send message + AI response
    │ POST   /{id}/finalize         │  Score & close session
    │ GET    /{id}/messages         │  Get message history
    └───────────────────────────────┘


    ┌─ QUESTIONS ROUTE ────────────────────┐
    │ GET    /                             │  List questions
    │ GET    /coverage                     │  Check available count
    │ GET    /{id}                         │  Get one question
    └──────────────────────────────────────┘


    ┌─ ANALYTICS ROUTE ─────────────────────────┐
    │ GET    /sessions/{id}/results             │  Get evaluation
    └───────────────────────────────────────────┘


    ┌─ AI ROUTE ────────────────────┐
    │ GET    /status                │  LLM health status
    │ POST   /chat                  │  Free-form chat
    └───────────────────────────────┘


    ┌─ VOICE ROUTE ────────────────┐
    │ POST   /tts                   │  Text-to-speech
    └───────────────────────────────┘
```

---

## 7. Data Flow: From Frontend to Database and Back

```
┌────────────────────────────────────────────────────────────────┐
│         COMPLETE DATA FLOW: Frontend → Backend → DB            │
└────────────────────────────────────────────────────────────────┘

FRONTEND STATE:
┌─────────────────────────────────────────┐
│  Next.js App                            │
│  ├─ useAuth() hook                      │
│  ├─ useSession() hook                   │
│  ├─ useUI() hook                        │
│  └─ Zustand stores                      │
│     ├─ authStore (token, user)          │
│     ├─ sessionStore (session, messages) │
│     └─ uiStore (theme, sidebar)         │
└─────────────────────────────────────────┘
        │
        │ apiFetch("POST /sessions/{id}/message")
        ▼


HTTP REQUEST:
┌────────────────────────────────────┐
│ POST /api/v1/sessions/42/message   │
│                                    │
│ Headers:                           │
│  Content-Type: application/json    │
│  Authorization: Bearer {JWT}       │
│                                    │
│ Body: { message: "..." }           │
└────────────────────────────────────┘
        │
        ▼


BACKEND MIDDLEWARE:
┌────────────────────────────────┐
│ ├─ CORSMiddleware              │ Allow origin
│ ├─ SecurityHeaders             │ Add X-* headers
│ └─ Auth Validation             │ Check JWT
│    └─ Extract email from token │
└────────────────────────────────┘
        │
        ▼


API ROUTER:
┌────────────────────────────────────┐
│ Route: POST /sessions/{id}/message │
│ Handler: sessions.send_message()   │
└────────────────────────────────────┘
        │
        ▼


BUSINESS LOGIC:
┌──────────────────────────────────────────┐
│ session_crud.get_session(db, 42)         │
│ └─ SELECT * FROM interview_sessions      │
│    WHERE id = 42 AND user_id = {user_id} │
│                                          │
│ Store message:                           │
│ message_crud.create_message(              │
│   session_id=42,                         │
│   role="student",                        │
│   content="..."                          │
│ )                                        │
│ └─ INSERT into messages table            │
│                                          │
│ Call InterviewEngine:                    │
│ ├─ Analyze user intent                   │
│ ├─ Call LLM (DeepSeek):                  │
│ │  ├─ Send: system_prompt + messages     │
│ │  └─ Receive: AI response               │
│ ├─ Score response (quick rubric)         │
│ └─ Decide next action (followup/next)    │
│                                          │
│ Store AI response:                       │
│ message_crud.create_message(             │
│   session_id=42,                         │
│   role="interviewer",                    │
│   content="..."                          │
│ )                                        │
│ └─ INSERT into messages table            │
│                                          │
│ Update session:                          │
│ session.skill_state = {...}              │
│ session.questions_asked_count = 2        │
│ db.add(session)                          │
│ db.commit()                              │
│ └─ UPDATE interview_sessions             │
└──────────────────────────────────────────┘
        │
        ▼


DATABASE CHANGES:
┌────────────────────────────────────┐
│ messages table:                    │
│ + INSERT { session_id: 42,         │
│     role: "student", content: "",  │
│     created_at: now() }            │
│                                    │
│ + INSERT { session_id: 42,         │
│     role: "interviewer", content   │
│     created_at: now() }            │
│                                    │
│ interview_sessions table:          │
│ UPDATE skill_state = {...}         │
│ WHERE id = 42                      │
└────────────────────────────────────┘
        │
        ▼


HTTP RESPONSE:
┌────────────────────────────────────┐
│ Status: 200 OK                     │
│                                    │
│ Body: {                            │
│   id: 2,                           │
│   session_id: 42,                  │
│   role: "interviewer",             │
│   content: "Great! Can you...",    │
│   created_at: "2026-02-02T..."     │
│ }                                  │
└────────────────────────────────────┘
        │
        ▼


FRONTEND RECEIVES:
┌────────────────────────────────────┐
│ Message object parsed from JSON    │
│ Zustand store updated:             │
│ sessionStore.addMessage(message)   │
│ └─ messages array now has 2 items  │
│                                    │
│ React re-renders:                  │
│ ├─ ChatWindow component            │
│ ├─ New message bubbles displayed   │
│ └─ User sees AI response           │
└────────────────────────────────────┘


REPEAT CYCLE on next user input...
```

---

## 8. Error Handling Flow

```
┌──────────────────────────────────┐
│   ERROR HANDLING & RECOVERY      │
└──────────────────────────────────┘

Error occurs in backend:
  │
  ├─ 400 Bad Request
  │  └─ Example: Missing required field
  │  └─ Response: { detail: "email is required" }
  │  └─ Frontend: Show error toast, highlight field
  │
  ├─ 401 Unauthorized
  │  └─ Example: Invalid/expired token
  │  └─ Response: { detail: "Invalid token" }
  │  └─ Frontend: Clear token, redirect to /login
  │
  ├─ 403 Forbidden
  │  └─ Example: Email not verified
  │  └─ Response: { detail: "Email not verified..." }
  │  └─ Frontend: Redirect to /verify with email
  │
  ├─ 404 Not Found
  │  └─ Example: Session doesn't exist
  │  └─ Response: { detail: "Session not found" }
  │  └─ Frontend: Redirect to /dashboard
  │
  ├─ 422 Unprocessable Entity
  │  └─ Example: Invalid enum value
  │  └─ Response: { detail: "Invalid difficulty 'expert'..." }
  │  └─ Frontend: Show validation error, suggest valid values
  │
  ├─ 429 Too Many Requests
  │  └─ Example: Rate limited (10 login attempts in 60 sec)
  │  └─ Response: { detail: "Rate limited..." }
  │  └─ Frontend: Disable button for 60 seconds, show timer
  │
  └─ 500 Internal Server Error
     └─ Example: Database connection failed
     └─ Response: { detail: "Internal server error" }
     └─ Frontend: Show error toast, log to Sentry, suggest retry


SPECIAL CASE: LLM Offline
──────────────────────────
  GET /ai/status
  ├─ Response: { configured: false, status: "offline", ... }
  │
  ├─ POST /ai/chat → Fallback response (no error)
  │  └─ Response: { reply: "AI is offline. Try again later.", mode: "fallback" }
  │
  └─ Frontend: Show "AI offline" badge, but don't crash


Frontend apiFetch error handler:
───────────────────────────────
  try {
    const data = await apiFetch(path, options);
  } catch (error) {
    if (error.status === 401) {
      useAuthStore.logout();
      window.location.href = '/login';
    } else if (error.status === 422) {
      setFormError(error.data?.detail);
    } else if (error.status === 429) {
      showToast("Too many attempts. Please wait.", "warning");
      disableForm(60); // seconds
    } else {
      showToast("Something went wrong. Please try again.", "error");
      console.error("API Error:", error);
    }
  }
```

---

## 9. Technology Stack Summary

```
┌──────────────────────────────────────────────────────────┐
│           COMPLETE TECHNOLOGY STACK                       │
└──────────────────────────────────────────────────────────┘

FRONTEND (Current - Vanilla)
├─ HTML5
├─ CSS3 (Tailwind utilities)
├─ JavaScript (vanilla)
├─ Browser APIs:
│  ├─ localStorage
│  ├─ Fetch API
│  ├─ Web Speech API (speech recognition)
│  └─ Audio API (TTS playback)
└─ CDN Libraries:
   ├─ Font Awesome 6.4 (icons)
   ├─ Google Fonts (typography)
   └─ Chart.js (if used)


FRONTEND (Target - Next.js)
├─ Next.js 14+ (App Router)
├─ React 18.2+
├─ TypeScript 5+
├─ Tailwind CSS 3.3+
├─ Zustand 4.4+ (state management)
├─ React Query 3.39+ (data fetching)
├─ Axios 1.6+ (HTTP client)
├─ Shadcn/UI (component library, optional)
└─ Testing:
   ├─ Vitest (unit tests)
   ├─ Playwright (integration tests)
   └─ Cypress (E2E tests)


BACKEND
├─ FastAPI 0.104+
├─ Python 3.11
├─ SQLAlchemy 2.0+ (ORM)
├─ Alembic (migrations)
├─ Pydantic (validation)
├─ python-jose (JWT)
├─ passlib + argon2 (password hashing)
├─ httpx (async HTTP client)
├─ python-multipart (form handling)
└─ uvicorn (ASGI server)


LLM INTEGRATION
├─ DeepSeek API
│  ├─ Base URL: https://api.deepseek.com
│  ├─ Model: deepseek-chat
│  ├─ Timeout: 45 seconds
│  └─ Retries: 2 with 0.8s backoff
├─ Fallback: Static responses (no 500 errors)
└─ Monitoring: Status endpoint + health checks


DATABASE
├─ PostgreSQL 14+
├─ pgvector (for embeddings, optional)
├─ Connection pooling: SQLAlchemy
└─ Schema: 15 tables, Alembic managed


EXTERNAL SERVICES
├─ ElevenLabs (TTS primary)
├─ Deepseek LLM (AI responses)
├─ SMTP (email verification, optional)
├─ Sentry (error tracking, optional)
└─ Analytics (optional)


DEPLOYMENT
├─ Backend: Docker (containerized)
├─ Frontend: Vercel (recommended) OR Docker
├─ Database: AWS RDS or self-hosted PostgreSQL
├─ CDN: Cloudflare or AWS CloudFront (optional)
└─ Monitoring: Sentry + DataDog (optional)
```

---

## 10. Component Hierarchy (Next.js)

```
┌────────────────────────────────────────────────────────┐
│         COMPONENT HIERARCHY (Next.js App)              │
└────────────────────────────────────────────────────────┘

<RootLayout>
├─ <Providers>
│  ├─ <AuthProvider>
│  ├─ <QueryProvider>
│  └─ <ThemeProvider>
│
├─ <body>
│  │
│  ├─ "/" (Landing Page)
│  │  ├─ <Navigation>
│  │  ├─ <HeroSection>
│  │  ├─ <FeaturesSection>
│  │  └─ <CTASection>
│  │
│  ├─ "(auth)" Group
│  │  ├─ "/login"
│  │  │  ├─ <LoginForm>
│  │  │  └─ <SignupLink>
│  │  ├─ "/signup"
│  │  │  ├─ <SignupForm>
│  │  │  ├─ <ProfileFields>
│  │  │  └─ <PreferencesFields>
│  │  └─ "/verify"
│  │     ├─ <VerificationForm>
│  │     └─ <ResendCodeButton>
│  │
│  └─ "(app)" Group (Protected by middleware)
│     ├─ <AppLayout>
│     │  ├─ <Sidebar>
│     │  │  ├─ <Logo>
│     │  │  ├─ <NavMenu>
│     │  │  └─ <LogoutButton>
│     │  │
│     │  ├─ <TopBar>
│     │  │  ├─ <PageTitle>
│     │  │  ├─ <StatusBadges>
│     │  │  └─ <UserProfile>
│     │  │
│     │  └─ <MainContent>
│     │     │
│     │     ├─ "/dashboard"
│     │     │  ├─ <DashboardHeader>
│     │     │  ├─ <StartInterviewCard>
│     │     │  │  ├─ <RoleSelect>
│     │     │  │  ├─ <CompanySelect>
│     │     │  │  ├─ <DifficultySelect>
│     │     │  │  └─ <StartButton>
│     │     │  ├─ <SessionHistory>
│     │     │  │  └─ <SessionCard> (loop)
│     │     │  └─ <PerformanceStats>
│     │     │
│     │     ├─ "/interview"
│     │     │  ├─ <InterviewHeader>
│     │     │  ├─ <ChatWindow>
│     │     │  │  └─ <MessageBubble> (loop)
│     │     │  │     ├─ <UserMessageBubble>
│     │     │  │     └─ <InterviewerMessageBubble>
│     │     │  ├─ <QuestionDisplay>
│     │     │  │  ├─ <QuestionPrompt>
│     │     │  │  ├─ <QuestionTags>
│     │     │  │  └─ <Timer> (optional)
│     │     │  └─ <InputArea>
│     │     │     ├─ <TextInput>
│     │     │     ├─ <VoiceButton>
│     │     │     └─ <SubmitButton>
│     │     │
│     │     ├─ "/chat"
│     │     │  ├─ <ChatHeader>
│     │     │  ├─ <ChatHistory>
│     │     │  │  └─ <ChatBubble> (loop)
│     │     │  └─ <ChatInput>
│     │     │
│     │     ├─ "/results/[id]"
│     │     │  ├─ <ScoreSection>
│     │     │  │  ├─ <ScoreGauge>
│     │     │  │  ├─ <ScoreSummary>
│     │     │  │  └─ <ActionButtons>
│     │     │  ├─ <RubricBreakdown>
│     │     │  │  └─ <RubricBar> (x5 skills)
│     │     │  ├─ <FeedbackCard>
│     │     │  │  ├─ <StrengthsList>
│     │     │  │  ├─ <WeaknessList>
│     │     │  │  └─ <NextStepsList>
│     │     │  └─ <ActionButtons>
│     │     │     ├─ <NewSessionButton>
│     │     │     ├─ <ExportButton>
│     │     │     └─ <ShareButton>
│     │     │
│     │     └─ "/settings"
│     │        ├─ <AppearanceSection>
│     │        │  ├─ <ThemeToggle>
│     │        │  └─ <AccentColorPicker>
│     │        ├─ <AudioSection>
│     │        │  ├─ <VoiceToggle>
│     │        │  └─ <VoiceSelectionDropdown>
│     │        ├─ <PreferencesSection>
│     │        │  ├─ <RoleSelect>
│     │        │  ├─ <DifficultySelect>
│     │        │  └─ <CompanySelect>
│     │        └─ <PrivacySection>
│     │           ├─ <DataDeletionButton>
│     │           └─ <ExportDataButton>

Legend:
  <Component>  = React component
  "/path"      = Route
  "(group)"    = Route group (layout sharing)
  └─           = Child element

Each component is:
  ├─ Typed with TypeScript
  ├─ Connected to Zustand stores (if needed)
  ├─ Using React hooks (useState, useEffect, custom)
  └─ Styled with Tailwind CSS
```

---

## 11. Database Relationships

```
┌────────────────────────────────────────────────────────┐
│         DATABASE RELATIONSHIPS (ER Diagram)            │
└────────────────────────────────────────────────────────┘

     ┌─ Users ──────────┐
     │ id (PK)          │
     │ email (unique)   │
     │ password_hash    │
     │ is_verified      │
     │ ...              │
     └──────────┬───────┘
                │ (1:N)
                │
      ┌─────────▼─────────────┐
      │ InterviewSessions     │
      │ id (PK)               │
      │ user_id (FK) ─────────┼──▶ Users.id
      │ role, track, etc.     │
      │ stage                 │
      │ skill_state (JSON)    │
      │ ...                   │
      └──────┬────┬──┬────────┘
             │    │  │
             │    │  └──────────────┐
             │    │                 │
      (1:N)  │    │  (1:1)         │ (1:1)
             │    │                 │
      ┌──────▼─┐ ┌─▼────────────┐ ┌▼──────────────┐
      │Messages│ │Evaluations   │ │SessionEmbedding
      │id (PK) │ │id (PK)       │ │id (PK)
      │session │ │session_id    │ │session_id
      │_id (FK)│ │(FK, unique)  │ │(FK)
      │role    │ │overall_score │ │embeddings (JSON)
      │content │ │rubric (JSON) │ │created_at
      │...     │ │summary (JSON)│ │...
      └────────┘ │...           │ └────────────────┘
                  └──────────────┘

      ┌─ Questions ──────────┐
      │ id (PK)              │
      │ track (indexed)      │
      │ company_style        │
      │ (indexed)            │
      │ difficulty (indexed) │
      │ title, prompt        │
      │ tags_csv             │
      │ question_type        │
      │ ...                  │
      └──────┬───────────────┘
             │ (1:N)
             │
      ┌──────▼──────────────────┐
      │ SessionQuestions        │
      │ id (PK)                 │
      │ session_id (FK)         │
      │ question_id (FK)        │
      │ order                   │
      │ created_at              │
      └─────────────────────────┘


OTHER TABLES:
─────────────
├─ PendingSignup
│  ├─ id (PK)
│  ├─ email
│  ├─ password_hash
│  ├─ verification_code
│  ├─ expires_at
│  └─ created_at
│
├─ UserQuestionSeen
│  ├─ id (PK)
│  ├─ user_id (FK)
│  ├─ question_id (FK)
│  └─ seen_at
│
├─ SessionFeedback
│  ├─ id (PK)
│  ├─ session_id (FK)
│  ├─ rating (1-5)
│  ├─ feedback_text
│  └─ created_at
│
├─ AuditLog
│  ├─ id (PK)
│  ├─ user_id (FK)
│  ├─ action
│  ├─ metadata (JSON)
│  └─ created_at
│
└─ [Additional tables for RAG, embeddings, etc.]
```

---

Perfect! I've created a comprehensive visual reference guide. Let me create one final master index document:
<function_calls>
<invoke name="create_file">
<parameter name="content"># Master Documentation Index

## 📚 Complete Interview Prep AI Documentation Suite

This document serves as an index to all comprehensive analysis and implementation guides for converting the Interview Prep AI frontend from vanilla JavaScript to Next.js.

---

## 📖 Documentation Files (in This Repository)

### 1. **COMPLETE_ANALYSIS_SUMMARY.md** ⭐ START HERE
**What:** Complete overview of the entire system
**Length:** 400+ lines
**Contents:**
- Executive summary
- Current architecture
- Database schema
- API endpoints (27 total)
- Authentication flow
- Current frontend architecture
- Next.js migration benefits
- Key implementation details
- API compatibility checklist
- Success criteria
- Tech stack

**When to read:** First, to get the big picture

---

### 2. **NEXTJS_CONVERSION_BLUEPRINT.md** 🏗️ ARCHITECTURE GUIDE
**What:** Detailed architecture and migration strategy
**Length:** 500+ lines
**Contents:**
- Database schema (15 tables)
- All API endpoints (organized by route)
- Complete Next.js project structure
- Core implementation details:
  - API client pattern
  - Auth store (Zustand)
  - Session service
  - Question service
  - AI service
  - Auth hook
  - Session hook
- Component mapping (vanilla → React)
- 8-week migration timeline
- Environment configuration
- Error handling strategy
- Performance optimizations
- Testing strategy
- Rollout plan
- Known considerations
- Deployment options
- FAQs

**When to read:** Before starting implementation, for detailed architecture

---

### 3. **API_REFERENCE.md** 📡 ENDPOINT DOCUMENTATION
**What:** Complete API reference with examples
**Length:** 600+ lines
**Contents:**
- Base configuration
- Auth endpoints (request/response examples)
- Session endpoints
- Question endpoints
- Analytics endpoints
- AI endpoints
- Voice/TTS endpoints
- Error responses (401, 422, 429, 500)
- Rate limiting rules
- Complete authentication flow example
- Complete interview flow example
- cURL testing examples for each endpoint
- Constants & enums (tracks, companies, difficulties)
- Headers reference
- Response structure details

**When to read:** When implementing API calls, for exact request/response format

---

### 4. **NEXTJS_IMPLEMENTATION_CHECKLIST.md** ✅ CODE TEMPLATES
**What:** Ready-to-use code templates and implementation checklist
**Length:** 700+ lines
**Contents:**
- Quick start template
- Environment setup
- Complete code files:
  - `src/lib/api.ts` (API client)
  - `src/lib/store/authStore.ts`
  - `src/lib/store/sessionStore.ts`
  - `src/lib/store/uiStore.ts`
  - `src/lib/services/authService.ts`
  - `src/lib/services/sessionService.ts`
  - `src/lib/services/questionService.ts`
  - `src/lib/services/aiService.ts`
  - `src/lib/hooks/useAuth.ts`
  - `src/lib/hooks/useSession.ts`
  - Component examples (Sidebar, TopBar, LoginPage)
  - Type definitions
- Build & deploy checklist
- Troubleshooting common issues
- Performance tips
- Summary of next steps

**When to read:** During implementation, copy-paste ready code

---

### 5. **QUICK_REFERENCE.md** 🎯 QUICK LOOKUP GUIDE
**What:** Quick reference for common lookups
**Length:** 400+ lines
**Contents:**
- At-a-glance summary table
- Critical integration points:
  - Auth token format
  - Session state
  - Question flow
  - Message exchange
  - Evaluation & scoring
- HTTP headers reference
- Complete user journey (API calls)
- Common pitfalls & solutions
- Key data structures (TypeScript interfaces)
- Environment variables
- Testing endpoints with cURL
- Security checklist
- Performance metrics
- Frontend key mappings
- Pre-migration checklist
- Go-live checklist
- Debugging commands
- File structure reference
- Key insights

**When to read:** As you're developing, for quick answers

---

### 6. **ARCHITECTURE_DIAGRAMS.md** (This File)
**What:** Visual reference and system architecture
**Length:** 500+ lines
**Contents:**
- High-level system architecture diagram
- Authentication flow diagram
- Interview session state machine
- Question selection & adaptive difficulty
- Message flow (question → answer → score)
- API endpoint network diagram
- Complete data flow diagram
- Error handling flow
- Technology stack summary
- Component hierarchy (Next.js)
- Database relationships (ER diagram)

**When to read:** For visualizing how pieces fit together

---

## 🗂️ How to Use This Documentation

### Scenario 1: "I'm new to the project"
1. Read: **COMPLETE_ANALYSIS_SUMMARY.md** (get overview)
2. Read: **ARCHITECTURE_DIAGRAMS.md** (visualize system)
3. Skim: **QUICK_REFERENCE.md** (understand terminology)

### Scenario 2: "I'm implementing the API client"
1. Read: **API_REFERENCE.md** (understand endpoints)
2. Copy: Code from **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (`lib/api.ts`)
3. Reference: **QUICK_REFERENCE.md** (HTTP headers, error codes)

### Scenario 3: "I'm building authentication"
1. Read: **COMPLETE_ANALYSIS_SUMMARY.md** (auth flow section)
2. Study: **ARCHITECTURE_DIAGRAMS.md** (auth flow diagram)
3. Implement: From **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (authService)
4. Test: Using cURL commands in **API_REFERENCE.md**

### Scenario 4: "I'm building interview flow"
1. Study: **ARCHITECTURE_DIAGRAMS.md** (session state machine, message flow)
2. Reference: **API_REFERENCE.md** (session endpoints)
3. Implement: From **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (useSession hook)
4. Debug: Using **QUICK_REFERENCE.md** (debugging section)

### Scenario 5: "I'm deploying to production"
1. Read: **NEXTJS_CONVERSION_BLUEPRINT.md** (rollout plan section)
2. Check: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (go-live checklist)
3. Reference: **QUICK_REFERENCE.md** (environment variables)
4. Review: **API_REFERENCE.md** (error handling for production)

---

## 🔍 Key Topics Index

### Architecture
- System diagram: **ARCHITECTURE_DIAGRAMS.md** #1
- Database schema: **NEXTJS_CONVERSION_BLUEPRINT.md** (Database Schema section)
- Component hierarchy: **ARCHITECTURE_DIAGRAMS.md** #10

### Authentication
- Auth flow: **COMPLETE_ANALYSIS_SUMMARY.md** (Authentication Flow section)
- Auth flow visual: **ARCHITECTURE_DIAGRAMS.md** #2
- Auth endpoints: **API_REFERENCE.md** (Auth Endpoints section)
- Auth implementation: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (authService code)

### API Endpoints
- All endpoints: **NEXTJS_CONVERSION_BLUEPRINT.md** (API Endpoints section)
- Detailed examples: **API_REFERENCE.md** (all sections)
- Testing: **QUICK_REFERENCE.md** (cURL examples)

### Interview Session
- State machine: **ARCHITECTURE_DIAGRAMS.md** #3
- Message flow: **ARCHITECTURE_DIAGRAMS.md** #5
- Session service: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (sessionService)
- API flow: **API_REFERENCE.md** (Sessions Endpoints)

### Questions & Scoring
- Question selection: **ARCHITECTURE_DIAGRAMS.md** #4
- Evaluation: **API_REFERENCE.md** (Finalize endpoint)
- Scoring: **COMPLETE_ANALYSIS_SUMMARY.md** (Evaluation & Scoring section)

### Implementation
- Project structure: **NEXTJS_CONVERSION_BLUEPRINT.md** (Next.js Project Structure)
- Code templates: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (all code sections)
- Component mapping: **NEXTJS_CONVERSION_BLUEPRINT.md** (Component Mapping table)

### Deployment
- Rollout strategy: **NEXTJS_CONVERSION_BLUEPRINT.md** (Rollout Plan)
- Deployment options: **NEXTJS_CONVERSION_BLUEPRINT.md** (Deployment section)
- Go-live checklist: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (Go-Live Checklist)
- Environment config: **QUICK_REFERENCE.md** (Environment Variables)

### Troubleshooting
- Common pitfalls: **QUICK_REFERENCE.md** (Common Pitfalls & Solutions)
- Debugging: **NEXTJS_IMPLEMENTATION_CHECKLIST.md** (Troubleshooting section)
- Error handling: **ARCHITECTURE_DIAGRAMS.md** #8

---

## 📊 Statistics & Quick Facts

| Metric | Value |
|---|---|
| **Total Documentation** | 3,000+ lines |
| **API Endpoints Documented** | 27 endpoints |
| **Database Tables** | 15 tables |
| **Backend Service Modules** | 11 modules |
| **Frontend Pages** | 7 pages |
| **Proposed Next.js Components** | 50+ components |
| **Implementation Timeline** | 6-8 weeks |
| **Code Templates Provided** | 10+ files |
| **cURL Examples** | 10+ examples |
| **Architecture Diagrams** | 11 diagrams |

---

## ✅ Pre-Implementation Checklist

Before starting implementation, ensure you have:

- [ ] Read COMPLETE_ANALYSIS_SUMMARY.md (complete overview)
- [ ] Reviewed ARCHITECTURE_DIAGRAMS.md (visual understanding)
- [ ] Backend running locally
- [ ] PostgreSQL database populated
- [ ] Tested all endpoints with cURL (from API_REFERENCE.md)
- [ ] Node.js 18+ installed
- [ ] TypeScript understanding
- [ ] React hooks knowledge
- [ ] Zustand state management familiarity

---

## 🚀 Phase-by-Phase Reading Guide

### Phase 0: Preparation (Week 0)
- **Read:** COMPLETE_ANALYSIS_SUMMARY.md
- **Study:** ARCHITECTURE_DIAGRAMS.md
- **Understand:** Database schema and API endpoints

### Phase 1: Infrastructure Setup (Week 1)
- **Reference:** NEXTJS_CONVERSION_BLUEPRINT.md (Infrastructure section)
- **Copy:** Code from NEXTJS_IMPLEMENTATION_CHECKLIST.md (Phases 1 & 2)
- **Test:** Using QUICK_REFERENCE.md (Testing section)

### Phase 2: Authentication (Week 1-2)
- **Read:** API_REFERENCE.md (Auth Endpoints)
- **Study:** ARCHITECTURE_DIAGRAMS.md (Auth Flow #2)
- **Implement:** From NEXTJS_IMPLEMENTATION_CHECKLIST.md (authService)
- **Test:** Using QUICK_REFERENCE.md (cURL examples)

### Phase 3: Dashboard & Interview (Week 2-4)
- **Read:** API_REFERENCE.md (Sessions Endpoints)
- **Study:** ARCHITECTURE_DIAGRAMS.md (Session State Machine #3)
- **Implement:** From NEXTJS_IMPLEMENTATION_CHECKLIST.md (useSession hook)
- **Reference:** QUICK_REFERENCE.md (message flow)

### Phase 4: Results & Analytics (Week 4)
- **Read:** API_REFERENCE.md (Analytics Endpoints)
- **Study:** ARCHITECTURE_DIAGRAMS.md (Data Flow #7)
- **Implement:** Custom components

### Phase 5: Testing & Optimization (Week 5-6)
- **Read:** NEXTJS_CONVERSION_BLUEPRINT.md (Testing Strategy)
- **Reference:** NEXTJS_IMPLEMENTATION_CHECKLIST.md (Troubleshooting)
- **Optimize:** Using performance tips

### Phase 6: Deployment (Week 6)
- **Read:** NEXTJS_CONVERSION_BLUEPRINT.md (Deployment & Rollout)
- **Check:** NEXTJS_IMPLEMENTATION_CHECKLIST.md (Build & Deploy checklist)
- **Execute:** QUICK_REFERENCE.md (Go-live checklist)

---

## 🎓 Learning Resources Provided

### 1. Code Templates
All ready-to-copy code in **NEXTJS_IMPLEMENTATION_CHECKLIST.md**:
- TypeScript types
- API client
- Zustand stores
- Service layer
- React hooks
- Components

### 2. Examples
Request/response examples in **API_REFERENCE.md**:
- All 27 endpoints
- Complete flows
- Error responses
- cURL commands

### 3. Diagrams
Visual architecture in **ARCHITECTURE_DIAGRAMS.md**:
- System overview
- Auth flow
- State machine
- Data flow
- Component hierarchy

### 4. Checklists
Actionable lists in **NEXTJS_IMPLEMENTATION_CHECKLIST.md** and **QUICK_REFERENCE.md**:
- Pre-migration
- Go-live
- Build & deploy

---

## 💡 Quick Navigation

**Need to find something quickly?**

- **"How does auth work?"** → ARCHITECTURE_DIAGRAMS.md #2 + QUICK_REFERENCE.md (Auth Token section)
- **"What's the exact API request format?"** → API_REFERENCE.md (specific endpoint)
- **"Show me the code template"** → NEXTJS_IMPLEMENTATION_CHECKLIST.md (specific section)
- **"What's the overall architecture?"** → ARCHITECTURE_DIAGRAMS.md #1 + COMPLETE_ANALYSIS_SUMMARY.md
- **"How do I test this?"** → API_REFERENCE.md (Testing with cURL section)
- **"What could go wrong?"** → QUICK_REFERENCE.md (Common Pitfalls)
- **"How do I deploy?"** → NEXTJS_CONVERSION_BLUEPRINT.md (Deployment section)

---

## 🔗 Cross-References

### Between Documents
- COMPLETE_ANALYSIS_SUMMARY.md references specific sections in other docs
- NEXTJS_CONVERSION_BLUEPRINT.md links to API_REFERENCE.md for details
- NEXTJS_IMPLEMENTATION_CHECKLIST.md provides code for concepts in NEXTJS_CONVERSION_BLUEPRINT.md
- QUICK_REFERENCE.md cross-references all other docs
- ARCHITECTURE_DIAGRAMS.md visualizes concepts from all docs

### Section Relationships
- **Auth Flow:** COMPLETE_ANALYSIS_SUMMARY → ARCHITECTURE_DIAGRAMS #2 → API_REFERENCE → NEXTJS_IMPLEMENTATION_CHECKLIST
- **Sessions:** NEXTJS_CONVERSION_BLUEPRINT → ARCHITECTURE_DIAGRAMS #3,#5 → API_REFERENCE → NEXTJS_IMPLEMENTATION_CHECKLIST
- **Deployment:** NEXTJS_CONVERSION_BLUEPRINT → NEXTJS_IMPLEMENTATION_CHECKLIST → QUICK_REFERENCE

---

## 📝 Notes & Tips

- **Start with the big picture:** Read COMPLETE_ANALYSIS_SUMMARY.md first
- **Visualize as you learn:** Use ARCHITECTURE_DIAGRAMS.md throughout
- **Copy, don't retype:** Use code from NEXTJS_IMPLEMENTATION_CHECKLIST.md
- **Reference during coding:** Keep QUICK_REFERENCE.md and API_REFERENCE.md open
- **Follow the timeline:** Use Phase-by-Phase reading guide
- **Test as you go:** Use cURL examples from API_REFERENCE.md

---

## ✨ Key Principles

1. **Zero Backend Changes** - All APIs work exactly as they do now
2. **Parallel Development** - Run both frontends simultaneously during transition
3. **Type Safety** - TypeScript for all code
4. **Clear Separation** - Services, hooks, components, stores
5. **Comprehensive Testing** - Unit, integration, E2E
6. **Gradual Rollout** - 10% → 50% → 100% of users
7. **Instant Rollback** - Feature flag to switch versions

---

## 🎯 Success Metrics

After implementing, you should achieve:

- ✅ All API endpoints working correctly
- ✅ Authentication flow identical to original
- ✅ Interview sessions state maintained accurately
- ✅ Message history preserved
- ✅ Scoring calculations identical
- ✅ Mobile responsive on all devices
- ✅ Lighthouse score > 90
- ✅ Zero runtime errors
- ✅ E2E tests passing
- ✅ Smooth production rollout

---

## 🤝 Support & Questions

If you need clarification:
1. Check the Quick Navigation section above
2. Search relevant document using Ctrl+F
3. Review QUICK_REFERENCE.md (Common Pitfalls section)
4. Check NEXTJS_IMPLEMENTATION_CHECKLIST.md (Troubleshooting section)

---

## 📞 Document Version

- **Created:** February 2, 2026
- **Status:** Complete & Ready for Implementation
- **Total Lines:** 3,000+
- **Estimated Read Time:** 4-6 hours (full suite)
- **Implementation Time:** 6-8 weeks

---

## 🏁 Final Checklist

Before you begin:
- [ ] All 6 documentation files read or skimmed
- [ ] Backend tested and running
- [ ] Project structure understood
- [ ] API endpoints familiar
- [ ] Development environment ready
- [ ] Next.js project scaffolded
- [ ] First code template copied

**You're ready to begin implementation!**

Good luck! 🚀

