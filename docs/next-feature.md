# upgrade-next-feature.md

## Feature: Career Level Calibration + Readiness Benchmarking (vNext)

### Why this upgrade

Our system already supports:

- Role selection (SWE intern, backend, cloud, cybersecurity, PM, etc.)
- Company type targeting (startup/FAANG/etc.)
- Difficulty modes (easy/medium/hard/adaptive)
- AI interview sessions + rubric scoring + improvement feedback

What’s missing is _career context_:

- Intern → Full-time conversion readiness
- Promotion readiness (e.g., SWE L3 → L4)
- Company-tier readiness (startup vs FAANG bar)
- Switch readiness (mid-level → senior)
- “What does my score actually mean for the next step?”

This upgrade adds a second layer of interpretation:
**Difficulty score (question hardness)** + **Level readiness score (career expectations).**

---

## Goals

1. Keep current UX unchanged (role/company/difficulty/interview/scoring still works).
2. Add **Level Calibration** so users receive:
   - Estimated level (Intern / Entry / Mid / Senior / Staff) OR PM levels
   - Readiness percent for target level and company tier
   - Clear gaps mapped to rubric categories
   - “Next best actions” plan (what to practice next)
3. Enable an optional **Calibration Mode** that auto-adjusts (adaptive) until the user’s level is detected with confidence.

---

## Key Concepts

### 1) Difficulty (existing)

- Easy / Medium / Hard / Adaptive
- Measures performance relative to question hardness.

### 2) Level Calibration (new)

- Measures performance relative to career expectations.
- Example outcomes:
  - “Strong Intern, nearing Entry SWE”
  - “Consistent L3, developing L4 signals”
  - “Senior-ready for startup, L4-ready for FAANG”

### 3) Company Tier Bars (new)

Different company types have different bars.

- Startup bar emphasizes execution + pragmatism
- Enterprise bar emphasizes reliability + collaboration + process
- FAANG bar emphasizes structured thinking + scale + tradeoffs + clarity

---

## UX: What users get and when

### After every interview (existing review page)

Add a new section: **Career Readiness Summary**

- Estimated Level: e.g., "Entry SWE (High confidence)"
- Target Track: e.g., "Promotion: L3 → L4" or "Intern → Full-time"
- Readiness vs Target: e.g., 68% ready for L4 at FAANG tier
- Strengths: top rubric signals
- Gaps: missing signals to reach next level
- Next Actions: 3–5 specific practice tasks

### Optional: “Calibration Interview” entry point

On dashboard, add a new optional button:

- “Calibrate my level (Adaptive)”
  This runs a session that adapts difficulty and scenario types to estimate level with confidence.

---

## Data Model Changes (Backend)

> Note: keep existing interview session schema unchanged as much as possible; add new tables/fields.

### A) Add Level Definitions

Create a configuration-driven schema (JSON or DB tables).

**level_definitions**

- id
- role (backend_engineer, pm, cloud, etc.)
- level (intern, entry, mid, senior, staff...) OR (pm1, pm2, senior_pm...)
- company_tier (startup, enterprise, faang)
- rubric_thresholds (json)
- required_signals (json)
- weights (json)
- created_at / updated_at

Example (simplified):

- Backend L4 FAANG might require:
  - System Design tradeoffs >= 80
  - Communication clarity >= 75
  - Edge cases & reliability >= 70
  - Complexity reasoning >= 75

### B) Store Level Outcomes per Interview

**interview_level_outcomes**

- id
- interview_session_id (FK)
- role
- company_tier
- estimated_level
- readiness_percent
- confidence (low/med/high) OR numeric
- strengths (json array)
- gaps (json array)
- next_actions (json array)
- created_at

### C) Benchmark Stats (Optional but recommended)

If we want “percentile” later:
**benchmark_stats**

- role
- company_tier
- level
- metric_name
- p50, p75, p90, etc. (or distribution buckets)
- updated_at

Start without percentiles if needed; add later.

---

## Scoring Integration (How to compute readiness)

### Current scoring (existing)

We already compute rubric category scores, e.g.:

- Technical correctness
- Communication clarity
- Tradeoff reasoning
- System design depth
- Behavioral STAR quality
- Leadership/ownership signals
  (Exact categories depend on role.)

### New: Level Readiness function

We compute readiness using:

- category scores from the interview session
- level thresholds from `level_definitions`
- company tier weights (optional)

