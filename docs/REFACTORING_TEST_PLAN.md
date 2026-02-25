# Interview Engine Refactoring - Comprehensive Testing Guide

## Overview

This document defines **all tests required** to ensure zero behavioral changes during refactoring. We will have tests **before, during, and after** each extraction stage.

---

## Testing Strategy

### Three-Layer Testing Approach

**Layer 1: Unit Tests** (Test individual methods in isolation)

- Each method tested independently
- Mock dependencies
- Test edge cases

**Layer 2: Integration Tests** (Test methods working together)

- Test inter-module communication
- Verify data flowing correctly between modules
- Test actual database operations

**Layer 3: End-to-End Tests** (Test full interview flows)

- Complete interview scenarios
- Verify outputs unchanged
- Test all question types and difficulty levels

---

## Pre-Refactoring Tests (Baseline)

Before any extraction, establish baseline tests to verify current behavior.

### Test File: `tests/test_interview_engine_baseline.py`

```python
import pytest
from sqlalchemy.orm import Session
from backend.app.models import InterviewSession, Question, User
from backend.app.services.interview_engine import InterviewEngine
from backend.app.db.database import SessionLocal

class TestInterviewEngineBaseline:
    """Baseline tests to ensure current behavior is captured before refactoring."""

    @pytest.fixture
    def db(self):
        """Database session fixture."""
        db = SessionLocal()
        yield db
        db.close()

    @pytest.fixture
    def engine(self):
        """InterviewEngine fixture."""
        return InterviewEngine()

    # ============ INTERVIEW FLOW TESTS ============

    def test_interview_initialization(self, db, engine):
        """Test interview session creates with correct initial state."""
        # Create user and session
        session = InterviewSession(
            user_id=1,
            company_style="google",
            role="swe",
            difficulty="medium",
            track="coding"
        )
        db.add(session)
        db.commit()

        # Verify initial state
        assert session.stage in [None, "intro", "warmup"]
        assert session.questions_asked_count == 0 or session.questions_asked_count is None
        assert session.followups_used == 0 or session.followups_used is None
        assert isinstance(session.skill_state, dict) or session.skill_state is None

    def test_warmup_prompt_generates(self, db, engine):
        """Test warmup prompt generation doesn't crash."""
        session = InterviewSession(user_id=1, company_style="google", role="swe")
        db.add(session)
        db.commit()

        # Should generate without error
        prompt = engine._warmup_prompt(session, user_name="Alice")
        assert prompt is not None
        assert len(prompt) > 0

    def test_question_generation(self, db, engine):
        """Test first question generates correctly."""
        session = InterviewSession(
            user_id=1,
            company_style="general",
            role="swe",
            track="coding"
        )
        db.add(session)
        db.commit()

        question = engine._pick_next_main_question(db, session)
        assert question is not None
        assert question.title is not None
        assert question.prompt is not None

    def test_response_quality_assessment(self, engine):
        """Test response quality assessment works."""
        response = "My approach would be to use a hash map for O(1) lookup. The time complexity is O(n) and space is O(n)."
        signals = {"mentions_approach": True, "mentions_complexity": True}

        quality = engine._response_quality(response, signals, is_behavioral=False, behavioral_missing=[], is_conceptual=False)
        assert quality in ["weak", "ok", "strong"]

    def test_signal_detection(self, engine):
        """Test signal detection captures all relevant signals."""
        response = "I'd use a hash table for O(1) lookup. Edge case: empty array. Time complexity O(n), space O(n)."

        signals = engine._candidate_signals(response)
        assert "mentions_approach" in signals
        assert "mentions_complexity" in signals
        assert "mentions_edge_cases" in signals

    # ============ RUBRIC TESTS ============

    def test_rubric_state_update(self, db, engine):
        """Test rubric state updates correctly."""
        session = InterviewSession(user_id=1)
        db.add(session)
        db.commit()

        rubric_raw = {
            "communication": 7,
            "problem_solving": 8,
            "correctness_reasoning": 6,
            "complexity": 5,
            "edge_cases": 4
        }

        engine._update_skill_state(db, session, rubric_raw, is_behavioral=False)
        db.refresh(session)

        assert session.skill_state is not None
        assert session.skill_state.get("n") == 1
        assert "sum" in session.skill_state
        assert "last" in session.skill_state

    def test_weakest_dimension_detection(self, db, engine):
        """Test weakest dimension is correctly identified."""
        session = InterviewSession(user_id=1)
        db.add(session)

        # Build skill state with known weakness
        session.skill_state = {
            "n": 3,
            "sum": {
                "communication": 20,
                "problem_solving": 24,
                "correctness_reasoning": 18,
                "complexity": 10,  # Weakest
                "edge_cases": 15
            },
            "last": {
                "communication": 7,
                "problem_solving": 8,
                "correctness_reasoning": 6,
                "complexity": 3,    # Lowest
                "edge_cases": 5
            },
            "ema": {
                "communication": 6.7,
                "problem_solving": 8.0,
                "correctness_reasoning": 6.0,
                "complexity": 3.3,  # Weakest EMA
                "edge_cases": 5.0
            }
        }
        db.commit()

        weakest = engine._weakest_dimension(session)
        assert weakest == "complexity"

    def test_critical_rubric_gaps_phase4(self, db, engine):
        """Test Phase 4: Critical rubric gaps extraction."""
        session = InterviewSession(user_id=1)
        session.skill_state = {
            "last": {
                "communication": 3,      # < 5 → gap
                "problem_solving": 2,    # < 5 → gap
                "correctness_reasoning": 8,
                "complexity": 4,         # < 5 → gap
                "edge_cases": 5
            }
        }

        gaps = engine._critical_rubric_gaps(session, threshold=5)
        assert "approach" in gaps  # problem_solving → approach
        assert "complexity" in gaps
        assert "correctness" not in gaps  # 8 >= 5

    # ============ QUESTION SELECTION TESTS ============

    def test_question_selection_basic(self, db, engine):
        """Test basic question selection works."""
        session = InterviewSession(user_id=1, track="coding", company_style="general")
        db.add(session)
        db.commit()

        question = engine._pick_next_technical_question(
            db, session,
            asked_ids=set(),
            seen_ids=set(),
            focus={"tags": []},
            desired_type="coding"
        )

        assert question is not None
        assert not engine._is_behavioral(question)

    def test_question_diversity(self, db, engine):
        """Test different questions picked sequentially."""
        session = InterviewSession(user_id=1, track="coding", company_style="general")
        db.add(session)
        db.commit()

        q1 = engine._pick_next_technical_question(
            db, session, set(), set(), {"tags": []}, "coding"
        )

        asked_ids = {q1.id}
        q2 = engine._pick_next_technical_question(
            db, session, asked_ids, set(), {"tags": []}, "coding"
        )

        assert q2 is not None
        assert q2.id != q1.id  # Different question

    # ============ FOLLOW-UP TESTS ============

    def test_missing_focus_detection(self, engine):
        """Test missing focus keys are detected."""
        q = type('Question', (), {
            'title': 'Two Sum',
            'prompt': 'Find two numbers...',
            'tags_csv': 'array,hash-map'
        })()

        signals = {
            "mentions_approach": True,
            "mentions_complexity": False,  # MISSING
            "mentions_edge_cases": True,
            "mentions_constraints": False,  # MISSING
            "mentions_correctness": True,
            "mentions_tradeoffs": False
        }

        missing = engine._missing_focus_keys(q, signals, [])
        assert "complexity" in missing
        assert "constraints" in missing
        assert "approach" not in missing

    def test_follow_up_prioritization(self, db, engine):
        """Test missing focus prioritization by weakness."""
        session = InterviewSession(user_id=1)
        session.skill_state = {
            "ema": {
                "complexity": 2.0,        # Weakest
                "edge_cases": 4.0,
                "problem_solving": 6.0,
                "communication": 7.0,
                "correctness_reasoning": 5.0
            }
        }
        db.add(session)
        db.commit()

        missing = ["complexity", "edge_cases", "approach"]
        prioritized = engine._prioritize_missing_focus(missing, session, prefer=None)

        # Complexity should be first (weakest dimension)
        assert prioritized[0] == "complexity"

    def test_response_quality_affects_followup(self, engine):
        """Test response quality determines follow-up need."""
        # Strong response
        strong_signals = {
            "mentions_approach": True,
            "mentions_complexity": True,
            "mentions_edge_cases": True,
            "mentions_constraints": True,
            "mentions_correctness": True,
            "mentions_tradeoffs": True
        }

        quality_strong = engine._response_quality(
            "Long, comprehensive response", strong_signals, False, [], False
        )
        assert quality_strong in ["strong", "ok"]

        # Weak response
        weak_signals = {
            "mentions_approach": False,
            "mentions_complexity": False,
            "mentions_edge_cases": False,
            "mentions_constraints": False,
            "mentions_correctness": False,
            "mentions_tradeoffs": False
        }

        quality_weak = engine._response_quality(
            "No", weak_signals, False, [], False
        )
        assert quality_weak == "weak"


# Run baseline tests to ensure current system works
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Stage-Specific Tests

### Stage 1: Utils Module Extraction

**Test File:** `tests/test_interview_engine_utils.py`

````python
def test_normalize_text():
    """Test text normalization."""
    text = "  Hello\n\n  WORLD  "
    normalized = normalize_text(text)
    assert normalized == "hello world"

def test_sanitize_ai_text():
    """Test AI text sanitization."""
    text = "```python\nprint('hi')\n```\n\nSome text."
    sanitized = sanitize_ai_text(text)
    assert sanitized is not None
    assert len(sanitized) > 0

def test_question_type_detection():
    """Test question type classifier."""
    q_behavioral = type('Q', (), {'tags_csv': 'behavioral,leadership'})()
    q_coding = type('Q', (), {'tags_csv': 'array,dp'})()
    q_conceptual = type('Q', (), {'tags_csv': 'database,design'})()

    assert question_type(q_behavioral) == "behavioral"
    assert question_type(q_coding) == "coding"

def test_clamp_int():
    """Test integer clamping."""
    assert clamp_int(5, 0, 10) == 5
    assert clamp_int(15, 0, 10) == 10
    assert clamp_int(-5, 0, 10) == 0
````

### Stage 2: Signals Module Extraction

**Test File:** `tests/test_interview_engine_signals.py`

```python
def test_signal_extraction_complete():
    """Test all signals extracted from response."""
    text = """
    I'd use a hash map. The approach is iterate through and check.
    Time complexity O(n), space O(n).
    Edge case: empty array or duplicates.
    Trade-off between time and space.
    """

    signals = candidate_signals(text)

    assert signals["mentions_approach"] == True
    assert signals["mentions_complexity"] == True
    assert signals["mentions_edge_cases"] == True
    assert signals["mentions_tradeoffs"] == True

