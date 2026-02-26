# Security Audit Report - Interview Prep AI

**Audit Date:** February 25, 2026  
**System Version:** Production-ready  
**Auditor:** Comprehensive security review

---

## Executive Summary

Your system has **good baseline security** but has some areas that need hardening before production deployment. Overall security score: **7/10**.

### Critical Issues: 1

### High Priority: 2

### Medium Priority: 3

### Low Priority: 2

---

## Detailed Audit Results

### 1. ✅ CORS Configuration - **IMPLEMENTED CORRECTLY**

**Status:** ✅ Good for dev, ⚠️ Needs production hardening

**Current Implementation:**

```python
# backend/app/main.py
origins = _parse_origins(settings.FRONTEND_ORIGINS)
origin_regex = None
if settings.ENV == "dev":
    # Allow any localhost/127.0.0.1 port in dev
    origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,  # ⚠️ Only in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Verdict:** ✅ **CORRECT APPROACH**

**What's good:**

- ✅ Dev mode uses regex for flexibility (localhost:any_port)
- ✅ Production relies on `FRONTEND_ORIGINS` env variable
- ✅ No wildcard (\*) in production if configured correctly
- ✅ Credentials allowed (needed for JWT cookies/auth headers)

**Action Required:** ⚠️ **Medium Priority**

```bash
# In production .env, set:
FRONTEND_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ENV=production
```

**Recommendation:** ✅ **NO CODE CHANGES NEEDED** - Just ensure production environment variables are set correctly.

---

### 2. ❌ Redirect URL Validation - **NOT APPLICABLE**

**Status:** ✅ Not a concern for this system

**Finding:** Your system does **NOT use redirects** in the traditional sense:

- No OAuth redirects
- No user-controlled redirect parameters
- No `redirect_uri` or `next` query parameters
- Frontend handles all navigation client-side (React Router)

**Grep Result:** Only 1 match found:

```python
# In prompt_templates.py (not a security issue):
"If they're strong in one area, acknowledge it and redirect to gaps..."
```

**Verdict:** ✅ **NO ACTION NEEDED**

Your system uses a Single Page Application (SPA) architecture where:

- Backend is a pure API (no HTML redirects)
- Frontend handles all routing client-side
- No external redirect vulnerabilities

**If you later add OAuth or external redirects:**

```python
# Add this validation function:
ALLOWED_REDIRECT_HOSTS = {"yourdomain.com", "www.yourdomain.com"}

def validate_redirect_url(url: str) -> bool:
    """Validate redirect URL against allowlist."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc in ALLOWED_REDIRECT_HOSTS
    except:
        return False
```

---

### 3. ⏳ Supabase Storage Policies - **NOT IMPLEMENTED YET**

**Status:** ⚠️ **HIGH PRIORITY** - Implement before production

**Current State:**

```python
# backend/app/core/config.py
SUPABASE_URL: str | None = None
SUPABASE_SERVICE_ROLE_KEY: str | None = None  # ⚠️ Admin key!
SUPABASE_BUCKET_PROFILE_PHOTOS: str = "intervIQ"
```

**Issue:** Using `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security (RLS).

**Risk:** If implemented without RLS policies, users could:

- Access other users' profile photos
- Delete files they don't own
- Upload unlimited files

**Recommendation:** ✅ **RIGHT THING TO DO** - Implement before using Supabase storage

**Required Supabase Policies:**

```sql
-- 1. Enable RLS on storage.objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- 2. Allow users to upload their own files
CREATE POLICY "Users can upload their own profile photos"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'intervIQ'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- 3. Allow users to read their own files
CREATE POLICY "Users can view their own profile photos"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'intervIQ'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- 4. Allow users to update their own files
CREATE POLICY "Users can update their own profile photos"
ON storage.objects FOR UPDATE
USING (
  bucket_id = 'intervIQ'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- 5. Allow users to delete their own files
CREATE POLICY "Users can delete their own profile photos"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'intervIQ'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- 6. Bucket configuration
UPDATE storage.buckets
SET public = false,
    file_size_limit = 5242880,  -- 5MB limit
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
WHERE id = 'intervIQ';
```

**Backend Implementation:**

```python
# Instead of service role key, use user JWT:
async def upload_profile_photo(
    file: UploadFile,
    user_id: int,
    supabase_user_jwt: str  # From user's auth token
):
    """Upload using user's JWT, not service role key."""
    client = create_client(
        settings.SUPABASE_URL,
        supabase_user_jwt  # ✅ User token, not service key
    )

    # File path: user_id/filename
    file_path = f"{user_id}/{file.filename}"

    # Supabase RLS will automatically check if user owns this path
    result = client.storage.from_('intervIQ').upload(
        file_path,
        file.file.read(),
        file_options={"content-type": file.content_type}
    )
