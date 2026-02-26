# Interview Prep AI - Complete Technical Deep Dive

## Executive Summary

**Interview Prep AI** is a sophisticated full-stack mock interview platform that simulates realistic FAANG-level technical interviews using AI. The system combines adaptive question selection, real-time conversation management, intelligent scoring, and machine learning to provide personalized interview practice.

### Key Capabilities

- 🎯 **1,757 curated questions** across 6+ companies and 3 difficulty levels
- 🤖 **AI-powered interviewer** with memory, pattern recognition, and progressive hints
- 📊 **Adaptive difficulty** based on real-time performance
- 🎓 **RAG-enhanced scoring** that learns from past sessions
- 📈 **Comprehensive analytics** with detailed feedback and improvement paths

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│  Next.js 16 + React 19 + TypeScript + Zustand + TailwindCSS       │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTP/REST API (JWT Auth)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND API LAYER                              │
│  FastAPI + Pydantic + SQLAlchemy + PostgreSQL                      │
├─────────────────────────────────────────────────────────────────────┤
│  ENDPOINTS:                                                         │
│  • /auth          → Signup, Login, Verification                    │
│  • /sessions      → Create, Start, Message, Finalize               │
│  • /questions     → Question bank management                       │
│  • /analytics     → Session history and performance                │
│  • /feedback      → User ratings and feedback                      │
│  • /embeddings    → RAG system for smart scoring                   │
│  • /ai            → LLM health status                              │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   INTELLIGENT SERVICES LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ InterviewEngine  │  │  ScoringEngine   │  │   RAG Service    │ │
│  │                  │  │                  │  │                  │ │
│  │ • Question Pool  │  │ • Transcript     │  │ • Embeddings     │ │
│  │ • Adaptive Diff  │  │   Analysis       │  │ • Similarity     │ │
│  │ • Diversity      │  │ • Rubric Scoring │  │   Search         │ │
│  │ • Followups      │  │ • Hire Signal    │  │ • Context Inject │ │
│  │ • Hints (1-3)    │  │ • Patterns       │  │ • Response DB    │ │
│  │ • Memory         │  │ • Calibration    │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   LLM Client     │  │ Session Embedder │  │ Rubric Loader    │ │
│  │                  │  │                  │  │                  │ │
│  │ • DeepSeek API   │  │ • Post-finalize  │  │ • Track-based    │ │
│  │ • Retry Logic    │  │ • Vector Gen     │  │   rubrics        │ │
│  │ • Health Track   │  │ • Response Ext   │  │ • Behavioral     │ │
│  │ • Fallbacks      │  │                  │  │   focus          │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                                 │
│  PostgreSQL 15+ with pgvector extension                            │
├─────────────────────────────────────────────────────────────────────┤
│  CORE TABLES (13):                                                  │
│  • users                    → User accounts                         │
│  • interview_sessions       → Session state + skill tracking       │
│  • questions                → Question bank (1,757 items)          │
│  • messages                 → Chat history                         │
│  • evaluations              → Final scores + feedback              │
│  • session_questions        → Asked questions tracking             │
│  • user_question_seen       → Avoid repetition                     │
│  • session_embeddings       → RAG vectors (384-dim)                │
│  • question_embeddings      → Question vectors                     │
│  • response_examples        → High-quality response DB             │
│  • session_feedback         → User ratings                         │
│  • pending_signup           → Email verification                   │
│  • audit_log                → Security tracking                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Deep Dive

### 1. Database Schema & Models

#### Core Models

**`interview_sessions`** - Interview state machine

```python
class InterviewSession:
    id: int
    user_id: int

    # Session Configuration
    role: str                          # "SWE Intern", "Senior Engineer", etc.
    track: str                         # "swe_intern", "ml_engineer", etc.
    company_style: str                 # "google", "amazon", "general", etc.
    difficulty: str                    # User-selected cap: "easy", "medium", "hard"
    difficulty_current: str            # Adaptive current difficulty
    adaptive_difficulty_enabled: bool  # Allow difficulty to change

    # State Machine
    stage: str                         # "intro" → "question" → "followups" → "evaluation" → "done"
    questions_asked_count: int         # Progress tracker
    followups_used: int                # Followup counter for current question

    # Interview Configuration
    max_questions: int                 # Target: 5-7 questions per session
    max_followups_per_question: int    # Max: 2 followups per question
    behavioral_questions_target: int   # Mix: 0-3 behavioral questions

    # Intelligence State (JSON column)
    skill_state: dict                  # Rich state tracking:
    """
    {
        "n": 3,                        # Questions answered
        "sum": {"communication": 18, "problem_solving": 21, ...},  # Cumulative scores
        "last": {"communication": 6, "problem_solving": 7, ...},   # Last rubric
        "ema": {"communication": 6.2, ...},                         # Exponential moving avg
        "streak": {"good": 2, "weak": 0},                          # Performance streak

        # Context tracking
        "warmup": {...},               # Warmup state
        "interviewer": {               # AI interviewer profile
            "id": "alex_rivera",
            "name": "Alex",
            "gender": "neutral",
            "image_url": "..."
        },
        "pool": {                      # Question pool constraints
            "available_difficulties": ["easy", "medium"],
            "difficulty_cap_override": null
        },
        "focus": {...},                # Weakness targeting
        "reanchor": {                  # Re-clarification tracking
            "qid": 42,
            "count": 1
        },
        "clarify": {                   # Missing topic tracking
            "qid": 42,
            "attempts": 1,
            "missing": ["complexity", "edge_cases"]
        },
        "plan": {...},                 # Session plan
        "patterns": {                  # Cross-question patterns (Intelligence Upgrade)
            "n": 3,
            "complexity_count": 2,
            "approach_count": 3,
            "tradeoffs_count": 0,
            "strong_types": ["coding"],
            "weak_types": ["system_design"]
        }
    }
    """

    current_question_id: int | None
    created_at: datetime
```

**`questions`** - Question bank

```python
class Question:
    id: int

    # Classification
    track: str                         # "swe_intern", "senior_engineer", etc.
    company_style: str                 # "google", "amazon", "general", etc.
    difficulty: str                    # "easy", "medium", "hard"
    question_type: str                 # "coding", "conceptual", "system_design", "behavioral"

    # Content
    title: str                         # "Two Sum", "Design Rate Limiter", etc.
    prompt: str                        # Full question text
    tags_csv: str                      # "arrays,hashmap,sliding-window"

    # Intelligence Features
    followups: list                    # Pre-written followup questions (optional)
    expected_topics: list              # Topics answer should cover ["approach", "complexity"]
    evaluation_focus: list             # What to evaluate ["correctness", "edge_cases"]
    meta: dict                         # Extra metadata

    created_at: datetime
```

**`messages`** - Chat history

```python
class Message:
    id: int
    session_id: int
    role: str                          # "student", "interviewer", "system"
    content: str                       # Message text
    created_at: datetime
```

**`evaluations`** - Final scoring

```python
class Evaluation:
    id: int
    session_id: int
    overall_score: int                 # 0-100 calibrated score

    rubric: dict                       # Per-dimension scores (0-10 each)
    """
    {
        "communication": 7,
        "problem_solving": 8,
        "correctness_reasoning": 6,
        "complexity": 5,
        "edge_cases": 4
    }
    """

    summary: dict                      # Rich evaluation results
    """
    {
        "strengths": ["Clear explanation...", "Good approach..."],
        "weaknesses": ["Missed edge cases...", "No complexity analysis..."],
        "next_steps": ["Practice edge cases...", "Study time complexity..."],

        # Intelligence Upgrade fields
        "hire_signal": "lean_yes",     # "strong_yes", "yes", "lean_yes", "no", "strong_no"
        "narrative": "Candidate demonstrated...",
        "patterns_observed": ["Used hashmaps consistently...", "Avoided nested loops..."],
        "standout_moments": ["Elegant optimization...", "Asked clarifying questions..."]
    }
    """

    created_at: datetime
```

#### RAG System Models

**`session_embeddings`** - Session-level vectors

```python
class SessionEmbedding:
    id: int
    session_id: int
    embedding: list[float]             # 384-dim vector
    overall_score: int
    track: str
    difficulty: str
    company_style: str
    metadata: dict
    created_at: datetime
```

**`question_embeddings`** - Question vectors

```python
class QuestionEmbedding:
    id: int
    question_id: int
    embedding: list[float]             # 384-dim vector
    track: str
    difficulty: str
    question_type: str
    created_at: datetime
```

**`response_examples`** - High-quality response database

```python
class ResponseExample:
    id: int
    session_id: int
    question_id: int
    response_text: str                 # Candidate's answer
    score: int                         # Rubric score (7-10)
    embedding: list[float]             # 384-dim vector
    metadata: dict
    created_at: datetime
```

**`session_feedback`** - User ratings

```python
class SessionFeedback:
    id: int
    session_id: int
    user_id: int

    # Quick feedback
    thumbs: str | None                 # "up" or "down"
    rating: int | None                 # 1-5 stars
    comment: str | None

    # Detailed rubric feedback
    rubric_feedback: dict | None
    """
    {
        "communication": 8,
        "problem_solving": 7,
        "correctness_reasoning": 6,
        "complexity": 5,
        "edge_cases": 4
    }
    """

    created_at: datetime
```

---

### 2. Interview Engine - The Brain

**Location:** `backend/app/services/interview_engine.py` (1,108 lines)

The Interview Engine orchestrates the entire interview flow with human-like intelligence.

#### Responsibilities

1. **Question Selection** - Smart, adaptive question picking
2. **Difficulty Management** - Real-time difficulty adjustment
3. **Followup Generation** - AI-powered or fallback followups
4. **Conversation Management** - Warmup, transitions, hints
5. **State Tracking** - Performance, patterns, memory

#### Key Algorithms

##### 2.1 Adaptive Question Selection

