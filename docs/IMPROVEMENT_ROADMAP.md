# Improvement Roadmap

## Overview

This document tracks all identified gaps, improvements, and the implementation status of each.
Updated after comprehensive codebase audit — March 2026.

---

## Priority 1 — High Impact (Fix Now)

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Feedback form UI on results page | ✅ Done | Stars + thumbs + comment modal; backend was already ready |
| 2 | Transcript download | ✅ Done | Download conversation as `.txt` from results page |
| 3 | Animated typing indicator | ✅ Done | Animated dots when AI is composing a reply |
| 4 | End session confirmation dialog | ✅ Done | "Are you sure?" before clearing session |
| 5 | Error boundary on results page | ✅ Done | LevelCalibrationSection wrapped in try/catch |
| 6 | Voice stops after session ends | ✅ Done | TTS guard + audio stop on stage='done' |
| 7 | Collapsible sidebar | ✅ Done | Icon-rail mode (w-14) with tooltip; toggle button in header |
| 8 | Color consistency (blue-900 theme) | ✅ Done | Interview header matches sidebar bg-blue-900 |

---

## Priority 2 — Near-Term Improvements

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | PerformanceSection with real charts | ✅ Done | SVG line chart with hover tooltips + color bands |
| 2 | History — transcript replay | ✅ Done | Modal with full conversation + download button |
| 3 | Chat thread rename/delete | ❌ Pending | Thread management UI incomplete |
| 4 | History search | ❌ Pending | Backend embeddings exist, no frontend search |
| 5 | Feedback admin dashboard | ✅ Done | Stats + rating distribution + filterable list |
| 6 | Bulk session delete | ❌ Pending | Can only delete one at a time |
| 7 | Admin audit log viewer | ✅ Done | Table view with color-coded actions + pagination |

---

## Priority 3 — Technical Debt

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 1 | No CI/CD pipeline | ❌ Pending | GitHub Actions needed |
| 2 | No frontend tests (Jest) | ❌ Pending | Zero test coverage on frontend |
| 3 | No error monitoring (Sentry) | ❌ Pending | Production errors invisible |
| 4 | No request timeouts on LLM calls | ❌ Pending | DeepSeek hang = user stuck |
| 5 | CORS too permissive in dev | ❌ Pending | Needs env-based origin lock |
| 6 | Database query indexes missing | ❌ Pending | Questions/sessions table slow at scale |
| 7 | No staging environment | ❌ Pending | Deploy directly to production |

---

## Priority 4 — Feature Roadmap

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Subscription / Premium tier | ❌ Planned | Stripe integration + tier management |
| 2 | Percentile comparisons (Phase 3) | ❌ Planned | "Better than 72% of candidates" |
| 3 | Question bank browser | ❌ Planned | Practice by topic, not just random |
| 4 | Share results page | ❌ Planned | Public link to show hiring managers |
| 5 | Interview bookmarks | ❌ Planned | Pin sessions, save specific feedback |
| 6 | Mobile app | ❌ Planned | iOS/Android native apps |
| 7 | Session replay (audio/video) | ❌ Planned | Re-watch interview recording |
| 8 | Real-time collaboration | ❌ Planned | Pair interview mode with WebSockets |

---

## Detailed Gap Analysis

### UX Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| No confirmation before ending session | High | Users lose progress accidentally |
| No typing/thinking indicator | Medium | Chat feels slow/unresponsive |
| No transcript download | Medium | Can't save or share interview |
| No feedback form on UI | Medium | Can't rate session experience |
| No error boundaries on components | High | One crash takes down whole page |
| No voice error recovery message | Medium | User stuck if TTS fails |

### Backend Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| No request timeouts on LLM calls | High | Can hang server indefinitely |
| CORS too open | Medium | Needs production domain lock |
| Missing `POST /feedback` from frontend | Medium | Backend ready, no frontend call |
| Missing `GET /analytics/performance-trends` | Medium | Needed for PerformanceSection |
| Missing `GET /sessions/{id}/transcript` | Low | For transcript export feature |
| No vector search endpoint | Low | Embeddings created but no search |

### Security Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| CORS allows all origins | Medium | Lock to production URL in env |
| No request body size limit | Low | Upload endpoint could be abused |
| No IP-based rate limiting | Low | Only user-based rate limiting |
| Audit logging incomplete | Low | Some admin actions not logged |

---

## Implementation Notes

### Feedback Form
- **Backend endpoint**: `POST /feedback` — accepts `session_id`, `rating` (1-5), `thumbs` (up/down), `comment`, plus optional `rating_questions`, `rating_feedback`, `rating_difficulty`
- **Frontend**: Modal triggered from Results page "Rate Session" button
- **State**: Check `GET /feedback/session/{id}` on results page load to show existing feedback

### Transcript Download
- **Client-side only**: Messages already in sessionStore — no backend call needed
- **Format**: Plain text (`.txt`) with speaker labels + timestamps
- **Trigger**: "Download Transcript" button on results page

### PerformanceSection Charts
- **Data needed**: `GET /sessions` with scores over time — already available
- **Charts**: Use lightweight lib (already have chart components) for score trends
- **Needs**: Session listing with `overall_score` returned in list endpoint

### Error Boundary Pattern
- Wrap `LevelCalibrationSection` in a React try/catch boundary
- On crash: silently render `null` — results page continues working

---

## Scoring

| Category | Score | Target |
|----------|-------|--------|
| Core Interview Flow | 9/10 | 10/10 |
| Level Calibration | 9/10 | 10/10 |
| Authentication | 9/10 | 10/10 |
| Error Handling | 6/10 | 9/10 |
| Frontend UX | 7/10 | 9/10 |
| Backend Architecture | 8/10 | 9/10 |
| Testing | 4/10 | 8/10 |
| Security | 7/10 | 9/10 |
| DevOps | 5/10 | 8/10 |
| **Overall** | **7.1/10** | **9/10** |