```

**Status:** ⏳ **Implement this before enabling profile photos**

---

### 4. ⚠️ Console.log in Production - **FOUND: 14 instances**

**Status:** ⚠️ **MEDIUM PRIORITY** - Clean up before production

**Current State:** Found 14 `console.error()` calls in frontend:

```typescript
// frontend-next/src/components/sections/DashboardSection.tsx:124
console.error("Failed to load sessions:", err);

// frontend-next/src/components/sections/InterviewSection.tsx:375
console.error("Failed to load AI status:", err);

// ... 12 more instances
```

**Risk:** ⚠️ **Medium**

- Error messages may expose API structure
- Stack traces visible in browser console
- Potential information disclosure

**Recommendation:** ✅ **RIGHT THING TO DO** - Remove or replace before production

**Solution 1: Environment-based logging (Recommended)**

```typescript
// src/lib/logger.ts
const isDev = process.env.NODE_ENV === "development";

export const logger = {
  error: (...args: any[]) => {
    if (isDev) {
      console.error(...args);
    }
    // In production, send to error tracking service (Sentry, LogRocket, etc.)
  },
  warn: (...args: any[]) => {
    if (isDev) console.warn(...args);
  },
  info: (...args: any[]) => {
    if (isDev) console.info(...args);
  },
};

// Replace all console.error with:
import { logger } from "@/lib/logger";
logger.error("Failed to load sessions:", err);
```

**Solution 2: Strip console.\* in production build**

```javascript
// next.config.ts
const nextConfig = {
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production"
        ? { exclude: ["error"] } // Keep console.error for critical issues
        : false,
  },
};
```

**Action Items:**

1. ✅ Implement structured logging with environment checks
2. ✅ Send production errors to monitoring service (Sentry recommended)
3. ✅ Remove sensitive data from error messages

---

### 5. ❌ Admin Role Checks - **NOT IMPLEMENTED** (By Design)

**Status:** ✅ **NOT APPLICABLE** - No admin features in current system

**Finding:** Your system **does NOT have admin roles or protected admin routes**:

- No `role` field in User model (only `role_pref` for interview preference)
- No admin-only endpoints
- No user management features
- No admin dashboard

**Database Schema:**

```python
# backend/app/models/user.py
class User(Base):
    id: int
    email: str
    full_name: str | None
    role_pref: str  # ← "SWE Intern", "Senior Engineer" (for interviews, not auth)
    # NO admin role field!
```

**Verdict:** ✅ **NO ACTION NEEDED** for current features

**If you later add admin features:**

```python
# 1. Add to User model:
is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

# 2. Create admin dependency:
from app.api.deps import get_current_user

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user

# 3. Protect admin routes:
@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(get_admin_user)):
    # Only admins can access this
    pass

# 4. Frontend: Check role before rendering admin UI
if (user?.is_admin) {
  return <AdminDashboard />;
}
```

**Important:** ⚠️ **NEVER rely on frontend-only role checks for security**. Always enforce on backend.

---

### 6. ⚠️ Password Reset Rate Limiting - **PARTIALLY IMPLEMENTED**

**Status:** ⚠️ **NEEDS IMPROVEMENT** - Current limits too generous

**Current Implementation:**

```python
# backend/app/api/v1/auth.py
@router.post("/request-password-reset")
def request_password_reset(payload: ResetRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "reset_request", email), max_calls=6, window_sec=60)
    # ...