```python
def _pick_next_question(self, db: Session, session: InterviewSession) -> Question | None:
    """
    Multi-dimensional question selection algorithm:

    1. Build candidate pool (track + company + difficulty)
    2. Apply diversity constraints (avoid repeated tags)
    3. Mix behavioral questions (target: 2-3)
    4. Target weak dimensions (from rubric gaps)
    5. Rank by quality score
    6. Apply smart fallbacks
    """

    # Step 1: Difficulty pool (adaptive if enabled)
    difficulties = self._adaptive_difficulty_try_order(session)

    # Step 2: Behavioral mix
    behavioral_count = self._behavioral_asked_count(db, session)
    target_behavioral = session.behavioral_questions_target
    prefer_behavioral = behavioral_count < target_behavioral

    # Step 3: Tag diversity (avoid repetition)
    seen_tags = self._session_tag_frequencies(db, session)

    # Step 4: Weakness targeting (from rubric)
    rubric_gaps = self._critical_rubric_gaps(session, threshold=5)
    weakness_dim = self._weakest_dimension(session)

    # Step 5: Build pool and score
    for difficulty in difficulties:
        candidates = self._build_question_pool(
            db, session, difficulty,
            prefer_behavioral=prefer_behavioral
        )

        # Score each question
        for q in candidates:
            score = 0

            # Diversity bonus (new tags)
            score += self._diversity_score(q, seen_tags)

            # Weakness targeting bonus
            score += self._weakness_score(q, weakness_keywords)
            score += self._question_rubric_alignment_score(q, rubric_gaps)

            # Type bonus (behavioral if needed)
            if prefer_behavioral and self._is_behavioral(q):
                score += 50

        # Pick highest score
        if candidates:
            return max(candidates, key=lambda q: score)

    return None  # Fallback if pool exhausted
```

##### 2.2 Adaptive Difficulty Algorithm

```python
def _maybe_bump_difficulty_current(self, db: Session, session: InterviewSession) -> None:
    """
    Real-time difficulty adjustment based on performance streaks:

    - Good streak (2+ strong answers, avg ≥ 7.5) → bump up one level
    - Weak streak (2+ weak answers, avg ≤ 4.5) → bump down one level
    - Respects user's selected difficulty as ceiling
    """
    if not session.adaptive_difficulty_enabled:
        return  # Stay at user-selected difficulty

    current = session.difficulty_current  # "easy", "medium", "hard"
    cap = session.difficulty              # User's max ceiling

    last_score = self._skill_last_overall(session)
    good_streak, weak_streak = self._skill_streaks(session)

    # Bump up if consistently strong
    if good_streak >= 2 and last_score >= 7.5:
        if self._difficulty_rank(current) < self._difficulty_rank(cap):
            session.difficulty_current = self._rank_to_difficulty(
                self._difficulty_rank(current) + 1
            )

    # Bump down if consistently weak
    elif weak_streak >= 2 and last_score <= 4.5:
        if self._difficulty_rank(current) > 0:
            session.difficulty_current = self._rank_to_difficulty(
                self._difficulty_rank(current) - 1
            )
```

##### 2.3 Progressive Hint System

```python
def _determine_hint_level(self, session: InterviewSession, question_id: int) -> int:
    """
    3-level progressive hint escalation:

    Level 0: No hints yet (open questions)
    Level 1: Weak performance after 1 followup (indirect nudge)
    Level 2: Still struggling (reveal direction)
    Level 3: Maximum scaffolding (near-direct hint)
    """
    last_score = self._skill_last_overall(session)
    if last_score is None or last_score >= 5.5:
        return 0  # Performing adequately

    followups_used = session.followups_used

    if followups_used == 0:
        return 0
    elif followups_used == 1:
        return 1 if last_score < 4.5 else 0
    elif followups_used == 2:
        if last_score < 3.5:
            return 3
        elif last_score < 5.0:
            return 2
        else:
            return 1
    else:
        return min(3, followups_used)
```

##### 2.4 Pattern Tracking (Intelligence Upgrade)

```python
def _session_patterns_summary(self, session: InterviewSession) -> str:
    """
    Generate cross-question pattern summary for controller context:

    Tracks:
    - Complexity analysis mentions
    - Approach/algorithm explanations
    - Trade-off discussions
    - Edge case coverage
    - Code-first without planning
    - Strong/weak question types
    """
    patterns = self._patterns_state(session)

    n = patterns.get("n", 0)
    if n == 0:
        return "No patterns yet (first question)."

    summary_lines = []

    # Complexity
    complexity_count = patterns.get("complexity_count", 0)
    if complexity_count >= max(2, n - 1):
        summary_lines.append(f"✓ Candidate consistently discusses complexity ({complexity_count}/{n}).")
    elif complexity_count == 0:
        summary_lines.append("⚠ Candidate has NOT mentioned complexity analysis in any answer.")

    # Trade-offs
    tradeoffs_count = patterns.get("tradeoffs_count", 0)
    if tradeoffs_count == 0 and n >= 2:
        summary_lines.append("⚠ Candidate has NOT discussed trade-offs.")
    elif tradeoffs_count >= 2:
        summary_lines.append(f"✓ Discusses trade-offs ({tradeoffs_count}/{n}).")

    # Edge cases
    edge_cases_count = patterns.get("edge_cases_count", 0)
    if edge_cases_count == 0 and n >= 2:
        summary_lines.append("⚠ No edge case coverage mentioned.")

    # Strong/weak types
    strong = patterns.get("strong_types", [])
    weak = patterns.get("weak_types", [])
    if strong:
        summary_lines.append(f"✓ Strong in: {', '.join(strong)}")
    if weak:
        summary_lines.append(f"⚠ Weaker in: {', '.join(weak)}")

    return "\n".join(summary_lines)
```

#### Conversation Quality Features

**Warmup Phase:**

- Personalized greeting with interviewer profile
- Natural smalltalk before diving into questions
- Sets professional but friendly tone

**Clarification Handling:**

- Detects when candidate asks for question clarification
- Re-states question without penalty
- Tracks clarification attempts to avoid loops

**Move-On Detection:**

- Recognizes "I don't know", "skip", "move on"
- Gracefully transitions without awkward pauses
- Suggests hints before giving up

**Non-Informative Response Detection:**

- Flags very short answers ("ok", "yes", "hmm")
- Prompts for elaboration without being pushy
- Balances between patience and progress

**Memory & Context:**

- Injects last 30 messages into LLM context
- References candidate's previous answers
- Cross-question pattern awareness

---

### 3. Scoring Engine

**Location:** `backend/app/services/scoring_engine.py` (165 lines)

Evaluates entire interview transcript with LLM-powered analysis.

#### Process Flow

```python
async def finalize(self, db: Session, session_id: int) -> dict:
    """
    1. Extract full transcript
    2. Load rubric context (track-specific)
    3. Get RAG context (similar sessions)
    4. Build evaluation prompt
    5. Call LLM for structured evaluation
    6. Calibrate overall score
    7. Store evaluation
    8. Trigger embedding generation (for future RAG)
    """
```

#### Rubric System

**5-Dimensional Scoring (0-10 each):**

```
communication          → Clarity, structure, vocabulary
problem_solving        → Approach, strategy, algorithm choice
correctness_reasoning  → Logic, proof, verification
complexity             → Time/space analysis, optimization
edge_cases             → Boundary conditions, error handling
```

**Overall Score (0-100):**

- Calibrated based on rubric average
- Considers difficulty level and adaptive performance
- Accounts for behavioral vs. technical mix

#### RAG-Enhanced Evaluation

```python
rag_context = _get_rag_context_safe(db, session_id)
"""
Injects similar session patterns:
- Score ranges for similar interviews
- Common strengths/weaknesses
- Example high-quality responses
- User feedback patterns
"""

sys = evaluator_system_prompt(
    rag_context=rag_context,
    difficulty=difficulty,
    difficulty_current=difficulty_current,
    adaptive=adaptive
)
```

#### Intelligence Upgrade Output

```json
{
  "overall_score": 78,
  "rubric": {
    "communication": 8,
    "problem_solving": 7,
    "correctness_reasoning": 8,
    "complexity": 6,
    "edge_cases": 7
  },
  "strengths": [
    "Clear explanation of hashmap approach",
    "Identified time complexity correctly",
    "Asked good clarifying questions"
  ],
  "weaknesses": [
    "Missed edge case: empty array",
    "Could discuss space-time tradeoffs more"
  ],
  "next_steps": ["Practice edge case analysis", "Study amortized complexity"],

  // Intelligence Upgrade fields
  "hire_signal": "lean_yes",
  "narrative": "Candidate demonstrated solid problem-solving fundamentals with clear communication. While they correctly identified the O(n) hashmap solution and explained their reasoning well, there's room for growth in edge case coverage and optimization discussion. Overall shows promise for an intern-level role.",
  "patterns_observed": [
    "Consistently used hashmaps for O(1) lookup",
    "Explained approach before coding",
    "Asked clarifying questions upfront"
  ],
  "standout_moments": [
    "Quickly pivoted from brute force to optimal solution",
    "Caught their own bug during explanation"
  ]
}
```

---

### 4. LLM Client

**Location:** `backend/app/services/llm_client.py` (205 lines)

Manages all DeepSeek API interactions with robustness features.

#### Features

**Retry Logic:**

```python
max_retries = 2
backoff = 0.8 seconds (exponential with jitter)
retry_on = [429, 500, 502, 503, 504]
```

**Health Tracking:**

```python
get_llm_status() → {
    "configured": bool,
    "status": "online" | "offline" | "unknown",
    "fallback_mode": bool,
    "last_ok_at": timestamp,
    "last_error_at": timestamp,
    "last_error": str
}
```

**JSON Parsing:**

