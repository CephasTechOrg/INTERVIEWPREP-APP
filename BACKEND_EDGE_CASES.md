# Backend Edge Cases & Issues - Interview Prep AI

**Generated:** February 11, 2026  
**Severity Levels:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## 🔴 CRITICAL ISSUES

### 1. **Race Condition: Concurrent Finalize Calls**

**File:** `backend/app/api/v1/sessions.py` (line 243-258)

**Issue:**

```python
async def finalize(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # NO LOCK OR STATE CHECK
    try:
        result = await scorer.finalize(db, session_id)
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e
    session_crud.update_stage(db, s, "done")
    return result
```

**Scenario:**

- User clicks "Finalize" button twice rapidly (network retry, accidental double-click)
- Two concurrent requests hit the same session
- Both bypass `session.stage` check
- Both call `scorer.finalize()` → runs LLM evaluation twice
- Both update database with potentially different evaluation results
- **Winner-takes-all:** Last write wins, potentially with stale data

**Impact:**

- Incorrect evaluation scores if LLM returns different results
- Wasted LLM API calls (cost, rate-limit burn)
- Database inconsistency (multiple evaluations for one session)

**Root Cause:**

- No `session.stage` validation before finalize
- No optimistic locking or unique constraint
- Async function can be interrupted mid-execution

**Fix:**

```python
@router.post("/{session_id}/finalize")
async def finalize(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # ✅ ADD: Check stage to prevent double-finalization
    if s.stage == "done":
        existing_eval = get_evaluation(db, session_id)
        if existing_eval:
            return {"overall_score": existing_eval.overall_score, "rubric": existing_eval.rubric, "summary": ...}
        raise HTTPException(status_code=400, detail="Session already finalized.")

    if s.stage not in ("question", "followups", "wrapup"):
        raise HTTPException(status_code=400, detail="Cannot finalize session in current stage.")

    # ✅ ADD: Transition stage BEFORE finalization to prevent re-entry
    session_crud.update_stage(db, s, "done")

    try:
        result = await scorer.finalize(db, session_id)
    except LLMClientError as e:
        # ✅ REVERT stage on error
        session_crud.update_stage(db, s, "wrapup")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e

    return result
```

---

### 2. **Session Not Locked During Interview Flow**

**File:** `backend/app/api/v1/sessions.py` (lines 211-241 for message handling)

**Issue:**

```python
@router.post("/{session_id}/message")
async def send_message(session_id: int, payload: SendMessageRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # NO STAGE CHECK - session could be in "done" or "wrapup"
    try:
        await engine.handle_student_message(db, s, content, user_name=getattr(user, "full_name", None))
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e
```

**Scenarios:**

1. **User sends message AFTER clicking Finalize:**
   - Session is in "done" stage
   - Message still gets processed, stored to DB
   - Interview flow logic receives "done" session → undefined behavior
2. **User finishes interview, then reopens old session (browser tab caching):**
   - Sends new message to completed session
   - Messages are added to finalized session
   - Evaluation becomes outdated but not recomputed

3. **Concurrent message + finalize:**
   - Message handler updates `skill_state`
   - Finalize reads stale `skill_state`
   - Scoring based on incomplete data

**Impact:**

- Invalid state transitions in `InterviewEngine`
- Data corruption (messages in completed session)
- Scoring inconsistencies

**Fix:**

```python
@router.post("/{session_id}/message")
async def send_message(session_id: int, payload: SendMessageRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # ✅ ADD: Validate stage before accepting messages
    if s.stage == "done":
        raise HTTPException(status_code=400, detail="Session is already finalized.")

    if s.stage not in ("intro", "question", "followups", "candidate_solution", "wrapup"):
        raise HTTPException(status_code=400, detail="Session is not ready for input.")

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content is required.")

    logger.info("Session message user_id=%s session_id=%s", user.id, session_id)
    try:
        await engine.handle_student_message(db, s, content, user_name=getattr(user, "full_name", None))
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e
```

---

### 3. **JSON State Corruption in skill_state**

**File:** `backend/app/services/interview_engine.py` (lines 200-370+)

**Issue:**

