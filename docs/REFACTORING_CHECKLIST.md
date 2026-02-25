# Interview Engine Refactoring - Extraction Checklist

## Master Checklist

Use this checklist for each extraction stage. Check off boxes to ensure nothing is missed.

---

## STAGE 0: Pre-Refactoring Setup

### Repository & Environment

- [ ] Git branch created: `git checkout -b refactor/interview-engine-modularization`
- [ ] Working directory clean: `git status` shows no uncommitted changes
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage baseline captured
- [ ] Performance baseline captured

### Documentation & Planning

- [ ] REFACTORING_PLAN.md reviewed and understood
- [ ] REFACTORING_TEST_PLAN.md reviewed and understood
- [ ] Extraction order confirmed (utils → signals → rubric → quality → followups → questions → prompts → warmup → transitions → main)
- [ ] Dependencies mapped for first module
- [ ] Team notified of refactoring work

### Test Infrastructure

- [ ] Pytest configured and working
- [ ] Test database populated with sample data
- [ ] Baseline tests created and passing
- [ ] Mock objects ready for unit tests

---

## STAGE 1: Extract `interview_engine_utils.py`

### Pre-Extraction (Safest Module - Zero Dependencies)

- [ ] Identify all utility methods (use `grep "def _" backend/app/services/interview_engine.py | head -20`)
- [ ] List all utilities to extract:
  - [ ] `_normalize_text(text)`
  - [ ] `_sanitize_ai_text(text)`
  - [ ] `_render_text(session, text)`
  - [ ] `_count_words(text)`
  - [ ] `_question_type(q)`
  - [ ] `_focus_tags(session)`
  - [ ] `_focus_dimension(session)`
  - [ ] `_clamp_int(val, default, lo, hi)`
  - [ ] `_company_label(style)`
  - [ ] `_interviewer_name(session)`
  - [ ] Other helper methods
- [ ] Verify these have NO dependencies on other methods (except built-ins)
- [ ] Create unit tests: `tests/test_interview_engine_utils.py`
- [ ] Run tests → **all pass** ✅

### File Creation

- [ ] Create new file: `backend/app/services/interview_engine_utils.py`
- [ ] Add imports (only standard library + models)
- [ ] Copy-paste ALL utility methods (unchanged logic)
- [ ] Add module docstring
- [ ] Run linter: `pylint backend/app/services/interview_engine_utils.py`
- [ ] Run type checker: `mypy backend/app/services/interview_engine_utils.py`

### Main File Update

- [ ] Add import: `from .interview_engine_utils import *`
- [ ] Place import at TOP of imports section (before class definition)
- [ ] Verify syntax: `python -m py_compile backend/app/services/interview_engine.py`

### Testing

- [ ] Unit tests pass: `pytest tests/test_interview_engine_utils.py -v`
- [ ] Baseline tests still pass: `pytest tests/test_interview_engine_baseline.py -v`
- [ ] No new warnings: `pylint backend/app/services/interview_engine.py | head -20`
- [ ] Import resolution: Start Python REPL, `from backend.app.services.interview_engine import InterviewEngine` → no errors

### Verification

- [ ] No line removed from original code (only moved)
- [ ] Method signatures unchanged
- [ ] No logic modifications
- [ ] Imports all resolve correctly
- [ ] Code compiles without errors

### Git Commit

```bash
git add backend/app/services/interview_engine_utils.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract utility methods to interview_engine_utils.py

- Moved _normalize_text, _sanitize_ai_text, _render_text, _count_words
- Moved _question_type, _focus_tags, _focus_dimension, _clamp_int
- Moved _company_label, _interviewer_name and other helpers
- Zero logic changes, all tests pass
- Stage 1/10 complete"
```

### Post-Extraction Smoke Test

- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] Interview engine imports correctly
- [ ] No performance degradation: baseline tests still fast
- [ ] Document any issues

---

## STAGE 2: Extract `interview_engine_signals.py`

### Pre-Extraction

- [ ] Dependencies identified: Imports from `interview_engine_utils`
- [ ] Methods listed:
  - [ ] `_candidate_signals(student_text)`
  - [ ] `_is_behavioral(q)`
  - [ ] `_is_conceptual_question(q)`
  - [ ] `_is_system_design_question(q)`
  - [ ] `_is_coding_question(q)`
  - [ ] `_behavioral_missing_parts(text)`
  - [ ] `_response_quality(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)`
  - [ ] `_is_thin_response(student_text, signals, is_behavioral, behavioral_missing, is_conceptual)`
  - [ ] `_is_off_topic(q, student_text, signals)`
  - [ ] `_get_code_blocks(text)`
  - [ ] Other signal methods
