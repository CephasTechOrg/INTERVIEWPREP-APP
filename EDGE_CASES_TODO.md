# Edge Cases & Issues - Consolidated TODO List

**Total Issues:** 31  
**Severity Distribution:** 9 Critical | 8 High | 8 Medium | 6 Low  
**Last Updated:** February 11, 2026

---

## 🔴 CRITICAL ISSUES (9)

### Priority 1: Must Fix Within 1 Week

- [ ] **Issue #1:** Race Condition - Concurrent Finalize Calls
  - **File:** `backend/app/api/v1/sessions.py` (line 243-258)
  - **Impact:** Double evaluations, inconsistent scores
  - **Effort:** 1h
  - **Fix:** Add stage validation + transaction lock in finalize()

- [ ] **Issue #2:** Session Not Locked During Message Handling
  - **File:** `backend/app/api/v1/sessions.py` (lines 211-241)
  - **Impact:** Invalid state transitions, data corruption
  - **Effort:** 1.5h
  - **Fix:** Validate stage before processing, use with_for_update()

- [ ] **Issue #22:** Behavioral Target Validation Missing
  - **File:** `backend/app/api/v1/sessions.py` (line 140)
  - **Impact:** Session deadlock (infinite question loop)
  - **Effort:** 1h
  - **Fix:** Validate behavioral_target ≤ max_questions

- [ ] **Issue #23:** Message Storage DoS (No Size Limits)
  - **File:** `backend/app/crud/message.py`
  - **Impact:** Database exhaustion, 5GB attack possible
  - **Effort:** 0.5h
  - **Fix:** Add max_length=50000 validation in add_message()

- [ ] **Issue #24:** Evaluation Scores Not Validated
  - **File:** `backend/app/services/scoring_engine.py`
  - **Impact:** Invalid scores (-50, 150) accepted and displayed
  - **Effort:** 1h
  - **Fix:** Cap all rubric scores to 0-10 range

### Priority 2: Must Fix Within 2 Weeks

- [ ] **Issue #3:** JSON State Corruption via Silent Exceptions
  - **File:** `backend/app/services/interview_engine.py` (lines 200-370)
  - **Impact:** Skill tracking broken, adaptive difficulty unreliable
  - **Effort:** 2h
  - **Fix:** Deep copy nested dicts, add logging for exceptions

- [ ] **Issue #21:** Skill State Corruption (Shallow Copies)
  - **File:** `backend/app/services/interview_engine.py` (lines 1944-1960)
  - **Impact:** Concurrent requests corrupt skill_state
  - **Effort:** 2h
  - **Fix:** Use deepcopy for nested dicts, refresh from DB before update

- [ ] **Issue #25:** Session Deletion Missing Cascades
  - **File:** `backend/app/crud/session.py`
  - **Impact:** GDPR violation, orphaned messages/evaluations
  - **Effort:** 1h (SQL migration) + 1h (testing)
  - **Fix:** Add CASCADE DELETE to FK constraints

- [ ] **Issue #26:** Token Expiry During Long Operations
  - **File:** `backend/app/api/deps.py` + async operations
  - **Impact:** User loses interview progress, data loss
  - **Effort:** 4h
  - **Fix:** Implement JWT refresh token mechanism + token re-validation

---

## 🟠 HIGH SEVERITY ISSUES (8)

### Priority 2-3: Fix Within 2-4 Weeks

- [ ] **Issue #4:** Behavioral Target Logic Flawed
  - **File:** `backend/app/services/interview_engine.py` (lines 2370-2390)
  - **Impact:** Negative questions remaining, logic breaks
  - **Effort:** 1h
  - **Fix:** Add validation: behavioral_target ≤ max_questions

- [ ] **Issue #5:** Empty Question Pool Handling
  - **File:** `backend/app/services/interview_engine.py` + `handle_student_message()`
  - **Impact:** Messy transcript with duplicate wrap messages
  - **Effort:** 1h
  - **Fix:** Prevent message processing in wrapup/done stages

- [ ] **Issue #6:** Interviewer Profile Injection Risk
  - **File:** `backend/app/api/v1/sessions.py` (line 136)
  - **Impact:** Bloated database fields, DoS via oversized profile
  - **Effort:** 0.5h
  - **Fix:** Add max_length constraints to InterviewerProfile fields