```python
def _update_skill_state(self, db: Session, session: InterviewSession, quick_rubric_raw: Any, is_behavioral: bool = False) -> None:
    try:
        state: dict = session.skill_state if isinstance(session.skill_state, dict) else {}
    except Exception:
        state = {}
    # ... OPERATIONS ON state ...
    session.skill_state = new_state
    db.add(session)
    db.commit()
    db.refresh(session)
```

**Problems:**

1. **Silent Type Coercion:**
   - If `skill_state` is corrupted (not a dict), exception caught silently
   - New state created as empty dict, losing all history
   - No logging of corruption

2. **Lost Intermediate State (Read-Modify-Write):**

   ```python
   state = dict(state)  # Shallow copy
   state["n"] = n_prev + 1
   state["sum"] = sums  # Dictionary reference, not deep copy
   # If sums dict is modified externally → state corrupted
   ```

3. **Numeric Overflow:**
   - `n` clamped to `hi=10_000`
   - But `sum` clamped to `hi=1_000_000` per key
   - With 5 rubric keys: max total = 5,000,000
   - Division: `avg = sum / n` could overflow float representation
   - EMA calculation could produce NaN/Inf if sums overflow

4. **Race Condition in Refresh:**
   - Multiple concurrent updates to same session
   - `db.commit()` + `db.refresh()` = 2 DB operations (non-atomic)
   - Between commit and refresh, another update could overwrite

**Scenario:**

```
Thread A: Read skill_state = {"n": 100, "sum": {...}}
Thread B: Read skill_state = {"n": 100, "sum": {...}}

Thread A: Update to {"n": 101, "sum": {...}}
Thread A: Commit + Refresh

Thread B: Update to {"n": 101, "sum": {...}}  (doesn't include A's changes)
Thread B: Commit + Refresh  (OVERWRITES A's partial data)

Result: Lost update, skill_state inconsistent
```

**Impact:**

- Skill tracking becomes unreliable
- Adaptive difficulty breaks (based on corrupted state)
- Evaluation focuses on wrong weaknesses

**Fix:**

```python
def _update_skill_state(self, db: Session, session: InterviewSession, quick_rubric_raw: Any, is_behavioral: bool = False) -> None:
    # ✅ Refresh from DB to get latest state
    db.refresh(session)

    try:
        state: dict = session.skill_state if isinstance(session.skill_state, dict) else {}
    except Exception as e:
        logger.error("skill_state corruption detected: %s. Rebuilding from scratch.", e)
        state = {}

    # ✅ Deep copy nested dicts to prevent external mutations
    warm = dict(state.get("warmup") if isinstance(state.get("warmup"), dict) else {})
    focus = dict(state.get("focus") if isinstance(state.get("focus"), dict) else {})
    pool = dict(state.get("pool") if isinstance(state.get("pool"), dict) else {})

    # ... existing logic ...

    new_state: dict[str, Any] = {
        "n": min(10_000, n_prev + 1),
        "sum": {k: min(1_000_000, sums[k]) for k in self._RUBRIC_KEYS},  # ✅ Cap sums
        "last": dict(last),  # ✅ Deep copy
        "ema": dict(ema),  # ✅ Deep copy
        "streak": dict({"good": good_prev, "weak": weak_prev}),
    }

    session.skill_state = new_state
    db.add(session)
    db.commit()
    # ✅ Consider removing refresh() or implement pessimistic locking
```

---

## 🟠 HIGH SEVERITY ISSUES

### 4. **No Validation: Negative Questions Remaining**

**File:** `backend/app/services/interview_engine.py` (lines ~2370-2390)

**Issue:**

```python
def _max_questions_reached(self, session: InterviewSession) -> bool:
    max_q = int(session.max_questions or 0)
    if max_q <= 0:
        return False
    return int(session.questions_asked_count or 0) >= max_q
```

**Scenario:**