- Handles markdown code blocks: \`\`\`json ...\`\`\`
- Extracts JSON from mixed text
- Validates structure with Pydantic

**Fallback Behavior:**

- Returns safe defaults if LLM unavailable
- Never crashes the interview flow
- Logs errors for debugging

---

### 5. RAG System

**Location:**

- `backend/app/services/rag_service.py` - Retrieval logic
- `backend/app/services/session_embedder.py` - Embedding generation
- `backend/app/services/embedding_service.py` - Vector computation

#### Embedding Pipeline

**1. After Session Finalization:**

```python
def embed_completed_session(db: Session, session_id: int) -> dict:
    """
    1. Extract session transcript
    2. Generate 384-dim embedding (sentence-transformers)
    3. Store in session_embeddings table
    4. Extract high-quality responses (score ≥ 7)
    5. Create response_examples with embeddings
    """
```

**2. During New Interviews:**

```python
def get_rag_context_for_session(db: Session, session_id: int) -> tuple[str, dict]:
    """
    1. Get current session embedding
    2. Find similar sessions (cosine similarity)
    3. Extract patterns (scores, strengths, weaknesses)
    4. Find similar high-quality responses
    5. Format as context string
    """
```

#### Vector Search

```sql
-- Cosine similarity query (pgvector)
SELECT
    session_id,
    1 - (embedding <=> query_embedding) AS similarity
FROM session_embeddings
WHERE track = 'swe_intern'
  AND difficulty = 'medium'
ORDER BY similarity DESC
LIMIT 5
```

#### Context Injection Example

```
CONTEXT FROM SIMILAR SESSIONS:

Session patterns (5 similar interviews):
- Average score range: 70-85
- Common strengths: Clear communication, good complexity analysis
- Common weaknesses: Missed edge cases, incomplete testing discussion
- Behavioral performance: Strong STAR format usage

Example high-quality responses:
1. [Question: Two Sum] "I'd use a hashmap to store complements..."
   Score: 8/10, Strong points: Complexity analysis, edge cases covered

2. [Question: LRU Cache] "The key insight is combining hashmap with doubly-linked list..."
   Score: 9/10, Strong points: Clear explanation, optimal approach

Feedback patterns:
- Users rated detailed complexity discussions highly
- Sessions with 5-6 questions scored better than 7+ (quality > quantity)
```

---

### 6. API Endpoints

#### Authentication (`/api/v1/auth`)

```
POST   /signup              → Create account + send verification
POST   /verify              → Verify email with token
POST   /login               → Get JWT token
POST   /request-reset       → Request password reset
POST   /reset-password      → Reset with token
```

#### Sessions (`/api/v1/sessions`)

```
GET    /                    → List user's sessions
POST   /                    → Create new session
GET    /{id}/messages       → Load chat history
POST   /{id}/start          → Get first AI message (warmup)
POST   /{id}/message        → Send candidate response + get AI reply
POST   /{id}/finalize       → Score interview + generate evaluation
DELETE /{id}                → Delete session
```

#### Questions (`/api/v1/questions`)

```
GET    /                    → List questions (paginated)
GET    /{id}                → Get question details
POST   /                    → Create question (admin)
GET    /stats               → Question bank statistics
GET    /counts              → Count by track/company/difficulty
```

#### Analytics (`/api/v1/analytics`)

```
GET    /summary             → User's performance summary
GET    /sessions            → Session history with scores
GET    /trends              → Performance over time
```

#### Feedback (`/api/v1/feedback`)

```
POST   /                    → Submit session feedback
GET    /session/{id}        → Get feedback for session
GET    /me                  → Current user's feedback
GET    /stats               → Aggregated feedback stats
```

#### Embeddings (`/api/v1/embeddings`)

```
GET    /stats               → Embedding counts
GET    /rag/status          → Check if RAG is ready
POST   /rag/test            → Test RAG retrieval
POST   /questions/embed-all → Embed all questions
POST   /sessions/{id}/embed → Embed single session
GET    /sessions/{id}/similar → Find similar sessions
GET    /questions/{id}/similar → Find similar questions
```

#### AI Status (`/api/v1/ai`)

```
GET    /status              → LLM health check
```

#### Users (`/api/v1/users`)

```
GET    /me                  → Get profile
PATCH  /me                  → Update profile
POST   /me/avatar           → Upload avatar
POST   /deactivate          → Deactivate account
```

---

## Interview Flow - Complete Lifecycle

### Phase 1: Session Creation

**User Input:**

```json
{
  "role": "SWE Intern",
  "track": "swe_intern",
  "company_style": "google",
  "difficulty": "medium",
  "adaptive_difficulty_enabled": true,
  "behavioral_questions_target": 2,
  "interviewer": {
    "id": "alex_rivera",
    "name": "Alex Rivera",
    "gender": "neutral",
    "image_url": "..."
  }
}
```

**Backend Process:**

```python
POST /sessions
↓
1. Validate inputs (track, company, difficulty exist)
2. Count available questions (ensure enough behavioral)
3. Create InterviewSession record
4. Initialize skill_state with interviewer profile
5. Set stage = "intro"
6. Return session object
```

### Phase 2: Warmup / Start

**Request:**

```
POST /sessions/{id}/start
```

**Backend Process:**

```python
1. Check stage == "intro"
2. Generate warmup greeting:
   - Use interviewer profile (name, style)
   - Create personalized opening
   - Set friendly tone
3. Create first AI message (role="interviewer")
4. Update stage → "question"
5. Return AI message
```

**Example Output:**

```
Hi! I'm Alex Rivera, and I'll be your interviewer today. I'm excited to work through some technical problems with you. Before we dive in, how are you feeling? Any questions about the format?
```

### Phase 3: Main Interview Loop

**For each question (5-7 total):**

#### 3.1 Pick Next Question

```python
POST /sessions/{id}/message {"content": "I'm ready!"}
↓
1. Detect stage transition needed
2. Call InterviewEngine._pick_next_question()
   - Build candidate pool
   - Apply diversity constraints
   - Target weak dimensions
   - Rank by quality
3. Mark question as asked (session_questions table)
4. Update current_question_id
5. Render question with company name
6. Return question to candidate
```

#### 3.2 Candidate Responds

```python
POST /sessions/{id}/message {"content": "I would use a hashmap..."}
↓
1. Store candidate message
2. Call InterviewEngine.handle_message()
3. Analyze response:
   - Check for clarification request
   - Check for "move on" / "don't know"
   - Check if too vague/short
4. Generate quick rubric (0-10 on 5 dimensions)
5. Update skill_state with scores
6. Determine next action:
   - Need followup? → Generate followup
   - Done with question? → Pick next question
   - Need clarification? → Re-state question
7. Call LLM for AI response
8. Return AI message
```

#### 3.3 Followup (1-2 max)

```python
if followups_used < max_followups_per_question:
    # Generate intelligent followup
    1. Identify rubric gaps (score < 5)
    2. Determine hint level (0-3)
    3. Generate pattern summary (cross-question context)
    4. Call LLM with controller prompt
    5. Return targeted followup
else:
    # Move to next question
    Pick next question from pool
```

### Phase 4: Finalization

**Request:**

```
POST /sessions/{id}/finalize
```

**Backend Process:**

```python
1. Extract full transcript (all messages)
2. Load track-specific rubric
3. Get RAG context (similar sessions)
4. Build evaluation prompt:
   - System: Evaluator guidelines + RAG context
   - User: Transcript + rubric + difficulty
5. Call DeepSeek LLM
6. Parse structured evaluation:
   - overall_score (0-100)
   - rubric (5 dimensions)
   - strengths, weaknesses, next_steps
   - hire_signal, narrative, patterns, standout_moments
7. Calibrate score (avoid harsh scoring)
8. Store evaluation in database
9. Update stage → "done"
10. Trigger embedding generation (async)
11. Return evaluation
```

### Phase 5: RAG Learning (Background)

**After finalization:**

```python
embed_completed_session(db, session_id)
↓
1. Extract transcript text
2. Generate 384-dim embedding
3. Store in session_embeddings
4. Extract high-quality responses (score ≥ 7):
   - For each question answered well
   - Extract candidate's response
   - Generate response embedding
   - Store in response_examples
5. This data powers future RAG context
```

---

## Intelligence Features

### 1. Adaptive Difficulty

**How it works:**

- User selects max difficulty (easy/medium/hard)
- System starts at selected level
- If enabled, adjusts based on performance:
  - 2+ strong answers (avg ≥ 7.5) → bump up
  - 2+ weak answers (avg ≤ 4.5) → bump down
- Never exceeds user's selected ceiling

**Benefits:**

- Keeps interview challenging but not frustrating
- Adjusts to candidate's actual skill level
- Provides more accurate assessment

### 2. Progressive Hint System

**3-Level Escalation:**

**Level 0 (No hints):**

- Open-ended followup questions
- "Can you walk me through your approach?"
- "What trade-offs would you consider?"

**Level 1 (Indirect nudge):**

- Reframe the problem
- "Think about what happens when you need to look up values quickly"
- Hint at direction without giving answer

**Level 2 (Reveal direction):**

- Point to specific data structure/concept
- "What data structure gives you O(1) lookup?"
- Provide framework without solution

**Level 3 (Maximum scaffolding):**

- Walk through solution together
- "Let's use a hashmap. What would you store as keys?"
- Near-direct guidance while keeping candidate engaged

### 3. Pattern Tracking

**Cross-Question Analysis:**

- Tracks recurring behaviors across all questions
- Identifies strengths and weaknesses
- Adjusts questioning strategy
- Provides context to LLM controller

**Tracked Patterns:**

- Complexity analysis mentions (does candidate always discuss Big-O?)
- Trade-off discussions (considers pros/cons?)
- Edge case coverage (thinks about boundaries?)
- Code-first vs. plan-first approach
- Strong/weak question types (coding vs. system design)

### 4. Memory & Context

**Full Conversation History:**

- Last 30 messages injected into every LLM call
- Controller can reference previous answers
- Cross-question consistency checking
- Natural conversation flow

**Session-Level State:**

- Rubric scores (cumulative, EMA, last)
- Performance streaks (good/weak runs)
- Weakness targeting (which dimension needs work)
- Tag diversity (avoid repetition)
- Clarification tracking (avoid loops)

### 5. RAG-Enhanced Scoring

**Learning from Past Sessions:**

- Builds vector database of completed interviews
- Retrieves similar sessions during evaluation
- Injects patterns and examples into prompts
- Learns what "good" looks like without retraining model

**Improves Over Time:**

- More sessions → better context
- User feedback → refinement signals
- High-quality responses → example database
- No model fine-tuning required

---

## Data Flow Examples

### Example 1: First Question

```
USER: Clicks "Start Interview"
  ↓
