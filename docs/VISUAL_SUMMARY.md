# Interview Prep AI - Visual Summary & Cheat Sheet

## 🎯 What This App Does (5-Second Version)

```
User logs in → Creates interview session →
AI asks 5-7 questions (with follow-ups) →
User answers → AI scores everything →
Shows results with feedback
```

---

## 🏗️ System Components (Bird's Eye View)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Next.js Frontend (React + TypeScript)                │   │
│  │ • Login/Signup pages                                 │   │
│  │ • Dashboard (create session)                         │   │
│  │ • Interview chat UI                                  │   │
│  │ • Results page with score breakdown                  │   │
│  │ State: Zustand (auth, session, UI)                  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/HTTPS + JWT Auth
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Core Services                                         │   │
│  │ • InterviewEngine: Pick questions, generate replies  │   │
│  │ • ScoringEngine: Evaluate and score interviews       │   │
│  │ • DeepSeekClient: Call LLM API with retries          │   │
│  │ • TTS: Generate audio for playback                   │   │
│  │ • RAG: Find similar sessions for context             │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ SQL
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL DATABASE                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Tables:                                               │   │
│  │ • users, sessions, questions, messages               │   │
│  │ • evaluations, embeddings, feedback, audit logs      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        ↑
        │ External APIs
        ├─ DeepSeek LLM
        ├─ ElevenLabs TTS (optional)
        └─ SMTP Email (optional)
```

---

## 📖 User Journey (Step by Step)

```
1. SIGNUP
   User enters email + password + name
        ↓ Sends verification code
   User enters 6-digit code
        ↓ Creates account
   Redirects to login

2. LOGIN
   User enters email + password
        ↓ Returns JWT token
   Token stored in browser localStorage
   Redirects to dashboard

3. CREATE SESSION
   User selects:
      • Role: "SWE Intern" / "SWE Engineer" / etc
      • Track: "swe_intern" / "data_science" / etc
      • Company: "Google" / "Apple" / "General"
      • Difficulty: "Easy" / "Medium" / "Hard"
        ↓ API creates InterviewSession row
   Returns session ID + start button

4. WARMUP (First message)
   User clicks "Start Interview"
        ↓ Backend generates greeting
   AI: "Hi, I'm Sarah from Google. How are you today?"
   User: "I'm doing well!"

5. MAIN INTERVIEW LOOP (5-7 questions)
   Backend picks next question (matching params + diversity)
   AI: "Question: Given an array of integers, find the two numbers..."
   User types/speaks answer (with code block if needed)
        ↓ LLM scores response on 5 dimensions
        ↓ Stores running average of scores

   Option A: AI asks follow-up
      AI: "Good! Can you explain the time complexity?"
      User: "It's O(n) because..."

   Option B: Move to next question
      AI: "Great. Next question..."

   [Repeat for 5-7 questions]

6. FINALIZATION
   User clicks "End Interview"
        ↓ Backend collects all messages
        ↓ LLM scores entire interview
   Returns: overall_score (0-100) + rubric breakdown

7. RESULTS
   Frontend displays:
      • Overall Score: 72/100
      • Rubric: {communication: 7, problem_solving: 7, ...}
      • Strengths: ["Clear explanations", ...]
      • Weaknesses: ["Missed edge case", ...]
      • Next Steps: ["Practice system design", ...]

8. HISTORY
   User can see all past sessions
   Compare scores over time
```

---

## 🔐 Data Flow: Authentication

```
BROWSER                          API SERVER
  │                               │
  ├─ POST /auth/signup ───────────→
  │  {email, password, name}      │ Hash password (Argon2)
  │                               │ Create pending_signup row
  │                               │ Send verification code email
  │  ←─────────── {ok: true} ─────┤
  │                               │
  ├─ POST /auth/verify ──────────→
  │  {email, code: "123456"}      │ Validate code
  │                               │ Create User row
  │  ←─────── {access_token} ─────┤ Generate JWT
  │                               │
  │ Store token in localStorage   │
  │ (key: "access_token")         │
  │                               │
  ├─ Subsequent API calls:        │
  ├─ GET /api/v1/sessions ───────→ Authorization: Bearer <TOKEN>
  │                               │ Decode JWT → get email → fetch user
  │                               │ Attach user to request context
  │  ←─────── {sessions: [...]} ──┤
```

---

## 🎮 Interview Engine: Question Selection Algorithm

```
When Backend Needs Next Question:
  │
  ├─ 1. Build pool of candidates:
  │      Questions where:
  │      • track = session.track (e.g., "swe_intern")
  │      • company_style = session.company_style
  │      • difficulty = session.difficulty_current
  │      • NOT already_seen by this user
  │
  ├─ 2. Apply tag diversity:
  │      • Track tags_seen in running scores
  │      • Prefer questions with NEW tags
  │      • Avoid duplicate tag combinations
  │
  ├─ 3. Check behavioral quota:
  │      if behavioral_questions_asked < behavioral_target:
  │         Pick behavioral question
  │      else:
  │         Pick technical question
  │
  ├─ 4. Adjust difficulty:
  │      Compute running skill average
  │      if avg_score > 7.5: difficulty_current = "hard"
  │      elif avg_score > 5: difficulty_current = "medium"
  │      else: difficulty_current = "easy"
  │
  └─ 5. Return selected question
