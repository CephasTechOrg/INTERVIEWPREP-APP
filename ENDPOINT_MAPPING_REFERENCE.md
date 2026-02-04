# Backend Endpoint Mappings - Quick Reference

## Interview Session Endpoints

### 1. Load Message History

```
ENDPOINT:  GET /sessions/{session_id}/messages
FRONTEND:  sessionService.getMessages(currentSession.id)
RESPONSE:  MessageHistoryOut[] (array of messages with timestamps)
CALLED IN: InterviewSection.tsx - loadMessages() on mount
TRIGGER:  useEffect when currentSession.id changes

Flow:
  ┌─────────────────────────────────────────┐
  │ Component mounts / sessionId changes     │
  │ ↓                                       │
  │ loadMessages() called                   │
  │ ↓                                       │
  │ GET /sessions/{id}/messages             │
  │ ↓                                       │
  │ setMessages(result) → store update      │
  │ ↓                                       │
  │ If empty → call startSession()          │
  └─────────────────────────────────────────┘
```

---

### 2. Start Session (First AI Message)

```
ENDPOINT:  POST /sessions/{session_id}/start
FRONTEND:  sessionService.startSession(currentSession.id)
RESPONSE:  MessageOut (interviewer's opening message)
CALLED IN: InterviewSection.tsx - loadMessages()
TRIGGER:  Auto-called if message history is empty

Implementation:
  const result = await sessionService.getMessages(currentSession.id);
  if (result.length === 0) {
    const firstMessage = await sessionService.startSession(currentSession.id);
    addMessage(firstMessage);
  }
```

---

### 3. Send Student Message

