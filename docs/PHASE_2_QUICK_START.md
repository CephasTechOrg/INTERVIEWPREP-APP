# Phase 2: Integration with Interview Engine - Quick Start

**Status:** PLANNING (Phase 1 Complete)  
**Target Date:** Week of March 10, 2026

---

## Overview

Phase 1 built the **level calibration engine**. Phase 2 will integrate it into the existing interview flow to **automatically generate level assessments** after each interview completes.

---

## Integration Points

### 1. After Interview Finalization

**Current Flow:**

```
Interview Session → Evaluation Generated → Results Page
```

**New Flow:**

```
Interview Session → Evaluation Generated → Level Calibration Calculated → Results Page
```

### 2. Where to Add Integration

**File:** `backend/app/api/v1/sessions.py`

The existing `finalize_session` endpoint (which generates evaluation) should:

1. Keep all existing logic
2. After evaluation is created, call level calibration
3. Store result in database
4. Return both evaluation + level outcome

---

## Implementation Steps

### Step 1: Import Service

```python
from app.services.level_calibration_service import LevelCalibrationService
from app.crud.interview_level_outcome import create_level_outcome
```

### Step 2: After Evaluation Created

Find where evaluation is created in `finalize_session`:

```python
# After: evaluation = create_evaluation(...)
# Add this:

# Extract rubric scores from evaluation
rubric_scores = {
    "communication": evaluation.rubric.get("communication", 0),
    "problem_solving": evaluation.rubric.get("problem_solving", 0),
    "correctness_reasoning": evaluation.rubric.get("correctness_reasoning", 0),
    "complexity": evaluation.rubric.get("complexity", 0),
    "edge_cases": evaluation.rubric.get("edge_cases", 0),
}

# Get session details (role, company tier)
session = session_crud.get_session(db, session_id)

# Calculate level
service = LevelCalibrationService()
outcome_data = service.estimate_level(
    role=session.role,
    company_tier=session.company_style,  # or however tier is stored
    rubric_scores=rubric_scores
)

# Store in database
level_outcome = create_level_outcome(
    db=db,
    session_id=str(session_id),
    outcome_data=outcome_data
)
```

### Step 3: Update Response

Return both evaluation and level outcome:

```python
return {
    "evaluation": evaluation,
    "level_outcome": level_outcome,
    "message": "Interview completed and evaluated"
}
```

---

## Data Mapping

### Session Fields → Level Calibration

```python
# From InterviewSession model
role = session.role          # e.g., "swe_intern"
company_tier = session.company_style  # OR use user preference
                             # "startup", "enterprise", "faang"

# From Evaluation model
rubric_scores = {
    "communication": evaluation.rubric["communication"],
    "problem_solving": evaluation.rubric["problem_solving"],
    "correctness_reasoning": evaluation.rubric["correctness_reasoning"],
    "complexity": evaluation.rubric["complexity"],
    "edge_cases": evaluation.rubric["edge_cases"],
}
```

**Note:** If company tier isn't in session, consider:

1. Adding company_tier field to user profile
2. Using hardcoded default ("startup")
3. Using role to infer tier

---

## Frontend Update (Minimal)

### Current Results Page

Already has `LevelCalibrationSection` component:

```tsx
<LevelCalibrationSection sessionId={sessionId} />
```

### What Happens

1. Component loads
2. Calls `analyticsService.getSessionLevelCalibration(sessionId)`
3. If level outcome exists, displays it
4. If not, shows "not yet generated" message

**No changes needed** - it will automatically work once backend integration complete!

---

## Testing the Integration

### Manual Test Steps

1. **Complete an interview:**
   - Start interview in any role
   - Answer questions
   - Wait for evaluation to generate

2. **Verify evaluation created:**

   ```bash
   curl -H "Authorization: Bearer <token>" \
     https://backend.onrender.com/api/v1/analytics/sessions/<id>/results
   ```

   Should return Evaluation with rubric scores

3. **Check level calibration created:**

   ```bash
   curl -H "Authorization: Bearer <token>" \
     https://backend.onrender.com/api/v1/analytics/sessions/<id>/level-calibration
   ```

   Should return InterviewLevelOutcome

4. **Verify frontend displays:**
   - Load results page
   - Should see level calibration section
   - Check all fields display correctly

### Automated Test

```python
def test_level_calibration_after_interview(session_id, db):
    """Verify level calibration is created after interview."""
    # Complete interview (existing test)
    finalize_session(session_id)

    # Check level outcome created
    outcome = get_level_outcome_by_session(db, str(session_id))
    assert outcome is not None
    assert outcome.estimated_level is not None
    assert outcome.confidence is not None
```

---

## Configuration Options

### Option A: Role Determines Tier

```python
# If tier not in session, infer from role
TIER_MAPPING = {
    "swe_intern": "startup",  # Or ask user
    "swe_engineer": "enterprise",  # Or ask user
    # ... etc
}
company_tier = TIER_MAPPING.get(session.role, "startup")
```