- [ ] Create unit tests: `tests/test_interview_engine_signals.py`
- [ ] Run tests → **all pass** ✅

### File Creation

- [ ] Create new file: `backend/app/services/interview_engine_signals.py`
- [ ] Add imports:
  - `import re`
  - `from .interview_engine_utils import ...`
  - Model imports
- [ ] Copy-paste ALL signal detection methods
- [ ] Add module docstring
- [ ] Linter & type checker pass

### Main File Update

- [ ] Add import: `from .interview_engine_signals import *`
- [ ] Verify syntax and imports

### Testing

- [ ] Unit tests: `pytest tests/test_interview_engine_signals.py -v` ✅
- [ ] Baseline tests: `pytest tests/test_interview_engine_baseline.py -v` ✅
- [ ] Full suite: `pytest tests/ -v` ✅
- [ ] No warnings/errors

### Verification

- [ ] ~500 lines moved (no removal)
- [ ] Signal detection works identically
- [ ] Method signatures unchanged
- [ ] All imports resolve

### Git Commit

```bash
git add backend/app/services/interview_engine_signals.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract signal detection to interview_engine_signals.py

- Moved _candidate_signals, _is_behavioral, _is_conceptual_question
- Moved _response_quality, _is_thin_response, _is_off_topic
- Moved _behavioral_missing_parts and related methods
- All signal detection logic preserved
- Stage 2/10 complete"
```

---

## STAGE 3: Extract `interview_engine_rubric.py` (Core Module)

### Pre-Extraction (Most Important - Phases 1-5 depend on this)

- [ ] Dependencies: Uses `interview_engine_utils`
- [ ] Critical methods:
  - [ ] `_update_skill_state(db, session, quick_rubric_raw, is_behavioral)` ⭐
  - [ ] `_skill_last_overall(session)` ⭐
  - [ ] `_weakest_dimension(session)` ⭐
  - [ ] `_critical_rubric_gaps(session, threshold)` ⭐ (Phase 4)
  - [ ] `_skill_streaks(session)`
  - [ ] `_reset_streaks(session)`
  - [ ] `_weakness_keywords(dimension)`
  - [ ] `_weakness_score(q, keywords)`
  - [ ] `_coerce_quick_rubric(data)`
  - [ ] `_clamp_int(val, default, lo, hi)` (already in utils)
- [ ] **Double-check Phase 4 methods are included**
- [ ] Create comprehensive tests: `tests/test_interview_engine_rubric.py`
- [ ] Run tests → **all pass** ✅

### File Creation

- [ ] Create: `backend/app/services/interview_engine_rubric.py`
- [ ] Imports:
  - `import contextlib, sqlalchemy`
  - `from .interview_engine_utils import ...`
  - Database & model imports
- [ ] Copy all rubric methods (EXACTLY as-is)
- [ ] Add constants: `_RUBRIC_KEYS`, `RUBRIC_KEYS`
- [ ] Add module docstring

### Main File Update

- [ ] Add import: `from .interview_engine_rubric import *`
- [ ] Verify syntax

### Critical Testing for Phases 1-5

- [ ] EMA calculation: `test_ema_calculation()` ✅
- [ ] Weakest dimension: `test_weakest_dimension_detection()` ✅
- [ ] **Critical rubric gaps (Phase 4):** `test_critical_rubric_gaps_phase4()` ✅
- [ ] Rubric state update: `test_rubric_state_update()` ✅
- [ ] Baseline tests: ✅
- [ ] Full suite: ✅

### Verification - CRITICAL

- [ ] `_critical_rubric_gaps()` works identically
- [ ] Phase 4 logic unchanged
- [ ] EMA calculations produce same results
- [ ] No rounding errors introduced
- [ ] All rubric state stored correctly

### Git Commit

```bash
git add backend/app/services/interview_engine_rubric.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract rubric tracking to interview_engine_rubric.py

- Moved _update_skill_state, _skill_last_overall, _weakest_dimension
- Moved _critical_rubric_gaps (Phase 4), _skill_streaks
- Moved _weakness_keywords, _weakness_score, _coerce_quick_rubric
- EMA calculations preserved exactly
- Phase 4 (smart follow-ups) logic unchanged
- Stage 3/10 complete"
```

