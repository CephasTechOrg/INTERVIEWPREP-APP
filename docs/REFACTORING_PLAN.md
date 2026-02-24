# Interview Engine Refactoring Plan

## Overview

Refactor `backend/app/services/interview_engine.py` (3,100+ lines) into modular, focused files while maintaining **100% behavioral equivalence** and zero logic changes.

**Goal:** Improve maintainability, debuggability, and testability without altering functionality.

---

## Phase 0: Pre-Refactoring (This Document)

### Step 1: Create Detailed Method Mapping

- Map all methods to target modules
- Identify dependencies between methods
- Document method signatures and imports needed

### Step 2: Create Comprehensive Tests

- Unit tests for each module BEFORE extraction
- Integration tests to verify inter-module communication
- End-to-end interview flow tests

### Step 3: Establish Refactoring Checklist

- Verification steps at each stage
- Rollback procedures
- Testing requirements before merging

---

## Proposed Module Structure

```
backend/app/services/
├── interview_engine.py                    (1) Main orchestrator (~400 lines)
│   └── Imports from sub-modules
│   └── Public API: generate_interview_response()
│   └── Main interview loop
│
├── interview_engine_rubric.py             (2) Rubric & Scoring (~600 lines)
│   ├── _update_skill_state()
│   ├── _skill_last_overall()
│   ├── _weakest_dimension()
│   ├── _critical_rubric_gaps()            [Phase 4]
│   ├── _coerce_quick_rubric()
│   ├── _skill_streaks()
│   └── All EMA/rubric calculation logic
│
├── interview_engine_signals.py            (3) Signal Detection (~500 lines)
│   ├── _candidate_signals()
│   ├── _is_behavioral()
│   ├── _is_conceptual_question()
│   ├── _behavioral_missing_parts()
│   ├── _response_quality()
│   ├── _is_thin_response()
│   ├── _is_off_topic()
│   └── All signal detection methods
│
├── interview_engine_questions.py          (4) Question Selection (~400 lines)
│   ├── _pick_next_main_question()
│   ├── _pick_next_technical_question()    [Phase 5]
│   ├── _pick_next_behavioral_question()
│   ├── _question_rubric_alignment_score() [Phase 5]
│   ├── _effective_difficulty()
│   ├── _matches_desired_type()
│   └── All question selection logic
│
├── interview_engine_followups.py          (5) Follow-up Logic (~500 lines)
│   ├── _missing_focus_keys()
│   ├── _prioritize_missing_focus()
│   ├── _missing_focus_summary()
│   ├── _missing_focus_tiers()
│   ├── _missing_focus_question()
│   ├── _soft_nudge_prompt()
│   ├── _phase_followup()
│   └── All follow-up decision logic
│
├── interview_engine_quality.py            (6) Quality Assessment (~300 lines)
│   ├── _response_quality()
│   ├── _weakness_dimension()
│   ├── _weakness_keywords()
│   ├── _weakness_score()
│   ├── _signal_summary()
│   ├── _skill_summary()
│   └── Response evaluation methods
│
├── interview_engine_prompts.py            (7) Prompt Generation (~300 lines)
│   ├── _soft_nudge_prompt()
│   ├── _phase_followup()
│   ├── _missing_focus_question()
│   ├── _warmup_behavioral_reply()
│   ├── _warmup_smalltalk_reply()
│   └── All prompt generation methods
│
├── interview_engine_warmup.py             (8) Warmup Flows (~200 lines)
│   ├── _warmup_prompt()
│   ├── _warmup_reply()
│   ├── _warmup_behavioral_question()
│   ├── _warmup_profile_from_state()
│   └── All warmup-related methods
│
├── interview_engine_transitions.py        (9) Transitions & State (~250 lines)
│   ├── _transition_preface()
│   ├── _advance_to_next_question()
│   ├── _reset_for_new_question()
│   ├── _set_question_type_state()
│   └── State management methods
│
└── interview_engine_utils.py              (10) Utilities (~200 lines)
    ├── _question_type()
    ├── _normalize_text()
    ├── _sanitize_ai_text()
    ├── _clamp_int()
    ├── _focus_tags()
    ├── _render_text()
    └── Helper utility methods
```

