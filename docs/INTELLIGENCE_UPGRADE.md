# Interview Engine Intelligence Upgrade

## Overview

This document describes the intelligence upgrade applied to the interview engine to
make it behave like a senior FAANG-caliber human interviewer rather than a scripted
question reader.

Four dimensions were upgraded:

| Dimension | Before | After |
|---|---|---|
| **Controller awareness** | Only sees the latest candidate message | Sees full 30-message history + cross-question patterns summary |
| **Hint system** | No hints — move on or repeat question | 3-level escalation: nudge → direction → near-direct hint |
| **Pattern tracking** | Per-question rubric only | Accumulated patterns across all answered questions |
| **Evaluation output** | Score + short bullets | Hire signal + narrative + patterns + standout moments |

---

## 1. Controller Intelligence

### System Prompt — What Makes This Interviewer Exceptional

`backend/app/services/prompt_templates.py` → `interviewer_controller_system_prompt()`

The controller system prompt was completely rewritten to establish five explicit
intelligence behaviours:

#### 1.1 Full Memory & Cross-Reference
The controller is instructed to treat the entire conversation history as
active working memory:
- Reference specific words or phrases the candidate used in earlier answers
- Point out contradictions (e.g., "Earlier you said O(n²) was fine, but now you're optimising — what changed?")
- Connect themes across questions (e.g., "You used a hash-map in Q1 — does that pattern apply here?")

#### 1.2 Specific Reactions
Generic filler responses ("Great answer!") are prohibited. Every response
must react to what the candidate _actually said_:
- Name the algorithm, approach, or trade-off they mentioned
- Challenge specific claims with evidence from their own words
- Acknowledge partial correctness precisely

#### 1.3 Pattern Awareness
The controller receives a `session_patterns` block (plain-English summary
generated from `_session_patterns_summary()`) that describes recurring
themes observed across all questions so far. Examples:
- "Candidate has mentioned complexity analysis in 3/3 answered questions — well covered."
- "Candidate has NOT discussed trade-offs in any question — probe this."

#### 1.4 Progressive Hint System
When a candidate is stuck, the controller receives a `hint_level` (0–3) and
responds appropriately:

| Level | When | Interviewer behaviour |
|---|---|---|
| `0` | No hints yet | Ask an open follow-up question |
| `1` | Weak + 1 followup used | Indirect nudge — reframe the problem |
| `2` | Still weak | Reveal a direction (e.g., "Think about what structure gives O(1) lookup") |
| `3` | Maximum hints | Near-direct scaffolding — walk toward the answer together |

#### 1.5 Authentic Tone
Varied, natural language — not the same opener every turn. The prompt includes
example openers and explicitly forbids hollow filler.

### User Prompt — Intelligence Directive

`interviewer_controller_user_prompt()` gained two new parameters:

```python
def interviewer_controller_user_prompt(
    ...,
    session_patterns: str | None = None,   # English summary of cross-Q patterns
    hint_level: int = 0,                   # 0–3 per-question hint escalation
) -> str:
```

When `session_patterns` is provided it is injected as a `[CROSS-QUESTION PATTERNS]`
block. When `hint_level > 0` a `[HINT LEVEL]` block instructs the controller how
deeply to scaffold.

---

## 2. Session Pattern Tracking

### Data Model

Patterns are stored in `session.skill_state["patterns"]` (a JSON column — no
schema migration required).

```json
{
  "n": 3,
  "complexity_count": 2,
  "approach_count": 3,
  "code_without_plan": 1,
  "tradeoffs_count": 0,
  "edge_cases_count": 1,
  "strong_types": ["coding", "conceptual"],
  "weak_types":   ["system_design"]
}
```

### `_update_session_patterns()` — `interview_engine_main.py`

Called after every rubric update (wrapped in `contextlib.suppress` so it never
crashes the interview).

Accumulates across questions:

| Field | Meaning |
|---|---|
| `n` | Total questions answered so far |
| `complexity_count` | Questions where candidate mentioned complexity |
| `approach_count` | Questions where candidate stated approach before coding |
| `code_without_plan` | Questions where candidate wrote code with no stated approach |
| `tradeoffs_count` | Questions where trade-offs were discussed |
| `edge_cases_count` | Questions where edge cases were mentioned |
| `strong_types` | Question types where rubric avg ≥ 7 |
| `weak_types` | Question types where rubric avg < 5 |

Signal detection uses the `signals` dict already produced by the engine
(e.g., `has_code`, `mentions_tests`, `mentions_tradeoffs`).

### `_session_patterns_summary()` — `interview_engine_main.py`

Converts the raw counters into natural-language sentences passed to the
controller:

```
Candidate has mentioned complexity analysis in 2/3 answered questions.
Candidate has NOT discussed trade-offs in any question — probe this.
Candidate tends to write code without stating an approach first (2/3 questions).
```