Pseudo-logic:

1. Fetch the user’s chosen role + company tier.
2. Pull the rubric scores from the interview session.
3. Evaluate against levels from lowest → highest:
   - Determine the highest level whose thresholds are satisfied (or closest).
4. Output:
   - estimated_level
   - readiness_percent to the next target level (or selected track)
   - confidence based on score margin and sample size

Readiness % suggestion:

- Use weighted distance-to-threshold:
  - If a threshold is 80 and user got 72, gap=8 points.
  - Convert gaps across categories into a normalized readiness score.
- Confidence:
  - Increase confidence when:
    - multiple questions across categories were asked
    - performance is consistent across categories
    - margins exceed threshold by a safe buffer

---

## Tracks Layer (Recommended)

Add a "Track" concept on top of existing role selection.

**User selects (optional):**

- Track: Intern→FT, Promotion, Company Switch, Role Pivot
  This does NOT replace role selection; it guides:
- question selection (scenario types)
- scoring interpretation (which signals matter most)
- next actions

**tracks**

- id
- name (intern_to_ft, promotion, switch, pivot)
- role
- company_tier
- target_level (optional)
- emphasis_weights (json)
- scenario_mix (json)
- created_at

If user does not pick a track:

- default track based on chosen role + company tier + difficulty.

---

## Interview Engine Changes (Question selection)

Keep existing engine, add a layer that controls the mix:

- For Promotion track:
  - more ambiguous scenarios
  - cross-team tradeoffs
  - leadership and impact prompts
- For Intern→FT:
  - execution + collaboration + learning mindset
  - basic design + debugging + communication
- For Company Switch (FAANG):
  - structured reasoning
  - scale constraints
  - system design + deep tradeoffs

**Adaptive mode + Calibration mode**

- Adaptive mode (existing): difficulty changes based on performance
- Calibration mode (new): also changes _scenario type_ to sample signals needed to estimate level

---

## UI Changes (Frontend)

### Review page

Add sections:

1. **Career Readiness Summary**
2. **Estimated Level + Confidence**
3. **Target readiness**
4. **Strengths / Gaps**
5. **Next best actions** (clickable)

### Dashboard

Add:

- Optional “Track” dropdown (default “General prep”)
- Optional “Calibrate my level” CTA (uses adaptive)

---

## Rollout Plan (Step-by-step)

### Phase 1 — Minimal Viable Level Calibration (fast)

- Add `level_definitions` config (hardcoded JSON first is okay)
- Implement readiness computation after interview
- Store to `interview_level_outcomes`
- Show new summary section on review page

✅ Result: users understand what their score means for career level.

### Phase 2 — Tracks (more differentiation)

- Add track selection
- Adjust question mix and scoring emphasis by track
- Add track-aware next actions

✅ Result: system feels like “career progression engine” not “practice app.”

### Phase 3 — Benchmarking & Percentiles (sticky + credible)

- Aggregate anonymized score distributions
- Show: “You’re in the top 25% for Backend L4 (Startup tier)”
- Add consistent progress charts across sessions

✅ Result: trust increases; employed engineers stay engaged.

### Phase 4 — Referral Readiness Gate (if we build referrals later)

- Gate referral requests by:
  - minimum readiness %
  - minimum confidence
  - minimum number of sessions
- Generate a shareable “Readiness Snapshot” (opt-in)

✅ Result: referrals become feasible because trust is measurable.

---

## Acceptance Criteria (Definition of Done)

- After an interview, the system produces:
  - estimated_level
  - readiness_percent
  - confidence
  - strengths/gaps
  - next_actions
- Results are consistent across repeated sessions (no random level flips without reason).
- Works for at least 2 roles initially (e.g., Backend Engineer + PM).
- No breaking changes to existing interview flow.

---

## Notes & Guardrails

- Difficulty remains user-controlled; level is system-estimated.
- Make level summaries opt-in shareable.
- Avoid overclaiming: always show confidence.
- Start with small set of roles and levels, expand gradually.

---

## Next Implementation Checklist

- [ ] Define rubric categories per role (existing)
- [ ] Draft level definitions for Backend (Intern/Entry/Mid/Senior) by company tier
- [ ] Build readiness computation function
- [ ] Create DB table for interview_level_outcomes
- [ ] Render new sections on review page
- [ ] Add "Track" optional selection (Phase 2)
- [ ] Add "Calibration Interview" mode (Phase 2)