```

**Current Limits:**

- ⚠️ **6 requests per email per minute** (360 per hour!)
- ⚠️ No daily/hourly cap
- ⚠️ No account lockout mechanism

**Your Requirement:**

> "Maximum 3 requests per email per hour"

**Recommendation:** ✅ **YES, IMPLEMENT THIS** - Much better security

**Improved Implementation:**

```python
# backend/app/api/rate_limit.py - Add hourly tracking
_hourly_buckets: dict[str, deque[float]] = defaultdict(deque)

def rate_limit_hourly(
    request: Request,
    key: str,
    max_calls: int = 3,
    window_sec: int = 3600,  # 1 hour
) -> None:
    """Stricter rate limit for sensitive operations."""
    now = time.time()
    bucket = _hourly_buckets[key]

    # Remove old entries
    while bucket and now - bucket[0] > window_sec:
        bucket.popleft()

    if len(bucket) >= max_calls:
        oldest = bucket[0]
        wait_seconds = int(window_sec - (now - oldest))
        raise HTTPException(
            status_code=429,
            detail=f"Too many password reset requests. Try again in {wait_seconds // 60} minutes."
        )

    bucket.append(now)

# backend/app/api/v1/auth.py
@router.post("/request-password-reset")
def request_password_reset(payload: ResetRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    # ✅ New: 3 requests per email per hour (not just per minute!)
    rate_limit_hourly(request, key=f"reset_hour:{email}", max_calls=3, window_sec=3600)

    # Keep the per-minute limit as backup (prevent rapid-fire)
    rate_limit(request, key=_rate_key(request, "reset_request", email), max_calls=3, window_sec=60)

    # ...
```

**Benefits:**

- ✅ Prevents email bombing (3/hour limit)
- ✅ Prevents brute force attempts
- ✅ Protects email delivery quota
- ✅ Better user experience (clear error messages)

**Production Recommendation:** Use Redis for distributed rate limiting:

```python
# For multi-server deployments:
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def rate_limit_redis(key: str, max_calls: int, window_sec: int):
    current = redis_client.get(key)
    if current and int(current) >= max_calls:
        ttl = redis_client.ttl(key)
        raise HTTPException(429, f"Try again in {ttl // 60} minutes.")

    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_sec)
    pipe.execute()
```

---

### 7. ✅ JWT Duration & Refresh Tokens - **PARTIALLY IMPLEMENTED**

**Status:** ⚠️ **MEDIUM PRIORITY** - Refresh token rotation not implemented

**Current Implementation:**

```python
# backend/app/core/config.py
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # ✅ 7 days

# backend/app/core/security.py
def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    # ...
```

**What's Good:**

- ✅ JWT expiration: 7 days (reasonable for interview prep app)
- ✅ Configurable expiration via environment variable
- ✅ Token validation on every request

**Your Requirement:**

> "Second JWTs duration to 7 days and implementing refresh token rotation"

**Current State:**

- ✅ JWT duration: 7 days (already implemented)
- ❌ Refresh token rotation: NOT implemented

**Recommendation:** ⚠️ **Optional for this use case**

**Analysis:**

**Do you need refresh token rotation?**

| Factor               | Current System          | With Refresh Tokens               |
| -------------------- | ----------------------- | --------------------------------- |
| **Session Length**   | 7 days                  | 7 days (or longer)                |
| **Token Theft Risk** | Medium (7-day window)   | Lower (short-lived access tokens) |
| **User Experience**  | Simple (one token)      | Seamless (auto-refresh)           |
| **Complexity**       | Low                     | Medium-High                       |
| **Data Sensitivity** | Medium (interview data) | High (banking, medical)           |

**Verdict:** ⚠️ **NOT CRITICAL** for interview prep, but ✅ **GOOD PRACTICE** for production

**If you implement refresh tokens:**

```python
# 1. Update config
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived
REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

# 2. Add to User model
class User(Base):
    refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# 3. Login returns both tokens
