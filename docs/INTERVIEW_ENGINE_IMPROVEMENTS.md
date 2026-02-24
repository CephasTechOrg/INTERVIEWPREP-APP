# Interview Engine Improvements Plan

## Goal

Make the interview engine smarter by:

- detecting question type (conceptual vs coding vs behavioral),
- using adaptive difficulty only when user enables it,
- adding basic code checking support,
- improving follow-up logic and rubric-driven guidance,
- selecting questions that target candidate's weak areas.

---

## Phase 1 — Question-Type Awareness ?

**Objective:** Distinguish question types so the interviewer avoids STAR prompts for non-behavioral questions and avoids code checks for conceptual prompts.

**Status:** Complete

**Key Changes:**
- Added _question_type() classifier using tags and keywords
- Routed prompts based on type (behavioral, coding, conceptual, system_design)
- Updated prompt templates with type-specific guidance

**Files:**
- backend/app/services/interview_engine.py
- backend/app/services/prompt_templates.py

---

## Phase 2 — Adaptive Difficulty Toggle ?

**Objective:** Allow users to choose adaptive difficulty; otherwise keep fixed.

**Status:** Complete

**Key Changes:**
- Added daptive_difficulty_enabled to InterviewSession (database)
- Created Alembic migration
- Updated UI with toggle on interview start
- Engine respects flag when adjusting difficulty

**Files:**
- backend/app/models/interview_session.py
- backend/alembic/versions/c1f2a8d5b6e7_add_adaptive_difficulty_enabled.py
- backend/app/services/interview_engine.py
- frontend-next/src/components/sections/InterviewSection.tsx

---

## Phase 3 — Code Checking / Validation ?

**Objective:** Detect coding responses and run lightweight checks to validate logic.

**Status:** Complete

**Key Changes:**
- Added code block detection signal
- Added test coverage mention detection
- Provides signals for follow-up logic
- (Sandboxed execution deferred to future phase)

**Files:**
- backend/app/services/interview_engine.py

---

## Phase 4 — Smarter Follow-ups ?

**Objective:** Make follow-ups adaptive based on missing rubric elements and prior answers.

**Status:** Complete

**Key Changes:**

1. **Rubric-aware gap detection** (new method _critical_rubric_gaps):
   - Extracts rubric dimensions with low scores (< 5)
   - Maps to focus keys: correctness, approach, complexity, edge_cases, communication
   - Returns list of areas to target in follow-ups

2. **Enhanced follow-up decision logic**:
   - Integrates rubric gaps into critical_missing list
   - Allows second follow-up if confidence < 0.6 (model uncertain)
   - Allows second follow-up if intent == DEEPEN with rubric gaps
   - Ensures depth only when strategically needed

3. **Enhanced LLM prompts**:
   - System: Added Phase 4 rules for allow_second_followup
   - User: Added Phase 4 guidance section

**Files:**
- backend/app/services/interview_engine.py
- backend/app/services/prompt_templates.py

**How It Works:**
- Stores rolling rubric scores in session.skill_state
- Extracts weak dimensions on next response
- Merges rubric gaps into critical_missing for follow-ups
- Respects max 2 follow-ups with intelligent depth control

---

## Phase 5 — Weakness-Targeted Question Selection ?

**Objective:** Prefer questions that target candidate's weak rubric areas.

**Status:** Complete

**Key Changes:**

1. **Rubric gap extraction** (reuses Phase 4 _critical_rubric_gaps):
   - Identifies weak rubric dimensions
   - Maps to focus keys for question targeting

2. **Question scoring by rubric alignment** (new method _question_rubric_alignment_score):
   - Examines question's meta.evaluation_focus metadata
   - Scores +10 for each rubric gap the question targets
   - Example: weak on complexity ? questions with "complexity" focus score higher

3. **Enhanced technical question selection**:
   - _pick_next_technical_question includes rubric_score
   - Scoring: (tag_overlap * 5) + weak_score + rubric_score - tag_penalty
   - Next question automatically targets weak areas

**Files:**
- backend/app/services/interview_engine.py

**How It Works:**
- When picking next technical question:
  - Call _critical_rubric_gaps to detect weak dimensions
  - Score each candidate question by alignment with gaps
  - Prefer questions targeting weaknesses
- Example: Candidate weak on "edge_cases" + "complexity" ? Q2 (targets both) gets +20, selected over Q1

**Key Benefit:**
- **Targeted learning:** Interview steers toward candidate's weak areas
- **Efficient depth:** Reinforces weak skills with strategic question selection

---

## Phase 6 — UI Feedback Enhancements

**Objective:** Show user hints about interview style and adaptive mode.

**Status:** Pending

**Implementation Steps:**
1. Add labels to Interview UI: question type + difficulty level
2. Display adaptive mode toggle result
3. Show rubric feedback in real-time during interview

**Files:**
- frontend-next/src/components/sections/InterviewSection.tsx

---

## Summary of Completed Phases

| Phase | Focus                        | Status  | Key Feature |
|-------|------------------------------|---------|------------|
| 1     | Question-type awareness      | ? Done | Type-specific prompts (behavioral, coding, conceptual, system design) |
| 2     | Adaptive difficulty toggle   | ? Done | User-controlled difficulty adjustment |
| 3     | Code checking signals        | ? Done | Code detection, test coverage tracking |
| 4     | Smarter follow-ups           | ? Done | Rubric-gap targeted, confidence-aware 2nd followup |
| 5     | Weakness-targeted questions  | ? Done | Next question targets candidate's weak rubric areas |
| 6     | UI feedback enhancements     | Pending | Real-time rubric + type display |

---

## Implementation Notes

**Key Metrics:**
- 5 rubric dimensions tracked: communication, problem_solving, correctness_reasoning, complexity, edge_cases
- Max 2 follow-ups per question with intelligent depth control
- Questions tagged with type: behavioral, coding, conceptual, system_design
- Adaptive difficulty only when user enables toggle
- Phase 5: Questions ranked by rubric gap alignment (+10 per matching gap)

**Architecture:**
- Rolling rubric state stored in session.skill_state (EMA tracking)
- Question scoring combines: tag overlap, weakness score, rubric alignment, penalty for repetition
- RAG context (from similar sessions) enhances LLM prompts for follow-ups
- Interview engine automatically targets weak areas without explicit user input

**Testing Checklist:**
1. ? Question-type routing (behavioral vs coding vs conceptual)
2. ? Adaptive difficulty toggle on/off behavior
3. ? Code detection signals (has_code, mentions_tests)
4. ? Follow-ups respect rubric gaps
5. ? Low confidence allows second follow-up
6. ? DEEPEN intent with gaps allows depth
7. ? Question selection targets weak areas
8. TODO: UI labels for type/difficulty display

**Future Enhancements (Beyond Phase 6):**
- Topic coverage tracking to avoid repetition across full interview
- Difficulty prediction based on candidate performance
- Skill clustering (group weak skills for efficiency)
- Post-interview weakness report with recommended practice areas