- Session created with `behavioral_questions_target = 10`, `max_questions = 5`
- This is logically impossible (can't ask 10 behavioral if max is 5)
- See `create_session()` in `backend/app/api/v1/sessions.py` line 163:
  ```python
  max_questions = max(7, behavioral_target)
  if tech_count == 0 and behavioral_target > 0:
      max_questions = behavioral_target
  ```
  This only fixes the case where `tech_count == 0`. Otherwise, behavioral questions can exceed max_questions.

**Impact:**

- Interview loop never terminates for behavioral questions
- Infinite follow-ups for behavioral answers
- Session hangs in "question" stage

**Fix:**

```python
# In create_session()
if behavioral_target > 0:
    max_questions = max(behavioral_target, behavioral_target + 2)  # At least behavioral_target + 2 tech

# In finalize()
max_questions = int(s.max_questions or 7)
if int(s.behavioral_questions_target or 0) > max_questions:
    logger.error("Session %d: behavioral_target > max_questions. Resetting.", s.id)
    s.behavioral_questions_target = max_questions - 1
    db.add(s)
    db.commit()
```

---

### 5. **Empty Question Pool Handling**

**File:** `backend/app/services/interview_engine.py` (lines ~2030-2060)

**Issue:**

```python
def _pick_next_main_question(self, db: Session, session: InterviewSession) -> Question | None:
    # ... returns None if no questions found
    q = self._pick_next_technical_question(...)
    if q:
        return q
    return self._pick_next_behavioral_question(db, session, asked_ids)
```

Then in `_advance_to_next_question()`:

```python
next_q = self._pick_next_main_question(db, session)
if not next_q:
    wrap = "No more questions available. Click Finalize to get your score."
    message_crud.add_message(db, session.id, "interviewer", wrap)
    session_crud.update_stage(db, session, "wrapup")  # ✅ OK
    return wrap
```

**But consider:**

- User can keep sending messages after `stage="wrapup"`
- No validation in `send_message()` prevents further messages
- Each message will trigger `handle_student_message()` → `_advance_to_next_question()` → returns wrap again
- Transcript gets polluted with duplicate wraps

**Scenario:**

- Questions run out at message #10
- User sends message #11 → wrap reply
- User sends message #12 → wrap reply again (duplicate)
- User sends message #13 → wrap reply again (duplicate)

**Impact:**

- Messy transcript for evaluation
- Wastes LLM tokens if scoring reads duplicate wraps
- Poor UX (confusing for user)

**Fix:**

```python
async def handle_student_message(self, db: Session, session: InterviewSession, content: str, user_name: str | None = None) -> None:
    # ✅ ADD: Prevent processing in wrapup/done stages
    if session.stage in ("wrapup", "done", "evaluation"):
        raise ValueError("Interview is no longer accepting input.")

    # ... existing logic ...
```

---

### 6. **No Validation: Interviewer Profile Injection**

**File:** `backend/app/api/v1/sessions.py` (line 136)

**Issue:**

```python
@router.post("")
def create_session(payload: CreateSessionRequest, ...):
    # ...
    interviewer = payload.interviewer.model_dump() if payload.interviewer else None
    # ...
    s = session_crud.create_session(
        ...
        interviewer=interviewer,
    )
```

**Schema Validation:**

- `CreateSessionRequest` should validate `interviewer`
- But there's no size limit on `interviewer` dict
- Frontend sends:
  ```json
  {
    "interviewer": {
      "id": "attacker-id",
      "name": "x".repeat(100000),
      "gender": "u".repeat(100000),
      "image_url": "http://..." + "x".repeat(100000)
    }
  }
  ```

````

**Impact:**
- `skill_state` JSON bloats (PostgreSQL JSON size limit may apply)
- Session bloats on each `_update_skill_state()` call
- DB storage wasted
- Serialization/deserialization performance degrades

**Fix:**
```python
# In schemas
class InterviewerProfile(BaseModel):
    id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    gender: str | None = Field(None, max_length=20)
    image_url: str | None = Field(None, max_length=500)
````

---

### 7. **LLM JSON Parsing: Incomplete Recovery**

**File:** `backend/app/services/llm_client.py` (lines 158-200)

**Issue:**

````python
async def chat_json(self, system_prompt: str, user_prompt: str, history: list[dict] | None = None) -> dict:
    raw = await self.chat(system_prompt, user_prompt, history=history)
    raw = (raw or "").strip()
    if not raw:
        raise LLMClientError("AI returned invalid JSON: empty response")

    # Try multiple parsing strategies...
    if raw.startswith("```"):
        raw2 = raw.strip("`").strip()
        if raw2.lower().startswith("json"):
            raw2 = raw2[4:].strip()
        raw = raw2

    # First attempt: full JSON
    obj = _loads(raw)
    if obj is None:
        # Second attempt: substring between {...}
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = _loads(raw[start : end + 1])

    if obj is None:
        # Third attempt: substring between [...]
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            obj = _loads(raw[start : end + 1])

    if obj is None or not isinstance(obj, dict):
        _record_llm_error("AI returned invalid JSON")
        raise LLMClientError("AI returned invalid JSON: expected an object")

    return obj
````

**Problems:**

1. **Substring Extraction Too Greedy:**

   ```
   Input: "The approach is { "name": "value" } and { "id": 1 }"
   Extracted: "{ "name": "value" } and { "id": 1 }"  (from first { to last })
   This is invalid JSON (two objects not in array)
   ```

2. **No Validation of Extracted Object:**
   - Pydantic schema validation happens in caller
   - If caller expects specific fields missing, ValidationError in caller
   - Error logged but not re-raised with context

3. **LLM Returns Malformed JSON Multiple Times:**
   - Retry logic in `_post_with_retries()` might retry
   - But if LLM consistently returns bad JSON, all retries fail
   - Eventual timeout after max_retries

**Impact:**

- False positives (extracted garbage looks like JSON)
- Evaluation data becomes invalid
- Frontend receives partial/wrong evaluation scores

---

## 🟡 MEDIUM SEVERITY ISSUES

### 8. **Database Constraint Missing: Duplicate Evaluations**

**File:** `backend/app/crud/evaluation.py` (assumed, not provided)

**Issue:**

- `session_id` should be unique in evaluations table
- But no `UNIQUE` constraint visible
- `upsert_evaluation()` uses `insert or replace` strategy
- If called twice rapidly, both may insert before either commits

**Scenario:**

```
Thread A: SELECT evaluation WHERE session_id=1 → None
Thread B: SELECT evaluation WHERE session_id=1 → None

Thread A: INSERT evaluation (session_id=1, score=85)
Thread B: INSERT evaluation (session_id=1, score=82)

Result: Two evaluations for session_id=1 (depends on DB conflict handling)
```

**Fix:**

```sql
ALTER TABLE evaluations ADD CONSTRAINT unique_session_evaluation UNIQUE(session_id);
```

---

### 9. **No Rate Limiting on Chat Messages**

**File:** `backend/app/api/v1/sessions.py` (line 211)

**Issue:**

```python
@router.post("/{session_id}/message")
async def send_message(session_id: int, payload: SendMessageRequest, ...):
    # NO rate limiting
```

**Compare with Auth:**

```python
# In auth.py
@router.post("/signup")
def signup(payload: SignupRequest, request: Request, ...):
    rate_limit(request, key=_rate_key(request, "signup", email), max_calls=6, window_sec=60)
```

**Attack Scenario:**

- User rapidly sends 100 messages (each triggers LLM call)
- Costs money (LLM API charges per token)
- Fills session transcript with garbage
- DoS vector

**Fix:**

```python
@router.post("/{session_id}/message")
async def send_message(session_id: int, payload: SendMessageRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # ✅ Add rate limiting
    rate_limit(request, key=f"session_message:{user.id}:{session_id}", max_calls=60, window_sec=60)
    # ... rest of function
```

---

### 10. **JWT Token Expiry Not Handled on Frontend**

**File:** `backend/app/api/v1/auth.py` (line 35)

**Issue:**

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
```

**Backend:**

- Tokens expire after 7 days
- Expired token returns 401

**Frontend:**

- Token stored in localStorage
- No refresh token mechanism visible
- When token expires, user gets 401 on next request
- Frontend redirects to `/login`
- **User loses session state** (current_session_id, messages, etc.)

**Scenario:**

1. User starts interview at 10am Monday
2. 7 days pass (they don't close browser tab)
3. User clicks "Send Message" at 10am the following Monday
4. 401 Unauthorized
5. Redirected to login
6. Session lost (no recovery mechanism)

**Impact:**

- Poor UX for long-running sessions
- No graceful token refresh
- Interview progress lost

**Fix:**

- Add refresh token rotation
- Implement token refresh middleware on frontend
- Or reduce token expiry to 1 day + add refresh endpoint

---

### 11. **Behavioral Question Fallback Hardcoded**

**File:** `backend/app/services/interview_engine.py` (lines ~1920-1930)

**Issue:**

```python
def _fallback_warmup_behavioral_question(self, session: InterviewSession) -> str:
    company = self._company_name(session.company_style)
    role = (session.role or "").strip().lower()
    if session.company_style == "general":
        if "intern" in role:
            return "Why are you interested in this internship?"
        return "Why are you interested in this role?"
    if "intern" in role:
        return f"Why do you want to intern at {company}?"
    return f"Why do you want to work at {company}?"
```

**Problems:**

1. **Always Returns "Why..." Questions:**
   - No variety in question types
   - Candidates memorize answers
   - Poor signal for evaluation

2. **Company Templating Breaks:**
   - If company_style = "Amazon", returns "Why do you want to work at amazon?" (lowercase)
   - Frontend display looks weird

3. **No Fallback for Track-Specific Questions:**
   - Data scientist role gets same "Why work at company?" as SWE
   - No domain-specific behavioral depth

**Fix:**

```python
def _fallback_warmup_behavioral_question(self, session: InterviewSession) -> str:
    company = self._company_name(session.company_style)
    role = (session.role or "").strip().lower()
    track = (session.track or "").strip().lower()

    questions_by_track = {
        "swe_intern": [
            "Why are you interested in this internship?",
            "What project are you most proud of?",
            "How do you handle debugging?",
        ],
        "swe_mid": [
            f"Why do you want to join {company}?",
            "Tell me about a time you led a technical initiative.",
            "How do you approach code reviews?",
        ],
        # ... more tracks
    }

    fallback_questions = questions_by_track.get(track, [
        f"Why are you interested in {company}?",
    ])

    # Deterministic rotation based on session ID
    idx = (session.id or 0) % len(fallback_questions)
    return fallback_questions[idx]
```

---

### 12. **Message Content Not Sanitized**

**File:** `backend/app/crud/message.py` (line 5)

**Issue:**

```python
def add_message(db: Session, session_id: int, role: str, content: str) -> Message:
    m = Message(session_id=session_id, role=role, content=content)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
```

**Scenario:**

- User sends message with very long content (10MB)
- Stored in DB as-is
- Later, when loading messages, memory spike
- Frontend renders 10MB of text → browser hangs

**Scenario 2:**

- User sends message with special characters (null bytes, etc.)
- Serialization could break JSON encoding
- Frontend fails to parse response

**Fix:**

```python
def add_message(db: Session, session_id: int, role: str, content: str) -> Message:
    # ✅ Sanitize and truncate
    content = (content or "").strip()
    if not content:
        raise ValueError("Message content cannot be empty")

    max_length = 50000  # ~10k tokens
    if len(content) > max_length:
        content = content[:max_length] + f"\n[truncated by system, {len(content) - max_length} chars removed]"

    # ✅ Remove null bytes
    content = content.replace('\x00', '')

    m = Message(session_id=session_id, role=role, content=content)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
```

---

### 13. **Behavioral Target Can Exceed Technical Questions**

**File:** `backend/app/api/v1/sessions.py` (line 140)

**Issue:**

```python
behavioral_count = question_crud.count_behavioral_questions(db, track, company_style, difficulty)
if behavioral_target > behavioral_count:
    raise HTTPException(status_code=422, detail="Not enough behavioral questions...")
```

But then:

```python
max_questions = max(7, behavioral_target)
if tech_count == 0 and behavioral_target > 0:
    max_questions = behavioral_target
```

**Scenario:**

- Track: "swe_intern"
- Behavioral available: 10
- Technical available: 15
- User requests: behavioral_target = 8, max_questions = 7
- Code sets `max_questions = max(7, 8) = 8`
- Interview tries to ask 8 behavioral + 0 technical = 8 questions
- But only 10 behavioral available total
- Follow-ups might repeat questions

**Fix:**

```python
behavioral_target = max(0, int(payload.behavioral_questions_target or 0))
behavioral_target = min(behavioral_target, behavioral_count)  # Cap to available
max_questions = max(behavioral_target + 2, 7)  # At least some technical
```

---

## 🟢 LOW SEVERITY ISSUES

### 14. **Silent Exception in Question Backfill**

**File:** `backend/app/crud/session.py` (lines 20-23)

**Issue:**

```python
def create_session(...):
    with contextlib.suppress(Exception):
        user_question_seen_crud.backfill_user_seen_questions(db, user_id=user_id)
    # If backfill fails, session created anyway
    # Potential: User might be asked questions they've already seen
```

**Impact:**

- Low probability (backfill fails rarely)
- Consequence is user gets repeat question (annoying, not fatal)

**Fix:**

```python
try:
    user_question_seen_crud.backfill_user_seen_questions(db, user_id=user_id)
except Exception as e:
    logger.warning("Failed to backfill seen questions for user_id=%s: %s", user_id, e)
    # Don't suppress entirely, but continue with session creation
```

---

### 15. **No Validation: Password Strength**

**File:** `backend/app/api/v1/auth.py` (line 39)

**Issue:**

```python
def signup(payload: SignupRequest, ...):
    # ...
    password_hash = hash_password(payload.password)
```

**What if:**

- Password = "123"
- Password = ""
- Password = "password"

**Fix:**

```python
# In schemas
class SignupRequest(BaseModel):
    password: str = Field(..., min_length=8, regex=r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)")
    # Requires: 8+ chars, 1 uppercase, 1 lowercase, 1 digit
```

---

### 16. **Interview Engine 2900+ Lines: Refactoring Debt**

**File:** `backend/app/services/interview_engine.py`

**Issue:**

- Single file: 2905 lines
- 200+ methods (many private utility methods)
- Hard to test individual methods
- High cyclomatic complexity
- Difficult to trace execution flow

**Scenario:**

- Bug in `_weakest_dimension()` affects `_prioritize_missing_focus()` → `_ask_new_main_question()`
- Hard to isolate where the bug originates

**Impact:**

- Maintenance nightmare
- Regressions likely when refactoring

**Recommendation:**

- Split into modules:
  - `interview_warmup_engine.py` (warmup logic)
  - `interview_question_engine.py` (question selection)
  - `interview_intent_engine.py` (intent classification)
  - `interview_rubric_engine.py` (scoring)
  - `interview_utils.py` (helper methods)

---

### 17. **No Logging of Invalid Input**

**File:** `backend/app/api/v1/sessions.py` (line 118)

**Issue:**

```python
role = (payload.role or "").strip() or "SWE Intern"
track = (payload.track or "").strip().lower()
company_style = (payload.company_style or "").strip().lower()
difficulty = (payload.difficulty or "").strip().lower()
_validate_session_inputs(track, company_style, difficulty)
```

**Scenario:**

- User sends invalid track "xyz_track"
- Validation raises HTTPException(422)
- No log of who attempted what

**Impact:**

- Can't audit suspicious behavior
- Hard to debug user errors

**Fix:**

```python
try:
    _validate_session_inputs(track, company_style, difficulty)
except HTTPException as e:
    logger.warning(
        "Invalid session input from user_id=%s: track=%s, company_style=%s, difficulty=%s. Error: %s",
        user.id, track, company_style, difficulty, e.detail
    )
    raise
```

---

### 18. **Evaluation Rubric Scores Not Capped**

**File:** `backend/app/services/scoring_engine.py` (line 135)

**Issue:**

```python
def _calibrate_overall_score(self, overall_score: int, rubric: dict) -> int:
    # ...
    if overall_score < (rubric_score - 5):
        return max(0, min(100, rubric_score - 2))
    return max(0, min(100, overall_score))
```

**What if LLM returns:**

```json
{
  "overall_score": 150,
  "rubric": {
    "communication": 15,
    "problem_solving": 12,
    ...
  }
}
```

**Current behavior:**

- `min(100, 150) = 100` ✓ capped
- But individual rubric scores not capped
- Frontend displays "problem_solving: 15/10" (invalid)

**Fix:**

```python
async def finalize(self, db: Session, session_id: int) -> dict:
    # ...
    try:
        data = await self.llm.chat_json(sys, user)
        parsed = EvaluationOutput.model_validate(data)
    except (LLMClientError, ValidationError):
        logger.exception("Evaluation fallback used for session_id=%s", session_id)
        parsed = EvaluationOutput.model_validate(self._fallback_evaluation_data())

    # ✅ CAP all rubric scores
    overall_score = max(0, min(100, int(parsed.overall_score or 0)))
    rubric = {k: max(0, min(10, int(v or 0))) for k, v in parsed.rubric.model_dump().items()}
```

---

### 19. **Hardcoded Magic Numbers**

**File:** Multiple files

**Examples:**

- `max_questions=7` (hardcoded in multiple places)
- `max_followups_per_question=2` (hardcoded)
- `temperature=0.4` (LLM)
- `alpha=0.35` (EMA smoothing)
- `timeout=45` (LLM)

**Issue:**

- No central config
- Changes require searching codebase
- Inconsistencies likely

**Fix:**

```python
# In app/core/config.py
INTERVIEW_CONFIG = {
    "max_questions_default": 7,
    "max_followups_per_question": 2,
    "llm_temperature": 0.4,
    "ema_alpha": 0.35,
    "rubric_keys": ("communication", "problem_solving", ...),
}
```

---

### 20. **No Audit Trail for Evaluations**

**File:** `backend/app/services/scoring_engine.py`

**Issue:**

- Evaluation created in `finalize()`
- No log of:
  - When evaluation was created
  - What LLM was used
  - Raw LLM response (before validation)
  - Fallback flag

**Impact:**

- Can't debug why scores are wrong
- Can't compare LLM outputs over time

**Fix:**

```python
# Add to Evaluation model
class Evaluation(Base):
    id: ...
    session_id: ...
    # ... existing fields ...
    llm_model: str = "deepseek-chat"
    was_fallback: bool = False
    created_at: datetime = server_default(func.now())
    updated_at: datetime = onupdate(func.now())
```

---

## Summary Table

| Issue                         | Severity | Category         | Fix Time | Risk   |
| ----------------------------- | -------- | ---------------- | -------- | ------ |
| Concurrent Finalize           | 🔴       | Race Condition   | 1h       | High   |
| Session Not Locked            | 🔴       | State Management | 1.5h     | High   |
| skill_state Corruption        | 🔴       | Data Integrity   | 2h       | High   |
| Behavioral Target Logic       | 🟠       | Logic Error      | 1h       | Medium |
| Empty Pool Handling           | 🟠       | Edge Case        | 0.5h     | Medium |
| Interviewer Profile Injection | 🟠       | Input Validation | 0.5h     | Medium |
| LLM JSON Parsing              | 🟠       | Error Handling   | 1h       | Medium |
| Missing DB Constraints        | 🟡       | Database         | 0.5h     | Low    |
| No Rate Limiting Messages     | 🟡       | Security         | 0.5h     | Low    |
| JWT Token Expiry              | 🟡       | UX               | 2h       | Low    |
| Others                        | 🟢       | Various          | Varies   | Low    |

---

## Recommendations for Immediate Action

**Priority 1 (Do First):**

1. Add stage validation to `send_message()` and `finalize()`
2. Fix session locking during message handling
3. Improve skill_state reliability

**Priority 2 (Do This Sprint):**

1. Add rate limiting to message endpoint
2. Validate behavioral_target logic
3. Add DB UNIQUE constraint on evaluations

**Priority 3 (Do Eventually):**

1. Refactor InterviewEngine into smaller modules
2. Add comprehensive logging/audit trail
3. Implement JWT refresh tokens