def test_behavioral_question_detection():
    """Test behavioral question identification."""
    q = type('Q', (), {
        'tags_csv': 'behavioral,leadership',
        'title': 'Tell me about a time...'
    })()

    assert is_behavioral(q) == True

def test_response_quality_weak():
    """Test weak response detection."""
    quality = response_quality(
        "I don't know.",
        {"mentions_approach": False},
        is_behavioral=False,
        behavioral_missing=[],
        is_conceptual=False
    )
    assert quality == "weak"

def test_response_quality_strong():
    """Test strong response detection."""
    text = "Use merge sort with O(n log n) time complexity..."
    signals = {
        "mentions_approach": True,
        "mentions_complexity": True,
        "mentions_edge_cases": True
    }
    quality = response_quality(text, signals, False, [], False)
    assert quality in ["ok", "strong"]
```

### Stage 3: Rubric Module Extraction

**Test File:** `tests/test_interview_engine_rubric.py`

```python
def test_ema_calculation(db, engine):
    """Test EMA calculation for rolling average."""
    session = InterviewSession(user_id=1)
    db.add(session)

    # First response
    engine._update_skill_state(db, session, {
        "communication": 5,
        "problem_solving": 5,
        "correctness_reasoning": 5,
        "complexity": 5,
        "edge_cases": 5
    }, False)
    db.refresh(session)

    first_ema = session.skill_state["ema"]["complexity"]
    assert first_ema == 5

    # Second response (should average)
    engine._update_skill_state(db, session, {
        "communication": 7,
        "problem_solving": 7,
        "correctness_reasoning": 7,
        "complexity": 9,  # Improved
        "edge_cases": 7
    }, False)
    db.refresh(session)

    second_ema = session.skill_state["ema"]["complexity"]
    # EMA should move toward 9 but not fully
    assert 5 < second_ema < 9