### Option B: User Preference

Add field to user profile:

```python
# In User model
company_tier_pref: Mapped[str] = mapped_column(
    String(50),
    default="startup",
    nullable=False
)
```

Then use:

```python
company_tier = user.company_tier_pref
```

### Option C: Session-Level Setting

Add to InterviewSession:

```python
# In SessionCreateRequest
company_tier?: "startup" | "enterprise" | "faang"
```

Then use when creating session and evaluating.

---

## Rollout Plan

### Phase 2a: Backend Integration (3-5 days)

- [ ] Add integration to finalize_session
- [ ] Update tests
- [ ] Deploy to staging
- [ ] Manual testing

### Phase 2b: Monitoring & Fixes (2-3 days)

- [ ] Monitor error logs
- [ ] Fix any issues
- [ ] Verify data quality

### Phase 2c: Frontend Polish (1-2 days)

- [ ] Optional: Improve UI
- [ ] Add animations
- [ ] Optimize performance

### Phase 2d: Launch (1 day)

- [ ] Deploy to production
- [ ] Announce feature
- [ ] Monitor usage

---

## Performance Considerations

### Service Speed

```
estimate_level() execution time: <10ms
(Pure Python calculations, no DB calls, no API calls)
```

### Database Impact

```
New table: interview_level_outcomes
- Small rows (~2KB each)
- ~1 write per interview completed
- 2 indices (session_id, role)
- Queries: Fast with indices
```

### API Impact

```
New endpoint: GET /analytics/sessions/{id}/level-calibration
- Same auth/permission model as existing
- No additional load
```

### Recommendations

- Add monitoring to track outcome creation time
- Set up alerts if service takes >100ms
- Monitor DB growth (will be fine)

---

## Troubleshooting

### Level outcome not created

**Check:**

1. Evaluation was created successfully
2. Rubric scores all present
3. Role valid (one of 6 roles)
4. Company tier valid (startup/enterprise/faang)
5. Service exception not silently caught

### Wrong level estimated

**Check:**

1. Rubric scores accurate
2. Role/tier combination exists in definitions
3. Service logic (unit tests validate)
4. Thresholds in level_definitions

### API returns 404

**Check:**

1. Session exists and belongs to user
2. Interview completed (evaluation created)
3. Level calibration created in DB
4. Session ID format (should be string in DB)

---

## Success Criteria

Phase 2 is successful when:

- [x] Level calibration automatically created after interview
- [x] Results page displays level information
- [x] All fields render correctly
- [x] No performance degradation
- [x] No errors in logs
- [x] User feedback positive
- [x] 100% of interviews get level outcomes

---

## Files That Will Change

### Backend

- `backend/app/api/v1/sessions.py` - Add level calibration call
- `backend/tests/test_sessions.py` - Add integration test
- Possibly: User profile schema (for company_tier preference)

### Frontend

- Minimal changes (component already ready)
- May optimize based on real-world usage

---

## Questions for Team

1. **Company Tier Selection:**
   - Should this be a user preference?
   - Should it be selectable per interview?
   - Should it match company_style field?

2. **UI Integration:**
   - Should level calibration be in a separate section?
   - Should it be visible before evaluation?
   - Should there be a summary at top?

3. **Data Privacy:**
   - Should level outcomes be visible to admin?
   - Should they be included in exports?
   - Should there be audit logging?

4. **Analytics:**
   - Should we track level distributions?
   - Should we compare across roles/tiers?
   - Should we identify trends?

---

## Appendix: Service API Reference

```python
from app.services.level_calibration_service import LevelCalibrationService

service = LevelCalibrationService()

result = service.estimate_level(
    role="swe_intern",                    # Required: one of 6 roles
    company_tier="faang",                 # Required: startup/enterprise/faang
    rubric_scores={                       # Required: dict of scores
        "communication": 75.0,
        "problem_solving": 78.0,
        "correctness_reasoning": 78.0,
        "complexity": 72.0,
        "edge_cases": 70.0,
    }
)

# Returns dict with:
result["estimated_level"]          # e.g., "meets_bar"
result["estimated_level_display"]  # e.g., "FAANG Intern (Meets Bar)"
result["readiness_percent"]        # 0-100
result["confidence"]               # "low" | "medium" | "high"
result["next_level"]               # e.g., "exceeds_bar" or None
result["strengths"]                # [{dimension, score, threshold, strength}, ...]
result["gaps"]                     # [{dimension, current, target, gap, interp}, ...]
result["next_actions"]             # ["action1", "action2", ...]
result["rubric_scores_used"]       # Input scores (for reference)
```

---

## Timeline

```
Mar 6:  Phase 1 Complete ✓
Mar 10: Phase 2 Planning + Backend Integration (3 days)
Mar 13: Testing + Monitoring (2 days)
Mar 15: UI Polish (1 day)
Mar 16: Production Launch + Announcement
```

---

**Status:** Ready for Phase 2 planning session