Returns `None` when fewer than 2 questions have been answered (not enough
signal to summarise).

---

## 3. Progressive Hint System

### Data Model

Hint levels are stored in `session.skill_state["hints"]` keyed by question ID:

```json
{
  "hints": {
    "42": 0,
    "17": 2
  }
}
```

### Methods

| Method | Description |
|---|---|
| `_get_hint_level(session, q_id)` | Returns current hint level for this question (0 if not yet hinted) |
| `_increment_hint_level(db, session, q_id)` | Increments up to max 3, persists to DB, returns new level |

### Escalation Logic — `handle_student_message()`

```python
hint_level = self._get_hint_level(session, q.id)
if response_quality == "weak" and int(session.followups_used or 0) >= 1:
    hint_level = self._increment_hint_level(db, session, q.id)
```

Hint level only increases when the candidate has already received at least one
follow-up and is still giving weak answers. This prevents unnecessary hand-holding.

---

## 4. Rich Evaluation

### `EvaluationOutput` Schema — `llm_schemas.py`

Four new fields added:

```python
class EvaluationOutput(BaseModel):
    # Existing fields preserved
    overall_score: int          # 0–100
    rubric: QuickRubric
    strengths: list[str]
    weaknesses: list[str]
    next_steps: list[str]

    # New rich fields
    hire_signal: str            # strong_yes | yes | borderline | no | strong_no
    narrative: str              # 2–3 sentence executive summary
    patterns_observed: list[str]  # Recurring themes across all questions
    standout_moments: list[str]   # Specific impressive or notable moments
```

### `hire_signal` Values

| Value | Meaning |
|---|---|
| `strong_yes` | Rare — exceptional, would advocate hard to hire |
| `yes` | Above bar, recommend hiring |
| `borderline` | Mixed signals, could go either way |
| `no` | Below bar |
| `strong_no` | Clearly not ready |

Calibrated to FAANG bar in the system prompt: most candidates should be
`borderline` or `no`, not `strong_yes`.

### Evaluator System Prompt Upgrades

`evaluator_system_prompt()` was completely rewritten with four explicit
requirements:

1. **Specificity** — Quote or paraphrase what the candidate said. No generic
   "good communicator" — say "Explained sliding window clearly with a concrete
   example using index pairs."

2. **Honest calibration** — Score against the FAANG bar, not the average
   candidate. A clear correct answer is not a 90 — it is a passing score.

3. **Pattern recognition** — Identify themes that recurred across questions
   (e.g., "Always stated approach before coding", "Consistently forgot edge cases").

4. **Actionability** — `next_steps` must be specific drills, not vague advice.
   Not "practice arrays" — "Solve 10 sliding window problems to fix the boundary
   off-by-one pattern observed in Q2 and Q4."

### Evaluator User Prompt Upgrades

`evaluator_user_prompt()` now requests a richer JSON response:

```json
{
  "overall_score": 68,
  "hire_signal": "borderline",
  "narrative": "Candidate showed solid fundamentals on dynamic programming but consistently skipped complexity analysis until prompted. Communication was clear but answers lacked depth on system design questions.",
  "rubric": { ... },
  "strengths": ["Named specific algorithm (Kadane's) without prompting", "..."],
  "weaknesses": ["Never voluntarily discussed trade-offs across 4/5 questions", "..."],
  "next_steps": ["Practice 15 complexity-analysis drills on LeetCode", "..."],
  "patterns_observed": ["Always stated approach before coding — strong habit", "..."],
  "standout_moments": ["Q2: Caught their own off-by-one without any hint — impressive", "..."]
}
```

### Storage

New fields are stored in the existing `evaluation.summary` JSON column —
**no database migration required**.

`scoring_engine.py` → `finalize()` includes all new fields in the summary dict:

```python
summary = {
    "strengths": parsed.strengths,
    "weaknesses": parsed.weaknesses,
    "next_steps": parsed.next_steps,
    "hire_signal": parsed.hire_signal,
    "narrative": parsed.narrative,
    "patterns_observed": parsed.patterns_observed,
    "standout_moments": parsed.standout_moments,
}
```

---

## 5. Results Page — `ResultsSection.tsx`

The frontend results page was completely redesigned to surface the new data.

### New Components

#### `HireSignalBadge`
Color-coded badge rendered in the header card:

| Signal | Color |
|---|---|
| `strong_yes` | Emerald (green) |
| `yes` | Blue |
| `borderline` | Amber (yellow) |
| `no` | Orange-red |
| `strong_no` | Red |

#### Narrative Card
The 2–3 sentence executive summary is displayed prominently below the score ring
in the header.

