# Career Level Calibration Feature - Prioritization Analysis

**Date:** March 6, 2026  
**Goal:** Assess which parts of the upgrade are worth implementing now vs. later

---

## 📊 Analysis Summary

| Priority              | Feature                           | Effort   | Impact                           | Recommend |
| --------------------- | --------------------------------- | -------- | -------------------------------- | --------- |
| 🔴 **IMPLEMENT NOW**  | Phase 1: Level Calibration (Core) | 2-3 days | HIGH                             | YES ✅    |
| 🟡 **IMPLEMENT SOON** | Phase 2: Tracks Layer             | 3-4 days | HIGH                             | YES ✅    |
| 🟢 **SKIP FOR NOW**   | Phase 3: Benchmarking/Percentiles | 5-7 days | MEDIUM                           | LATER ⏳  |
| 🟡 **SKIP FOR NOW**   | Phase 4: Referral Gates           | 2-3 days | LOW (depends on referral system) | LATER ⏳  |

---

## 🔴 PHASE 1: Level Calibration (IMPLEMENT NOW)

### Why This Should Be First

**Current State:** Users get a score (0-100) but no context for what it means.

- "I got 72. Is that good?"
- "Does this score mean I'm ready for L4?"
- "What specifically am I missing?"

**This Feature Solves:** Career context interpretation in 2-3 days of work.

### Implementation Steps

#### Step 1: Create Level Definitions (1 hour)

```python
# backend/app/core/level_definitions.py

LEVEL_DEFINITIONS = {
    "backend_engineer": {
        "startup": {
            "entry": {
                "thresholds": {
                    "problem_solving": 70,
                    "communication": 65,
                    "correctness_reasoning": 70,
                    "complexity": 60,
                    "edge_cases": 60,
                },
                "required_signals": [
                    "can_implement_basic_algorithms",
                    "asks_clarifying_questions"
                ]
            },
            "mid": {
                "thresholds": {
                    "problem_solving": 80,
                    "communication": 75,
                    "correctness_reasoning": 80,
                    "complexity": 75,
                    "edge_cases": 75,
                },
                "required_signals": [
                    "considers_tradeoffs",
                    "thinks_about_scale",
                    "explains_approach_first"
                ]
            },
            "senior": {
                "thresholds": {
                    "problem_solving": 85,
                    "communication": 85,
                    "correctness_reasoning": 85,
                    "complexity": 85,
                    "edge_cases": 85,
                },
                "required_signals": [
                    "drives_design",
                    "mentions_production_concerns",
                    "identifies_ambiguities"
                ]
            }
        },
        "faang": {
            "entry": {...},  # Higher thresholds
            "mid": {...},
            "senior": {...}
        }
    }
}
```

**Effort:** 1 hour (copy the structure above, fill in thresholds based on existing rubric)

#### Step 2: Implement Readiness Calculation (2-3 hours)