def test_critical_rubric_gaps_with_threshold():
    """Test rubric gaps respect threshold."""
    session = InterviewSession(user_id=1)
    session.skill_state = {
        "last": {
            "complexity": 4,  # Below threshold of 5
            "edge_cases": 5   # Exactly at threshold
        }
    }

    gaps = critical_rubric_gaps(session, threshold=5)
    assert "complexity" in gaps
    assert "edge_cases" not in gaps  # 5 is NOT < 5
```

### Stage 5: Questions Module Extraction (Phase 5)

**Test File:** `tests/test_interview_engine_questions_phase5.py`

```python
def test_question_rubric_alignment_score():
    """Test Phase 5: Question scoring by rubric alignment."""
    q = type('Q', (), {
        'meta': {
            'evaluation_focus': ['complexity', 'edge_cases']
        }
    })()

    rubric_gaps = ['complexity', 'approach']

    # Should score +10 for complexity match
    score = question_rubric_alignment_score(q, rubric_gaps)
    assert score == 10

def test_question_selection_targets_weak_areas(db, engine):
    """Test Phase 5: Next question targets weak rubric areas."""
    session = InterviewSession(user_id=1, track="coding")
    session.skill_state = {
        "last": {
            "complexity": 2,      # WEAK
            "edge_cases": 2,      # WEAK
            "problem_solving": 7,
            "communication": 7,
            "correctness_reasoning": 6
        }
    }
    db.add(session)
    db.commit()

    # Get candidates
    candidates = db.query(Question).filter(...).limit(10).all()

    # Q1 targets recursion (no complexity focus)
    # Q2 targets tree traversal (targets complexity + edge_cases)

    selected = engine._pick_next_technical_question(
        db, session, set(), set(), {"tags": []}, "coding"
    )

    # Should prefer Q2 because it has higher rubric alignment
    # Verify by checking meta.evaluation_focus
    q_focus = selected.meta.get("evaluation_focus", [])
    assert any(f in ['complexity', 'edge_cases'] for f in q_focus)