#### Patterns Observed Card
Indigo left-border card listing recurring cross-question themes with a pattern icon
per item.

#### Standout Moments Card
Amber left-border card with quote-style formatting highlighting specific impressive
or notable moments from the session.

### Preserved Sections
- Score ring with overall percentage
- Rubric breakdown (5 dimensions with progress bars + per-dimension scores)
- Strengths / Weaknesses / Next Steps in a 3-column grid
- Per-question performance (if data available)

---

## 6. Files Changed

| File | Change |
|---|---|
| `backend/app/services/prompt_templates.py` | Controller + evaluator system/user prompts completely rewritten |
| `backend/app/services/interview_engine_main.py` | Added `_update_session_patterns`, `_session_patterns_summary`, `_get_hint_level`, `_increment_hint_level`; updated controller call |
| `backend/app/services/llm_schemas.py` | Added `hire_signal`, `narrative`, `patterns_observed`, `standout_moments` to `EvaluationOutput` |
| `backend/app/services/scoring_engine.py` | Updated `finalize()` to include new evaluation fields in summary dict |
| `frontend-next/src/components/sections/ResultsSection.tsx` | Complete rewrite with `HireSignalBadge`, narrative, patterns, standout moments |

---

## 7. Architecture — Data Flow

```
Candidate message
        │
        ▼
handle_student_message()
        │
        ├─ _session_patterns_summary()  ←  skill_state["patterns"]
        │
        ├─ _get_hint_level()            ←  skill_state["hints"][q_id]
        │  └─ (if weak + followup used) → _increment_hint_level()
        │
        ▼
interviewer_controller_user_prompt(
    session_patterns=...,   ← cross-Q English summary
    hint_level=...,         ← 0–3
)
        │
        ▼
LLM (JSON mode) → InterviewControllerOutput
        │
        ▼
Post-response:
  _update_skill_state()          ← per-question rubric EMA
  _update_session_patterns()     ← cross-question accumulators

─────────────── On session end ───────────────

finalize_session()
        │
        ▼
evaluator_user_prompt(full transcript)
        │
        ▼
LLM → EvaluationOutput
  { hire_signal, narrative, patterns_observed, standout_moments, ... }
        │
        ▼
scoring_engine.finalize()
  → evaluation.summary (JSON column)
        │
        ▼
ResultsSection.tsx
  → HireSignalBadge + Narrative + Patterns + Standout Moments
```

---

## 8. Difficulty-Aware Grading

The evaluator now knows the difficulty level the candidate chose and calibrates
its scoring thresholds accordingly.

### Fields read from the session

| Field | Values | Meaning |
|---|---|---|
| `difficulty` | `easy \| medium \| hard` | Difficulty the user selected at session start |
| `difficulty_current` | `easy \| medium \| hard` | Difficulty reached by end (differs from `difficulty` only in adaptive mode) |
| `adaptive_difficulty_enabled` | `bool` | Whether the session scaled difficulty in real time |

### Calibrated thresholds per difficulty

| Difficulty | Strong Yes | Yes | Borderline | No | Strong No |
|---|---|---|---|---|---|
| **Easy** | 90–100 | 75–89 | 60–74 | 40–59 | <40 |
| **Medium** | 90–100 | 75–89 | 60–74 | 40–59 | <40 |
| **Hard** | 88–100 | 70–87 | 52–69 | 35–51 | <35 |
| **Adaptive** | Uses thresholds for highest difficulty reached | | | | |

**Easy note:** The LLM is explicitly told that acing easy questions is the baseline
expectation, not exceptional performance. `next_steps` will always recommend
attempting medium difficulty.

**Hard note:** The LLM is told to credit structured thinking even on partial
solutions, because engaging seriously with hard problems is itself a signal.

### How it flows

```
scoring_engine.finalize()
  ├─ session.difficulty            → passed to evaluator_system_prompt()
  ├─ session.difficulty_current    → passed to evaluator_system_prompt()
  ├─ session.adaptive_difficulty_enabled → passed to both prompts
  │
  ▼
evaluator_system_prompt(difficulty=..., difficulty_current=..., adaptive=...)
  → injects a "DIFFICULTY CONTEXT" block with the correct thresholds
  → LLM scores hire_signal and overall_score against those thresholds
  │
evaluator_user_prompt(difficulty=..., adaptive=...)
  → first line of the prompt is "Interview difficulty: HARD" (or ADAPTIVE note)
  → LLM sees difficulty context before reading the transcript
```

No database migration is needed — `difficulty`, `difficulty_current`, and
`adaptive_difficulty_enabled` already exist on `InterviewSession`.

## 9. No Migration Required (General)

All new data is stored in existing JSON columns:
- `session.skill_state` — patterns and hints
- `evaluation.summary` — all new evaluation fields

No Alembic migration is needed.