FRONTEND: POST /sessions/{id}/start
  ↓
BACKEND: InterviewEngine.start_interview()
  ├─ Generate warmup greeting
  ├─ Store AI message (role="interviewer")
  ├─ Update stage → "question"
  └─ Return: "Hi! I'm Alex Rivera..."
  ↓
FRONTEND: Display greeting in chat
  ↓
USER: Types "I'm ready to start"
  ↓
FRONTEND: POST /sessions/{id}/message {"content": "I'm ready to start"}
  ↓
BACKEND: InterviewEngine.handle_message()
  ├─ Detect: need to pick first question
  ├─ Call _pick_next_question()
  │  ├─ Build pool: track=swe_intern, company=google, difficulty=medium
  │  ├─ Filter: avoid already-asked questions
  │  ├─ Score: diversity (no repeated tags yet)
  │  └─ Pick: highest-scoring question
  ├─ Store question in session_questions
  ├─ Update current_question_id
  ├─ Render question (replace {company} with "Google")
  └─ Return: "Great! Let's start with a coding question..."
  ↓
FRONTEND: Display question + prompt
```

### Example 2: Candidate Answers Question

```
USER: Types full answer explaining hashmap approach
  ↓
FRONTEND: POST /sessions/{id}/message {"content": "I would use a hashmap..."}
  ↓
BACKEND: InterviewEngine.handle_message()
  ├─ Store candidate message
  ├─ Analyze response:
  │  ├─ Extract keywords (hashmap, O(n), iterate)
  │  ├─ Check for complexity mention → YES
  │  ├─ Check for edge cases → NO
  │  ├─ Check if vague/short → NO
  │  └─ Response is substantive
  ├─ Generate quick rubric:
  │  ├─ Call LLM with rubric prompt
  │  ├─ Parse: {"communication": 7, "problem_solving": 8, ...}
  │  └─ Detect: edge_cases score = 3 (gap!)
  ├─ Update skill_state:
  │  ├─ n: 0 → 1
  │  ├─ sum: {communication: 7, problem_solving: 8, ...}
  │  ├─ last: {communication: 7, ...}
  │  ├─ ema: {communication: 7.0, ...}
  │  └─ patterns: {complexity_count: 1, edge_cases_count: 0}
  ├─ Determine action:
  │  ├─ followups_used = 0
  │  ├─ gap detected: edge_cases
  │  └─ Generate targeted followup
  ├─ Build controller prompt:
  │  ├─ System: "You're an expert interviewer..."
  │  ├─ Context: Last 30 messages
  │  ├─ Patterns: "Candidate mentioned complexity but not edge cases"
  │  ├─ Hint level: 0 (no hints yet)
  │  └─ User: "Generate followup targeting edge_cases"
  ├─ Call DeepSeek LLM
  ├─ Parse response: "Good approach! What edge cases should we consider?"
  ├─ Store AI message
  ├─ Increment followups_used → 1
  └─ Return AI message
  ↓
FRONTEND: Display followup question
```

### Example 3: Finalization

```
USER: Clicks "Finish & Evaluate"
  ↓
FRONTEND: POST /sessions/{id}/finalize
  ↓
BACKEND: ScoringEngine.finalize()
  ├─ Load all messages (200 max)
  ├─ Build transcript:
  │  INTERVIEWER: Hi! I'm Alex...
  │  CANDIDATE: I'm ready to start
  │  INTERVIEWER: Let's start with Two Sum...
  │  CANDIDATE: I would use a hashmap...
  │  (continues for all messages)
  ├─ Load rubric context (track-specific)
  ├─ Get RAG context:
  │  ├─ Find similar sessions (cosine similarity)
  │  ├─ Extract patterns (5 similar sessions)
  │  └─ Format: "Average score: 70-85, Common strengths: ..."
  ├─ Build evaluation prompt:
  │  ├─ System: Evaluator guidelines + RAG context + difficulty
  │  └─ User: Full transcript + rubric dimensions
  ├─ Call DeepSeek LLM
  ├─ Parse structured evaluation:
  │  {
  │    "overall_score": 78,
  │    "rubric": {"communication": 8, ...},
  │    "strengths": [...],
  │    "weaknesses": [...],
  │    "next_steps": [...],
  │    "hire_signal": "lean_yes",
  │    "narrative": "...",
  │    "patterns_observed": [...],
  │    "standout_moments": [...]
  │  }
  ├─ Calibrate score: Check rubric avg vs. overall_score
  ├─ Store evaluation in database
  ├─ Update stage → "done"
  ├─ Trigger embedding generation:
  │  ├─ Generate session embedding (384-dim)
  │  ├─ Extract high-quality responses (score ≥ 7)
  │  ├─ Generate response embeddings
  │  └─ Store in session_embeddings + response_examples
  └─ Return evaluation
  ↓
FRONTEND: Display results page with score, rubric, feedback
```

---

## Configuration & Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/interview_prep
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# JWT Auth
JWT_SECRET_KEY=<generated-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080  # 7 days

# DeepSeek LLM
DEEPSEEK_API_KEY=<your-api-key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=45
DEEPSEEK_MAX_RETRIES=2

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<password>
FROM_EMAIL=noreply@interview-prep.com

# Frontend
FRONTEND_ORIGINS=http://localhost:3000,https://your-domain.com

# Environment
ENV=dev  # dev | staging | production
```

### Running Locally

```bash
# 1. Start PostgreSQL
docker-compose up -d

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Start backend
uvicorn app.main:app --reload --port 8000

# 4. Start frontend
cd frontend-next
npm install
npm run dev  # Runs on port 3000
```

### Database Migrations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

---

## Testing

### Backend Tests (Pytest)

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html
```

**Test Coverage:**

- Unit tests for services (interview_engine, scoring_engine)
- Integration tests for API endpoints
- Database CRUD operations
- Authentication flows
- Edge cases and error handling

### Frontend Tests (Vitest)

```bash
cd frontend-next
npm test
```

**Test Coverage:**

- Component rendering
- State management (Zustand)
- API service calls
- User interactions
- Error boundaries

---

## Performance Characteristics

### Database

**Indexed Columns:**

- `users.email` - Login lookups
- `interview_sessions.user_id` - User's session list
- `questions.track`, `questions.company_style`, `questions.difficulty` - Question pool queries
- `messages.session_id` - Chat history retrieval
- `session_questions.session_id` - Asked questions tracking

**Query Optimization:**

- Prepared statements via SQLAlchemy
- Connection pooling (size=20, overflow=10)
- Limited result sets (paginated endpoints)
- Eager loading for relationships

### LLM Calls

**Latency:**

- Typical: 1-3 seconds per response
- Followups: 2-4 seconds (longer prompts)
- Finalization: 5-10 seconds (full transcript analysis)

**Optimization:**

- Async/await for non-blocking
- Retry with exponential backoff
- Timeout: 45 seconds max
- Fallback responses if unavailable

### RAG Vector Search

**Embedding Generation:**

- Per session: ~1-2 seconds (sentence-transformers)
- Batch all questions: ~30-60 seconds for 1,757 questions

**Similarity Search:**

- Cosine similarity via pgvector
- Indexed vector columns
- Query time: <100ms for top-5 results

---

## Security Features

### Authentication

- JWT tokens with 7-day expiry
- Bcrypt password hashing (cost factor: 12)
- Email verification required
- Rate limiting on auth endpoints
- Password reset via token

### Authorization

- All API endpoints require valid JWT
- User can only access own sessions/data
- Admin-only endpoints for question management
- CORS configured per environment

### Data Protection

- SQL injection protection (SQLAlchemy)
- XSS protection (escaped outputs)
- CSRF protection (stateless API)
- Security headers (X-Frame-Options, etc.)
- HTTPS in production (Strict-Transport-Security)

### Audit Logging

- Track critical operations (login, signup, data changes)
- Stored in `audit_log` table
- Retention policy configurable

---

## Key Design Decisions

### 1. **Difficulty-First File Organization**

Questions organized as:

```
data/questions/{track}/{company}/{difficulty}.json
```

**Rationale:**

- Matches user mental model (pick difficulty first)
- Simpler file management (3 files vs. 9+)
- Flexible query patterns (filter by type at runtime)
- Real interviews mix question types

### 2. **JSON Column for skill_state**

Store complex state in single JSON column vs. separate tables.

**Rationale:**

- State is session-scoped (no joins needed)
- Schema flexibility (can add fields without migration)
- Atomic updates (no consistency issues)
- Faster reads (single column vs. multiple rows)

### 3. **Quick Rubric After Every Response**

Generate 5-dimension score after each answer, not just at end.

**Rationale:**

- Enables adaptive difficulty in real-time
- Targets weak dimensions with followups
- Provides running feedback to interviewer
- Improves final evaluation context

### 4. **RAG Instead of Fine-Tuning**

Use retrieval-augmented generation rather than fine-tuning LLM.

**Rationale:**

- No expensive retraining
- Learns continuously (new sessions → better context)
- Transparent (can inspect retrieved examples)
- Flexible (works with any LLM provider)

### 5. **Progressive Hint System**

Escalate hints gradually (0 → 1 → 2 → 3) rather than binary (hint or no hint).

**Rationale:**

- More realistic (human interviewers guide gradually)
- Avoids giving away answer too quickly
- Keeps candidate engaged and thinking
- Better assessment of true skill level

---

## Known Limitations & Future Work

### Current Limitations

1. **Single-threading:** Sequential question selection (could be cached)
2. **LLM Dependency:** Relies on DeepSeek availability (fallbacks are conservative)
3. **Embedding Model:** Fixed to sentence-transformers (could support custom models)
4. **No Code Execution:** Can't run candidate's code (relies on explanation)
5. **English Only:** No multi-language support yet

### Planned Enhancements

1. **Code Execution Sandbox** - Run and test candidate's code
2. **Voice Interview Mode** - Speech-to-text and text-to-speech
3. **Multi-Language Support** - Support for non-English interviews
4. **Video Recording** - Record interview for later review
5. **Team Collaboration** - Share sessions with mentors/peers
6. **Custom Question Import** - Allow users to add own questions
7. **Advanced Analytics** - Trend analysis, skill gap identification
8. **Mobile App** - iOS/Android native apps

---

## Advanced Implementation Details

### Interviewer Personality System

The system includes 4 distinct interviewer personalities that affect tone, response style, and questioning approach:

**1. Cephas** - Calm & Easygoing

```python
{
    "style": "calm and easygoing",
    "traits": (
        "Relaxed and patient — never intimidating. "
        "Use light humor when natural. Gentle nudges without spoiling. "
        "Celebrate briefly: 'Nice, that's clean.' / 'Yeah, I like that.'"
    ),
    "warmup_openers": [
        "How's it going today?",
        "What's been keeping you busy lately?",
        "Ready to dive in, or do you need a minute?"
    ]
}
```

**2. Mason** - Rigorous & Direct

```python
{
    "style": "rigorous and direct",
    "traits": (
        "High bar from first question. Polite but no-nonsense. "
        "Don't let vague answers slide. Call out wrong/imprecise directly. "
        "Short acknowledgments: 'Okay. Now prove it.' / 'That works. What breaks it?'"
    )
}
```

**3. Erica** - Warm & Collaborative

```python
{
    "style": "warm and collaborative",
    "traits": (
        "Solving problems together, not against. Openly empathetic. "
        "Guide with curiosity: 'What made you go that route?' "
        "Celebrate effort: 'Good thinking even if approach needs work.'"
    )
}
```

**4. Maya** - Analytical & Methodical

```python
{
    "style": "analytical and methodical",
    "traits": (
        "Cares about HOW someone thinks more than answer. "
        "Ask for explicit reasoning: 'Walk me through exactly why that works.' "
        "Probe assumptions: 'What are you assuming?' / 'Under what conditions does that break?'"
    )
}
```

### Company-Specific Style Guides

Each company has distinct interviewing characteristics:

```python
def _company_style_guide(company_style: str) -> str:
    if company_style == "amazon":
        return (
            "Tone: direct, structured, high-bar. "
            "Focus: leadership principles (ownership, dive deep, customer impact). "
            "Ask for trade-offs, risks, and how success would be measured."
        )
    elif company_style == "google":
        return (
            "Tone: precise, rigorous, engineering-focused. "
            "Focus: correctness, invariants, complexity, and edge cases. "
            "Ask for clear justification."
        )
    elif company_style == "meta":
        return (
            "Tone: fast-paced, collaborative, product-aware. "
            "Focus: iteration, metrics, and clear trade-offs. "
            "Encourage thinking aloud and alternatives."
        )
    # ... more companies