- [ ] **Issue #27:** Verification Code Brute Force Possible
  - **File:** `backend/app/api/v1/auth.py`
  - **Impact:** Account takeover via 6-digit code brute force
  - **Effort:** 2h
  - **Fix:** Add per-code attempt counter + 10min expiry + stronger rate limiting

- [ ] **Issue #28:** Pessimistic Lock Missing During Message Handling
  - **File:** `backend/app/api/v1/sessions.py` + `interview_engine.py`
  - **Impact:** Concurrent messages pick same next question
  - **Effort:** 1.5h
  - **Fix:** Use with_for_update() on session reads

- [ ] **Issue #29:** Warmup State Machine Not Atomic
  - **File:** `interview_engine.py` warmup flow
  - **Impact:** Warmup state/stage inconsistency, stuck users
  - **Effort:** 2h
  - **Fix:** Wrap multi-step state changes in transaction

- [ ] **Issue #30:** Difficulty Can Be Changed Mid-Session
  - **File:** `interview_engine.py:_effective_difficulty()`
  - **Impact:** Sudden difficulty jumps, score inconsistency
  - **Effort:** 1h
  - **Fix:** Lock difficulty after session creation, validate consistency

- [ ] **Issue #31:** Skill State Parsing Too Lenient
  - **File:** `interview_engine.py` (multiple `_*_state()` methods)
  - **Impact:** Silent data loss when skill_state corrupted
  - **Effort:** 1h
  - **Fix:** Log warnings on exception, add corruption detection

---

## 🟡 MEDIUM SEVERITY ISSUES (8)

### Priority 3: Fix Within 1 Month

- [ ] **Issue #7:** LLM JSON Parsing Incomplete
  - **File:** `backend/app/services/llm_client.py` (lines 158-200)
  - **Impact:** Greedy substring extraction, invalid JSON accepted
  - **Effort:** 1h
  - **Fix:** Improve parsing logic, validate extracted JSON schema

- [ ] **Issue #8:** Missing DB Constraints
  - **File:** Database schema
  - **Impact:** Duplicate evaluations possible
  - **Effort:** 0.5h (SQL migration)
  - **Fix:** Add UNIQUE constraint on evaluations.session_id

- [ ] **Issue #9:** No Rate Limiting on Message Endpoint
  - **File:** `backend/app/api/v1/sessions.py` (line 211)
  - **Impact:** Message DoS attack possible
  - **Effort:** 0.5h
  - **Fix:** Add rate_limit() call: max_calls=60, window_sec=60

- [ ] **Issue #10:** JWT Token Expiry Not Handled on Frontend
  - **File:** Frontend authentication logic (Next.js)
  - **Impact:** User kicked out after 7 days, no graceful recovery
  - **Effort:** 3h
  - **Fix:** Implement token refresh middleware + auto-retry on 401

- [ ] **Issue #11:** Behavioral Fallback Questions Hardcoded
  - **File:** `interview_engine.py` (lines 1920-1930)
  - **Impact:** Low variety, no track-specific depth
  - **Effort:** 1h
  - **Fix:** Create question pool by track, deterministic rotation

- [ ] **Issue #12:** Message Content Not Sanitized
  - **File:** `backend/app/crud/message.py`
  - **Impact:** HTML injection, null bytes, memory issues
  - **Effort:** 1h
  - **Fix:** Strip whitespace, remove null bytes, truncate to 50k chars

- [ ] **Issue #13:** Behavioral Target Exceeds Technical Questions
  - **File:** `backend/app/api/v1/sessions.py` (line 140)
  - **Impact:** Interview structure deviation, question repetition
  - **Effort:** 1h
  - **Fix:** Cap behavioral_target to available questions, adjust max_questions

- [ ] **Issue #14:** Silent Exception in Question Backfill
  - **File:** `backend/app/crud/session.py` (lines 20-23)
  - **Impact:** User asked repeated questions
  - **Effort:** 0.5h
  - **Fix:** Log exception warning instead of silent suppress

---

## 🟢 LOW SEVERITY ISSUES (6)

### Priority 4: Fix When Time Permits

- [ ] **Issue #15:** No Password Strength Validation
  - **File:** `backend/app/api/v1/auth.py` (line 39)
  - **Impact:** Weak passwords (123, "password")
  - **Effort:** 0.5h
  - **Fix:** Add min_length=8, regex for uppercase/lowercase/digit