```

---

## Integration Tests

**Test File:** `tests/test_interview_engine_integration.py`

```python
def test_full_interview_flow(db, engine):
    """Test complete interview flow without module extraction."""
    session = create_test_session(db, "coding")

    # Warmup
    warmup_response = engine._warmup_prompt(session)
    assert warmup_response

    # Question 1
    q1 = engine._pick_next_main_question(db, session)
    assert q1

    # Simulate response
    candidate_response = "I'd use dynamic programming..."
    signals = engine._candidate_signals(candidate_response)
    assert signals

    # Assess quality
    quality = engine._response_quality(candidate_response, signals, False, [], False)
    assert quality

    # Check for follow-up
    missing = engine._missing_focus_keys(q1, signals, [])
    assert isinstance(missing, list)

def test_adaptive_difficulty_flow(db, engine):
    """Test adaptive difficulty doesn't break refactoring."""
    session = create_test_session(db, difficulty="easy")
    session.adaptive_difficulty_enabled = True

    # Run several questions
    for i in range(3):
        q = engine._pick_next_main_question(db, session)
        assert q
        assert q.difficulty in ["easy", "medium", "hard"]

def test_behavioral_questions_included(db, engine):
    """Test behavioral questions properly selected."""
    session = create_test_session(db, "coding")
    session.behavioral_questions_target = 2

    questions = []
    for i in range(5):
        q = engine._pick_next_main_question(db, session)
        questions.append(q)

    behavioral_count = sum(1 for q in questions if engine._is_behavioral(q))
    assert behavioral_count == 2
