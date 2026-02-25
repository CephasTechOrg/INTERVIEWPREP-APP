# Interview Prep AI - Quick Reference Guide

## 🎯 Project at a Glance

| Aspect             | Details                                                                     |
| ------------------ | --------------------------------------------------------------------------- |
| **Purpose**        | Mock interview platform with AI interviewer, dynamic questions, and scoring |
| **Backend**        | FastAPI (Python) + PostgreSQL + DeepSeek LLM                                |
| **Frontend**       | Next.js 16 (React 19 + TypeScript) + Zustand                                |
| **Deployment**     | Docker Compose with local PostgreSQL                                        |
| **Authentication** | JWT tokens + email verification                                             |
| **Database**       | 13+ tables with Alembic migrations                                          |

---

## 🔄 Interview Flow (Simple)

```
1. User Signup/Login
   └─ JWT Token → localStorage

2. Create Session
   └─ Select: role, track, company, difficulty

3. Warmup Phase
   └─ AI greeting + introduce interviewer profile

4. Interview Loop (5-7 questions)
   ├─ AI picks adaptive difficulty question
   ├─ User answers (text/code/voice)
   ├─ AI scores response (0-10 on each dimension)
   ├─ AI generates follow-up
   └─ User answers follow-up (up to 2 per question)

5. Finalization
   └─ Score entire interview with LLM

6. Results
   └─ Show score, rubric breakdown, feedback
```

---

## 📂 Core File Locations

### Backend Logic

- **Interview Flow:** `backend/app/services/interview_engine.py`
- **Scoring:** `backend/app/services/scoring_engine.py`
- **LLM Integration:** `backend/app/services/llm_client.py`
- **Session API:** `backend/app/api/v1/sessions.py`
- **Database Models:** `backend/app/models/`

### Frontend Components

- **Main App:** `frontend-next/src/app/page.tsx`
- **Interview UI:** `frontend-next/src/components/sections/InterviewSection.tsx`
- **API Client:** `frontend-next/src/lib/api.ts`
- **State Management:** `frontend-next/src/lib/stores/`
- **Services:** `frontend-next/src/lib/services/sessionService.ts`

### Configuration & Data

- **Backend Config:** `backend/.env`
- **Frontend Config:** `frontend-next/.env.local`
- **Questions:** `data/questions/{track}/`
- **Migrations:** `backend/alembic/versions/`

---

## 🔌 API Endpoints (v1)

### Authentication

```
POST   /auth/signup              # Create account
POST   /auth/verify              # Verify email code
POST   /auth/login               # Get JWT token
POST   /auth/forgot-password     # Start password reset
POST   /auth/reset-password      # Complete password reset
```

### Sessions (Interview)

```
GET    /sessions                 # List user's sessions
POST   /sessions                 # Create new session
GET    /sessions/{id}/messages   # Get chat history
POST   /sessions/{id}/start      # Initialize interview
POST   /sessions/{id}/message    # Send response → get AI reply
POST   /sessions/{id}/finalize   # Score interview
DELETE /sessions/{id}            # Delete session
```

### Questions

```
GET    /questions/{id}           # Get question details
GET    /questions/coverage       # Question availability
```

### Analytics

```
GET    /analytics/sessions/{id}/results   # Get final evaluation
```

### Utilities

```
GET    /ai/status                # LLM health check
POST   /voice/tts                # Generate audio
GET    /users/profile            # Get user info
```

---

## 💾 Database Schema (Simplified)

```
users
├─ id (PK)
├─ email (unique)
├─ full_name
├─ role_pref
└─ password_hash

interview_sessions
├─ id (PK)
├─ user_id (FK)
├─ track (swe_intern|...)
├─ difficulty
├─ stage (intro|question|followups|evaluation|done)
├─ questions_asked_count
├─ skill_state (JSON - running scores)
└─ current_question_id

questions
├─ id (PK)
├─ track
├─ company_style
├─ difficulty
├─ title
├─ prompt
├─ tags_csv
├─ followups (JSON)
└─ question_type (coding|system_design|behavioral)

messages
├─ id (PK)
├─ session_id (FK)
├─ role (interviewer|student|system)
├─ content (text)
└─ created_at

evaluations
├─ id (PK)
├─ session_id (FK, unique)
├─ overall_score (0-100)
├─ rubric (JSON)
├─ summary (JSON)
└─ created_at
```

---

## ⚙️ Configuration Values

### Backend (.env)

```
ENV=dev                                              # dev|production
SECRET_KEY=your-secret-key                          # JWT signing key
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/interviewprep

# Optional: LLM
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Optional: Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxx

# Optional: TTS
ELEVENLABS_API_KEY=sk-...
ELEVENLABS_VOICE_ID=cgSgspJ2msn4yqJNXP1l

# Optional: Frontend CORS
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend (.env.local)

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1
```

---