```

---

## 📊 Message Flow: User Answers Question

```
User types answer in chat input
         ↓
User clicks "Send" button
         ↓
Frontend validates input (not empty, < 5000 chars)
         ↓
POST /sessions/{session_id}/message
  {
    "input_mode": "text",
    "content": "I would use a HashMap to store indices..."
  }
         ↓
BACKEND processes:
  1. Store message in DB (role="student")

  2. Compute quick rubric score:
     LLM or rule-based scoring:
     {
       "communication": 7,
       "problem_solving": 6,
       "correctness_reasoning": 7,
       "complexity": 8,
       "edge_cases": 5
     }

  3. Update skill_state running average:
     skill_state = {
       "n": 3,  // number of responses
       "sum": {...scores summed...},
       "last": {...latest scores...}
     }

  4. Check for special cases:
     • Did user say "I don't know"? → Simple follow-up
     • Was answer too vague? → Prompt for detail
     • Is user off-topic? → Redirect with reanchoring

  5. Generate AI follow-up or next question:
     Use LLM with prompts or fallback dataset-driven followups

  6. Store interviewer response in DB

  7. Check if max followups reached
     if followups_used >= max:
       Mark ready for next question

  ↓
Response: {
  "role": "interviewer",
  "content": "Great! Can you walk me through the time complexity...",
  "ready_for_next": false
}
         ↓