```

---

## Detailed Algorithm Walkthroughs

### Algorithm 1: Question Selection with Multi-Dimensional Scoring

**Location:** `interview_engine_questions.py::_pick_next_technical_question()`

This algorithm balances multiple competing objectives:

```python
def _pick_next_technical_question(
    db: Session,
    session: InterviewSession,
    asked_ids: set[int],
    seen_ids: set[int],
    focus: dict[str, Any] | None,
    desired_type: str | None = None,
) -> Question | None:
    """
    Multi-stage question selection:
    1. Build candidate pool (track, company, difficulty)
    2. Filter out already-asked and seen questions
    3. Score each candidate on 5 dimensions
    4. Pick highest-scoring question
    """

    # Stage 1: Base query filters
    diff = self._effective_difficulty(session)
    company = (session.company_style or "").strip().lower() or "general"

    base = db.query(Question).filter(
        Question.track == session.track,
        Question.company_style == company,
        Question.difficulty == diff,
        ~Question.tags_csv.ilike("%behavioral%"),  # Technical only
        Question.question_type != "behavioral",
    )

    # Stage 2: Exclusion filters
    if asked_ids:
        base = base.filter(~Question.id.in_(asked_ids))
    if seen_ids:
        base = base.filter(~Question.id.in_(seen_ids))

    # Stage 3: Random sample (prevents always picking same question)
    candidates = base.order_by(func.random()).limit(120).all()

    if desired_type:
        candidates = [c for c in candidates if self._matches_desired_type(c, desired_type)]

    if not candidates:
        return None

    # Stage 4: Multi-dimensional scoring
    focus_tags = set((focus or {}).get("tags") or [])
    asked_tags = self._get_asked_tags(db, asked_ids)
    rubric_gaps = self._critical_rubric_gaps(session, threshold=5)
    weakness_dim = self._weakest_dimension(session)
    weak_keywords = self._weakness_keywords(weakness_dim)

    best = None
    best_score = -10_000

    for q in candidates:
        tags = {t.strip().lower() for t in (q.tags() or []) if t}

        # Dimension 1: Focus tag match (+5 per match)
        overlap = len(tags & focus_tags) if focus_tags else 0

        # Dimension 2: Tag diversity penalty (-1 per repeated tag)
        penalty = len(tags & asked_tags) if asked_tags else 0

        # Dimension 3: Weakness targeting (+1 per keyword match)
        weak_score = self._weakness_score(q, weak_keywords)

        # Dimension 4: Rubric gap alignment (+10 per gap addressed)
        rubric_score = self._question_rubric_alignment_score(q, rubric_gaps)

        # Dimension 5: Question quality bonus (future: rating system)
        quality_bonus = 0  # Reserved for future use

        # Compute total score
        score = (overlap * 5) + weak_score + rubric_score + quality_bonus - penalty

        if best is None or score > best_score:
            best = q
            best_score = score

    return best
```

**Scoring Example:**

Candidate answered previous question with rubric:

```json
{
  "communication": 8,
  "problem_solving": 7,
  "correctness_reasoning": 7,
  "complexity": 3, // ← GAP!
  "edge_cases": 4 // ← GAP!
}
```

Question candidates scoring:

```
Question A: "Optimize Array Search"
  Tags: ["arrays", "binary-search", "optimization"]
  evaluation_focus: ["complexity", "optimization"]

  Score breakdown:
  + Focus overlap: 0 (no focus tags yet)
  + Weakness score: 2 (mentions "optimize", "complexity")
  + Rubric alignment: 10 (targets complexity gap!)
  - Tag penalty: 1 (arrays already seen)
  = Total: 11 points ← SELECTED!

