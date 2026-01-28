# Smart Intent System - Overview

## What Changed

The interview engine now uses **AI-powered intent classification** instead of simple keyword matching. This makes it understand context like a human would.

## Before vs After

### Example 1: Clarification Requests

**User says:** "what?"

- **Old System**: Keyword match for "what" fails → treats as vague response → asks for more detail
- **New System**: AI understands from context → recognizes clarification request → **repeats question**

### Example 2: Thinking Out Loud

**User says:** "not sure but let me think... maybe a hash map?"

- **Old System**: Sees "not sure" → marks as "don't know" → **moves to next question**
- **New System**: AI sees full context → recognizes thinking process → **continues conversation**

### Example 3: Short Technical Answers

**User says:** "O(n) time"

- **Old System**: Only 2 words → flagged as vague → asks for more detail
- **New System**: AI recognizes technical content → **accepts as valid answer**

### Example 4: Contextual Questions

**User says:** "what was that again?"

- **Old System**: Might not match keyword "repeat" → treated as off-topic
- **New System**: AI understands intent → **repeats question**

## How It Works

```python
# 1. User sends message
user_message = "can you say that again?"

# 2. AI analyzes intent with context
intent = await _classify_user_intent(
    text=user_message,
    question_context="Question: Two Sum - Find two numbers..."
)

# 3. Returns structured classification
{
    "intent": "clarification",
    "confidence": 0.95,
    "reasoning": "User is asking to repeat the question"
}

# 4. System responds appropriately
→ Restates the question (doesn't penalize candidate)
```

## Intent Types

| Intent | Meaning | Response |
|--------|---------|----------|
| `clarification` | Asking to repeat/clarify question | Restate question without penalty |
| `answering` | Providing an answer/solution | Continue normal flow |
| `move_on` | Want to skip to next question | Move to next question |
| `dont_know` | Don't know the answer | Move to next question with encouragement |
| `thinking` | Thinking through the problem | Let them continue |
| `greeting` | Small talk/greeting | Respond naturally |

## Fallback Behavior

If the AI classification service is unavailable, the system falls back to keyword heuristics (the old way). This ensures the interview never breaks.

## Benefits

1. **More Human-Like**: Understands nuance and context
2. **Fewer False Positives**: Won't misinterpret technical jargon
3. **Better UX**: Candidates don't get frustrated by premature moves
4. **Flexible**: Handles varied phrasings ("repeat", "what?", "huh?", "clarify")

## Testing

The system logs intent classifications at DEBUG level:

```
Intent classified: clarification (0.95 confidence) - User is asking to repeat the question
```

Check logs during interviews to see the AI's reasoning.