```python
# backend/app/services/level_calibration.py

class LevelCalibratorService:
    def estimate_level(self, session_id: int, role: str, company_tier: str):
        """
        Determine estimated level + readiness % to next level
        """
        # Get rubric scores from evaluation
        evaluation = Evaluation.get(session_id)
        rubric = evaluation.rubric  # {"communication": 7, ...}

        # Normalize 0-10 to 0-100
        rubric_100 = {k: v * 10 for k, v in rubric.items()}

        # Get level thresholds
        definitions = LEVEL_DEFINITIONS[role][company_tier]

        # Find highest level satisfied
        estimated_level = "entry"
        for level_name in ["entry", "mid", "senior", "staff"]:
            level_def = definitions.get(level_name)
            if level_def:
                if self._meets_thresholds(rubric_100, level_def["thresholds"]):
                    estimated_level = level_name
                else:
                    break

        # Calculate readiness to next level
        next_level = self._next_level(estimated_level)
        if next_level:
            readiness_percent = self._compute_readiness(
                rubric_100,
                definitions[next_level]["thresholds"]
            )
        else:
            readiness_percent = 100  # At max level

        # Calculate confidence
        confidence = self._calculate_confidence(
            rubric_100,
            definitions[estimated_level]["thresholds"],
            num_questions=len(session.questions_asked)
        )

        # Identify gaps
        gaps = self._identify_gaps(
            rubric_100,
            definitions[next_level]["thresholds"] if next_level else {}
        )

        return {
            "estimated_level": estimated_level,
            "readiness_percent": readiness_percent,
            "confidence": confidence,  # "low" | "medium" | "high"
            "gaps": gaps,
            "strengths": self._identify_strengths(rubric_100)
        }

    def _compute_readiness(self, actual, target_thresholds):
        """
        Calculate % readiness to next level threshold
        Example: if target is 80 and actual is 72, readiness = 90%
        """
        total_gap = 0
        total_needed = 0
        for key, target_score in target_thresholds.items():
            actual_score = actual.get(key, 0)
            gap = max(0, target_score - actual_score)
            total_gap += gap
            total_needed += target_score

        if total_needed == 0:
            return 100

        readiness = max(0, min(100, 100 * (1 - (total_gap / total_needed))))
        return int(readiness)
```

**Effort:** 2-3 hours (straightforward math, no LLM, no DB changes needed yet)

#### Step 3: Add API Endpoint (1 hour)

```python
# backend/app/api/v1/analytics.py

@router.get("/sessions/{session_id}/level-calibration")
def get_level_calibration(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Return level calibration for a session"""
    session = session_crud.get_session(db, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404)

    evaluation = evaluation_crud.get_evaluation(db, session_id)
    if not evaluation:
        raise HTTPException(status_code=422, detail="Session not finalized")

    calibrator = LevelCalibratorService()
    result = calibrator.estimate_level(
        session_id,
        role=session.role,
        company_tier=session.company_style
    )

    return result
```

**Effort:** 1 hour (simple endpoint)

#### Step 4: Update Results Page (Frontend) (2-3 hours)

```tsx
// frontend-next/src/components/sections/ResultsSection.tsx

export const ResultsSection = () => {
  const [levelCalibration, setLevelCalibration] = useState(null);

  useEffect(() => {
    // Fetch level calibration
    api
      .get(`/sessions/${sessionId}/level-calibration`)
      .then((res) => setLevelCalibration(res.data));
  }, [sessionId]);

  return (
    <div>
      {/* Existing score section */}
      <ScoreDisplay overall={evaluation.overall_score} />

      {/* NEW: Level Calibration */}
      <LevelCalibrationCard
        estimatedLevel={levelCalibration?.estimated_level}
        readinessPercent={levelCalibration?.readiness_percent}
        confidence={levelCalibration?.confidence}
        gaps={levelCalibration?.gaps}
        strengths={levelCalibration?.strengths}
      />

      {/* Existing rubric display */}
      <RubricDisplay rubric={evaluation.rubric} />
    </div>
  );
};
```

**Effort:** 2-3 hours (design + component + styling)

### Why This First?

1. **No breaking changes** - doesn't touch existing interview flow
2. **Fast ROI** - users immediately see career context
3. **Foundation** - Phases 2-4 build on this
4. **Data-driven** - can gather feedback before adding complexity
5. **Minimal DB changes** - just reading existing rubric scores

### What It Solves

✅ Users understand what their score means  
✅ Career progression clarity  
✅ Actionable next steps  
✅ Builds trust (scores feel less arbitrary)

---

## 🟡 PHASE 2: Tracks Layer (IMPLEMENT SOON - After Phase 1)

### Why This Second

After Phase 1, users see "You're Entry-level." Phase 2 answers: "For what goal?"

Current problem:

- Same interview used for "Intern→FT," "Promotion," "Company Switch," "Role Pivot"
- No differentiation in question selection or scoring emphasis
- Next actions feel generic