Question B: "Implement LRU Cache"
  Tags: ["hashmap", "linked-list", "design"]
  evaluation_focus: ["approach", "correctness"]

  Score breakdown:
  + Focus overlap: 0
  + Weakness score: 0 (doesn't mention complexity keywords)
  + Rubric alignment: 0 (doesn't target gaps)
  - Tag penalty: 0
  = Total: 0 points
```

### Algorithm 2: Adaptive Difficulty with Streak Detection

**Location:** `interview_engine.py::_maybe_bump_difficulty_current()`

```python
def _maybe_bump_difficulty_current(self, db: Session, session: InterviewSession) -> None:
    """
    Smart difficulty adjustment based on performance patterns:

    - 2+ strong answers (avg ≥ 7.5) → bump up
    - 2+ weak answers (avg ≤ 4.5) → bump down
    - Respects user's selected ceiling
    - Only applies if adaptive_difficulty_enabled=True
    """

    # Check if adaptive mode enabled
    selected = session.difficulty  # User's max ceiling
    adaptive_enabled = session.adaptive_difficulty_enabled

    if not adaptive_enabled:
        # Lock to user-selected difficulty
        if session.difficulty_current != selected:
            session.difficulty_current = selected
            db.commit()
        return

    # Get current state
    current = session.difficulty_current or selected
    cap_rank = self._difficulty_rank(selected)      # 0=easy, 1=medium, 2=hard
    current_rank = self._difficulty_rank(current)

    # Get performance indicators
    last_overall = self._skill_last_overall(session)  # Last rubric avg (0-10)
    good_streak, weak_streak = self._skill_streaks(session)

    # Decision logic
    bumped = current_rank

    # Bump UP condition: 2+ strong answers, currently below cap
    if last_overall >= 7.5 and good_streak >= 2:
        if current_rank < cap_rank:
            bumped = current_rank + 1
            logger.info(f"Session {session.id}: Bumping difficulty UP (streak={good_streak}, score={last_overall})")

    # Bump DOWN condition: 2+ weak answers, currently above easy
    elif last_overall <= 4.5 and weak_streak >= 2:
        if current_rank > 0:
            bumped = current_rank - 1
            logger.info(f"Session {session.id}: Bumping difficulty DOWN (streak={weak_streak}, score={last_overall})")

    # Apply change
    if bumped != current_rank:
        session.difficulty_current = self._rank_to_difficulty(bumped)
        db.commit()
        db.refresh(session)
```

**Example Timeline:**

```
Interview starts: difficulty=medium, difficulty_current=medium

Q1: Two Sum (medium)
    Answer: Good explanation, mentions O(n), clean code
    Rubric: {communication: 8, problem_solving: 8, ..., complexity: 7, edge_cases: 6}
    Average: 7.4
    → good_streak = 1 (but need 2 to bump)

Q2: Valid Parentheses (medium)
    Answer: Excellent stack solution, discusses edge cases
    Rubric: {communication: 9, problem_solving: 9, ..., complexity: 8, edge_cases: 8}
    Average: 8.4
    → good_streak = 2 ✓
    → Bump UP to difficulty_current=hard

Q3: Longest Substring Without Repeating (hard)
    Answer: Struggles, doesn't identify sliding window
    Rubric: {communication: 5, problem_solving: 4, ..., complexity: 3, edge_cases: 4}
    Average: 4.0
    → weak_streak = 1, good_streak = 0

Q4: Merge K Sorted Lists (hard)
    Answer: Still struggling, incomplete solution
    Rubric: {communication: 4, problem_solving: 3, ..., complexity: 2, edge_cases: 3}
    Average: 3.2
    → weak_streak = 2 ✓
    → Bump DOWN to difficulty_current=medium

Q5: Group Anagrams (medium)
    Answer: Much better, hashmap approach clear
    Rubric: {communication: 7, problem_solving: 7, ..., complexity: 7, edge_cases: 6}
    Average: 6.8
    → Stays at medium
```

### Algorithm 3: Progressive Hint Escalation

**Location:** `interview_engine_main.py::_get_hint_level()` + controller prompt

The hint system has 4 levels (0-3) that progressively reveal more information:

```python
def _get_hint_level(self, session: InterviewSession, q_id: int) -> int:
    """
    Determine hint level based on:
    1. Number of followups already used
    2. Performance on latest answer
    3. Track hint history per question

    Level 0: No hints (open questions)
    Level 1: Indirect nudge (reframe problem)
    Level 2: Reveal direction (point to data structure/concept)
    Level 3: Maximum scaffolding (walk through together)
    """
    last_score = self._skill_last_overall(session)

    # If performing adequately, no hints needed
    if last_score is None or last_score >= 5.5:
        return 0

    followups_used = session.followups_used

    # Escalation rules
    if followups_used == 0:
        return 0  # First attempt, no hints yet

    elif followups_used == 1:
        # After first followup, provide hint if still struggling
        return 1 if last_score < 4.5 else 0

    elif followups_used == 2:
        # After second followup, escalate based on severity
        if last_score < 3.5:
            return 3  # Critical: maximum scaffolding
        elif last_score < 5.0:
            return 2  # Struggling: reveal direction
        else:
            return 1  # Slight difficulty: indirect nudge

    else:
        # After 2+ followups, cap at level 3
        return min(3, followups_used)
```

**Hint Level Examples:**

**Level 0 (No hints):**

```
Candidate: "I think we can use a nested loop to find all pairs."
Interviewer: "Walk me through your approach. What's the time complexity?"
```

**Level 1 (Indirect nudge):**

```
Candidate: "I'm trying nested loops but it's O(n²)."
Interviewer: "Right. Think about what you're doing in the inner loop—
             you're searching for a specific value. Is there a data structure
             that makes searching faster than O(n)?"
```

**Level 2 (Reveal direction):**

```
Candidate: "Maybe... an array? I'm not sure."
Interviewer: "A hashmap gives you O(1) lookup. How could you use that here?
             What would you store as keys and values?"
```

**Level 3 (Maximum scaffolding):**

```
Candidate: "I'm lost. I don't know how to structure it."
Interviewer: "Let's work through it together. As you iterate through the array,
             you can store each number in a hashmap. The key is the number,
             and the value is its index. Then, for each number x, you can check
             if (target - x) exists in the hashmap. Does that make sense?
             Let's start implementing that."
```

### Algorithm 4: Response Quality Detection

**Location:** `interview_engine.py::_candidate_signals()` and `_is_response_thin()`

The system analyzes candidate responses for content richness:

```python
def _candidate_signals(self, text: str | None) -> dict[str, bool]:
    """
    Extract 8 content signals from candidate response:
    1. has_code - Contains code block or syntax
    2. mentions_complexity - Discusses time/space complexity
    3. mentions_edge_cases - Discusses boundary conditions
    4. mentions_constraints - Discusses input limits
    5. mentions_approach - Explains algorithm/strategy
    6. mentions_tradeoffs - Compares alternatives
    7. mentions_correctness - Proves why solution works
    8. mentions_tests - Mentions test cases
    """
    return {
        "has_code": self._has_code_block(text),
        "mentions_complexity": self._mentions_complexity(text),
        "mentions_edge_cases": self._mentions_edge_cases(text),
        "mentions_constraints": self._mentions_constraints(text),
        "mentions_approach": self._mentions_approach(text),
        "mentions_tradeoffs": self._mentions_tradeoffs(text),
        "mentions_correctness": self._mentions_correctness(text),
        "mentions_tests": self._mentions_tests(text),
    }

def _is_response_thin(
    self,
    text: str | None,
    signals: dict,
    is_behavioral: bool = False,
    is_conceptual: bool = False,
) -> bool:
    """
    Determine if response lacks substance:
    - Too short (< 8 tokens for conceptual)
    - No technical content for coding questions
    - Missing STAR components for behavioral
    - Has code but no explanation
    """
    if self._is_clarification_request(text):
        return False  # Clarifying questions are valid

    tokens = self._clean_tokens(text)
    if not tokens:
        return True

    # Conceptual questions need at least 8 words
    if is_conceptual:
        return len(tokens) < 8

    # Short responses with technical content are OK
    if len(tokens) >= 3:
        t_lower = (text or "").lower()
        technical_patterns = ["array", "hash", "map", "o(n)", "time", "space"]
        if any(pattern in t_lower for pattern in technical_patterns):
            return False

    # Behavioral needs STAR elements
    if is_behavioral:
        behavioral_missing = self._behavioral_missing_parts(text)
        return len(behavioral_missing) >= 3  # Missing 3+ STAR parts

    # Code without explanation is thin
    if signals.get("has_code") and not signals.get("mentions_approach"):
        return True

    # No substantial content signals
    content_signals = [
        "mentions_approach", "mentions_constraints", "mentions_correctness",
        "mentions_complexity", "mentions_edge_cases", "mentions_tradeoffs",
    ]
    return not any(signals.get(k) for k in content_signals)
```

**Detection Examples:**

````python
# Example 1: Thin response (will trigger clarification prompt)
response = "I would use a hashmap."
signals = {
    "has_code": False,
    "mentions_complexity": False,
    "mentions_edge_cases": False,
    "mentions_approach": False,  # ← No explanation!
}
is_thin = True
→ Interviewer: "Can you walk me through how that hashmap approach would work?"

# Example 2: Rich response (no prompt needed)
response = """
I would use a hashmap to store numbers we've seen and their indices.
The approach is to iterate through the array once (O(n) time).
For each number, I check if target - number exists in the hashmap.
If it does, we found our pair. If not, I add the current number to the hashmap.
The space complexity is O(n) in the worst case where no pair exists.
"""
signals = {
    "has_code": False,
    "mentions_complexity": True,   # ✓
    "mentions_approach": True,     # ✓
    "mentions_edge_cases": False,
}
is_thin = False
→ Interviewer proceeds with meaningful followup

# Example 3: Code without explanation (thin)
response = """
```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
````

"""
signals = {
"has_code": True,
"mentions_approach": False, # ← Didn't explain!
}
is_thin = True
→ Interviewer: "Good. Can you explain your approach and analyze the complexity?"

````

### Algorithm 5: Cross-Question Pattern Tracking

**Location:** `interview_engine_main.py::_update_session_patterns()` and `_session_patterns_summary()`

The system tracks behavioral patterns across all questions:

```python
def _update_session_patterns(
    self,
    db: Session,
    session: InterviewSession,
    signals: dict,
    q: Question,
    response_quality: str,  # "strong" | "weak" | "neutral"
) -> None:
    """
    Accumulate cross-question patterns in session.skill_state["patterns"]:

    {
        "n": 3,                      # Questions answered
        "complexity_count": 2,       # Mentioned complexity 2/3 times
        "approach_count": 3,         # Always explains approach
        "code_without_plan": 0,      # Never jumps to code
        "tradeoffs_count": 1,        # Mentioned tradeoffs 1/3 times
        "edge_cases_count": 0,       # Never mentioned edge cases
        "strong_types": ["coding"],  # Strong at coding questions
        "weak_types": ["system_design"]  # Weak at system design
    }
    """
    state = dict(session.skill_state or {})
    pat = dict(state.get("patterns", {}))

    # Increment question counter
    n = int(pat.get("n", 0)) + 1
    pat["n"] = n

    # Track signal patterns
    if signals.get("mentions_complexity"):
        pat["complexity_count"] = int(pat.get("complexity_count", 0)) + 1

    if signals.get("mentions_approach"):
        pat["approach_count"] = int(pat.get("approach_count", 0)) + 1

    # Detect anti-pattern: code without plan
    if signals.get("has_code") and not signals.get("mentions_approach"):
        pat["code_without_plan"] = int(pat.get("code_without_plan", 0)) + 1

    if signals.get("mentions_tradeoffs"):
        pat["tradeoffs_count"] = int(pat.get("tradeoffs_count", 0)) + 1

    if signals.get("mentions_edge_cases"):
        pat["edge_cases_count"] = int(pat.get("edge_cases_count", 0)) + 1

    # Track question type strengths/weaknesses
    qt = self._question_type(q)  # "coding", "system_design", etc.
    if response_quality == "strong":
        strong = list(pat.get("strong_types", []))
        if qt not in strong:
            strong.append(qt)
        pat["strong_types"] = strong
    elif response_quality == "weak":
        weak = list(pat.get("weak_types", []))
        if qt not in weak:
            weak.append(qt)
        pat["weak_types"] = weak

    # Save
    state["patterns"] = pat
    session.skill_state = state
    db.add(session)
    db.commit()

def _session_patterns_summary(self, session: InterviewSession) -> str | None:
    """
    Convert accumulated patterns to English summary for LLM context.

    Returns None if insufficient data (< 2 questions).
    """
    state = dict(session.skill_state or {})
    pat = dict(state.get("patterns", {}))
    n = int(pat.get("n", 0))

    if n < 2:
        return None  # Not enough data yet

    observations = []

    # Complexity analysis pattern
    cx = int(pat.get("complexity_count", 0))
    if cx == 0:
        observations.append(
            "⚠ Candidate has NOT mentioned complexity analysis across ANY question—recurring gap."
        )
    elif cx < (n + 1) // 2:
        observations.append(
            f"⚠ Candidate mentions complexity inconsistently ({cx}/{n} questions)."
        )
    else:
        observations.append(
            f"✓ Candidate consistently discusses complexity ({cx}/{n} questions)."
        )

    # Approach explanation pattern
    ap = int(pat.get("approach_count", 0))
    if ap < (n + 1) // 2:
        observations.append(
            f"⚠ Candidate tends to skip approach explanation ({ap}/{n} questions)."
        )

    # Code-first anti-pattern
    cwp = int(pat.get("code_without_plan", 0))
    if cwp >= 2:
        observations.append(
            f"⚠ Candidate has jumped straight to code without verbal plan {cwp} times—push for planning."
        )

    # Trade-offs discussion
    tr = int(pat.get("tradeoffs_count", 0))
    if tr == 0 and n >= 3:
        observations.append(
            "⚠ Candidate has NOT discussed trade-offs on any question—worth probing."
        )

    # Edge cases
    ec = int(pat.get("edge_cases_count", 0))
    if ec == 0 and n >= 3:
        observations.append(
            "⚠ Candidate has NOT mentioned edge cases this session—target this."
        )

    # Strong/weak types
    strong = list(pat.get("strong_types", []))
    weak = list(pat.get("weak_types", []))
    if strong:
        observations.append(f"✓ Strong on: {', '.join(strong)} questions.")
    if weak:
        observations.append(f"⚠ Weaker on: {', '.join(weak)} questions.")

    return " | ".join(observations) if observations else None
````

**Pattern Summary Example:**

After 4 questions answered:

```python
patterns = {
    "n": 4,
    "complexity_count": 1,        # Only 1/4 mentioned complexity
    "approach_count": 4,          # Always explains approach
    "code_without_plan": 0,
    "tradeoffs_count": 0,         # Never discussed tradeoffs
    "edge_cases_count": 1,
    "strong_types": ["coding"],
    "weak_types": ["system_design"]
}

summary = _session_patterns_summary(session)
# Returns:
"""
⚠ Candidate mentions complexity inconsistently (1/4 questions). |
✓ Candidate always explains approach (4/4 questions). |
⚠ Candidate has NOT discussed trade-offs on any question—worth probing. |
⚠ Candidate has NOT mentioned edge cases—target this. |
✓ Strong on: coding questions. |
⚠ Weaker on: system_design questions.
"""

# This summary is injected into the controller system prompt
# so the AI interviewer knows to:
# 1. Probe for complexity analysis
# 2. Push for trade-off discussions
# 3. Ask about edge cases
# 4. Be supportive on system design questions
```

---

## RAG System Deep Dive

### Embedding Pipeline

**Step 1: Session Completion** → `scoring_engine.py::finalize()`

```python
async def finalize(self, db: Session, session_id: int) -> dict:
    # ... evaluation logic ...

    # After storing evaluation, trigger embedding generation
    _trigger_embedding_generation(db, session_id)

    return evaluation

def _trigger_embedding_generation(db: Session, session_id: int) -> None:
    """Async trigger for embedding creation (non-blocking)."""
    try:
        from app.services.session_embedder import embed_completed_session
        result = embed_completed_session(db, session_id)
        logger.info(f"Embeddings created for session {session_id}: {result}")
    except Exception as e:
        logger.debug(f"Embedding generation skipped: {e}")
```

**Step 2: Extract Session Text** → `session_embedder.py::build_session_text()`

```python
def build_session_text(messages: list, include_system: bool = False) -> str:
    """
    Build embedding-optimized text from messages:

    Format:
        Interviewer: Hi! I'm Alex. Let's start with Two Sum...
        Candidate: I would use a hashmap to store...
        Interviewer: Good. What's the time complexity?
        Candidate: O(n) time because we iterate once...
        ...

    This format preserves:
    - Question-answer structure
    - Technical terminology
    - Candidate's thinking process
    """
    parts = []

    for msg in messages:
        role = msg.role
        content = msg.content

        if role == "system" and not include_system:
            continue

        if role == "interviewer":
            parts.append(f"Interviewer: {content}")
        elif role == "student":
            parts.append(f"Candidate: {content}")

    return "\n\n".join(parts)
```

**Step 3: Generate Embedding** → `embedding_service.py::generate_embedding()`

```python
def generate_embedding(text: str) -> list[float]:
    """
    Generate 384-dimensional embedding using sentence-transformers.

    Model: all-MiniLM-L6-v2
    - Fast (< 50ms on CPU)
    - Semantic similarity optimized
    - Max input: ~512 tokens

    Returns: list of 384 floats
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Truncate if too long
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        # Generate embedding
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        # Return zero vector as fallback
        return [0.0] * 384
```

**Step 4: Store in Database** → `session_embedder.py::embed_completed_session()`

```python
def embed_completed_session(db: Session, session_id: int) -> dict:
    """
    Complete embedding pipeline:
    1. Extract session transcript
    2. Generate embedding
    3. Store in session_embeddings table
    4. Extract high-quality responses (score ≥ 7)
    5. Create response_examples for RAG
    """
    session = get_session(db, session_id)
    messages = list_messages(db, session_id, limit=100)

    # Build text
    text = build_session_text(messages)
    if len(text) < 100:
        return {"error": "Insufficient content"}

    # Generate session-level embedding
    session_embedding = generate_embedding(text)

    # Store with metadata
    create_session_embedding(
        db=db,
        session_id=session_id,
        source_text=text,
        embedding=session_embedding,
        embedding_type="full_session",
        role=session.role,
        track=session.track,
        difficulty=session.difficulty,
    )

    # Extract high-quality responses for few-shot learning
    response_count = 0
    evaluation = get_evaluation(db, session_id)
    if evaluation and evaluation.overall_score >= 70:
        # Extract individual Q&A pairs where candidate scored ≥ 7
        asked_questions = get_asked_questions(db, session_id)
        for q in asked_questions:
            response_text = extract_candidate_response(messages, q.id)
            if response_text and len(response_text) >= 50:
                # Score this specific response
                response_score = estimate_response_quality(response_text, signals)
                if response_score >= 7:
                    response_embedding = generate_embedding(response_text)
                    create_response_example(
                        db=db,
                        session_id=session_id,
                        question_id=q.id,
                        response_text=response_text,
                        score=response_score,
                        embedding=response_embedding,
                    )
                    response_count += 1

    return {
        "session_embedded": True,
        "response_examples_created": response_count,
    }
```

### Similarity Search

**Cosine Similarity Query** (using pgvector):

```sql
-- Find sessions similar to query embedding
SELECT
    session_id,
    role,
    track,
    difficulty,
    overall_score,
    feedback_rating,
    1 - (embedding <=> %s::vector) AS similarity
FROM session_embeddings
WHERE track = %s
  AND difficulty = %s
  AND feedback_rating >= 4  -- Only high-rated sessions
ORDER BY embedding <=> %s::vector  -- Cosine distance
LIMIT 5;
```

**Python API** → `rag_service.py::get_rag_context_for_session()`

```python
def get_rag_context_for_session(
    db: Session,
    session_id: int,
    current_question: str | None = None,
) -> tuple[str, RAGContext | None]:
    """
    Main RAG entry point for interview engine.

    Returns:
        (context_string, metadata)

    Context string format:
        === Examples from highly-rated past interviews ===

        --- Example 1 (rated 5/5) ---
        Interviewer: Let's start with Two Sum...
        Candidate: I would use a hashmap...
        ...

        --- Example 2 (rated 5/5) ---
        ...
    """
    session = get_session(db, session_id)
    messages = list_messages(db, session_id, limit=50)

    # Build query from recent conversation
    recent_text = build_session_text(messages[-10:])
    if current_question:
        recent_text = f"{current_question}\n\n{recent_text}"

    # Retrieve similar sessions
    context = retrieve_session_context(
        db=db,
        query_text=recent_text,
        role=session.role,
        track=session.track,
        min_rating=4,
        top_k=3,
        exclude_session_ids=[session_id],
    )

    # Format for prompt injection
    context_string = build_rag_prompt_context(
        session_examples=context.session_examples,
        max_examples=2,
    )

    return context_string, context
```

### RAG Context Injection

**During Interview** → `interview_engine_main.py::handle_student_message()`

```python
async def handle_student_message(
    self,
    db: Session,
    session: InterviewSession,
    content: str,
    user_name: str | None = None,
) -> None:
    # ... store message, analyze response ...

    # Get RAG context
    rag_context = _get_rag_context_for_interview(db, session.id)

    # Build controller prompt with RAG context
    ctrl_sys = interviewer_controller_system_prompt(
        company_style=session.company_style,
        role=session.role,
        interviewer_name=self._interviewer_name(session),
        interviewer_id=self._interviewer_id(session),
        rag_context=rag_context,  # ← RAG injection!
        session_patterns=patterns_summary,
        hint_level=hint_level,
    )

    # Call LLM with enriched context
    ai_response = await self.llm.chat(ctrl_sys, ctrl_user, history=history)
```

**During Evaluation** → `scoring_engine.py::finalize()`

```python
async def finalize(self, db: Session, session_id: int) -> dict:
    # ... build transcript ...

    # Get RAG context (similar sessions)
    rag_context = _get_rag_context_safe(db, session_id)

    # Build evaluation prompt with RAG context
    sys = evaluator_system_prompt(
        rag_context=rag_context,  # ← RAG injection!
        difficulty=difficulty,
        difficulty_current=difficulty_current,
        adaptive=adaptive,
    )

    user = evaluator_user_prompt(transcript, rubric_context, difficulty, adaptive)

    # Call LLM with enriched context
    evaluation = await self.llm.chat_json(sys, user)
```

**RAG Context Example:**

Query: "Implement Two Sum with O(n) time"

Retrieved similar sessions:

```
Session #42 (similarity: 0.89, rating: 5/5):
  Interviewer: Let's start with Two Sum. Given an array and target...
  Candidate: I would use a hashmap to store numbers we've seen.
             As I iterate, I check if target - current exists in the hashmap.
             This gives us O(n) time and O(n) space.
  Interviewer: Good. What about edge cases?
  Candidate: We should handle empty arrays, single elements, and duplicates...

Session #78 (similarity: 0.82, rating: 4/5):
  Interviewer: Tell me your approach for Two Sum.
  Candidate: Start with hashmap approach for O(n). Store number → index mapping.
             For each num, check if (target - num) exists...
```

This context is injected into prompts so the AI can:

- See examples of high-quality answers
- Learn what constitutes thorough explanations
- Understand common patterns (e.g., "hashmap for O(1) lookup")
- Calibrate scoring expectations

---

## Prompt Engineering Details

### Controller System Prompt (Intelligence Upgrade)

**Location:** `prompt_templates.py::interviewer_controller_system_prompt()`

```python
def interviewer_controller_system_prompt(
    company_style: str,
    role: str,
    interviewer_name: str | None = None,
    interviewer_id: str | None = None,
    rag_context: str | None = None,
    session_patterns: str | None = None,
    hint_level: int = 0,
) -> str:
    """
    Build controller system prompt with full context:

    Components:
    1. Role and company style
    2. Interviewer personality
    3. RAG context (similar sessions)
    4. Session patterns (cross-question behaviors)
    5. Hint level (scaffolding guidance)
    6. General guidelines
    """

    name_line = f"You are {interviewer_name}, conducting an interview." if interviewer_name else "You are a senior engineer conducting an interview."

    personality_block = _interviewer_personality_block(interviewer_id)
    style_guide = _company_style_guide(company_style)
    focus_checklist = _company_focus_checklist(company_style)

    # Build comprehensive system prompt
    parts = [
        f"{name_line} You are running a {company_style} interview for a {role} role.",
        f"Company style: {style_guide}",
        f"Focus priorities: {focus_checklist}",
    ]

    if personality_block:
        parts.append(personality_block)

    # RAG context injection
    if rag_context:
        parts.append("\n[CONTEXT FROM SIMILAR SESSIONS]")
        parts.append(rag_context)
        parts.append("\nUse these examples to calibrate your expectations and responses.")

    # Cross-question patterns
    if session_patterns:
        parts.append("\n[CROSS-QUESTION PATTERNS OBSERVED THIS SESSION]")
        parts.append(session_patterns)
        parts.append("\nAdjust your follow-ups based on these recurring patterns.")

    # Hint level guidance
    if hint_level > 0:
        hint_guidance = _get_hint_guidance(hint_level)
        parts.append(f"\n[HINT LEVEL: {hint_level}]")
        parts.append(hint_guidance)

    # General guidelines
    parts.append("""
General personality — sound like a real human senior engineer:
- React naturally to what the candidate just said. Brief genuine reactions are good.
- Vary your language — don't repeat phrases or start every response the same way.
- Think out loud when appropriate: "So if I'm reading this right..." or "Walk me through that again."

Technical rules:
- Ask ONE thing at a time and be concise (under 120 words).
- Do NOT reveal full solutions.
- Guide progression: plan → solve → optimize → validate.
- After a solution, ask 1-2 short follow-ups (max 2 per question).
- Adapt depth: clarify when weak, push optimization when strong.

Formatting:
- Do NOT use markdown, labels like "Title:", or code fences.
- Do NOT reference other sessions or prior interviews.
- Keep responses natural and conversational.
""")

    return "\n\n".join(parts).strip()

def _get_hint_guidance(hint_level: int) -> str:
    """Return hint-level specific guidance for the controller."""
    if hint_level == 1:
        return """
The candidate is struggling slightly. Provide an INDIRECT NUDGE:
- Reframe the problem from a different angle
- Ask a guiding question that points toward the solution
- Example: "Think about what happens when you need fast lookups."
Do NOT reveal the specific data structure or algorithm yet.
"""
    elif hint_level == 2:
        return """
The candidate is still struggling. REVEAL DIRECTION:
- Point to a specific data structure or concept
- Example: "A hashmap gives you O(1) lookups. How could that help?"
- Provide framework without giving full solution
"""
    elif hint_level >= 3:
        return """
The candidate needs MAXIMUM SCAFFOLDING:
- Walk through the solution together
- Ask step-by-step leading questions
- Example: "Let's use a hashmap. What would you store as keys? And values?"
- Keep candidate engaged while guiding strongly
"""
    else:
        return ""
```

**Example Full Controller Prompt:**

```
You are Alex Rivera, conducting an interview. You are running a Google SWE Intern interview for a SWE Intern role.

Company style: Tone: precise, rigorous, engineering-focused. Focus: correctness, invariants, complexity, and edge cases. Ask for clear justification.

Focus priorities: Follow-up priorities: correctness, invariants, complexity, and edge cases.

Your interviewer style: calm and easygoing.
You are relaxed and patient — your default mode is encouraging, never intimidating. Use light humor when it feels natural. If someone struggles, offer a gentle nudge without spoiling it. Celebrate good thinking briefly: 'Nice, that's clean.' / 'Yeah, I like that.' / 'Good instinct.' You never rush anyone.

[CONTEXT FROM SIMILAR SESSIONS]
=== Examples from highly-rated past interviews ===

--- Example 1 (rated 5/5) ---
Interviewer: Let's start with Two Sum. Given an array of integers and a target...
Candidate: I would use a hashmap to store numbers we've seen and their indices. As I iterate through the array, for each number I check if target minus that number exists in the hashmap. If it does, I've found my pair. If not, I add the current number to the hashmap. This gives us O(n) time complexity because we iterate once, and O(n) space complexity for the hashmap.
Interviewer: Good. What about edge cases?
Candidate: We should handle empty arrays, arrays with fewer than 2 elements, and cases where no valid pair exists. Also need to ensure we don't use the same element twice...

Use these examples to calibrate your expectations and responses.

[CROSS-QUESTION PATTERNS OBSERVED THIS SESSION]
⚠ Candidate mentions complexity inconsistently (1/3 questions). | ✓ Candidate always explains approach (3/3 questions). | ⚠ Candidate has NOT discussed trade-offs on any question—worth probing. | ✓ Strong on: coding questions.

Adjust your follow-ups based on these recurring patterns.

[HINT LEVEL: 1]
The candidate is struggling slightly. Provide an INDIRECT NUDGE:
- Reframe the problem from a different angle
- Ask a guiding question that points toward the solution
- Example: "Think about what happens when you need fast lookups."
Do NOT reveal the specific data structure or algorithm yet.

General personality — sound like a real human senior engineer:
- React naturally to what the candidate just said. Brief genuine reactions are good.
- Vary your language — don't repeat phrases or start every response the same way.
- Think out loud when appropriate: "So if I'm reading this right..." or "Walk me through that again."

Technical rules:
- Ask ONE thing at a time and be concise (under 120 words).
- Do NOT reveal full solutions.
- Guide progression: plan → solve → optimize → validate.
- After a solution, ask 1-2 short follow-ups (max 2 per question).
- Adapt depth: clarify when weak, push optimization when strong.

Formatting:
- Do NOT use markdown, labels like "Title:", or code fences.
- Do NOT reference other sessions or prior interviews.
- Keep responses natural and conversational.
```

---

## Conclusion

Interview Prep AI is a production-ready, intelligent interview platform that combines:

✅ **Robust Backend** - FastAPI + PostgreSQL + SQLAlchemy  
✅ **Smart AI** - Adaptive difficulty, progressive hints, memory  
✅ **RAG Learning** - Continuous improvement without retraining  
✅ **Quality Dataset** - 1,757 curated questions, properly classified  
✅ **Realistic Flow** - Warmup, questions, followups, scoring  
✅ **Comprehensive Evaluation** - 5-dimension rubric + narrative feedback  
✅ **Modern Frontend** - Next.js 16 + React 19 + TypeScript  
✅ **Scalable Architecture** - Modular services, database-backed

The system is **end-to-end functional** with sophisticated intelligence features that rival commercial platforms like Pramp, interviewing.io, and LeetCode Mock Interviews.

**Architecture highlights:**

- Modular service layer (InterviewEngine, ScoringEngine, RAG)
- Rich state tracking (JSON columns for flexibility)
- Progressive enhancement (works even if LLM offline)
- Continuous learning (RAG system improves over time)

**Production ready:**

- Error handling and fallbacks throughout
- Comprehensive test coverage
- Security best practices (JWT, bcrypt, CORS)
- Performance optimization (indexing, pooling, caching)
- Clear documentation and code organization

This is a **professional-grade system** that demonstrates advanced software engineering:

- Clean separation of concerns
- Intelligent algorithms (adaptive difficulty, pattern tracking)
- Machine learning integration (embeddings, RAG)
- Real-time state management
- Scalable data models

**Key Innovations:**

1. **Multi-dimensional question selection** - Balances diversity, weakness-targeting, and rubric alignment
2. **Progressive hint system** - 4-level escalation mimics human interviewer intuition
3. **Cross-question pattern tracking** - Remembers behavioral patterns across entire session
4. **RAG-enhanced scoring** - Learns from past sessions without model retraining
5. **Personality-driven interviewing** - 4 distinct interviewer styles with company-specific guidelines