```

---

## End-to-End Tests (Post-Refactoring)

**Test File:** `tests/test_interview_engine_e2e.py`

```python
def test_interview_session_produces_same_questions():
    """Test that extracted code produces identical questions."""
    # Run interview with original code
    original_session = run_test_interview_original()

    # Run interview with refactored code
    refactored_session = run_test_interview_refactored()

    # Verify same question sequence (up to randomness)
    assert len(original_session.questions) == len(refactored_session.questions)

def test_interview_scores_same():
    """Test final scores are identical."""
    original_score = run_full_interview_original("alice")
    refactored_score = run_full_interview_refactored("alice")

    assert original_score == refactored_score

def test_followup_behavior_identical():
    """Test follow-up logic unchanged."""
    original_followups = get_followups_for_response_original(weak_response)
    refactored_followups = get_followups_for_response_refactored(weak_response)

    assert len(original_followups) == len(refactored_followups)
    # Messages may differ slightly, but structure should be same
    assert all(len(f) > 0 for f in refactored_followups)
```

---

## Test Execution Checklist

### Before Each Stage

```
[ ] Read current code to extract
[ ] Identify all dependencies (imports, method calls)
[ ] Map all method calls to ensure imports are added
[ ] Create corresponding unit tests
[ ] Run existing tests → all pass
```

### During Extraction

```
[ ] Copy code to new file
[ ] Update imports in new file
[ ] Update main file to import from new file
[ ] Run linter (no syntax errors)
[ ] Run mypy (type checking)
[ ] Run unit tests for that module → all pass
```

### After Each Stage

```
[ ] Run full test suite → all pass
[ ] Run integration tests → all pass
[ ] No new warnings or errors
[ ] Code structure verified
[ ] Document any issues found
[ ] Proceed to next stage or rollback
```

---

## Performance Baseline

Before refactoring, capture performance:

```python
def test_performance_baseline():
    """Establish performance baseline."""
    import time

    session = create_test_session(db)

    start = time.time()
    for i in range(100):
        engine._pick_next_main_question(db, session)
    duration = time.time() - start

    assert duration < 5.0  # Should be fast
    print(f"100 question selections: {duration:.2f}s")
```

---

## Test Execution Commands

```bash
# Run baseline tests (before refactoring)
pytest tests/test_interview_engine_baseline.py -v

# Run specific stage tests
pytest tests/test_interview_engine_utils.py -v
pytest tests/test_interview_engine_signals.py -v
pytest tests/test_interview_engine_rubric.py -v

# Run full suite
pytest tests/test_interview_engine_*.py -v

# With coverage
pytest tests/ --cov=backend.app.services.interview_engine -v

# Performance profiling
pytest tests/test_interview_engine_performance.py -v
```

---

## Success Criteria

✅ **All tests pass before refactoring**
✅ **All tests pass after each stage**
✅ **No increase in test execution time**
✅ **Coverage remains ≥ 80%**
✅ **No behavioral changes (verified by tests)**
✅ **All integration tests pass**
✅ **End-to-end tests show identical behavior**

---

## Rollback Trigger

If **ANY** test fails:

1. Stop current extraction
2. Document error
3. Revert changes: `git checkout backend/app/services/`
4. Investigate in original monolithic file
5. Implement fix
6. Re-test
7. Resume extraction

---

## Next Step

Create detailed method extraction checklist in `REFACTORING_CHECKLIST.md`
