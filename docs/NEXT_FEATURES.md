# Next Features & Bug Fixes

**Created:** February 26, 2026  
**Status:** Planning  
**Priority:** High

---

## 🐛 BUG FIX: Banned Users Can Still Login

### Problem
Users with `is_banned = true` can still login. The login endpoint doesn't check the ban status.

### Current Code (auth.py, line 83-95)
```python
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "login", email), max_calls=10, window_sec=60)
    user = authenticate(db, email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_verified:
        # ... checks verification but NOT ban status!
```

### Fix Required
Add ban check after authentication:
```python
if user.is_banned:
    log_audit(db, "login_banned", user_id=user.id, metadata={"email": user.email}, request=request)
    raise HTTPException(status_code=403, detail="Your account has been suspended.")
```

### Files to Update
- `backend/app/api/v1/auth.py` - Add ban check in login endpoint

---

## ✨ NEW FEATURE: Delete User (Admin)

### Requirements
- Admin can permanently delete a user from the system
- Should delete all associated data (sessions, messages, etc.)
- Add confirmation before delete (frontend)
- Log the action in audit logs

### Backend Changes

#### 1. New Endpoint: `DELETE /api/v1/admin/users/{user_id}`

```python
@router.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: int,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a user and all their data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    
    email = user.email  # Store for audit log
    
    # Delete user (CASCADE will handle related records)
    db.delete(user)
    db.commit()
    
    log_audit(
        db,
        "admin_delete_user",
        user_id=None,  # User no longer exists
        metadata={"admin_id": admin.id, "deleted_email": email, "deleted_user_id": user_id},
    )
    
    return {"ok": True, "message": f"User {email} has been permanently deleted"}
```

#### 2. Database Considerations
Ensure CASCADE delete is set up for:
- `interview_sessions` (user_id)
- `messages` (through sessions)
- `chat_threads` (user_id)
- `evaluations` (through sessions)

### Frontend Changes
- Add "Delete" button in `/admin/users` page
- Show confirmation modal before delete
- Update `adminService.ts` with `deleteUser(userId)` method

---

## 🚦 RATE LIMITING: Free User Quotas

### Overview
Free users need usage limits to control costs and encourage upgrades. This is the **most important feature** for sustainability.

### What Needs Limits

| Feature | What to Limit | Why |
|---------|---------------|-----|
| AI Chat (Dashboard) | Messages per day | DeepSeek API costs |
| Interview Sessions | Sessions per month | DeepSeek + ElevenLabs costs |
| ElevenLabs TTS | Characters per month | Direct cost per character |

### Suggested Free Tier Limits

| Resource | Limit | Reset Period | Rationale |
|----------|-------|--------------|-----------|
| **AI Chat Messages** | 50/day | Daily at midnight UTC | ~$0.01/message, allows testing |
| **Interview Sessions** | 10/month | Monthly | Main product, encourage upgrade |
| **ElevenLabs Characters** | 10,000/month | Monthly | ~$0.30 cost, basic usage |
| **Interview Duration** | 15 min/session | Per session | Limits API calls per session |

### Database Schema: Usage Tracking

```sql
CREATE TABLE user_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Daily counters (reset at midnight UTC)
    chat_messages_today INTEGER DEFAULT 0,
    chat_reset_date DATE DEFAULT CURRENT_DATE,
    
    -- Monthly counters (reset on 1st of month)
    interview_sessions_month INTEGER DEFAULT 0,
    tts_characters_month INTEGER DEFAULT 0,
    usage_month DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE),
    
    -- Lifetime stats (never reset)
    total_chat_messages INTEGER DEFAULT 0,
    total_interview_sessions INTEGER DEFAULT 0,
    total_tts_characters INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id)
);

CREATE INDEX idx_user_usage_lookup ON user_usage(user_id);
```

### Implementation Approach

#### Option A: Per-User Total (Recommended for Now)
- Track total usage across ALL interviews/chats
- Simpler to implement
- User decides how to spend their quota

#### Option B: Per-Interview Limits
- Limit calls per interview session
- More complex, harder to explain to users

**Recommendation:** Start with **Option A** (total monthly limits). It's simpler and more flexible.

### Rate Limit Response