### What This Adds

**Track Selection (One-time on dashboard):**

```
"What's your goal?"
○ General interview prep
○ Intern → Full-time conversion
○ Promotion (L3 → L4)
○ Company switch (startup → FAANG)
○ Role pivot (Backend → ML)
```

**Per-Track Configuration:**

```python
TRACKS = {
    "intern_to_ft": {
        "question_mix": {
            "behavioral": 0.4,      # More behavioral (culture fit)
            "coding": 0.4,          # Fundamentals
            "system_design": 0.2    # Maybe one design question
        },
        "emphasis": {
            "communication": 1.2,   # Weight communication higher
            "problem_solving": 1.0,
            "edge_cases": 0.8       # Less emphasis on edge cases
        },
        "next_actions": [
            "Practice explaining your thought process clearly",
            "Review STAR method for behavioral questions",
            "Strengthen communication on simpler problems"
        ]
    },
    "promotion_l3_l4": {
        "question_mix": {
            "behavioral": 0.3,      # Less behavioral
            "coding": 0.2,          # Less basic coding
            "system_design": 0.5    # Heavy on system design
        },
        "emphasis": {
            "communication": 1.0,
            "problem_solving": 1.3,  # Heavier on problem-solving depth
            "complexity": 1.3,       # Big-O, tradeoffs
            "edge_cases": 1.2       # More on edge cases
        },
        "next_actions": [
            "Master distributed system tradeoffs",
            "Practice design decisions for scale",
            "Develop leadership communication"
        ]
    }
}
```

### Implementation

**Backend Changes (2 hours):**

1. Add `track` field to `CreateSessionRequest`
2. Modify question selection to use track's question_mix
3. Modify readiness scoring to use track's emphasis weights

**Frontend Changes (1 hour):**

1. Add track dropdown on dashboard
2. Show track-specific next actions

**Effort Total:** 3-4 days

### Why After Phase 1?

- Phase 1 proves the concept works
- Can gather user feedback on level estimates before adding track complexity
- Tracks are optional (default to generic prep)

---

## 🟢 PHASE 3: Benchmarking/Percentiles (SKIP FOR NOW)

### What This Would Do

Show users percentile rank:

- "You're in the top 25% for Backend Engineer L4 (Startup tier)"
- Compare progress across sessions
- See distribution curves

### Why SKIP For Now

1. **Needs scale** - Percentiles meaningless with <100 sessions
2. **Premature optimization** - Don't have enough data yet
3. **Privacy concerns** - Need to carefully anonymize data
4. **Technical debt** - Requires new tables (benchmark_stats) and aggregation jobs

### When to Revisit

- Once you have 500+ sessions across roles/levels
- When users start asking "how do I compare?"
- Consider adding simple "trending" first (show improvement over time)

### Simpler Alternative Now

Instead of percentiles, show:

```
"You scored higher than your last 3 sessions (72 → 76 → 78)"
```

This gives progress feedback without percentile complexity.

---

## 🟢 PHASE 4: Referral Gates (SKIP FOR NOW)

### What This Would Do

Gate referral program on readiness:

- Only users with 75%+ readiness to target level can request referrals
- Prevents low-quality referrals

### Why SKIP For Now

1. **Depends on referral system** - Don't have it yet
2. **Marketing decision** - What's the referral strategy first?
3. **Low priority** - Focus on core features first

### When to Revisit

- After Phase 1 + 2 are stable
- After you've designed the referral program
- When you have enough data to validate readiness scores

---

## 🎯 Recommended Rollout Timeline

```
Week 1-2:  Phase 1 (Level Calibration) ✅
           └─ 5-6 hours dev, 1-2 hours QA
           └─ Deploy to prod, gather feedback

Week 3-4:  Phase 2 (Tracks Layer) ✅
           └─ 3-4 days dev
           └─ Optional feature (doesn't break if not used)

Month 2+:  Phase 3 & 4 (when data supports it)
```

