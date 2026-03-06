# Phase 1 Implementation Plan: Role-Aware Level Calibration

**Date:** March 6, 2026  
**Timeline:** 5-7 days  
**Scope:** ALL roles (SWE Intern, SWE Engineer, Data Science, PM, DevOps, Cybersecurity)

---

## 📋 Implementation Steps

1. [Database Migrations](#1-database-migrations)
2. [Level Definitions Config](#2-level-definitions-config)
3. [Backend Service](#3-backend-service)
4. [API Endpoint](#4-api-endpoint)
5. [Frontend Components](#5-frontend-components)
6. [Testing & Deploy](#6-testing--deploy)

---

## 1. Database Migrations

### Create Migration
```bash
cd backend
alembic revision --autogenerate -m "Add level calibration tables"
```

### Tables Needed

**`level_definitions`** (optional - can use config file instead)
- Stores role/tier/level mappings if we want database-driven definitions

**`interview_level_outcomes`** (required)
```sql
CREATE TABLE interview_level_outcomes (
    id SERIAL PRIMARY KEY,
    session_id INTEGER UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
    role VARCHAR(100) NOT NULL,
    company_tier VARCHAR(50) NOT NULL,
    estimated_level VARCHAR(100) NOT NULL,
    estimated_level_display VARCHAR(200) NOT NULL,
    readiness_percent INTEGER NOT NULL,
    confidence VARCHAR(50) NOT NULL,
    strengths JSONB NOT NULL,
    gaps JSONB NOT NULL,
    next_level VARCHAR(100),
    next_actions JSONB NOT NULL,
    rubric_scores_used JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_level_outcomes_session ON interview_level_outcomes(session_id);
CREATE INDEX idx_level_outcomes_role_tier ON interview_level_outcomes(role, company_tier);
```

---

## 2. Level Definitions Config

**File:** `backend/app/core/level_definitions.py`

Structure for each role:
```python
LEVEL_DEFINITIONS = {
    "swe_intern": {
        "startup": { "below_bar": {...}, "meets_bar": {...}, "exceeds_bar": {...} },
        "enterprise": { "below_bar": {...}, "meets_bar": {...}, "exceeds_bar": {...} },
        "faang": { "below_bar": {...}, "meets_bar": {...}, "exceeds_bar": {...} }
    },
    "swe_engineer": {
        "startup": { "entry": {...}, "mid": {...}, "senior": {...}, "staff": {...} },
        "enterprise": { "entry": {...}, "mid": {...}, "senior": {...} },
        "faang": { "entry": {...}, "mid": {...}, "senior": {...}, "staff": {...} }
    },
    "data_science": {
        "startup": { "analyst": {...}, "junior_ds": {...}, "senior_ds": {...}, "ml_engineer": {...} },
        "enterprise": { "analyst": {...}, "junior_ds": {...}, "senior_ds": {...} },
        "faang": { "analyst": {...}, "junior_ds": {...}, "senior_ds": {...} }
    },
    "product_management": {
        "startup": { "apm": {...}, "pm": {...}, "senior_pm": {...}, "director": {...} },
        "enterprise": { "apm": {...}, "pm": {...}, "senior_pm": {...} },
        "faang": { "apm": {...}, "pm": {...}, "senior_pm": {...} }
    },
    "devops_cloud": {
        "startup": { "junior": {...}, "engineer": {...}, "senior": {...}, "architect": {...} },
        "enterprise": { "junior": {...}, "engineer": {...}, "senior": {...} },
        "faang": { "junior": {...}, "engineer": {...}, "senior": {...} }
    },
    "cybersecurity": {
        "startup": { "analyst": {...}, "engineer": {...}, "senior": {...}, "principal": {...} },
        "enterprise": { "analyst": {...}, "engineer": {...}, "senior": {...} },
        "faang": { "analyst": {...}, "engineer": {...}, "senior": {...} }
    }
}
```

**Each level contains:**
- `display_name`: "FAANG Intern (Meets Bar)"
- `thresholds`: {"communication": 72, "problem_solving": 78, ...}
- `required_signals`: ["implements_efficiently", "considers_complexity", ...]
- `focus_areas`: ["algorithms", "complexity", "communication"]
- `description`: "Solid FAANG intern, on track for return offer."

**Helper functions:**
```python
def get_level_progression(role: str, company_tier: str) -> list[str]:
    """Return ordered list of levels for a role/tier."""
    
def get_level_definition(role: str, company_tier: str, level_name: str) -> dict | None:
    """Get specific level definition."""
```

---

## 3. Backend Service

**File:** `backend/app/services/level_calibration_service.py`

```python
class LevelCalibratorService:
    def estimate_level(self, db: Session, session_id: int, role: str, company_tier: str) -> dict:
        """
        Returns:
        {
            "role": "swe_intern",
            "company_tier": "faang",
            "estimated_level": "meets_bar",
            "estimated_level_display": "FAANG Intern (Meets Bar)",
            "readiness_percent": 68,
            "confidence": "high",
            "next_level": "exceeds_bar",
            "strengths": [...],
            "gaps": [...],
            "next_actions": [...]
        }
        """
        # 1. Get evaluation rubric
        # 2. Normalize to 0-100 scale
        # 3. Find highest satisfied level
        # 4. Calculate readiness to next level
        # 5. Calculate confidence (high/medium/low)
        # 6. Identify strengths and gaps
        # 7. Generate next actions
```

**Core methods:**
- `_meets_thresholds(actual, thresholds) -> bool`
- `_compute_readiness_percent(actual, target) -> int`
- `_calculate_confidence(actual, thresholds, num_questions) -> str`
- `_identify_strengths(actual, thresholds) -> list`
- `_identify_gaps(actual, target_thresholds) -> list`
- `_generate_next_actions(role, gaps) -> list`

---

## 4. API Endpoint

**File:** `backend/app/api/v1/analytics.py`

```python
@router.get("/sessions/{session_id}/level-calibration")
def get_level_calibration(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Get level calibration for completed interview."""
    # 1. Verify session belongs to user
    # 2. Verify session has evaluation
    # 3. Call calibrator.estimate_level()
    # 4. Store result in database
    # 5. Return result
```

---

## 5. Frontend Components

### A. Types
**File:** `frontend-next/src/types/level-calibration.ts`
```typescript
export interface LevelCalibrationResult {
  role: string;
  company_tier: string;
  estimated_level: string;
  estimated_level_display: string;
  readiness_percent: number;
  confidence: "low" | "medium" | "high";
  next_level: string | null;
  strengths: Array<{dimension: string; actual_score: number; threshold: number; strength: string}>;
  gaps: Array<{dimension: string; actual_score: number; target_score: number; gap: number; interpretation: string}>;
  next_actions: string[];
  rubric_scores_used: Record<string, number>;
}
```

### B. Service
**File:** `frontend-next/src/lib/services/levelCalibrationService.ts`
```typescript
export const levelCalibrationService = {
  async getLevelCalibration(sessionId: number): Promise<LevelCalibrationResult> {
    const response = await api.get(`/analytics/sessions/${sessionId}/level-calibration`);
    return response.data;
  }
};
```

### C. Component
**File:** `frontend-next/src/components/sections/LevelCalibrationCard.tsx`

Shows:
- Level title (e.g., "FAANG Intern (Meets Bar)")
- Confidence badge (High/Medium/Low)
- Readiness progress bar (% to next level)
- Strengths (top 3 dimensions)
- Gaps (areas to improve)
- Next actions (specific advice)

### D. Integration
**File:** `frontend-next/src/components/sections/ResultsSection.tsx`

Add below score display:
```tsx
{levelCalibration && <LevelCalibrationCard calibration={levelCalibration} />}
```

---

## 6. Testing & Deploy

### Local Testing
```bash
# Backend
cd backend
pytest tests/test_level_calibration.py
alembic upgrade head

# Frontend
cd frontend-next
npm test
npm run build
```

### End-to-End Test
1. Complete interview session
2. Verify level calibration displays
3. Test all roles (SWE Intern, SWE, DS, PM, DevOps, Security)
4. Test all company tiers (startup, enterprise, faang)
5. Verify readiness calculations
6. Check confidence levels

### Deploy
```bash
git checkout -b feature/phase-1-level-calibration
git add .
git commit -m "feat: Add role-aware level calibration (Phase 1)"
git push origin feature/phase-1-level-calibration
# Create PR → Review → Merge to main
```

---

## ✅ Implementation Checklist

### Database (1 hour)
- [ ] Create migration file
- [ ] Add `interview_level_outcomes` table
- [ ] Run migration locally
- [ ] Test up/down migrations

### Backend (6 hours)
- [ ] Create `level_definitions.py` with all roles
  - [ ] SWE Intern (3 tiers × 3 levels)
  - [ ] SWE Engineer (3 tiers × 4 levels)
  - [ ] Data Science (3 tiers × 4 levels)
  - [ ] Product Management (3 tiers × 4 levels)
  - [ ] DevOps/Cloud (3 tiers × 4 levels)
  - [ ] Cybersecurity (3 tiers × 4 levels)
- [ ] Create `level_calibration_service.py`
  - [ ] `estimate_level()` method
  - [ ] `_meets_thresholds()`
  - [ ] `_compute_readiness_percent()`
  - [ ] `_calculate_confidence()`
  - [ ] `_identify_strengths()`
  - [ ] `_identify_gaps()`
  - [ ] `_generate_next_actions()`
- [ ] Add API endpoint in `analytics.py`
- [ ] Create model `interview_level_outcome.py`
- [ ] Write tests

### Frontend (4 hours)
- [ ] Create types
- [ ] Create service
- [ ] Create `LevelCalibrationCard` component
  - [ ] Header (level + confidence)
  - [ ] Readiness progress bar
  - [ ] Strengths section
  - [ ] Gaps section
  - [ ] Next actions section
  - [ ] Dark mode support
  - [ ] Responsive design
- [ ] Integrate into `ResultsSection`
- [ ] Add loading states
- [ ] Add error handling

### Testing (5 hours)
- [ ] Unit tests for calibrator service
- [ ] Unit tests for helper functions
- [ ] API endpoint tests
- [ ] Frontend component tests
- [ ] E2E test: SWE Intern
- [ ] E2E test: SWE Engineer
- [ ] E2E test: Data Science
- [ ] E2E test: Product Management
- [ ] E2E test: DevOps
- [ ] E2E test: Cybersecurity
- [ ] Test edge cases (perfect score, low score, mid score)

### Documentation (2 hours)
- [ ] Code docstrings
- [ ] User-facing FAQ
- [ ] Admin guide

### Deploy (2 hours)
- [ ] Test on staging
- [ ] Production deployment
- [ ] Monitor first 100 sessions
- [ ] Collect feedback

**Total: ~20 hours (2-3 dev days)**

---

## 🎯 Success Criteria

- ✅ All 6 roles supported (SWE Intern, SWE, DS, PM, DevOps, Security)
- ✅ All 3 company tiers work (startup, enterprise, faang)
- ✅ Level calibration displays for 100% of completed sessions
- ✅ Readiness calculations accurate (validate against 20+ sessions)
- ✅ Confidence levels make sense (high = clear signal, low = ambiguous)
- ✅ UI renders correctly on mobile, tablet, desktop
- ✅ Dark mode works
- ✅ No performance degradation (< 500ms API response)
- ✅ All tests pass

---

## 🔮 Future Extensibility

**Adding a new role (e.g., "Mobile Engineer") takes ~2 hours:**

1. Add to `ALLOWED_TRACKS` in `constants.py`
2. Add level definitions to `level_definitions.py`
3. Add question data files
4. Update frontend role mapping

**No code changes needed to:**
- Backend service logic ✅
- API endpoints ✅
- Database schema ✅
- Frontend components ✅

System is **fully dynamic** and reads from config at runtime.