- [ ] **Issue #16:** InterviewEngine Refactoring Debt (2900+ lines)
  - **File:** `backend/app/services/interview_engine.py`
  - **Impact:** Maintenance nightmare, bugs hard to isolate
  - **Effort:** 20h (split into multiple PRs)
  - **Fix:** Extract into modules: warmup, question, rubric, utils

- [ ] **Issue #17:** No Logging of Invalid Input
  - **File:** `backend/app/api/v1/sessions.py` (line 118)
  - **Impact:** Can't audit suspicious behavior
  - **Effort:** 0.5h
  - **Fix:** Log all validation errors with user_id and details

- [ ] **Issue #18:** Evaluation Rubric Scores Not Capped
  - **File:** `backend/app/services/scoring_engine.py` (line 135)
  - **Impact:** Display "problem_solving: 15/10" (invalid)
  - **Effort:** 0.5h
  - **Fix:** Cap all scores: max(0, min(10, score))

- [ ] **Issue #19:** Hardcoded Magic Numbers
  - **File:** Multiple files (main.py, sessions.py, interview_engine.py)
  - **Impact:** Config scattered, inconsistencies likely
  - **Effort:** 1h
  - **Fix:** Move to app/core/config.py InterviewConfig class

- [ ] **Issue #20:** No Audit Trail for Evaluations
  - **File:** `backend/app/services/scoring_engine.py`
  - **Impact:** Can't debug why scores are wrong
  - **Effort:** 2h
  - **Fix:** Add audit table + log LLM model, fallback flag, timestamps

---

## 📊 Summary Table

| Priority  | Issues            | Severity    | Est. Hours | Critical Path |
| --------- | ----------------- | ----------- | ---------- | ------------- |
| Week 1    | #1,#2,#22,#23,#24 | 🔴 Critical | 4-5h       | YES           |
| Week 2-3  | #3,#21,#25,#26    | 🔴 Critical | 9-10h      | YES           |
| Week 2-4  | #4-6,#27-31       | 🟠 High     | 12-15h     | PARTIAL       |
| Month 1   | #7-14             | 🟡 Medium   | 8-10h      | NO            |
| Backlog   | #15-20            | 🟢 Low      | 24-28h     | NO            |
| **TOTAL** | **31**            | **Mixed**   | **57-68h** | -             |

---

## 🎯 Phase Breakdown

### PHASE 1 (1 Week) - Blocking Issues

- [ ] Issue #1: Finalize race condition
- [ ] Issue #2: Session message locking
- [ ] Issue #22: Behavioral target validation
- [ ] Issue #23: Message size limits
- [ ] Issue #24: Evaluation score validation

**Estimated Effort:** 4-5 hours  
**Deployment Risk:** LOW  
**Business Impact:** CRITICAL

### PHASE 2 (2 Weeks) - High Impact

- [ ] Issue #3: Skill state corruption
- [ ] Issue #21: Deep copy nested dicts
- [ ] Issue #25: Cascade deletes
- [ ] Issue #26: JWT refresh tokens
- [ ] Issue #4-6, #27-31: High severity issues

**Estimated Effort:** 18-25 hours  
**Deployment Risk:** MEDIUM  
**Business Impact:** HIGH

### PHASE 3 (1 Month) - Stability

- [ ] Issue #7-14: Medium severity fixes
- [ ] Comprehensive testing
- [ ] Monitoring setup
- [ ] Documentation updates

**Estimated Effort:** 20-30 hours  
**Deployment Risk:** LOW  
**Business Impact:** MEDIUM

### PHASE 4 (Backlog) - Polish

- [ ] Issue #15-20: Low severity fixes
- [ ] Refactoring (issue #16)
- [ ] Code quality improvements

**Estimated Effort:** 24-28 hours  
**Deployment Risk:** LOW  
**Business Impact:** LOW

---

## ✅ Completion Checklist

When marking issues complete, verify:

- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Code review approved
- [ ] No performance regression
- [ ] Error handling tested
- [ ] Backwards compatible
- [ ] Database migration tested (if applicable)
- [ ] Monitoring/alerts configured
- [ ] Documentation updated
- [ ] Deployed to staging + verified

---

## 📝 Notes

- **Concurrency issues** (#1, #2, #28, #29) require load testing to verify fixes
- **Data integrity issues** (#3, #21, #31) need automated detection/alerting
- **Security issues** (#27) require penetration testing
- **GDPR issues** (#25) require legal review before deployment
- **Long operations** (#26) need end-to-end testing with real LLM delays