---

## 💡 Quick Wins Within Phase 1

If you have extra time:

### 1. "Next Actions" Generation (Add LLM prompt)

```python
# Instead of hardcoded next_actions, generate from gaps
gaps = ["complexity reasoning weak", "edge cases mentioned 1/3 questions"]
next_actions = await llm.generate_next_actions(role, gaps, track)
```

**Time:** 1 hour
**Value:** More personalized feedback

### 2. Confidence Badge

```tsx
<ConfidenceBadge level="high" />  // Green checkmark
<ConfidenceBadge level="medium" /> // Yellow warning
<ConfidenceBadge level="low" />    // Red info
```

**Time:** 30 minutes
**Value:** Users understand how confident the estimate is

### 3. "Retake To Improve" CTA

```
"Your readiness is 68% to L4. Take another session to improve."
// Link directly to new session creation with same role/company/track
```

**Time:** 1 hour
**Value:** Increases session volume, improves monetization

---

## ⚠️ Risks to Watch

### Phase 1 Risks

| Risk                                                       | Mitigation                                                |
| ---------------------------------------------------------- | --------------------------------------------------------- |
| Level thresholds too harsh → users discouraged             | Start conservative, gather feedback, adjust               |
| Threshold values don't match reality                       | Get feedback from actual engineers on level accuracy      |
| Readiness % confusing (90% ready but doesn't feel like it) | Add explainer text: "Gap is only in complexity reasoning" |

### Phase 2 Risks

| Risk                                                | Mitigation                                       |
| --------------------------------------------------- | ------------------------------------------------ |
| Track changes question mix → results not comparable | Tag sessions with track, allow switching later   |
| Too many options → paralysis                        | Start with 3 tracks (general, promotion, switch) |

---

## 📋 Concrete To-Do List (Phase 1)

```
[ ] 1. Define level thresholds for each role/company_tier combo
[ ] 2. Write LevelCalibratorService.estimate_level()
[ ] 3. Write LevelCalibratorService.compute_readiness()
[ ] 4. Add GET /analytics/sessions/{id}/level-calibration endpoint
[ ] 5. Update frontend ResultsSection to fetch + display level card
[ ] 6. Design LevelCalibrationCard UI
[ ] 7. Write tests for readiness calculation
[ ] 8. Deploy to staging, test manually
[ ] 9. Gather feedback from 5-10 users
[ ] 10. Adjust thresholds based on feedback
[ ] 11. Deploy to production
[ ] 12. Monitor usage + feedback
```

**Estimated Time:** 5-6 dev hours + 2 QA hours = ~1 week with part-time focus

---

## Summary Table

| Phase                    | Priority  | Effort   | Impact                     | Dependencies           | Recommend |
| ------------------------ | --------- | -------- | -------------------------- | ---------------------- | --------- |
| **1: Level Calibration** | 🔴 HIGH   | 2-3 days | HIGH (clarity)             | None                   | ✅ YES    |
| **2: Tracks Layer**      | 🟡 MEDIUM | 3-4 days | HIGH (relevance)           | Phase 1                | ✅ YES    |
| **3: Benchmarking**      | 🟢 LOW    | 5-7 days | MEDIUM (comparison)        | Phase 2 + Scale        | ⏳ LATER  |
| **4: Referral Gates**    | 🟢 LOW    | 2-3 days | LOW (depends on referrals) | Referral system exists | ⏳ LATER  |

---

## Final Recommendation

**Implement Phase 1 + 2, skip Phase 3 + 4 for now.**

**Rationale:**

- ✅ Phase 1 solves the "what does my score mean" problem
- ✅ Phase 2 adds relevance (intern prep ≠ promotion prep)
- ⏳ Phase 3 needs scale (data-driven decision)
- ⏳ Phase 4 needs referral system first

**Expected outcome:** Users feel the system is personalized to their career goals, not just a generic practice app. This increases retention and word-of-mouth.
