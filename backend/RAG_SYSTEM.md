# RAG + Feedback Learning System

## Overview

This system makes the interview AI smarter by learning from past sessions **without retraining the model**. It uses:

1. **User Feedback** - Collect thumbs up/down, star ratings, and detailed rubric feedback
2. **Session Embeddings** - Convert sessions and responses into vector representations  
3. **RAG (Retrieval-Augmented Generation)** - Inject relevant past examples into prompts

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   User Rates    │ ───► │    Feedback     │ ───► │   Embeddings    │
│   Interview     │      │   Stored in DB  │      │   Generated     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   New Session   │ ◄─── │   RAG Context   │ ◄─── │  Similar Finds  │
│   Gets Smarter  │      │   Injected      │      │  (Cosine Sim)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Components

### Database Tables

| Table | Purpose |
|-------|---------|
| `session_feedback` | User ratings (1-5 stars, thumbs, comments, detailed rubric) |
| `session_embeddings` | 384-dim vectors for session transcripts |
| `question_embeddings` | 384-dim vectors for question prompts |
| `response_examples` | High-quality response snippets for RAG |

### Services

| File | Purpose |
|------|---------|
| `app/services/embedding_service.py` | Generate embeddings (sentence-transformers or fallback) |
| `app/services/session_embedder.py` | Extract and embed session data after completion |
| `app/services/rag_service.py` | Retrieve similar sessions and build context |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/feedback` | POST | Submit session feedback |
| `/api/v1/feedback/session/{id}` | GET | Get feedback for a session |
| `/api/v1/feedback/me` | GET | Get current user's feedback |
| `/api/v1/feedback/stats` | GET | Aggregated feedback stats |
| `/api/v1/embeddings/stats` | GET | Embedding counts |
| `/api/v1/embeddings/rag/status` | GET | Check if RAG is ready |
| `/api/v1/embeddings/rag/test` | POST | Test RAG retrieval |
| `/api/v1/embeddings/questions/embed-all` | POST | Embed all questions |
| `/api/v1/embeddings/sessions/{id}/embed` | POST | Embed single session |

## How It Works

### 1. Feedback Collection (Frontend)
After an interview, users see a feedback card on the results page:
- **Quick feedback**: Thumbs up/down + star rating
- **Detailed feedback**: Per-rubric ratings (communication, problem solving, etc.)
- Stored in `session_feedback` table

### 2. Embedding Generation (Automatic)
When a session is finalized via `ScoringEngine.finalize()`:
1. The evaluation is computed
2. `_trigger_embedding_generation()` calls `session_embedder.embed_completed_session()`
3. Session transcript is embedded and stored
4. High-quality responses (score >= 7) are saved as `ResponseExample`

### 3. RAG Context Injection
During interviews and evaluations:

**Live Interview** (`interview_engine.py`):
```python
rag_context = _get_rag_context_for_interview(db, session.id)
ctrl_sys = interviewer_controller_system_prompt(..., rag_context=rag_context)
```

**Final Evaluation** (`scoring_engine.py`):
```python
rag_context = _get_rag_context_safe(db, session_id)
sys = evaluator_system_prompt(rag_context=rag_context)
```

### 4. What Gets Injected

The RAG context includes:
- Similar session patterns (score ranges, strengths/weaknesses)
- Example responses for similar questions
- Feedback patterns (what users rated highly)

Example injected context:
```
CONTEXT FROM SIMILAR SESSIONS:
Session patterns (similar interviews):
- Average score range: 75-85
- Common strengths: Clear communication, Good approach explanation
- Common weaknesses: Missing edge cases, Incomplete complexity analysis

Example responses for similar questions:
Q: "Two Sum" - Strong response pattern:
"I'd use a hash map to store complements..."
```

## Configuration

### Embedding Model
Uses `sentence-transformers/all-MiniLM-L6-v2`:
- 384 dimensions
- Fast and runs locally
- Free (no API costs)

### Fallback Mode
If sentence-transformers isn't available:
- Uses deterministic hash-based pseudo-embeddings
- Still works for similarity (less accurate)
- Set `EMBEDDING_FALLBACK=1` env var

### Minimum Data for RAG
RAG only activates when:
- At least 3 similar sessions exist
- At least 1 response example exists
- Check via `/api/v1/embeddings/rag/status`

## Usage

### Bootstrap the System

1. **Run migration** (already done if you're reading this):
   ```bash
   alembic upgrade head
   ```

2. **Embed existing questions**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/embeddings/questions/embed-all \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Complete some interviews** - Embeddings are auto-generated on finalize

4. **Check RAG status**:
   ```bash
   curl http://localhost:8000/api/v1/embeddings/rag/status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### Testing RAG

```bash
curl -X POST http://localhost:8000/api/v1/embeddings/rag/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1}'
```

## Future Improvements

- [ ] Use pgvector extension for faster similarity search
- [ ] Add question-level feedback (per-question ratings)
- [ ] Implement feedback-weighted example selection
- [ ] Add A/B testing to measure RAG impact
- [ ] Periodic retraining triggers based on accumulated feedback

## Files Created

```
backend/
├── app/
│   ├── models/
│   │   ├── session_feedback.py
│   │   └── session_embedding.py
│   ├── schemas/
│   │   └── feedback.py
│   ├── crud/
│   │   ├── feedback.py
│   │   └── embedding.py
│   ├── services/
│   │   ├── embedding_service.py
│   │   ├── session_embedder.py
│   │   └── rag_service.py
│   └── api/v1/
│       ├── feedback.py
│       └── embeddings.py
├── alembic/versions/
│   └── a8c3e5f7b9d1_add_rag_and_feedback_tables.py
└── RAG_SYSTEM.md (this file)

frontend/
├── assets/
│   ├── css/
│   │   └── feedback.css
│   └── js/
│       └── feedback.js
└── results.html (updated)
```
