# API Reference & Request/Response Examples

## Base Configuration

```
Base URL: http://127.0.0.1:8000/api/v1
Headers: Content-Type: application/json
Auth: Bearer {access_token} (in Authorization header)
```

---

## Auth Endpoints

### 1. POST /auth/signup

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201):**

```json
{
  "ok": true,
  "message": "Verification code sent. Enter the 6-digit code to finish signup."
}
```

**Error (400):**

```json
{
  "detail": "Email already registered."
}
```

---

### 2. POST /auth/login

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

**Error (401):**

```json
{
  "detail": "Invalid email or password."
}
```

---

### 3. POST /auth/verify

**Request:**

```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

**Error (400):**

```json
{
  "detail": "Invalid or expired verification code."
}
```

---

## Session Endpoints

### 4. POST /sessions (Create Interview Session)

**Request:**

```json
{
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "behavioral_questions_target": 2
}
```

**Response (201):**

```json
{
  "id": 42,
  "user_id": 1,
  "role": "SWE Intern",
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "stage": "intro",
  "current_question_id": null,
  "questions_asked_count": 0,
  "max_questions": 7,
  "behavioral_questions_target": 2,
  "interviewer": {
    "id": "1",
    "name": "Alex",
    "gender": "male",
    "image_url": "https://..."
  },
  "created_at": "2026-02-02T10:30:00Z"
}
```

---

### 5. GET /sessions

**Query Params:** `?limit=50`

**Response (200):**

```json
[
  {
    "id": 42,
    "role": "SWE Intern",
    "track": "swe_intern",
    "company_style": "google",
    "difficulty": "medium",
    "stage": "done",
    "current_question_id": null,
    "questions_asked_count": 5,
    "max_questions": 7,
    "behavioral_questions_target": 2,
    "overall_score": 78,
    "interviewer": {
      "id": "1",
      "name": "Alex"
    },
    "created_at": "2026-02-02T10:30:00Z"
  }
]
```

---

### 6. GET /sessions/{id}

**Response (200):**

```json
{
  "id": 42,
  "user_id": 1,
  "role": "SWE Intern",
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "stage": "question",
  "current_question_id": 123,
  "questions_asked_count": 1,
  "followups_used": 0,
  "max_questions": 7,
  "max_followups_per_question": 2,
  "behavioral_questions_target": 2,
  "skill_state": {
    "n": 1,
    "sum": {
      "communication": 7,
      "problem_solving": 6,
      "correctness_reasoning": 7,
      "complexity": 5,
      "edge_cases": 4
    },
    "last": {
      "communication": 7,
      "problem_solving": 6,
      "correctness_reasoning": 7,
      "complexity": 5,
      "edge_cases": 4
    }
  },
  "interviewer": {
    "id": "1",
    "name": "Alex",
    "gender": "male",
    "image_url": "https://..."
  },
  "created_at": "2026-02-02T10:30:00Z"
}
```

---

### 7. POST /sessions/{id}/message (Send Message & Get AI Response)

**Request:**

```json
{
  "message": "I would solve this problem using a hash map to store seen values for O(1) lookup time."
}
```

**Response (200):**

```json
{
  "session_id": 42,
  "role": "interviewer",
  "content": "That's a good instinct! Hash maps are perfect for lookups. Can you walk me through your approach step by step? What would be the time and space complexity?",
  "created_at": "2026-02-02T10:35:00Z",
  "session_stage": "question",
  "next_action": "awaiting_response"
}
```

**Error (422):**

```json
{
  "detail": "Message is required."
}
```

---

### 8. POST /sessions/{id}/finalize (Score & Close Session)

**Request:**

```json
{}
```

**Response (200):**

```json
{
  "session_id": 42,
  "overall_score": 76,
  "rubric": {
    "communication": 8,
    "problem_solving": 7,
    "correctness_reasoning": 7,
    "complexity": 6,
    "edge_cases": 5
  },
  "summary": {
    "strengths": [
      "Clear articulation of approach",
      "Good problem decomposition"
    ],
    "weaknesses": [
      "Could have discussed edge cases earlier",
      "Minor calculation error on space complexity"
    ],
    "next_steps": [
      "Practice thinking aloud more consistently",
      "Review time/space complexity calculations"
    ]
  },
  "created_at": "2026-02-02T10:45:00Z"
}
```

---

## Question Endpoints

### 9. GET /questions

**Query Params:** `?track=swe_intern&company_style=google&difficulty=medium`

**Response (200):**

```json
[
  {
    "id": 101,
    "track": "swe_intern",
    "company_style": "google",
    "difficulty": "medium",
    "title": "Two Sum",
    "prompt": "Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target.",
    "tags": ["hash-map", "arrays", "two-pointer"],
    "question_type": "coding"
  },
  {
    "id": 102,
    "track": "swe_intern",
    "company_style": "google",
    "difficulty": "medium",
    "title": "Merge Intervals",
    "prompt": "Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals...",
    "tags": ["intervals", "sorting", "arrays"],
    "question_type": "coding"
  }
]
```

---

### 10. GET /questions/coverage

**Query Params:** `?track=swe_intern&company_style=google&difficulty=medium&include_behavioral=false`

**Response (200):**

```json
{
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "count": 24,
  "fallback_general": 15
}
```

---

### 11. GET /questions/{id}

**Response (200):**

```json
{
  "id": 101,
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "title": "Two Sum",
  "prompt": "Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target.",
  "tags": ["hash-map", "arrays", "two-pointer"],
  "question_type": "coding"
}
```

---

## Analytics Endpoints

### 12. GET /analytics/sessions/{id}/results

**Response (200):**

```json
{
  "session_id": 42,
  "overall_score": 76,
  "rubric": {
    "communication": 8,
    "problem_solving": 7,
    "correctness_reasoning": 7,
    "complexity": 6,
    "edge_cases": 5
  },
  "summary": {
    "strengths": [
      "Clear articulation of approach",
      "Good problem decomposition"
    ],
    "weaknesses": [
      "Could have discussed edge cases earlier",
      "Minor calculation error on space complexity"
    ],
    "next_steps": [
      "Practice thinking aloud more consistently",
      "Review time/space complexity calculations"
    ]
  }
}
```

---

## AI Endpoints

### 13. GET /ai/status

**Response (200):**

```json
{
  "configured": true,
  "status": "online",
  "fallback_mode": false,
  "last_ok_at": 1706804100.5,
  "last_error_at": null,
  "last_error": null,
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

**Fallback Response (when API key missing):**

```json
{
  "configured": false,
  "status": "offline",
  "fallback_mode": true,
  "reason": "DEEPSEEK_API_KEY not set",
  "last_ok_at": null,
  "last_error_at": null,
  "last_error": null,
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

---

### 14. POST /ai/chat (Free-form Chat)

**Request:**

```json
{
  "message": "What's the difference between merge sort and quick sort?",
  "history": [
    {
      "role": "user",
      "content": "Explain big-O notation"
    },
    {
      "role": "assistant",
      "content": "Big-O notation describes the worst-case time complexity of an algorithm..."
    }
  ]
}
```

**Response (200):**

```json
{
  "reply": "Merge sort uses divide-and-conquer with guaranteed O(n log n) in all cases, while quick sort averages O(n log n) but can degrade to O(n²) in worst case. Merge sort requires O(n) extra space; quick sort is in-place.",
  "mode": "live"
}
```

**Fallback Response (when offline):**

```json
{
  "reply": "AI is currently offline. Set DEEPSEEK_API_KEY in backend/.env and restart the server to enable chat responses.",
  "mode": "fallback"
}
```

---

## Voice/TTS Endpoints

### 15. POST /tts

**Request (JSON):**

```json
{
  "text": "Welcome to the interview. Let's start with the first question."
}
```

**Response (200) - Audio Available:**

```
Content-Type: audio/mpeg
X-TTS-Provider: elevenlabs
[binary audio data]
```

**Response (200) - Text Fallback:**

```json
{
  "mode": "text",
  "text": "Welcome to the interview. Let's start with the first question.",
  "tts_provider": "default"
}
```

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid token."
}
```

### 403 Forbidden

```json
{
  "detail": "Email not verified. Use the 6-digit verification code."
}
```

### 404 Not Found

```json
{
  "detail": "Session not found."
}
```

### 422 Unprocessable Entity (Validation)

```json
{
  "detail": "Invalid difficulty 'expert'. Allowed: easy, medium, hard."
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limited. Please try again later."
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

| Endpoint                 | Limit     | Window                  |
| ------------------------ | --------- | ----------------------- |
| `/auth/signup`           | 6 calls   | 60 sec (per IP + email) |
| `/auth/login`            | 10 calls  | 60 sec (per IP + email) |
| `/ai/chat`               | 30 calls  | 60 sec (per user)       |
| `/sessions/{id}/message` | Unlimited | -                       |
| Others                   | Unlimited | -                       |

---

## Authentication Flow (Complete Example)

```
1. User SignUp
   POST /auth/signup
   ├─ Email: user@example.com
   ├─ Password: SecurePass123!
   └─ → Gets 6-digit code via email

2. User Verifies Email
   POST /auth/verify
   ├─ Email: user@example.com
   ├─ Code: 123456
   └─ → Returns access_token

3. User Stores Token
   localStorage.setItem('token', access_token)

4. Future Requests
   GET /sessions
   ├─ Authorization: Bearer {access_token}
   └─ → Success

5. Token Expires (7 days)
   GET /sessions
   └─ → 401 Unauthorized
   └─ → Frontend redirects to /login
```

---

## Interview Flow (Complete Example)

```
1. Create Session
   POST /sessions
   ├─ track: "swe_intern"
   ├─ company_style: "google"
   ├─ difficulty: "medium"
   └─ → Session ID: 42, Stage: "intro"

2. Intro Message
   POST /sessions/42/message
   ├─ message: "Hello"
   └─ → AI: "Hi! I'm your interviewer today..."

3. Get Question
   POST /sessions/42/message
   ├─ message: "I'm ready for the first question"
   └─ → AI provides question (Stage: "question")

4. Answer Question (loop for followups)
   POST /sessions/42/message
   ├─ message: "I would use a hash map..."
   └─ → AI follows up or moves to next question

5. Complete Questions
   (Repeat until max_questions reached)

6. Finalize Session
   POST /sessions/42/finalize
   └─ → Returns overall_score, rubric, feedback

7. View Results
   GET /analytics/sessions/42/results
   └─ → Full evaluation data
```

---

## Testing with cURL

### Signup

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'
```

### Login

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### Create Session (with token)

```bash
TOKEN="your_access_token_here"
curl -X POST http://127.0.0.1:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "track": "swe_intern",
    "company_style": "google",
    "difficulty": "medium"
  }'
```

### Send Message

```bash
SESSION_ID=42
curl -X POST http://127.0.0.1:8000/api/v1/sessions/$SESSION_ID/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "My approach would be to use a two-pointer technique"
  }'
```

### Finalize Session

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sessions/$SESSION_ID/finalize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}'
```

---

## Constants & Enums

### Tracks

```
"swe_intern"
"swe_engineer"
"senior_engineer"
"cybersecurity"
"data_science"
"devops_cloud"
"product_management"
```

### Company Styles

```
"general"
"amazon"
"apple"
"google"
"microsoft"
"meta"
```

### Difficulties

```
"easy"
"medium"
"hard"
```

### Question Types

```
"coding"
"system_design"
"behavioral"
"conceptual"
```

### Session Stages

```
"intro"           # Greeting/warmup
"question"        # Asking main question
"followups"       # Followup questions
"evaluation"      # Scoring
"done"            # Complete
```

---

## Headers Reference

```
Required Headers:
  Content-Type: application/json
  Authorization: Bearer {token}  (except auth endpoints)

Optional Headers:
  User-Agent: Mozilla/5.0 ...
  Accept: application/json
  Accept-Language: en-US

Response Headers:
  Content-Type: application/json OR audio/mpeg
  X-TTS-Provider: elevenlabs|default
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
```
