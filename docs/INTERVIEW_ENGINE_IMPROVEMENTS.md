# Interview Engine Improvements Plan

## Goal

Make the interview engine smarter by:

- detecting question type (conceptual vs coding vs behavioral),
- using adaptive difficulty only when user enables it,
- adding basic code checking support,
- improving follow-up logic and rubric-driven guidance.

---

## Phase 1 — Question-Type Awareness

**Objective:** Distinguish question types so the interviewer avoids STAR prompts for non-behavioral questions and avoids code checks for conceptual prompts.

**Implementation Steps:**

1. **Add question type classifier** (rule-based, then LLM-backed):
   - Inputs: question tags, title/prompt keywords, and existing `_is_behavioral()` / `_is_conceptual_question()`.
   - Output: `question_type = behavioral | coding | conceptual | system_design`.
2. **Store question type in session state** for current question.
3. **Route prompts based on type**:
   - Behavioral → STAR prompts allowed.
   - Conceptual → definition/explanation prompts, no STAR.
   - Coding → approach, complexity, edge cases, tests.
   - System design → tradeoffs, scaling, APIs, data modeling.

**Files:**

- backend/app/services/interview_engine.py
- backend/app/services/prompt_templates.py

---

## Phase 2 — Adaptive Difficulty Toggle

**Objective:** Allow users to choose adaptive difficulty; otherwise keep fixed.

**Implementation Steps:**

1. Add `adaptive_difficulty_enabled` to InterviewSession (db).
2. Add UI toggle on interview start.
3. Update engine:
   - If adaptive enabled → allow `_maybe_bump_difficulty_current()`.
   - If disabled → keep current behavior (fixed).

**Files:**

- backend/app/models/interview_session.py
- backend/alembic/versions (migration)
- backend/app/services/interview_engine.py
- frontend-next/src/components/sections/InterviewSection.tsx
- backend/app/api/v1/interviews.py (if needed)

---

## Phase 3 — Code Checking / Validation

**Objective:** Detect coding responses and run lightweight checks to validate logic.

**Implementation Steps:**

1. Add **code detection** in engine: look for code blocks or syntax signals.
2. If coding question + code detected:
   - Run static checks (complexity mention, edge cases mention).
   - (Optional) run sandboxed unit tests later.
3. Provide feedback prompt: highlight potential bugs, missing tests, or edge cases.

**Files:**

- backend/app/services/interview_engine.py
- backend/app/services/code_check.py (new)

---

## Phase 4 — Smarter Follow-ups

**Objective:** Make follow-ups adaptive based on missing rubric elements and prior answers.

**Implementation Steps:**

1. Expand rubric focus:
   - `correctness_reasoning`, `complexity`, `edge_cases`, `tradeoffs`, `testing`.
2. Use last rubric scores to pick follow-up focus.
3. Allow 2 follow-ups only if confidence is low or missing focus is high.

**Files:**

- backend/app/services/interview_engine.py
- backend/app/services/llm_schemas.py

---

## Phase 5 — Coverage & Progress Tracking

**Objective:** Avoid repetitive topics and ensure coverage.

**Implementation Steps:**

1. Track topic coverage in `skill_state`.
2. Prefer questions from under-covered areas.

**Files:**

- backend/app/services/interview_engine.py

---

## Phase 6 — UI Feedback Enhancements

**Objective:** Show user hints about interview style and adaptive mode.

**Implementation Steps:**

1. Add labels to Interview UI: question type + difficulty level.
2. Add toggle for adaptive difficulty in interview setup.

**Files:**

- frontend-next/src/components/sections/InterviewSection.tsx

---

## Next Step (Start With)

**Phase 1**: Question-type awareness.

If you approve, I’ll start Phase 1 with the engine changes and prompt routing logic.