---

## Method-to-Module Mapping (Detailed)

### Module 1: interview_engine.py (Orchestrator)

**Responsibility:** Main interview loop, API entry points, imports all sub-modules

```python
# Core API
- generate_interview_response(db, session, user_id, student_text)
- ensure_question_and_intro(db, session, user_name)
- ensure_candidate_ready(db, session)
- ensure_question_setup(db, session, preface)

# Interview Loop
- _interview_response_impl(db, session, history, stage)
- _handle_stage_transitions(db, session, stage)

# Imports from all sub-modules
from .interview_engine_rubric import *
from .interview_engine_signals import *
from .interview_engine_questions import *
from .interview_engine_followups import *
from .interview_engine_quality import *
from .interview_engine_prompts import *
from .interview_engine_warmup import *
from .interview_engine_transitions import *
from .interview_engine_utils import *
```

### Module 2: interview_engine_rubric.py (Skill Tracking)

**Responsibility:** Rubric scoring, skill state management, weakness detection

```python
# Skill State Management (Phase 1-2)
- _update_skill_state(db, session, quick_rubric_raw, is_behavioral)
- _skill_last_overall(session)
- _skill_streaks(session)
- _reset_streaks(session)

# Weakness Detection (Phase 4-5)
- _weakest_dimension(session)
- _critical_rubric_gaps(session, threshold)  [NEW - Phase 4]
- _weakness_keywords(dimension)
- _weakness_score(q, keywords)

# Rubric Utilities
- _coerce_quick_rubric(data)
- _clamp_int(val, default, lo, hi)

# Constants
- _RUBRIC_KEYS
- RUBRIC_KEYS = ["communication", "problem_solving", "correctness_reasoning", "complexity", "edge_cases"]
```

**Dependencies:**

- Imports: contextlib, sqlalchemy functions
- Exports to: Main orchestrator, questions module (for Phase 5), followups module (for Phase 4)

---

### Module 3: interview_engine_signals.py (Signal Detection)

**Responsibility:** Detect signals from candidate responses

```python
# Signal Detection (Phase 3)
- _candidate_signals(student_text)
  - Detects: has_code, mentions_approach, mentions_complexity, mentions_edge_cases,
    mentions_constraints, mentions_correctness, mentions_tradeoffs, mentions_tests, has_code

# Question Classification
- _is_behavioral(q)
- _is_conceptual_question(q)
- _is_system_design_question(q)
- _is_coding_question(q)

# Response Analysis
- _behavioral_missing_parts(text)
- _response_quality(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)
- _is_thin_response(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)
- _is_off_topic(q, student_text, signals)

# Utilities
- _normalize_text(text)
- _get_code_blocks(text)
- _count_words(text)
```

**Dependencies:**

- Imports: re (regex), standard lib
- Exports to: Main orchestrator, followups, quality modules

---

### Module 4: interview_engine_questions.py (Question Selection)

**Responsibility:** Pick next question based on difficulty, focus, and rubric gaps (Phase 5)

```python
# Main Question Selection
- _pick_next_main_question(db, session)
- _pick_next_technical_question(db, session, asked_ids, seen_ids, focus, desired_type)
  - UPDATED in Phase 5: Now includes rubric_score
- _pick_next_behavioral_question(db, session, asked_ids)

# Question Scoring (Phase 5)
- _question_rubric_alignment_score(q, rubric_gaps)  [NEW - Phase 5]
- _matches_desired_type(q, desired_type)
- _weakness_score_for_question(q, dimension)

# Difficulty Management
- _effective_difficulty(session)
- _rank_to_difficulty(rank)
- _difficulty_rank(difficulty)

# Utilities
- _seen_question_subquery(session)
```

**Dependencies:**

- Imports: sqlalchemy, database models
- Imports from: rubric module (\_critical_rubric_gaps, \_weakest_dimension)
- Exports to: Main orchestrator, transitions module

---

### Module 5: interview_engine_followups.py (Follow-up Logic)

**Responsibility:** Generate follow-ups, manage focus areas (Phases 4-5)

