# Rate Limiting Implementation TODO

**Created:** February 24, 2026  
**Status:** 🔴 Not Implemented  
**Priority:** High (Cost Control & System Stability)

---

## Overview

This document outlines the need to implement per-user rate limiting for two critical external API services that incur costs and could be abused:

1. **ElevenLabs TTS API** - Voice synthesis for interviewer responses
2. **AI Chat System (DeepSeek)** - LLM-powered interview orchestration

---

## 1. ElevenLabs Voice Rate Limiting

### Current State

- ✅ Per-interviewer voice mapping implemented (`elevenlabs_tts.py`)
- ✅ Provider fallback system in place
- ✅ Quota detection for ElevenLabs errors
- ❌ **No per-user rate limiting**

### Rationale

- ElevenLabs has API quota limits based on subscription tier
- Characters/month limits can be exceeded by heavy usage
- Need to prevent individual users from exhausting quota
- Fair usage distribution across all users

### Implementation Requirements

#### Rate Limit Specifications

- **Per User Limits:**
  - Characters per hour: 5,000 (configurable via env)
  - Characters per day: 50,000 (configurable via env)
  - Characters per month: 500,000 (configurable via env)
- **Global Limits:**
  - Total characters per hour: 100,000
  - Total characters per day: 1,000,000

#### Technical Approach

1. **Storage:** Redis or database table for rate limit tracking
   - Key: `rate_limit:tts:{user_id}:{timeframe}`
   - Value: Character count consumed
   - TTL: Auto-expire based on timeframe

2. **Middleware Location:**
   - `backend/app/api/endpoints/tts.py` - Before calling `tts_service.generate_speech()`
   - Check limits → Increment counter → Call service OR return 429 error

3. **Database Schema (if using PostgreSQL):**

   ```sql
   CREATE TABLE user_tts_usage (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       characters_used INTEGER DEFAULT 0,
       period_start TIMESTAMP NOT NULL,
       period_end TIMESTAMP NOT NULL,
       period_type VARCHAR(10) CHECK (period_type IN ('hour', 'day', 'month')),
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW(),
       UNIQUE(user_id, period_start, period_type)
   );
   CREATE INDEX idx_user_tts_usage_lookup ON user_tts_usage(user_id, period_type, period_end);
   ```

4. **Response Handling:**
   - Return `429 Too Many Requests` when limit exceeded
   - Include headers:
     ```
     X-RateLimit-Limit: 5000
     X-RateLimit-Remaining: 0
     X-RateLimit-Reset: 1735689600
     ```
   - Fallback to text-only mode (disable TTS) when rate limited

#### Affected Files

- `backend/app/api/endpoints/tts.py` - Add rate limit check
- `backend/app/services/tts/tts_service.py` - Track character count
- `backend/app/utils/rate_limiter.py` - **NEW FILE** - Rate limit logic
- `frontend-next/src/lib/services/aiService.ts` - Handle 429 errors
- `frontend-next/src/components/sections/InterviewSection.tsx` - Display rate limit message

---

## 2. AI Chat System Rate Limiting

### Current State

- ✅ DeepSeek integration for interview orchestration
- ✅ Interview engine with context management
- ❌ **No per-user rate limiting**

### Rationale

- DeepSeek API has token limits and costs per request
- Prevent spam/abuse of chat functionality
- Ensure fair resource distribution
- Control API costs

### Implementation Requirements

#### Rate Limit Specifications

- **Per User Limits:**
  - Requests per minute: 10
  - Requests per hour: 100
  - Requests per day: 500
  - Tokens per day: 100,000 (configurable via env)
- **Global Limits:**
  - Requests per minute: 200
  - Requests per hour: 5,000

#### Technical Approach

1. **Storage:** Redis preferred (fast, built-in TTL)
   - Key: `rate_limit:chat:{user_id}:{timeframe}`
   - Value: Request count or token count
   - TTL: Auto-expire based on timeframe

2. **Middleware Location:**
   - `backend/app/api/endpoints/sessions.py` - `send_message` endpoint
   - `backend/app/api/endpoints/chat.py` - Chat endpoint (if exists)
   - Check limits → Increment counter → Call LLM OR return 429 error

3. **Token Tracking:**
   - Track both request count AND token usage
   - Store tokens used from LLM response metadata
   - Separate limits for interview vs casual chat

4. **Response Handling:**
   - Return `429 Too Many Requests` when limit exceeded
   - Include rate limit headers
   - Display user-friendly message: "You've reached your message limit. Please try again in X minutes."

#### Affected Files

- `backend/app/api/endpoints/sessions.py` - Add rate limit check to `send_message`
- `backend/app/services/interview_engine.py` - Track token usage
- `backend/app/utils/rate_limiter.py` - **NEW FILE** - Shared rate limit logic
- `frontend-next/src/lib/services/sessionService.ts` - Handle 429 errors
- `frontend-next/src/components/sections/InterviewSection.tsx` - Display rate limit UI
- `frontend-next/src/components/sections/ChatSection.tsx` - Display rate limit UI

---

## 3. Shared Rate Limiter Implementation

### Recommended Architecture

#### Option A: Redis-Based (Recommended)

**Pros:**

- Fast in-memory operations
- Built-in TTL/expiration
- Atomic increment operations
- Industry standard for rate limiting

**Cons:**

- Additional infrastructure dependency
- Need Redis setup in production

**Implementation:**

