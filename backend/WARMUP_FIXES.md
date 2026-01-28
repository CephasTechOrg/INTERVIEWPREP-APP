# Warmup Conversation Fixes

## Issues Fixed

### 1. **Reciprocal Questions Not Acknowledged**
**Problem:**
```
AI: "How is your day going?"
User: "Great! How is your day going?"
AI: "Great to hear. What has been the highlight of your day?" ❌ (ignores reciprocal question)
```

**Solution:**
Now detects reciprocal questions during warmup and responds naturally:
```
AI: "How is your day going?"
User: "Great! How is your day going?"
AI: "I'm doing well, thank you for asking! What's been keeping you busy lately?" ✅
```

### 2. **Context Ignored During Warmup**
**Problem:**
```
User: "I asked you how you are doing"
AI: "Great to hear. Let's dive in. Tell me about a time..." ❌ (doesn't acknowledge)
```

**Solution:**
Detects when user is continuing conversation:
```
User: "I asked you how you are doing"
AI: "I'm doing great, thanks for asking! Let's get started. Tell me about a time..." ✅
```

### 3. **Repeat Requests Not Working in Warmup**
**Problem:**
```
User: "repeat the question again"
AI: "Could you restate the problem and clarify any constraints?" ❌ (wrong context)
```

**Solution:**
Uses smart intent detection to recognize clarification requests:
```
User: "repeat the question again"
AI: "Of course! Here's the question again:\n\nTell me about a time you took ownership..." ✅
```

## Technical Changes

### 1. **Smart Intent Detection in Warmup**
Added AI-powered intent classification during all warmup stages:

```python
# Before: No intent detection in warmup
if stage == "warmup_behavioral":
    # Just move to next question

# After: Smart detection
if stage == "warmup_behavioral":
    intent = await self._classify_user_intent(text, context)
    if intent.intent == "clarification":
        # Repeat the question naturally
```

### 2. **Reciprocal Question Detection**
Added pattern matching for common reciprocal phrases:

```python
is_reciprocal = any(phrase in text.lower() for phrase in [
    "how are you", "how about you", "what about you",
    "how is your", "and you", "yourself", "asked you"
])

if is_reciprocal:
    response = "I'm doing well, thank you for asking! "
    # Continue conversation naturally
```

### 3. **Contextual Question Repetition**
Searches recent conversation history to find the actual question:

```python
# Find last behavioral/question from interviewer
msgs = message_crud.list_messages(db, session.id, limit=10)
for m in reversed(msgs):
    if m.role == "interviewer" and ("tell me about" in m.content.lower()):
        return f"Of course! Here's the question again:\n\n{m.content}"
```

## Flow Comparison

### Old Flow (Rigid)
```
1. AI: "Hi, how are you?"
2. User: "Great! How are you?"
3. AI: [Ignores] "What's been keeping you busy?" ❌
4. User: "I asked you how you are"
5. AI: [Ignores] "Let's dive in..." ❌
6. User: "repeat the question"
7. AI: [Generic] "Restate the problem..." ❌
```

### New Flow (Natural)
```
1. AI: "Hi, how are you?"
2. User: "Great! How are you?"
3. AI: "I'm doing well, thanks for asking! What's been keeping you busy?" ✅
4. User: "Work stuff. And you?"
5. AI: "I'm doing great, thanks! Let's get started. Tell me about..." ✅
6. User: "repeat that"
7. AI: "Of course! Tell me about a time you took ownership..." ✅
```

## Impact

- **More Human-Like**: AI responds to social cues naturally
- **Better Context**: Tracks conversation and responds appropriately
- **Clearer Communication**: Repeats questions when asked, even in warmup
- **Less Frustration**: Users don't feel ignored during casual conversation

## Testing

The system now logs intent classifications during warmup:
```
DEBUG: Intent classified: clarification (0.92 confidence) - User asking to repeat question
DEBUG: Reciprocal question detected during step 2
DEBUG: Natural response: "I'm doing well, thank you for asking!"
```
