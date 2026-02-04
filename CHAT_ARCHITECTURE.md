# Chat History Integration - Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ChatSection.tsx                                                         │
│  ├─ useState(threads, activeId, input, isLoading)                      │
│  ├─ useEffect → load threads from DB on mount                          │
│  ├─ handleSend → save messages to DB → call AI → save response         │
│  ├─ handleNewChat → create thread in DB                                │
│  └─ handleDeleteChat → delete thread from DB                           │
│                              ↓                                           │
│  chatService.ts                                                          │
│  ├─ createThread(title, messages) → POST /chat-threads                │
│  ├─ listThreads(limit, offset) → GET /chat-threads?limit=...         │
│  ├─ getThread(id) → GET /chat-threads/{id}                           │
│  ├─ updateThread(id, updates) → PUT /chat-threads/{id}               │
│  └─ deleteThread(id) → DELETE /chat-threads/{id}                     │
│                              ↓                                           │
│  apiClient.ts (Axios wrapper)                                           │
│  ├─ Auto-attaches Authorization: Bearer {token}                        │
│  ├─ Handles 401 redirects to /login                                    │
│  └─ Formats error responses                                            │
│                              ↓                                           │
│  HTTP (JSON over REST)                                                  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                          HTTP Requests
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  API Router (/api/v1)                                                    │
│  └─ chat_threads.py                                                      │
│     ├─ @router.post("") → create_chat_thread()                          │
│     ├─ @router.get("") → list_chat_threads()                           │
│     ├─ @router.get("/{id}") → get_chat_thread()                        │
│     ├─ @router.put("/{id}") → update_chat_thread()                     │
│     └─ @router.delete("/{id}") → delete_chat_thread()                  │
│        (All require: Depends(get_current_user), Depends(get_db))       │
│                              ↓                                           │
│  CRUD Layer (crud/chat_thread.py)                                       │
│  ├─ create_chat_thread(db, user_id, create_request)                    │
│  ├─ list_chat_threads(db, user_id, limit, offset)                      │
│  ├─ get_chat_thread(db, thread_id, user_id)  ← Enforces ownership      │
│  ├─ update_chat_thread(db, thread_id, user_id, update_request)         │
│  └─ delete_chat_thread(db, thread_id, user_id)                         │
│                              ↓                                           │
│  Database Layer (SQLAlchemy ORM)                                        │
│  └─ ChatThread model                                                     │
│     ├─ Validates user_id ownership                                      │
│     ├─ Manages JSON messages column                                     │
│     └─ Maintains timestamps (created_at, updated_at)                   │
│                              ↓                                           │
└─────────────────────────────────────────────────────────────────────────┘
                    PostgreSQL Connection
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  chat_threads TABLE                                                      │
│  ┌────────────┬───────────┬─────────┬──────────┬───────────┬────────────┐
│  │ id (PK)    │ user_id   │ title   │ messages │ created   │ updated    │
│  │            │ (FK, IDX) │ (str)   │ (JSON)   │ _at       │ _at        │
│  ├────────────┼───────────┼─────────┼──────────┼───────────┼────────────┤
│  │ 1          │ 42        │ "How..  │ [{...}]  │ 2026-02.. │ 2026-02..  │
│  │ 2          │ 42        │ "Syst.  │ [{...}]  │ 2026-02.. │ 2026-02..  │
│  │ 3          │ 7         │ "New..  │ [{...}]  │ 2026-02.. │ 2026-02..  │
│  └────────────┴───────────┴─────────┴──────────┴───────────┴────────────┘
│                                                                           │
│  INDEX: ix_chat_threads_user_id                                         │
│  └─ Fast lookup: SELECT * FROM chat_threads WHERE user_id = ?          │
│                                                                           │
│  Sample message JSON:                                                    │
│  [                                                                       │
│    {                                                                     │
│      "role": "user",                                                     │
│      "content": "How do I prepare for system design?"                   │
│    },                                                                    │
│    {                                                                     │
│      "role": "assistant",                                               │
│      "content": "Here's a roadmap..."                                   │
│    }                                                                     │
│  ]                                                                       │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### 1. Loading Chats on App Start

```
User opens chat app
    ↓
ChatSection useEffect triggers
    ↓
chatService.listThreads()
    ↓
GET /api/v1/chat-threads?limit=50&offset=0
    ↓
Backend: get_current_user validates token
    ↓
Backend: list_chat_threads(db, current_user.id, 50, 0)
    ↓
SQL: SELECT * FROM chat_threads WHERE user_id = 42 ORDER BY updated_at DESC LIMIT 50 OFFSET 0
    ↓
Returns: [ChatThreadSummary{id, title, message_count, updated_at}, ...]
    ↓
Frontend: Load first thread details immediately
    ↓
Frontend: Lazy-load remaining threads in background
    ↓
UI: Display in sidebar, select first active thread
```

### 2. User Sends Message

```
User types message and clicks Send
    ↓
handleSend event triggers
    ↓
1. Create ChatMessage: {role: "user", content: "..."}
    ↓
2. Add to local state: messages = [...messages, newMessage]
    ↓
3. Call chatService.updateThread(activeThread.id, {messages})
    ↓
   PUT /api/v1/chat-threads/123
   Body: {"messages": [existing..., {role: "user", content: "..."}]}
    ↓
   Backend: update_chat_thread(db, 123, user_id=42, ...)
    ↓
   SQL: UPDATE chat_threads SET messages=..., updated_at=now()
        WHERE id=123 AND user_id=42
    ↓
4. Call aiService.chat({message, history})
    ↓
   POST /api/v1/ai/chat
   Body: {"message": "...", "history": [{...}, ...]}
    ↓
   Backend calls LLM, returns reply
    ↓
   Returns: ChatResponse{reply: "Here's my response...", mode: "live"}
    ↓
5. Create assistantMessage: {role: "assistant", content: reply}
    ↓
6. Call chatService.updateThread(activeThread.id, {messages, title})
    ↓
   PUT /api/v1/chat-threads/123
   Body: {"messages": [..., assistant], "title": "How do I..."}
    ↓
   Backend updates DB with new title
    ↓
7. Update local state with response
    ↓
UI refreshes with new messages
```