@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.email, payload.password)

    access_token = create_access_token(user.email, expires_minutes=15)
    refresh_token = create_refresh_token(user.email)

    # Store refresh token in DB
    user.refresh_token = refresh_token
    user.refresh_token_expires_at = datetime.now(UTC) + timedelta(days=7)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# 4. Refresh endpoint
@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    user = verify_refresh_token(db, refresh_token)
    if not user:
        raise HTTPException(401, "Invalid refresh token")

    # ✅ Rotation: Invalidate old, issue new
    new_access = create_access_token(user.email, expires_minutes=15)
    new_refresh = create_refresh_token(user.email)

    user.refresh_token = new_refresh
    user.refresh_token_expires_at = datetime.now(UTC) + timedelta(days=7)
    db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh
    }

# 5. Frontend: Auto-refresh before expiration
// src/lib/api.ts
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        const { data } = await axios.post('/auth/refresh', { refresh_token: refreshToken });
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        // Retry original request
        return api(error.config);
      }
    }
    return Promise.reject(error);
  }
);
```

**My Recommendation:**

- ⏳ **Phase 1 (Now):** Keep 7-day JWT (current system) - Simple and adequate
- ⏳ **Phase 2 (Production):** Add refresh token rotation - Better security
- ⏳ **Phase 3 (Scale):** Use Redis for token revocation - Instant logout across devices

---

## Security Score Summary

| Category                     | Score    | Status                              |
| ---------------------------- | -------- | ----------------------------------- |
| CORS Configuration           | 9/10     | ✅ Good (needs prod config)         |
| Redirect Validation          | N/A      | ✅ Not applicable                   |
| Supabase Policies            | 0/10     | ⚠️ Not implemented yet              |
| Console Logs                 | 5/10     | ⚠️ 14 instances found               |
| Admin Role Checks            | N/A      | ✅ Not applicable                   |
| Password Reset Rate Limiting | 6/10     | ⚠️ Too generous (360/hour)          |
| JWT & Refresh Tokens         | 7/10     | ✅ JWT good, no rotation            |
| **Overall Security**         | **7/10** | ⚠️ Good foundation, needs hardening |

---

## Priority Action Items

### 🔴 Critical (Before Production)

1. **Implement Supabase RLS policies** (if using storage)
2. **Harden password reset rate limiting** (3/hour per email)

### 🟡 High Priority (Before Production)

1. **Remove/strip console.error in production**
2. **Set production CORS origins** in environment variables

### 🟢 Medium Priority (Good Practice)

1. **Implement refresh token rotation** (better security)
2. **Add structured logging** (error tracking service)

### ⚪ Low Priority (Future Enhancement)

1. **Add Redis-based rate limiting** (for multi-server)
2. **Implement account lockout** (after N failed attempts)

---

## Additional Security Recommendations

### 1. **Password Strength Validation**

```python
# Add to signup validation
import re

def validate_password_strength(password: str) -> bool:
    """Enforce strong passwords."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True
```

### 2. **SQL Injection Protection**

✅ **Already protected** - Using SQLAlchemy ORM with parameterized queries

### 3. **XSS Protection**

✅ **Already protected** - React auto-escapes by default

### 4. **CSRF Protection**

✅ **Not needed** - Stateless JWT API (no cookies)

### 5. **Content Security Policy (CSP)**

```python
# Add to security headers middleware
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.deepseek.com;"
)
```

---

## Final Verdict

**Your system has a GOOD security foundation** (7/10) with proper:

- ✅ JWT authentication
- ✅ Password hashing (bcrypt)
- ✅ Environment-based CORS
- ✅ Rate limiting framework
- ✅ Security headers
- ✅ Audit logging

**Action Required:**

1. ✅ **Your suggestions are CORRECT** - All are valid security improvements
2. ⚠️ **2 are CRITICAL** before production (Supabase RLS, password reset rate limiting)
3. ✅ **2 are already good** (CORS strategy correct, JWTs at 7 days)
4. ✅ **3 are nice-to-have** (console.log cleanup, refresh tokens, admin checks if needed)

**Bottom Line:** Implement the critical items now, the rest can follow in production hardening phase. Your security instincts are spot-on! 🛡️
