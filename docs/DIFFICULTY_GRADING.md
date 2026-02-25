# Difficulty-Aware Grading System

## Overview

The evaluation engine now calibrates its scoring thresholds, hire signal, and
feedback language based on the difficulty level the candidate chose and whether
adaptive difficulty was enabled.

Before this update, the evaluator applied the same FAANG hiring bar to every
session regardless of difficulty — an easy-level candidate and a hard-level
candidate were scored against identical thresholds. This is now fixed.

---

## Session Difficulty Fields

Three fields on `InterviewSession` drive the grading calibration:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `difficulty` | `str` | `"easy"` | Difficulty selected by the user at session start (`easy \| medium \| hard`) |
| `difficulty_current` | `str` | `"easy"` | Difficulty actually in use at session end (only differs from `difficulty` in adaptive mode) |
| `adaptive_difficulty_enabled` | `bool` | `False` | Whether the engine scaled difficulty in real time based on performance |

---

## How Grading Is Calibrated

### Easy Difficulty

The candidate chose easy questions. The bar reflects this:

- Expectations: solid fundamentals, correct basic solutions, clear communication,
  basic O(n)/O(n²) complexity awareness.
- **Strong Yes** (90–100): Mastery far beyond easy — unprompted optimisation, deep
  edge-case coverage, exceptional clarity. Very rare at this level.
- **Yes** (75–89): Aced easy questions cleanly with little prompting.
- **Borderline** (60–74): Handled easy questions with noticeable gaps — needed
  prompting, minor errors, shallow explanations.
- **No** (40–59): Struggled on easy material. Fundamentals are shaky.
- **Strong No** (<40): Could not handle basic problems.

`next_steps` will always include a recommendation to attempt **medium difficulty**
as the natural next step.

---

### Medium Difficulty

Standard FAANG hiring bar. The default.

- **Strong Yes** (90–100): Exceptional. Would hire immediately. Rare.
- **Yes** (75–89): Clear hire. Strong performance with minor gaps.
- **Borderline** (60–74): Some strengths but significant gaps. Depends on role/level.
- **No** (40–59): Meaningful gaps. Not ready for this role.
- **Strong No** (<40): Fundamental gaps.

---

### Hard Difficulty

Hard questions require advanced algorithms, system-level reasoning, deep
optimisation, and constraint-awareness. The LLM is told to credit structured
thinking even on partial solutions, because engaging seriously with hard problems
is itself a signal of seniority.

- **Strong Yes** (88–100): Exceptional on hard material. Clean optimal solutions
  with full reasoning.
- **Yes** (70–87): Solid hard-difficulty performance. Structured thinking, minor
  gaps acceptable.
- **Borderline** (52–69): Showed the right approach with meaningful gaps. Potential
  at senior level.
- **No** (35–51): Struggled significantly. Reasoning was unclear or solutions were
  fundamentally wrong.
- **Strong No** (<35): Not ready for hard-difficulty interviews.

`next_steps` will acknowledge the difficulty attempted and give advanced-level
targeted guidance.

---

### Adaptive Difficulty

When `adaptive_difficulty_enabled = true`, the engine scales question difficulty
in real time as the candidate performs well. The evaluator is told:

- What difficulty the session started at (`difficulty`)
- What difficulty was reached by the end (`difficulty_current`)
- To credit the candidate for sustaining or improving performance as questions
  became harder
- To apply the scoring thresholds of the **highest difficulty reached**

Example narrative note: "This interview used ADAPTIVE difficulty — started at EASY,
reached MEDIUM by end of session."

---

## Data Flow

```
User starts session → selects difficulty (easy | medium | hard)
                      optionally enables adaptive difficulty
        │
        ▼
Interview runs
  ├─ adaptive=false: all questions at selected difficulty
  └─ adaptive=true: difficulty_current increases as candidate performs well
        │
        ▼
User ends session → POST /api/v1/sessions/{id}/finalize
        │
        ▼
scoring_engine.finalize(db, session_id)
  ├─ reads session.difficulty
  ├─ reads session.difficulty_current
  ├─ reads session.adaptive_difficulty_enabled
  │
  ├─ evaluator_system_prompt(
  │      rag_context=...,
  │      difficulty=difficulty,
  │      difficulty_current=difficulty_current,
  │      adaptive=adaptive,
  │  )
  │  → injects DIFFICULTY CONTEXT block with calibrated thresholds
  │
  └─ evaluator_user_prompt(
         transcript,
         rubric_context=...,
         difficulty=difficulty,
         adaptive=adaptive,
     )
     → first line: "Interview difficulty: HARD" (or ADAPTIVE note)
        │
        ▼
LLM evaluates transcript with correct context → returns hire_signal, overall_score,
narrative, strengths, weaknesses, patterns_observed, next_steps, standout_moments
        │
        ▼
evaluation.summary stored in DB (JSON column — no migration needed)
        │
        ▼
ResultsSection.tsx displays HireSignalBadge, narrative, score ring, rubric, feedback
```

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/services/scoring_engine.py` | `finalize()` extracts `difficulty`, `difficulty_current`, `adaptive_difficulty_enabled` from session and passes them to evaluator prompts |
| `backend/app/services/prompt_templates.py` | `evaluator_system_prompt()` accepts difficulty params and injects difficulty-calibrated thresholds block; `evaluator_user_prompt()` prepends difficulty context line |

---

## No Migration Required

`difficulty`, `difficulty_current`, and `adaptive_difficulty_enabled` already
exist on `InterviewSession`. No Alembic migration is needed.

---

## Threshold Comparison Table

| Difficulty | Strong Yes | Yes | Borderline | No | Strong No |
|---|---|---|---|---|---|
| **Easy** | 90–100 | 75–89 | 60–74 | 40–59 | <40 |
| **Medium** | 90–100 | 75–89 | 60–74 | 40–59 | <40 |
| **Hard** | 88–100 | 70–87 | 52–69 | 35–51 | <35 |
| **Adaptive** | Highest difficulty reached | | | | |

Easy and medium share the same numeric thresholds, but the evaluator is told
explicitly that acing easy questions is the **baseline**, not exceptional
performance — so the hire signal interpretation differs even at the same score.