```python
# backend/app/utils/rate_limiter.py
from typing import Optional, Tuple
import redis
from datetime import datetime, timedelta
from app.core.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

class RateLimiter:
    @staticmethod
    async def check_and_increment(
        user_id: int,
        limit_type: str,  # "tts" or "chat"
        timeframe: str,   # "minute", "hour", "day", "month"
        max_count: int,
        increment_by: int = 1
    ) -> Tuple[bool, int, int]:
        """
        Returns: (allowed, current_count, limit)
        """
        key = f"rate_limit:{limit_type}:{user_id}:{timeframe}"

        # Get current count
        current = redis_client.get(key)
        current_count = int(current) if current else 0

        # Check if limit exceeded
        if current_count + increment_by > max_count:
            return False, current_count, max_count

        # Increment and set TTL
        pipe = redis_client.pipeline()
        pipe.incrby(key, increment_by)
        if current_count == 0:  # First request in period
            ttl = _get_ttl_seconds(timeframe)
            pipe.expire(key, ttl)
        pipe.execute()

        return True, current_count + increment_by, max_count
```

#### Option B: Database-Based

**Pros:**

- No additional infrastructure
- Persistent tracking
- Can query usage analytics

**Cons:**

- Slower than Redis
- More complex cleanup logic
- Higher database load

---

## 4. Environment Variables

Add to `.env` and `.env.example`:

```bash
# Rate Limiting - ElevenLabs TTS
RATE_LIMIT_TTS_CHARS_PER_HOUR=5000
RATE_LIMIT_TTS_CHARS_PER_DAY=50000
RATE_LIMIT_TTS_CHARS_PER_MONTH=500000
RATE_LIMIT_TTS_GLOBAL_CHARS_PER_HOUR=100000

# Rate Limiting - AI Chat
RATE_LIMIT_CHAT_REQUESTS_PER_MINUTE=10
RATE_LIMIT_CHAT_REQUESTS_PER_HOUR=100
RATE_LIMIT_CHAT_REQUESTS_PER_DAY=500
RATE_LIMIT_CHAT_TOKENS_PER_DAY=100000
RATE_LIMIT_CHAT_GLOBAL_REQUESTS_PER_MINUTE=200

# Redis Configuration (for rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

---

## 5. Frontend UX Considerations

### User Feedback

When rate limited, display clear messages:

**TTS Rate Limit:**

```
"Voice synthesis limit reached. You've used 5,000 characters this hour.
Resets in 23 minutes. Text responses will continue."
```

**Chat Rate Limit:**

```
"Message limit reached. You've sent 10 messages this minute.
Please wait 30 seconds before sending another message."
```

### Graceful Degradation

- **TTS:** Automatically fall back to text-only mode
- **Chat:** Queue messages locally, send when limit resets
- Display countdown timer for limit reset
- Show usage indicators (e.g., "8/10 messages used this minute")

---

## 6. Implementation Checklist

### Phase 1: Infrastructure Setup

- [ ] Set up Redis (local + production)
- [ ] Add Redis connection to backend
- [ ] Create `rate_limiter.py` utility module
- [ ] Add rate limit environment variables
- [ ] Create database migration for usage tracking (if not using Redis)

### Phase 2: Backend Implementation

- [ ] Implement TTS rate limiting in `/tts/generate` endpoint
- [ ] Implement chat rate limiting in `/sessions/send-message` endpoint
- [ ] Add rate limit response headers
- [ ] Log rate limit violations for monitoring
- [ ] Add admin endpoint to view/reset user limits

### Phase 3: Frontend Implementation

- [ ] Handle 429 errors in `aiService.ts`
- [ ] Display rate limit messages in `InterviewSection.tsx`
- [ ] Display rate limit messages in `ChatSection.tsx`
- [ ] Add usage indicators in UI
- [ ] Add countdown timer for limit reset
- [ ] Implement graceful TTS fallback

### Phase 4: Testing

- [ ] Unit tests for rate limiter logic
- [ ] Integration tests for TTS rate limiting
- [ ] Integration tests for chat rate limiting
- [ ] Load testing to verify limits work under pressure
- [ ] Test Redis failure scenarios (fallback behavior)

### Phase 5: Monitoring

- [ ] Add metrics for rate limit hits
- [ ] Dashboard for usage analytics
- [ ] Alerts for unusual rate limit patterns
- [ ] Adjust limits based on production usage data

---

## 7. Monitoring & Analytics

### Metrics to Track

- Rate limit hits per user (hourly/daily)
- Most rate-limited users (potential abuse)
- Average usage per user (optimize limits)
- API cost savings from rate limiting
- User complaints about rate limits (too strict?)

### Logging

Log every rate limit violation:

```python
logger.warning(
    f"Rate limit exceeded for user {user_id}: "
    f"type={limit_type}, timeframe={timeframe}, "
    f"current={current_count}, limit={max_count}"
)
```

---

## 8. Future Enhancements

### Tiered Rate Limits

- Free tier: Lower limits
- Pro tier: Higher limits
- Enterprise: Custom limits

### Dynamic Rate Limiting

- Adjust limits based on time of day
- Increase limits during low-traffic periods
- Decrease during high-traffic periods

### Smart Rate Limiting

- Whitelist power users
- Temporary limit increases for special events
- Adaptive limits based on user behavior patterns

---

## Notes

- Consider using a library like `slowapi` or `fastapi-limiter` for FastAPI
- Test rate limiting thoroughly in staging before production
- Document limits clearly in user-facing documentation
- Add rate limit info to API response even when NOT limited (show remaining quota)
- Consider caching interviewer voice responses to reduce TTS API calls

---

## References

- ElevenLabs pricing: https://elevenlabs.io/pricing
- DeepSeek API limits: [Insert URL when available]
- FastAPI rate limiting: https://github.com/laurentS/slowapi
- Redis rate limiting patterns: https://redis.io/docs/manual/patterns/rate-limiter/
