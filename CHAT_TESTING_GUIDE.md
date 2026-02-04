# Chat History Database - Testing Guide

## Quick Start Testing

### Prerequisites

- Backend running: `uvicorn backend.app.main:app --reload` (Port 8000)
- Frontend running: `npm run dev` in frontend-next (Port 3000)
- Database: PostgreSQL with migrations applied

### Test Scenario 1: Create and Save Chat

1. **Open the application** at http://localhost:3000
2. **Login** with test credentials
3. **Navigate to Chat** section (sidebar)
4. **Click "New chat"** button
5. **Type a message**: "Hello, how can I prepare for interviews?"
6. **Click Send**
7. **Expected result**:
   - ✅ Message appears immediately in chat
   - ✅ AI response loads and appears
   - ✅ Thread title auto-generated from first message
   - ✅ Thread appears in left sidebar
   - ✅ Chat history persists (reload page - still there!)

### Test Scenario 2: Multiple Chats

1. **In sidebar**, click "New chat"
2. **Send different message**: "What's a system design interview?"
3. **Verify**:
   - ✅ New thread created
   - ✅ Both threads in sidebar
   - ✅ Can switch between threads
   - ✅ Each thread keeps its own messages
   - ✅ Active thread highlighted in blue

### Test Scenario 3: Delete Chat

1. **In sidebar**, hover over any thread
2. **Click trash icon** on the right
3. **Expected result**:
   - ✅ Thread removed from sidebar immediately
   - ✅ If it was active, switches to another thread
   - ✅ If last thread, creates new blank thread
   - ✅ Cannot undo (deleted from database)

### Test Scenario 4: Cross-Device Persistence

1. **Complete Test Scenario 1** with 2-3 messages
2. **Note the thread title** in sidebar
3. **Open private browser** window or different browser
4. **Login** with same account
5. **Navigate to Chat**
6. **Expected result**:
   - ✅ Same thread appears in sidebar
   - ✅ All previous messages visible
   - ✅ Can continue conversation
   - ✅ Works perfectly

### Test Scenario 5: Reload Persistence

1. **Create a chat** with several messages
2. **Press F5** or Ctrl+R to reload page
3. **Expected result**:
   - ✅ Chat section loads
   - ✅ Shows "Loading chat..." briefly
   - ✅ All threads appear in sidebar
   - ✅ Chat messages still there
   - ✅ Can send more messages

### Test Scenario 6: Loading States

1. **Open chat section**
2. **Observe initial load**:
   - ✅ Sidebar shows "Loading chats..."
   - ✅ After ~500ms, threads appear
   - ✅ Can't click "New chat" during load
   - ✅ Textarea is disabled during load

3. **While AI is responding**:
   - ✅ "Typing..." indicator appears
   - ✅ Send button shows "Sending..."
   - ✅ Can't send another message
   - ✅ Input disabled until response arrives

## API Testing (Using cURL or Postman)

### 1. Get Auth Token

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Response:

```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer"
}
```

### 2. Create Chat Thread

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat-threads \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "System Design Prep",
    "messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi there!"}
    ]
  }'
```

### 3. List All Threads

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/chat-threads?limit=10&offset=0" \
  -H "Authorization: Bearer {token}"
```

Expected:

```json
[
  {
    "id": 1,
    "title": "System Design Prep",
    "message_count": 2,
    "updated_at": "2026-02-02T10:30:00"
  }
]
```

### 4. Get Specific Thread

```bash
curl -X GET http://127.0.0.1:8000/api/v1/chat-threads/1 \
  -H "Authorization: Bearer {token}"
```

### 5. Update Thread

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/chat-threads/1 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi there!"},
      {"role": "user", "content": "Tell me more"}
    ]
  }'
```

### 6. Delete Thread

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/chat-threads/1 \
  -H "Authorization: Bearer {token}"
```

## Browser DevTools Testing

### Network Tab

1. **Open DevTools** (F12) → Network tab
2. **Send a message** in chat
3. **Observe requests**:
   - ✅ `PUT /api/v1/chat-threads/{id}` - Save user message (status 200)
   - ✅ `POST /api/v1/ai/chat` - Get AI response (status 200)
   - ✅ `PUT /api/v1/chat-threads/{id}` - Save AI response (status 200)
4. **Check request/response bodies** are valid JSON
5. **Verify latency** is reasonable (<500ms per request)

### Application Tab (Storage)

1. **Open DevTools** → Application → Storage
2. **Check localStorage**:
   - ✅ `access_token` should be set
   - ✅ NO `ai-chat-history` key (old code removed!)
   - ✅ NO `chat_threads` key