Frontend receives and displays in chat
```

---

## 🏆 Interview Finalization: Scoring Process

```
When interview ends (max_questions reached):
  │
  ├─ 1. Collect transcript:
  │      All messages from session.messages
  │      Format as alternating INTERVIEWER/CANDIDATE lines
  │
  ├─ 2. Build scoring context:
  │      • Rubric for evaluated dimensions
  │      • Whether behavioral questions included
  │      • Similar session context (RAG)
  │
  ├─ 3. Call LLM to score:
  │      System Prompt: "You are an expert tech interviewer..."
  │      User Prompt: "Score this interview transcript..."
  │
  ├─ 4. Parse LLM response:
  │      {
  │        "overall_score": 72,
  │        "rubric": {
  │          "communication": 7,
  │          "problem_solving": 7,
  │          "correctness_reasoning": 6,
  │          "complexity": 8,
  │          "edge_cases": 5
  │        },
  │        "strengths": ["Clear explanation", ...],
  │        "weaknesses": ["Missed edge case", ...],
  │        "next_steps": ["Practice system design", ...]
  │      }
  │
  ├─ 5. Calibrate score:
  │      Adjust overall_score based on rubric signals
  │      Ensure consistency (don't award 100 if rubric avg is 5)
  │
  ├─ 6. Store evaluation:
  │      CREATE evaluation row with scores
  │
  ├─ 7. Trigger embedding generation:
  │      Convert session to embedding for RAG
  │      Store in session_embedding table
  │
  └─ 8. Return evaluation to frontend
         Frontend displays score + breakdown
```

---

## 🗄️ Data Model Relationships

```
USER
  ├─ 1:Many ──→ INTERVIEW_SESSION
  │              ├─ 1:Many ──→ MESSAGE
  │              │              └─ role: interviewer|student
  │              ├─ 1:Many ──→ SESSION_QUESTION
  │              │              └─ FK → QUESTION
  │              ├─ 1:One ──→ EVALUATION
  │              │             ├─ overall_score: 0-100
  │              │             ├─ rubric: JSON
  │              │             └─ summary: JSON
  │              └─ 1:Many ──→ SESSION_EMBEDDING
  │                             └─ vector embedding
  │
  └─ 1:Many ──→ USER_QUESTION_SEEN
                 └─ Tracks which questions user already saw
                    (prevents repeats)

QUESTION
  ├─ 1:Many ──→ SESSION_QUESTION
  └─ Properties:
     ├─ track (swe_intern, data_science, etc)
     ├─ company_style (google, apple, general)
     ├─ difficulty (easy, medium, hard)
     ├─ tags_csv (arrays, sorting, medium, etc)
     ├─ question_type (coding, system_design, behavioral)
     └─ followups (JSON - optional)
```

---

## 🔧 Tech Stack Summary

| Layer      | Technology            | Purpose                   |
| ---------- | --------------------- | ------------------------- |
| Frontend   | Next.js 16 + React 19 | Web UI, routing, SSR      |
| State      | Zustand               | Client-side state         |
| API Client | Axios                 | HTTP requests with auth   |
| Backend    | FastAPI               | REST API framework        |
| Database   | PostgreSQL            | Persistent data storage   |
| ORM        | SQLAlchemy            | Python↔SQL mapping        |
| Migrations | Alembic               | Schema versioning         |
| Auth       | PyJWT + Argon2        | Token + password security |
| LLM        | DeepSeek API          | Interview generation      |
| TTS        | ElevenLabs + fallback | Audio generation          |
| Testing    | Pytest + Vitest       | Unit tests                |

---

## 🚀 Running the Full System

```bash
# Terminal 1: Database
docker-compose up -d          # Starts PostgreSQL

# Terminal 2: Backend
cd backend
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # Apply migrations
python seed.py --questions    # Load questions
uvicorn app.main:app --reload # Start server @ http://127.0.0.1:8000

# Terminal 3: Frontend
cd frontend-next
npm install
npm run dev                    # Start @ http://localhost:3000

# Open browser → http://localhost:3000
# Sign up → Create session → Start interview!
```

---

## 🧠 Key Concepts

### 1. Adaptive Difficulty

- Start: easy
- Track running score average
- Adjust question pool difficulty based on performance

### 2. Tag Diversity

- Ensure questions cover different topics
- Avoid asking multiple "array" questions
- Maintain breadth across domains

### 3. Behavioral Mix

- Target 2-3 behavioral questions per session
- Mix with technical questions
- Behavioral score influences overall score

### 4. LLM Fallback

- If DeepSeek unavailable: use dataset-driven fallbacks
- If no response: return conservative generic follow-ups
- Score fallback: simple rules instead of LLM

### 5. RAG (Retrieval-Augmented Generation)

- After interview finalized: embed session as vector
- Retrieve similar past sessions
- Use context to improve evaluation consistency

### 6. Skill State Tracking

```python
skill_state = {
  "n": 3,  # responses scored so far
  "sum": {  # cumulative scores
    "communication": 20,
    "problem_solving": 18,
    ...
  },
  "last": {  # scores from latest response
    "communication": 7,
    "problem_solving": 6,
    ...
  },
  "pool": {...question pool metadata...},
  "interviewer": {...interviewer profile...},
  "intro_used": true  # track greeting sent
}
```

---

## 📈 Expected Interview Timeline

| Phase          | Duration      | Events                    |
| -------------- | ------------- | ------------------------- |
| Warmup         | 1-2 min       | Greeting + small talk     |
| Question 1     | 3-5 min       | Question + 1-2 follow-ups |
| Question 2     | 3-5 min       | Question + 1-2 follow-ups |
| Question 3     | 3-5 min       | Question + 1-2 follow-ups |
| Question 4     | 3-5 min       | Question + 1-2 follow-ups |
| Question 5     | 3-5 min       | Question + 1-2 follow-ups |
| (Optional 6-7) | 3-5 min       | Additional questions      |
| **Total**      | **25-40 min** | Complete interview        |
| Finalization   | 5-30 sec      | LLM scoring               |

---

## ⚡ Performance Characteristics

| Operation          | Time  | Notes                    |
| ------------------ | ----- | ------------------------ |
| Signup             | 500ms | Email sending async      |
| Login              | 200ms | JWT verification         |
| Create session     | 500ms | DB write                 |
| Load messages      | 200ms | < 100 messages           |
| Send message       | 3-15s | Includes LLM call        |
| Finalize           | 5-30s | Full transcript LLM eval |
| Generate embedding | 2-5s  | After finalization       |

---

## 🎓 Code Paths for Common Tasks

### "I want to add a new question type"

1. Update `Question.question_type` enum in model
2. Add rubric section in `rubric_loader.py`
3. Update question selection logic in `interview_engine.py`
4. Create migration: `alembic revision --autogenerate -m "add question type"`

### "I want to customize scoring"

1. Edit `scoring_engine.py` → `_fallback_evaluation_data()`
2. Modify prompt in `prompt_templates.py` → `evaluator_system_prompt()`
3. Adjust calibration in `_calibrate_overall_score()`

### "I want to add a new difficulty level"

1. Update `ALLOWED_DIFFICULTIES` in `backend/app/core/constants.py`
2. Add difficulty tier to question datasets in `data/questions/`
3. Update frontend form validation

### "I want to integrate a different LLM"

1. Create new client in `backend/app/services/llm_client.py`
2. Implement `chat()` and `chat_json()` methods
3. Update imports in `interview_engine.py` and `scoring_engine.py`

---

## 📞 Debugging Checklist

```
[ ] Is backend running? (check http://127.0.0.1:8000/health)
[ ] Is frontend running? (check http://localhost:3000)
[ ] Is PostgreSQL running? (check docker ps)
[ ] Are migrations applied? (alembic current)
[ ] Is DATABASE_URL correct? (check .env)
[ ] Is token in localStorage? (DevTools → Application)
[ ] Does token have correct user? (JWT.io → decode)
[ ] Is LLM API key set? (check /api/v1/ai/status)
[ ] Are questions seeded? (check database)
[ ] Are CORS origins correct? (check /api/v1/sessions → preflight)
```

---

## 🎯 Project Goals Achieved

✅ Realistic interview simulation  
✅ Dynamic question selection  
✅ AI-powered follow-ups  
✅ Comprehensive scoring  
✅ Local deployment  
✅ JWT authentication  
✅ Session history & analytics  
✅ Adaptive difficulty  
✅ Fallback mechanisms  
✅ Production-ready architecture

---

**Print this page as reference while working on the project!**