---

## STAGE 4: Extract `interview_engine_quality.py` + `interview_engine_followups.py`

### Pre-Extraction - Quality Module

- [ ] Dependencies: `interview_engine_utils`, `interview_engine_signals`, `interview_engine_rubric`
- [ ] Methods:
  - [ ] `_response_quality()` (might duplicate from signals - verify)
  - [ ] `_is_thin_response()` (might duplicate - verify)
  - [ ] `_weakness_score()`
  - [ ] `_skill_summary()`
  - [ ] `_signal_summary()`
- [ ] Tests: `tests/test_interview_engine_quality.py` ✅

### Pre-Extraction - Followups Module (CRITICAL for Phase 4)

- [ ] Dependencies: `interview_engine_rubric` (for `_critical_rubric_gaps`)
- [ ] **Critical Phase 4 Methods:**
  - [ ] `_missing_focus_keys(q, signals, behavioral_missing)`
  - [ ] `_prioritize_missing_focus(missing, session, prefer)` ⭐ Uses rubric gaps
  - [ ] `_missing_focus_tiers(missing, is_behavioral, behavioral_missing)`
  - [ ] `_missing_focus_summary(missing, behavioral_missing)`
  - [ ] `_missing_from_coverage(coverage, is_behavioral)`
- [ ] Other methods:
  - [ ] `_normalize_focus_key(key)`
  - [ ] `_question_focus_keys(q)`
  - [ ] `_dimension_to_missing_key(dimension)`
  - [ ] `_get_reanchor_count(session, q_id)`
  - [ ] `_set_reanchor_count(db, session, q_id, count)`
  - [ ] `_update_clarify_tracking(db, session, q_id, critical_missing)`
  - [ ] `_max_followups_reached(session)`
- [ ] **Verify Phase 4 logic uses rubric gaps correctly**
- [ ] Tests: `tests/test_interview_engine_followups.py` ✅

### File Creation

- [ ] Create: `backend/app/services/interview_engine_quality.py`
- [ ] Create: `backend/app/services/interview_engine_followups.py`
- [ ] Add proper imports to each
- [ ] Copy all methods exactly

### Main File Update

- [ ] Add imports for both new modules
- [ ] Verify syntax

### Phase 4 Testing - CRITICAL

- [ ] `test_missing_focus_detection()` ✅
- [ ] `test_follow_up_prioritization()` ✅
- [ ] `test_response_quality_affects_followup()` ✅
- [ ] **Phase 4 follow-up logic unchanged** ⭐
- [ ] Baseline tests: ✅

### Verification

- [ ] Phase 4 follow-up logic works identically
- [ ] Rubric gaps integrated correctly into `_prioritize_missing_focus()`
- [ ] No behavioral changes

### Git Commits

```bash
git add backend/app/services/interview_engine_quality.py
git add backend/app/services/interview_engine_followups.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract response quality and follow-up logic

- Moved response quality assessment methods to interview_engine_quality.py
- Moved follow-up generation and prioritization to interview_engine_followups.py
- Phase 4 smart follow-up logic preserved exactly
- Rubric gap integration verified
- Stage 4/10 complete"
```

---

## STAGE 5: Extract `interview_engine_questions.py` (Phase 5 Integration)

### Pre-Extraction - CRITICAL for Phase 5

- [ ] Dependencies: `interview_engine_rubric`, `interview_engine_quality`
- [ ] **Phase 5 New Method:**
  - [ ] `_question_rubric_alignment_score(q, rubric_gaps)` ⭐ (NEW in Phase 5)
- [ ] **Updated Method:**
  - [ ] `_pick_next_technical_question()` ⭐ (NOW includes rubric_score)
- [ ] Other methods:
  - [ ] `_pick_next_main_question(db, session)`
  - [ ] `_pick_next_behavioral_question(db, session, asked_ids)`
  - [ ] `_matches_desired_type(q, desired_type)`
  - [ ] `_effective_difficulty(session)`
  - [ ] `_difficulty_rank(difficulty)`
  - [ ] `_rank_to_difficulty(rank)`
  - [ ] `_seen_question_subquery(session)`