3. **Verify no old chat data** hanging around

### Console Tab

1. **Open DevTools** → Console
2. **Send a message**
3. **Expected logs**:
   - No errors (red)
   - No TypeScript warnings (orange)
   - May see API success/error messages if added

## Error Testing

### Test: Unauthorized Access (Invalid Token)

1. **Manually set invalid token** in localStorage:

   ```javascript
   localStorage.setItem("access_token", "invalid.token.here");
   ```

2. **Reload page and try to send message**

3. **Expected result**:
   - ✅ Network error shown
   - ✅ Redirected to /login
   - ✅ Token cleared from localStorage

### Test: Accessing Other User's Thread

1. **Get your thread ID** from URL or API
2. **Manually call API** with that ID but different token
3. **Expected result**:
   - ✅ Returns 404 (not 403, prevents enumeration)
   - ✅ User never sees other user's data

### Test: Deleted Thread

1. **Get a thread ID**: e.g., 999
2. **Delete it** via UI
3. **Try to send message** in that thread
4. **Expected result**:
   - ✅ Chat section automatically switches thread
   - ✅ No error shown to user
   - ✅ Clean UX

## Performance Testing

### Measure Load Time

1. **Open DevTools** → Performance tab
2. **Record page load** and chat section load
3. **Expected**:
   - ✅ Page ready: <2 seconds
   - ✅ Chat threads load: <500ms
   - ✅ First thread display: <1 second

### Database Query Performance

1. **Connect to PostgreSQL**:

   ```bash
   psql postgresql://user:password@localhost/interview_prep
   ```

2. **Check table size**:

   ```sql
   SELECT pg_size_pretty(pg_total_relation_size('chat_threads'));
   ```

3. **Check index usage**:

   ```sql
   SELECT * FROM pg_stat_user_indexes WHERE relname='chat_threads';
   ```

4. **Check query plans**:
   ```sql
   EXPLAIN SELECT * FROM chat_threads WHERE user_id = 42 ORDER BY updated_at DESC LIMIT 50;
   ```

## Edge Cases

### Case 1: Network Interrupted During Send

1. **Start sending message**
2. **Disconnect network** before response
3. **Expected behavior**:
   - ✅ Message saves to DB (user message)
   - ✅ AI call fails gracefully
   - ✅ User sees error in console
   - ✅ No crash, can retry

### Case 2: Multiple Tabs Open

1. **Open chat in two browser tabs**
2. **Send message in Tab A**
3. **Check Tab B**:
   - ✅ Tab A shows new message immediately
   - ✅ Tab B doesn't auto-update (expected)
   - ✅ Reload Tab B to see new message
   - Note: Could add WebSocket for real-time sync (future feature)

### Case 3: Very Long Conversation

1. **Send 50+ messages** to same thread
2. **Expected**:
   - ✅ Chat still scrolls smoothly
   - ✅ No lag when scrolling
   - ✅ All messages persist
   - ✅ Can scroll to top and see first message

### Case 4: Special Characters

1. **Send message with**:
   - Emojis: "🚀 System design 🎯"
   - Quotes: `"quoted text"`
   - JSON: `{"key": "value"}`
   - HTML: `<script>alert('xss')</script>`

2. **Expected**:
   - ✅ All stored correctly in DB
   - ✅ All displayed correctly in UI
   - ✅ No HTML injection
   - ✅ Emojis display properly

## Checklist Before Deployment

- [ ] All tests pass locally
- [ ] No console errors
- [ ] Network requests all return 200-201
- [ ] Chat history persists across page reloads
- [ ] Chat history available on different devices
- [ ] Delete button works
- [ ] Loading states display correctly
- [ ] Error handling works gracefully
- [ ] Performance acceptable
- [ ] No localStorage keys for chat data
- [ ] Database migrations applied
- [ ] Backend running without errors
- [ ] Frontend TypeScript compiles (0 errors)
- [ ] Auth token validation working

## Deployment Verification

After deploying to production:

1. **Verify database migration** applied on production DB
2. **Check new endpoints** respond at production URLs
3. **Test with production domain** (not localhost)
4. **Verify CORS headers** allow frontend domain
5. **Monitor logs** for errors during first 24 hours
6. **Ask users to test** new chat feature
7. **Collect feedback** and iterate

## Rollback Plan

If issues found in production:

1. **Frontend**: Deploy old version from git tag
2. **Backend**:
   - Keep new tables (don't rollback migration)
   - Switch to old API endpoints
   - Chat data remains in DB for recovery
3. **After fixing**:
   - Test thoroughly in staging
   - Deploy again with fixes