````
ENDPOINT:  POST /sessions/{session_id}/message
FRONTEND:  sessionService.sendMessage(currentSession.id, {content: string})
PAYLOAD:   SendMessageRequest { content: string }
RESPONSE:  MessageOut (AI's reply)
CALLED IN: InterviewSection.tsx - handleSendMessage()
TRIGGER:  User clicks "Send" button

Payload Formats:
  ┌──────────────────────────────────┐
  │ Input Mode: TEXT                 │
  ├──────────────────────────────────┤
  │ {                                │
  │   "content": "Hello, I think..." │
  │ }                                │
  └──────────────────────────────────┘

  ┌──────────────────────────────────┐
  │ Input Mode: CODE                 │
  ├──────────────────────────────────┤
  │ {                                │
  │   "content": "```\n              │
  │              def factorial(n):\n │
  │              ...\n               │
  │              ```"                │
  │ }                                │
  └──────────────────────────────────┘

Flow:
  ┌─────────────────────────────────────────────────┐
  │ User types message → Click Send                 │
  │ ↓                                              │
  │ buildMessagePayload() - format based on mode   │
  │ ↓                                              │
  │ POST /sessions/{id}/message {content}          │
  │ ↓                                              │
  │ Backend:                                       │
  │  1. Store student message                      │
  │  2. Run through LLM                            │
  │  3. Generate AI response                       │
  │  4. Store AI message                           │
  │  5. Return latest message (AI's reply)         │
  │ ↓                                              │
  │ addMessage(response) → UI updates              │
  │ ↓                                              │
  │ Clear input fields                             │
  └─────────────────────────────────────────────────┘
````

---

### 4. Finalize Session & Get Evaluation

```
ENDPOINT:  POST /sessions/{session_id}/finalize
FRONTEND:  sessionService.finalizeSession(currentSession.id)
RESPONSE:  Evaluation {
             session_id: number,
             overall_score: number,
             rubric?: any,
             summary?: {
               strengths?: string[],
               weaknesses?: string[],
               next_steps?: string[]
             }
           }
CALLED IN: InterviewSection.tsx - handleFinalize()
TRIGGER:  User clicks "Submit & Evaluate" button

Backend Process:
  ┌─────────────────────────────────────────────────┐
  │ POST /sessions/{id}/finalize                    │
  │ ↓                                              │
  │ Backend runs ScoringEngine:                     │
  │  1. Fetch all session messages                 │
  │  2. Get current question details               │
  │  3. Send to LLM for scoring                    │
  │  4. Generate rubric scores                     │
  │  5. Create evaluation summary                  │
  │  6. Store evaluation in database               │
  │  7. Update session stage to 'done'             │
  │ ↓                                              │
  │ Return Evaluation object                       │
  └─────────────────────────────────────────────────┘

Frontend Response Handling:
  const result = await sessionService.finalizeSession(currentSession.id);
  setEvaluation(result);      // Store evaluation
  setCurrentPage('results');  // Navigate to results
```

---

### 5. Delete Session (End Early)

```
ENDPOINT:  DELETE /sessions/{session_id}
FRONTEND:  sessionService.deleteSession(currentSession.id)
RESPONSE:  { ok: boolean }
CALLED IN: InterviewSection.tsx - handleEndSession()
TRIGGER:  User clicks "End" button

Flow:
  ┌─────────────────────────────────────────────────┐
  │ User clicks "End" button                        │
  │ ↓                                              │
  │ DELETE /sessions/{id}                          │
  │ ↓                                              │
  │ Backend:                                       │
  │  1. Verify user owns session                   │
  │  2. Delete all messages for session            │
  │  3. Delete evaluation if exists                │
  │  4. Delete session record                      │
  │  5. Return { ok: true }                        │
  │ ↓                                              │
  │ clearSession()      → Clear global state       │
  │ setCurrentPage('dashboard')  → Navigate back   │
  └─────────────────────────────────────────────────┘
```

---

## Supporting Endpoints

### 6. Get Question Details

```
ENDPOINT:  GET /questions/{question_id}
FRONTEND:  questionService.getQuestion(latestQuestionId)
RESPONSE:  Question {
             id, title, prompt, company_style, difficulty,
             question_type, tags, ...
           }
CALLED IN: InterviewSection.tsx - loadCurrentQuestion()
TRIGGER:  Auto-called when latestQuestionId changes

Auto-Trigger Logic:
  const latestQuestionId = useMemo(() => {
    // Search messages backwards for current_question_id
    // Fall back to session.current_question_id
  }, [messages, currentSession.current_question_id])

  useEffect(() => {
    loadCurrentQuestion();  // Triggered when latestQuestionId changes
  }, [latestQuestionId]);

Display:
  - Title (bold)
  - Metadata (company, difficulty, type)
  - Prompt (monospace, preserved formatting)
  - Tags (blue badges with # prefix)
  - Copy to clipboard button
```

---

### 7. Get AI Service Status

```
ENDPOINT:  GET /ai/status
FRONTEND:  aiService.getStatus()
RESPONSE:  AIStatusResponse {
             status: 'online' | 'offline',
             configured: boolean,
             fallback_mode?: boolean,
             reason?: string,
             last_ok_at?: timestamp,
             last_error_at?: timestamp,
             last_error?: string
           }
CALLED IN: InterviewSection.tsx - loadAIStatus()
TRIGGER:  On mount + every 30 seconds

Polling Setup:
  useEffect(() => {
    loadAIStatus();
    const statusInterval = setInterval(loadAIStatus, 30000);
    return () => clearInterval(statusInterval);
  }, []);

Status Indicator Display:
  - Green dot + "Online" → status === 'online'
  - Red dot + "Offline" → status === 'offline'
  - Gray dot + "Checking..." → else
```

---

### 8. Text-to-Speech (Replay)

```
ENDPOINT:  POST /tts
FRONTEND:  aiService.generateSpeech({ text: string })
PAYLOAD:   { text: string }
RESPONSE:  {
             mode: 'audio' | 'text',
             audio_url?: string
           }
CALLED IN: InterviewSection.tsx - handleReplayLast()
TRIGGER:  User clicks "Replay" button

Flow:
  ┌─────────────────────────────────────────────────┐
  │ User clicks "Replay"                            │
  │ ↓                                              │
  │ Find last AI message (role === 'interviewer')  │
  │ ↓                                              │
  │ POST /tts { text: lastMessage.content }        │
  │ ↓                                              │
  │ Backend generates audio via TTS service        │
  │ ↓                                              │
  │ Return audio_url or error                      │
  │ ↓                                              │
  │ If audio_url:                                  │
  │   Create Audio element                         │
  │   Set src = audio_url                          │
  │   Call play()                                  │
  │ ↓                                              │
  │ Audio plays in browser                         │
  └─────────────────────────────────────────────────┘
```

---

## Error Codes & Handling

All endpoints can return these status codes:

```
✅ 200 OK
   Success - normal response returned

❌ 400 Bad Request
   Malformed request - check payload

❌ 401 Unauthorized
   Not authenticated - redirect to login

❌ 403 Forbidden
   Authenticated but not authorized

❌ 404 Not Found
   - Session doesn't exist
   - Question doesn't exist
   - User is not owner of session

❌ 422 Unprocessable Entity
   - Validation errors (e.g., invalid track)
   - Missing required fields
   - Business logic violations

❌ 502 Bad Gateway
   - LLM service error
   - Timeout calling external API
   - AI configuration issues

❌ 500 Internal Server Error
   - Database error
   - Unexpected server error

Frontend Handling:
  try {
    const result = await sessionService.sendMessage(...);
    addMessage(result);
  } catch (err) {
    const errorMsg = err instanceof Error
      ? err.message
      : 'Failed to send message';
    setLocalError(errorMsg);  // Show in toast
    setError(errorMsg);       // Store globally
  }
```

---

## Session Stages (Backend)

The backend tracks session progression via `session.stage`:

```
'intro'      → Session started, first message shown
'question'   → Question displayed, waiting for answer
'followup'   → AI asked follow-up question
'evaluation' → Finalize endpoint called
'done'       → Scoring complete, interview closed
```

Frontend respects stage:

- Disables input when stage === 'done'
- Uses stage for visual indicators
- Sends stage in session metadata

---

## Complete Call Sequence (Happy Path)

```
1. Dashboard: POST /sessions
   → Creates session, returns sessionId

2. InterviewSection loads with sessionId

3. useEffect: GET /sessions/{id}/messages
   → Empty array returned

4. Auto-call: POST /sessions/{id}/start
   → Returns AI's first message

5. Display: GET /questions/{questionId}
   → Load & display current question

6. Poll: GET /ai/status
   → Check if AI service online

7. User sends response: POST /sessions/{id}/message
   → Returns AI's next reply

   [Repeat step 7 multiple times]

8. User clicks Submit: POST /sessions/{id}/finalize
   → Returns evaluation

9. Navigate to results page with evaluation data

10. If user clicks End: DELETE /sessions/{id}
    → Session deleted
    → Return to dashboard
```

---

## Request/Response Examples

### Example 1: Send Text Message

**Request:**

```json
POST /sessions/123/message
{
  "content": "I would start by understanding the problem constraints."
}
```

**Response:**

```json
{
  "id": 5,
  "session_id": 123,
  "role": "interviewer",
  "content": "Good approach. Can you elaborate on what specific constraints you're considering?",
  "current_question_id": 42,
  "created_at": "2025-02-02T10:30:45Z"
}
```

---

### Example 2: Finalize Session

**Request:**

```
POST /sessions/123/finalize
(no payload)
```

**Response:**

```json
{
  "session_id": 123,
  "overall_score": 78,
  "rubric": {
    "communication": 8,
    "problem_solving": 7,
    "coding": 8,
    "optimization": 7
  },
  "summary": {
    "strengths": [
      "Clear problem breakdown",
      "Efficient algorithmic approach",
      "Good edge case handling"
    ],
    "weaknesses": [
      "Could have discussed more tradeoffs",
      "Time complexity analysis was brief"
    ],
    "next_steps": [
      "Practice dynamic programming patterns",
      "Work on space optimization techniques",
      "Build stronger communication habits"
    ]
  }
}
```

---

## Summary Table

| #   | Endpoint                  | Method | Frontend Call       | Response    | Purpose           |
| --- | ------------------------- | ------ | ------------------- | ----------- | ----------------- |
| 1   | `/sessions/{id}/messages` | GET    | `getMessages()`     | Message[]   | Load chat history |
| 2   | `/sessions/{id}/start`    | POST   | `startSession()`    | Message     | Get first AI msg  |
| 3   | `/sessions/{id}/message`  | POST   | `sendMessage()`     | Message     | Send response     |
| 4   | `/sessions/{id}/finalize` | POST   | `finalizeSession()` | Evaluation  | Score interview   |
| 5   | `/sessions/{id}`          | DELETE | `deleteSession()`   | {ok:bool}   | End early         |
| 6   | `/questions/{id}`         | GET    | `getQuestion()`     | Question    | Display question  |
| 7   | `/ai/status`              | GET    | `getStatus()`       | AIStatus    | Check LLM online  |
| 8   | `/tts`                    | POST   | `generateSpeech()`  | {audio_url} | Replay audio      |

---

✅ **All 8 endpoints properly wired and called in production-ready InterviewSection.tsx**