- [ ] **Verify Phase 5 rubric alignment scoring**
- [ ] Tests: `tests/test_interview_engine_questions_phase5.py` ✅

### File Creation

- [ ] Create: `backend/app/services/interview_engine_questions.py`
- [ ] Imports:
  - `from .interview_engine_rubric import _critical_rubric_gaps`
  - `from .interview_engine_quality import _weakness_score`
  - Database imports
- [ ] **Copy Phase 5 updated `_pick_next_technical_question()` exactly**
- [ ] Copy `_question_rubric_alignment_score()` exactly

### Phase 5 Testing - CRITICAL

- [ ] `test_question_rubric_alignment_score()` ✅
- [ ] `test_question_selection_targets_weak_areas()` ✅
- [ ] `test_question_diversity()` ✅
- [ ] **Phase 5 question selection unchanged** ⭐

### Verification

- [ ] Rubric alignment scoring works correctly
- [ ] Questions selected to target weak areas
- [ ] No changes to logic

### Git Commit

```bash
git add backend/app/services/interview_engine_questions.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract question selection to interview_engine_questions.py

- Moved question selection logic
- Included Phase 5 new method: _question_rubric_alignment_score()
- Included Phase 5 updated: _pick_next_technical_question() with rubric_score
- Weakness-targeted question selection preserved
- Stage 5/10 complete"
```

---

## STAGE 6: Extract `interview_engine_prompts.py` + `interview_engine_warmup.py`

### Pre-Extraction

- [ ] Methods to move to prompts module (~300 lines)
- [ ] Methods to move to warmup module (~200 lines)
- [ ] Tests for each module
- [ ] All tests pass ✅

### File Creation & Testing

- [ ] Create both files with proper imports
- [ ] Copy all prompt generation methods
- [ ] Copy all warmup methods
- [ ] Linter & type checks pass

### Verification

- [ ] Prompt generation produces same output
- [ ] Warmup flows identical
- [ ] No logic changes

### Git Commit

```bash
git add backend/app/services/interview_engine_prompts.py
git add backend/app/services/interview_engine_warmup.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract prompts and warmup flows

- Moved prompt generation to interview_engine_prompts.py
- Moved warmup flows to interview_engine_warmup.py
- All warmup and prompt generation logic preserved
- Stage 6/10 complete"
```

---

## STAGE 7: Extract `interview_engine_transitions.py`

### Pre-Extraction

- [ ] List all transition methods (~250 lines)
- [ ] Tests pass ✅

### File Creation

- [ ] Create file with proper imports
- [ ] Copy all transition methods

### Verification

- [ ] State transitions work identically
- [ ] Question advancement unchanged
- [ ] All tests pass ✅

### Git Commit

```bash
git add backend/app/services/interview_engine_transitions.py
git add backend/app/services/interview_engine.py
git commit -m "refactor: extract state transitions to interview_engine_transitions.py

- Moved question advancement logic
- Moved state transition methods
- All transitions preserved exactly
- Stage 7/10 complete"
```

---

## STAGE 8: Final Update to Main `interview_engine.py`

### Pre-Finalization Checklist

- [ ] All sub-modules created (8 files)
- [ ] Main file only imports from sub-modules
- [ ] Main file ~400 lines (orchestrator only)
- [ ] All tests pass: `pytest tests/ -v` ✅

### File Update

- [ ] Remove extracted method definitions from main file
- [ ] Keep only:
  - Class definition: `class InterviewEngine:`
  - Constructor: `__init__()`
  - Public API: `generate_interview_response()`, `ensure_question_and_intro()`, etc.
  - Main interview loop logic
  - All imports from sub-modules at top
- [ ] Verify structure
- [ ] Linter passes

### Final Testing

- [ ] All unit tests pass ✅
- [ ] All integration tests pass ✅
- [ ] End-to-end tests pass ✅
- [ ] Full test suite: `pytest tests/ -v` ✅
- [ ] Coverage maintained: `pytest --cov=backend.app.services.interview_engine`
- [ ] Performance baseline met

### Code Review

- [ ] Main file is clean and readable
- [ ] All modules have proper docstrings
- [ ] Imports are organized (utils → signals → rubric → quality → followups → questions → prompts → warmup → transitions)
- [ ] No circular dependencies

### Git Commit (Final)