```python
# Missing Focus Detection
- _missing_focus_keys(q, signals, behavioral_missing)
- _prioritize_missing_focus(missing, session, prefer)
- _missing_focus_summary(missing, behavioral_missing)
- _missing_focus_tiers(missing, is_behavioral, behavioral_missing)
- _missing_from_coverage(coverage, is_behavioral)

# Critical Focus Extraction (Phase 4)
- Uses _critical_rubric_gaps() from rubric module

# Focus Key Management
- _normalize_focus_key(key)
- _question_focus_keys(q)
- _dimension_to_missing_key(dimension)

# Follow-up Helpers
- _get_reanchor_count(session, q_id)
- _set_reanchor_count(db, session, q_id, count)
- _update_clarify_tracking(db, session, q_id, critical_missing)
- _max_followups_reached(session)
```

**Dependencies:**

- Imports: database CRUD operations
- Imports from: rubric module (\_critical_rubric_gaps)
- Exports to: Main orchestrator, prompts module

---

### Module 6: interview_engine_quality.py (Response Quality)

**Responsibility:** Assess response quality, calculate scores

```python
# Response Assessment
- _response_quality(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)
- _is_thin_response(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)
- _is_off_topic(q, student_text, signals)

# Skill Summaries
- _skill_summary(session)
- _signal_summary(signals, missing_keys, behavioral_missing)

# Weakness Scoring
- _weakness_score(q, keywords)
- _weakness_dimension(session)
- _weakness_keywords(dimension)

# Text Analysis
- _normalize_text(text)
- _count_words(text)
```

**Dependencies:**

- Imports from: signals module, rubric module
- Exports to: Main orchestrator, followups module

---

### Module 7: interview_engine_prompts.py (Prompt Generation)

**Responsibility:** Generate follow-up questions and nudges

```python
# Follow-up Question Generation
- _missing_focus_question(key, behavioral_missing)
- _soft_nudge_prompt(is_behavioral, missing_keys, behavioral_missing)
- _phase_followup(q, signals, session, followups_used)

# Warmup Replies
- _warmup_behavioral_reply(session, focus, question_text, tone_line)
- _warmup_smalltalk_reply(tone_line, question)
- _warmup_focus_line(focus)
- _warmup_transition_line(profile)

# Utilities
- _render_text(session, text)
- _sanitize_ai_text(text)
```

**Dependencies:**

- Imports from: utils, followups module
- Exports to: Main orchestrator

---

### Module 8: interview_engine_warmup.py (Warmup Flows)

**Responsibility:** Warmup greeting and small talk

```python
# Warmup Main Methods
- _warmup_prompt(session, user_name)
- _warmup_reply(session, student_text, user_name, focus, db, tone_line)
- _warmup_behavioral_question(db, session)

# Warmup State
- _warmup_state(session)
- _warmup_profile_from_state(session)
- _set_warmup_state(db, session, step, done)
- _warmup_behavioral_ack(student_text)

# Tone & Profile
- _warmup_tone_profile(tone, energy)
- _smalltalk_question(q, topic)

# Utilities
- _set_intro_used(db, session)
- _last_interviewer_message(db, session_id)
```

**Dependencies:**

- Imports from: prompts module, LLM module
- Exports to: Main orchestrator, transitions module

---

### Module 9: interview_engine_transitions.py (State Transitions)

**Responsibility:** Handle stage transitions, advance questions, reset state

```python
# Question Advancement
- _advance_to_next_question(db, session, history, user_name, preface)
- _ask_new_main_question(db, session, q, history, user_name, preface)
- _reset_for_new_question(db, session, q_id)

# State Transitions
- _transition_preface(session)
- _set_question_type_state(db, session, q)
- _maybe_bump_difficulty_current(db, session)

# Question Tracking
- _increment_questions_asked(db, session)
- _increment_followups_used(db, session)
- _max_questions_reached(session)

# Interview Finalization
- _interview_score_and_wrap(db, session)
```

**Dependencies:**

- Imports from: questions module, database CRUD
- Exports to: Main orchestrator

---

### Module 10: interview_engine_utils.py (Utilities)

**Responsibility:** Shared utility functions