## 🎬 Quick Start Commands

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py --questions
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend-next
npm install
npm run dev
```

### Database (Docker)

```bash
docker-compose up -d
```

---

## 🧪 Testing Commands

### Backend

```bash
cd backend
pytest                          # Run all tests
pytest --cov=app               # With coverage
pytest tests/test_sessions.py  # Specific test
```

### Frontend

```bash
cd frontend-next
npm run test                    # Run tests
npm run test:coverage          # With coverage
```

---

## 🔍 Key Algorithms

### Question Selection

```python
# For each session:
1. Get pool: questions matching (track, company_style, difficulty_current)
2. Exclude: already_seen (UserQuestionSeen)
3. Prioritize: new tags (tag diversity)
4. Maintain: behavioral question mix (target: 2 per session)
5. Adjust: difficulty based on skill_state scores
```

### Adaptive Difficulty

```python
# skill_state tracks running average of 5 scores:
# {communication, problem_solving, correctness, complexity, edge_cases}

avg_score = sum(scores) / count

if avg_score > 7.5:
    difficulty_current = "hard"
elif avg_score > 5:
    difficulty_current = "medium"
else:
    difficulty_current = "easy"
```

### Quick Rubric Scoring

```python
# After each user response, LLM scores on 5 dimensions (0-10):
scores = {
    "communication": 7,
    "problem_solving": 6,
    "correctness_reasoning": 7,
    "complexity": 8,
    "edge_cases": 5
}

# Stored in skill_state for running average
```

### Final Scoring

```python
# LLM evaluates entire transcript:
overall_score = weighted_average_of_rubric_scores * calibration_factor

# Return:
{
    "overall_score": 72,  # 0-100
    "rubric": {
        "communication": 7,
        ...
    },
    "strengths": [...],
    "weaknesses": [...],
    "next_steps": [...]
}
```

---

## 🚀 Deployment Checklist

- [ ] Environment: Set `ENV=production`
- [ ] Secrets: Generate strong `SECRET_KEY`, `DEEPSEEK_API_KEY`
- [ ] Database: Use production PostgreSQL instance
- [ ] CORS: Set `FRONTEND_ORIGINS` to production domain only
- [ ] Migrations: Run `alembic upgrade head`
- [ ] SSL/TLS: Enable HTTPS
- [ ] Logging: Set up centralized logging
- [ ] Monitoring: Monitor API health and LLM status
- [ ] Backups: Configure database backups
- [ ] Secrets: Rotate regularly

---

## 🐛 Debugging Tips

### Backend Issues

```bash
# Check logs
tail -f backend/app/main.py  # See startup logs

# Check database
psql -U user -d interviewprep -c "\dt"  # List tables

# Check LLM
curl -X GET http://127.0.0.1:8000/api/v1/ai/status

# Run migrations
alembic current
alembic history
```

### Frontend Issues

```bash
# Check console
# Open browser DevTools → Console tab

# Check network
# DevTools → Network tab → see API calls

# Check storage
# DevTools → Application → localStorage → check token
```

### Common Problems

| Issue                        | Solution                                     |
| ---------------------------- | -------------------------------------------- |
| "Cannot connect backend"     | Check `uvicorn` running, CORS settings       |
| "401 Unauthorized"           | Verify JWT token in localStorage             |
| "Database connection failed" | Check DATABASE_URL, Postgres running         |
| "Migrations pending"         | Run `alembic upgrade head`                   |
| "LLM offline"                | Check DEEPSEEK_API_KEY, network connectivity |
| "Questions empty"            | Run `python seed.py --questions`             |

---

## 📊 Performance Metrics

### Expected Response Times

- Session creation: < 500ms
- Question selection: < 200ms
- LLM response: 2-10 seconds (depends on API)
- Finalization: 5-30 seconds (full transcript eval)
- List sessions: < 500ms

### Scalability

- Up to 1000 concurrent sessions per backend instance
- Database query optimization with indexes
- Consider caching for frequently accessed questions
- Use connection pooling (SQLAlchemy default)

---

## 📚 Key Dependencies

### Backend

- `fastapi==0.115.6` - Web framework
- `sqlalchemy==2.0.36` - ORM
- `psycopg2-binary==2.9.10` - PostgreSQL driver
- `alembic>=1.18.0` - Migrations
- `httpx==0.28.1` - Async HTTP client (LLM calls)
- `elevenlabs>=1.0.0` - TTS provider

### Frontend

- `next==16.1.6` - React framework
- `react==19.2.3` - UI library
- `zustand==5.0.11` - State management
- `axios==1.13.4` - HTTP client
- `tailwindcss==3.4.17` - CSS framework

---

## 🎓 Learning Path

1. **Understand the flow:** Read this guide + architecture docs
2. **Explore database:** Check schema in `backend/app/models/`
3. **Review API:** Check `backend/app/api/v1/` endpoints
4. **Read services:** Study `interview_engine.py` and `scoring_engine.py`
5. **Frontend components:** Check `InterviewSection.tsx` and stores
6. **Run locally:** Follow quick start commands
7. **Write tests:** Add test cases in `backend/tests/` and `frontend-next/__tests__/`
8. **Deploy:** Follow deployment checklist

---

## 📖 Documentation Files

| File                       | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| `README.md`                | Project overview                                 |
| `PROJECT_UNDERSTANDING.md` | Detailed technical guide (this guide created it) |
| `ARCHITECTURE_DIAGRAM.md`  | System architecture & data flows                 |
| `setup.md`                 | Local setup instructions                         |
| `MIGRATIONS.md`            | Database migration guide                         |
| `TESTING_GUIDE.md`         | Testing procedures                               |
| `EDGE_CASES_TODO.md`       | Known issues & fixes (31 cases)                  |

---

**Last Updated:** February 23, 2026