### 3. User Deletes a Thread

```
User clicks trash icon on thread
    ↓
handleDeleteChat(thread.id) triggers
    ↓
chatService.deleteThread(123)
    ↓
DELETE /api/v1/chat-threads/123
    ↓
Backend: delete_chat_thread(db, 123, user_id=42)
    ↓
SQL: DELETE FROM chat_threads WHERE id=123 AND user_id=42
    ↓
Return: {message: "Chat thread deleted successfully."}
    ↓
Frontend: Remove from threads state
    ↓
If active thread was deleted:
  - Switch to next thread in sidebar
  - OR create new blank thread if none remain
    ↓
UI: Sidebar updates, chat area clears or shows new thread
```

### 4. User Creates New Chat

```
User clicks "New chat" button
    ↓
handleNewChat() triggers
    ↓
chatService.createThread("New Chat", [])
    ↓
POST /api/v1/chat-threads
Body: {"title": "New Chat", "messages": []}
    ↓
Backend: create_chat_thread(db, user_id=42, ...)
    ↓
SQL: INSERT INTO chat_threads (user_id, title, messages, created_at, updated_at)
     VALUES (42, "New Chat", '[]', now(), now())
    ↓
Returns: ChatThread{id: 456, user_id: 42, title: "New Chat", ...}
    ↓
Frontend: Add to threads state
    ↓
Frontend: Set activeId = 456
    ↓
UI: New thread appears in sidebar, chat area is empty
```

## Security Model

```
┌─ Every endpoint requires authenticated user
│
├─ get_current_user(Depends(...))
│  └─ Extracts JWT token from Authorization header
│  └─ Validates token signature
│  └─ Returns User object with id
│
├─ Every CRUD operation includes user_id validation
│  └─ Thread must belong to authenticated user
│  └─ Prevents cross-user access
│
└─ Example:
   GET /api/v1/chat-threads/999

   Unauthenticated request → 401 Unauthorized
   Wrong user's thread → 404 Not Found (prevents enumeration)
   Correct user → Return thread data
```

## Performance Optimization

```
Frontend Optimization:
├─ Load thread list immediately (lightweight summaries)
├─ Load first thread details immediately (most likely needed)
└─ Load remaining threads lazily (background)

Backend Optimization:
├─ Index on (user_id) for fast WHERE user_id = ?
├─ Order by updated_at DESC for recency
└─ Pagination with LIMIT/OFFSET for scalability

Database Optimization:
├─ Partial indexes on active user IDs only
├─ Archive old threads to separate table if needed
└─ JSON column stays compact (no normalization needed)

Network Optimization:
├─ Summarize threads in list (no full messages)
├─ Load full details on-demand
├─ Cache in component state during session
└─ Batch updates (user + assistant in one PUT)
```

## Error Handling Flow

```
Frontend Error Scenarios:
│
├─ 401 Unauthorized (Token expired)
│  └─ Clear localStorage.access_token
│  └─ Redirect to /login
│
├─ 403 Forbidden (Accessing other user's thread)
│  └─ Log error, show generic "Not Found"
│
├─ 404 Not Found (Thread deleted by admin)
│  └─ Remove from local state
│  └─ Switch to another thread
│
├─ 422 Unprocessable (Invalid data)
│  └─ Display error message to user
│  └─ Don't retry automatically
│
├─ Network Error (Backend offline)
│  └─ Show "Offline" state
│  └─ Display cached data if available
│
└─ 500 Server Error
   └─ Log error
   └─ Show "Try again" message
```

## Database Query Examples

```sql
-- List threads for user (in recency order)
SELECT id, title, JSON_ARRAY_LENGTH(messages) as message_count, updated_at
FROM chat_threads
WHERE user_id = $1
ORDER BY updated_at DESC
LIMIT $2 OFFSET $3

-- Get full thread
SELECT * FROM chat_threads
WHERE id = $1 AND user_id = $2

-- Add message to existing thread
UPDATE chat_threads
SET messages = JSONB_CONCAT(messages, '[{"role":"...", "content":"..."}]'),
    updated_at = now()
WHERE id = $1 AND user_id = $2

-- Count threads per user
SELECT user_id, COUNT(*) as thread_count
FROM chat_threads
GROUP BY user_id

-- Find threads with specific keywords
SELECT * FROM chat_threads
WHERE user_id = $1
AND messages::text ILIKE '%keyword%'
```

## Type Flow

```
Frontend ChatMessage
  ↓
  {role: 'user' | 'assistant', content: string}
  ↓
  Serialized to JSON
  ↓
Backend ChatMessageSchema
  ↓
  Validated by Pydantic
  ↓
  Converted to dict
  ↓
  Stored in PostgreSQL JSON column
  ↓
  Retrieved from DB (as list)
  ↓
  Returned in ChatThreadOut response
  ↓
Frontend ChatThread
  ↓
  messages: ChatMessage[]
  ↓
  Displayed in UI
```