```bash
git add backend/app/services/interview_engine.py
git commit -m "refactor: finalize main orchestrator, remove extracted methods

- Main file now acts as orchestrator only
- ~400 lines (down from 3,100+)
- All logic preserved in sub-modules
- All tests passing
- Ready for production
- Refactoring complete: Stage 8/10"
```

---

## STAGE 9: Documentation & Code Cleanup

### Documentation Updates

- [ ] Update `REFACTORING_PLAN.md`: Mark as complete
- [ ] Create `INTERVIEW_ENGINE_ARCHITECTURE.md`: Describe new module structure
- [ ] Add module docstrings to all new files
- [ ] Add method docstrings where missing
- [ ] Create import diagram (docs/module_dependencies.md)

### Code Cleanup

- [ ] Remove any temporary comments
- [ ] Ensure consistent formatting across all files
- [ ] Run formatter: `black backend/app/services/interview_engine*.py`
- [ ] Run linter: `pylint backend/app/services/interview_engine*.py`
- [ ] Run type checker: `mypy backend/app/services/interview_engine*.py`

### Final Testing

- [ ] All tests pass: `pytest tests/ -v` ✅
- [ ] No warnings or errors
- [ ] Coverage report generated

### Git Commit

```bash
git add docs/INTERVIEW_ENGINE_ARCHITECTURE.md
git commit -m "docs: add architecture documentation for refactored interview engine

- Documented module structure and dependencies
- Created module diagram
- Added architectural guidelines for future maintenance
- Refactoring documentation complete"
```

---

## STAGE 10: Merge & Deployment

### Pre-Merge Verification

- [ ] All tests passing on refactor branch
- [ ] All tests passing on main branch (no regression)
- [ ] Code review completed
- [ ] Performance benchmarks met
- [ ] No warnings/errors in CI/CD

### Merge Steps

```bash
git checkout main
git pull origin main
git merge refactor/interview-engine-modularization --no-ff
git push origin main
```

### Post-Deployment Verification

- [ ] Server starts without errors
- [ ] Interview sessions work end-to-end
- [ ] All interview engine tests pass in production
- [ ] Monitor logs for errors (first 24h)
- [ ] Performance metrics normal

### Documentation

- [ ] Update CONTRIBUTING.md with modular structure info
- [ ] Create troubleshooting guide for new developers
- [ ] Document adding new modules to the engine

### Git Commit (Main Branch)

```bash
git commit -m "Merge refactor: modularize interview engine for maintainability

Refactoring Summary:
- Split 3,100+ line monolithic file into 10 focused modules
- No logic changes: 100% behavioral equivalence verified
- Comprehensive testing: baseline + unit + integration + e2e
- Improved debuggability, maintainability, testability
- All tests passing, performance baseline met
- Ready for active development and future enhancements

Modules:
- interview_engine.py (orchestrator)
- interview_engine_utils.py (utilities)
- interview_engine_signals.py (signal detection)
- interview_engine_rubric.py (skill tracking)
- interview_engine_quality.py (response assessment)
- interview_engine_followups.py (follow-up logic)
- interview_engine_questions.py (question selection, Phase 5)
- interview_engine_prompts.py (prompt generation)
- interview_engine_warmup.py (warmup flows)
- interview_engine_transitions.py (state transitions)

Fixes #<issue-number>"
```

---

## Rollback Procedure

If any stage fails:

```bash
# Immediate rollback
git reset --hard HEAD~1

# Or to rollback entire refactoring
git checkout main
git branch -D refactor/interview-engine-modularization
```

Then:

1. Document exact error
2. Investigate root cause in original file
3. Fix issue
4. Create new branch and retry

---

## Success Metrics (Final Check)

✅ All unit tests pass
✅ All integration tests pass
✅ All end-to-end tests pass
✅ Code coverage ≥ 80%
✅ No performance regression
✅ 0 lines of code removed
✅ 0 logic changes verified
✅ All modules created and documented
✅ Main orchestrator file clean and readable
✅ Ready for deployment

---

## Sign-Off

- [ ] Developer: Refactoring complete and tested
- [ ] Reviewer: Code reviewed and approved
- [ ] QA: All tests passing in staging
- [ ] DevOps: Deployment verified in production

---

**Date Started:** ******\_\_\_******
**Date Completed:** ******\_\_\_******
**Notes:** **********************************\_\_\_\_**********************************