```python
# Text Processing
- _normalize_text(text)
- _sanitize_ai_text(text)
- _render_text(session, text)
- _count_words(text)

# Question Classification
- _question_type(q)  [Phase 1]
- _interview_action_from_intent(intent)

# Tag & Focus Management
- _focus_tags(session)
- _focus_dimension(session)
- _focus_keys_for_type(question_type)

# Utilities
- _clamp_int(val, default, lo, hi)
- _company_label(style)
- _interviewer_name(session)
```

**Dependencies:**

- Imports: re, standard lib
- Exports to: All modules

---

## Extraction Order (Safe & Tested)

### Stage 1: Utilities (No Dependencies)

1. Extract `interview_engine_utils.py` (safest, zero dependencies)
2. Run tests: Verify all utility functions work independently

### Stage 2: Signal Detection

3. Extract `interview_engine_signals.py` (depends on utils)
4. Run tests: Verify signal detection accuracy

### Stage 3: Rubric Module (Core)

5. Extract `interview_engine_rubric.py` (depends on utils)
6. Run tests: Verify rubric calculations, EMA tracking, gap detection

### Stage 4: Follow-up & Quality

7. Extract `interview_engine_quality.py` (depends on signals, rubric)
8. Extract `interview_engine_followups.py` (depends on rubric, quality)
9. Run tests: Verify follow-up logic, focus prioritization

### Stage 5: Questions (Phase 5 Integration)

10. Extract `interview_engine_questions.py` (depends on rubric)
11. Run tests: Verify question selection, rubric alignment scoring

### Stage 6: Prompts & Warmup

12. Extract `interview_engine_prompts.py` (depends on followups, utils)
13. Extract `interview_engine_warmup.py` (depends on prompts, LLM)
14. Run tests: Verify prompt generation

### Stage 7: Transitions

15. Extract `interview_engine_transitions.py` (depends on questions, warmup)
16. Run tests: Verify state transitions, question advancement

### Stage 8: Main Orchestrator

17. Update `interview_engine.py` (imports all sub-modules)
18. Run full integration tests

---

## Key Refactoring Rules

### ✅ ALLOWED

- ✅ Copy-paste code to new files
- ✅ Update imports (add new `from .module import ...`)
- ✅ Rename internal method references (e.g., `self._method` → `self._method`)
- ✅ Add docstrings
- ✅ Add type hints

### ❌ NOT ALLOWED

- ❌ Change method logic
- ❌ Remove or rename public methods
- ❌ Change method signatures
- ❌ Alter control flow
- ❌ Remove lines of code
- ❌ Refactor conditionals
- ❌ Change variable names in logic

---

## Verification Checklist (Per Stage)

At each stage, verify:

```
[ ] Code compiles without syntax errors
[ ] All imports resolve correctly
[ ] Method signatures unchanged
[ ] Unit tests pass (100%)
[ ] No new warnings or errors
[ ] Interview flow still works end-to-end
[ ] Rollback plan documented
```

---

## Rollback Procedure

If any stage breaks:

1. Revert all changes: `git checkout backend/app/services/`
2. Identify failure in test output
3. Document root cause
4. Fix in original file first
5. Re-attempt extraction

---

## Success Criteria

### Before Refactoring

- ✅ Full test suite passes
- ✅ No system warnings
- ✅ Interview engine works end-to-end

### After Refactoring

- ✅ All unit tests pass (new + existing)
- ✅ All integration tests pass
- ✅ Interview flow identical
- ✅ No performance degradation
- ✅ Same number of lines of code (no removal)
- ✅ No logic changes verified

---

## Timeline

- Stage 1 (Utils): ~30 min + testing
- Stage 2 (Signals): ~30 min + testing
- Stage 3 (Rubric): ~45 min + testing
- Stage 4 (Followup/Quality): ~60 min + testing
- Stage 5 (Questions): ~45 min + testing
- Stage 6 (Prompts/Warmup): ~45 min + testing
- Stage 7 (Transitions): ~45 min + testing
- Stage 8 (Main): ~30 min + full testing

**Total: ~4-5 hours with comprehensive testing**

---

## Next Step

Document the comprehensive test plan in `REFACTORING_TEST_PLAN.md`