When limit exceeded, return:
```json
{
  "detail": "Daily chat limit reached (50/50). Upgrade to Pro for unlimited access.",
  "limit_type": "chat_messages",
  "current": 50,
  "limit": 50,
  "reset_at": "2026-02-27T00:00:00Z",
  "upgrade_url": "/pricing"
}
```

HTTP Status: `429 Too Many Requests`

### Where to Add Checks

| Endpoint | File | Check |
|----------|------|-------|
| `POST /chat/send` | `backend/app/api/v1/chat.py` | `chat_messages_today < 50` |
| `POST /interview/start` | `backend/app/api/v1/interview.py` | `interview_sessions_month < 10` |
| `POST /tts/generate` | `backend/app/api/v1/tts.py` | `tts_characters_month < 10000` |

### Frontend Handling

1. **Show Usage Dashboard** (on profile or dashboard page):
   ```
   AI Chat: 23/50 today
   Interviews: 3/10 this month
   ```

2. **Handle 429 Errors Gracefully**:
   - Show friendly modal/toast
   - Include upgrade CTA

3. **Pre-check Before Actions**:
   - Disable "Start Interview" button if quota exceeded
   - Show "Upgrade" button instead

---

## 📊 Future: Premium Tiers

| Feature | Free | Pro ($9/mo) | Enterprise |
|---------|------|-------------|------------|
| AI Chat | 50/day | 500/day | Unlimited |
| Interviews | 10/month | 100/month | Unlimited |
| TTS Characters | 10K/month | 100K/month | 500K/month |
| Interview Duration | 15 min | 45 min | Unlimited |
| Custom Interviewers | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ |

*This is for future reference - implement free tier limits first.*

---

## 📋 Implementation Priority

### Phase 1: Critical (Do First)
1. ✅ **Fix ban login bug** - Security issue
2. ✅ **Add delete user** - Admin functionality

### Phase 2: Rate Limiting (Main Goal)
3. 🔲 Create `user_usage` table + migration
4. 🔲 Add usage tracking service
5. 🔲 Implement chat message limits
6. 🔲 Implement interview session limits
7. 🔲 Implement TTS character limits
8. 🔲 Add usage display on frontend

### Phase 3: Polish
9. 🔲 Add usage reset cron job (or check on request)
10. 🔲 Create pricing page placeholder
11. 🔲 Add upgrade CTAs when limits hit

---

## 💡 Suggestions

### ElevenLabs: Total vs Per-Interviewer
**Recommendation:** Use **total monthly quota** across all interviewers.

Why:
- Simpler to track and explain
- User flexibility to use one or multiple interviewers
- Easier to implement
- "You have 10,000 characters/month" is clearer than "2,000 per interviewer"

If a user only uses one interviewer, they get the full quota. If they use 5, they split it.

### Interview Counting
**What counts as an interview?**
- ✅ Count when user clicks "Start Interview"
- ❌ Don't count incomplete/abandoned sessions
- ✅ Count when session reaches "in_progress" stage

This prevents users from gaming the system by starting and immediately canceling.

---

## Files to Create/Modify

### New Files
- `backend/app/models/user_usage.py` - Usage tracking model
- `backend/app/crud/user_usage.py` - CRUD operations
- `backend/app/services/usage_limiter.py` - Rate limit logic
- `backend/alembic/versions/xxx_add_user_usage.py` - Migration

### Modified Files
- `backend/app/api/v1/auth.py` - Add ban check
- `backend/app/api/v1/admin.py` - Add delete user endpoint
- `backend/app/api/v1/chat.py` - Add usage check
- `backend/app/api/v1/interview.py` - Add usage check
- `frontend-next/src/app/admin/users/page.tsx` - Add delete button
- `frontend-next/src/lib/services/adminService.ts` - Add deleteUser
- `frontend-next/src/components/dashboard/UsageDisplay.tsx` - New component

---

## Questions to Decide

1. **Reset Time:** Midnight UTC or user's local timezone?
   - *Recommendation:* UTC (simpler, consistent)

2. **Soft vs Hard Limit:** Warn at 80% or just block at 100%?
   - *Recommendation:* Warn at 80%, block at 100%

3. **Grace Period:** Allow 1-2 extra after limit?
   - *Recommendation:* No grace for MVP, add later if needed

4. **Rollover:** Unused quota carries to next month?
   - *Recommendation:* No rollover (standard SaaS practice)
