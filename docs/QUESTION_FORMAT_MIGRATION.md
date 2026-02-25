# Question JSON Format Migration Guide

## Overview

We've enhanced the question JSON structure to include two new fields:

- `expected_topics`: Topics the candidate's answer should cover
- `evaluation_focus`: What aspects to evaluate (e.g., complexity, edge_cases, clarity)

## New JSON Structure

```json
{
  "track": "swe_intern",
  "company_style": "general",
  "difficulty": "easy",
  "questions": [
    {
      "title": "Two Sum",
      "prompt": "Given an array of integers nums and an integer target...",
      "question_type": "coding",
      "tags": ["arrays", "hashmap"],
      "followups": [
        "What is the time complexity?",
        "What edge cases should we consider?"
      ],
      "expected_topics": ["hash map usage", "O(n) time", "O(n) space"],
      "evaluation_focus": ["complexity", "edge_cases"]
    }
  ]
}
```

## Field Definitions

### `expected_topics` (array of strings)

Topics the candidate should mention in their answer. Examples:

- **Coding questions**: `["hash map usage", "O(n) time complexity", "edge case handling"]`
- **Conceptual questions**: `["clear definition", "practical examples", "use cases"]`
- **System design**: `["architecture", "data flow", "scaling strategy", "bottlenecks"]`
- **Behavioral**: `["situation", "task", "action", "result"]` (STAR format)

### `evaluation_focus` (array of strings)

What to evaluate in the answer. Common values:

- **Coding**: `["complexity", "edge_cases"]`
- **Conceptual**: `["clarity", "depth"]`
- **System design**: `["scalability", "trade_offs", "components"]`
- **Behavioral**: `["star_format", "impact"]`

## Migration Steps

### 1. Database Migration (Already Done ✅)

The database has been updated with two new columns:

- `expected_topics` (JSON array)
- `evaluation_focus` (JSON array)

Migration file: `alembic/versions/2e847a45e9b6_add_expected_topics_evaluation_focus_to_.py`

### 2. Update JSON Files

**Option A: Automatic Migration (Recommended)**

Run the migration script to automatically add these fields to all question files:

```bash
# Preview changes without modifying files
python scripts/migrate_question_format.py --dry-run

# Apply changes to all JSON files
python scripts/migrate_question_format.py
```

The script will:

- Add `expected_topics` and `evaluation_focus` to all questions
- Intelligently infer values based on `question_type` and `tags`
- Preserve existing data and formatting

**Option B: Manual Migration**

Edit each JSON file to add the new fields. Example:

```json
{
  "title": "Two Sum",
  "prompt": "...",
  "question_type": "coding",
  "tags": ["arrays", "hashmap"],
  "followups": ["What is the time complexity?"],
  "expected_topics": ["hash map", "O(n) time", "O(n) space"],
  "evaluation_focus": ["complexity", "edge_cases"]
}
```

### 3. Re-seed the Database

After updating JSON files, re-seed the database:

```bash
cd backend
python seed.py --questions
```

This will upsert all questions with the new fields.

## Question Type Guidelines

### Coding Questions

```json
{
  "question_type": "coding",
  "expected_topics": ["hash map", "O(n) time", "edge cases"],
  "evaluation_focus": ["complexity", "edge_cases"]
}
```

### Conceptual Questions

```json
{
  "question_type": "conceptual",
  "expected_topics": ["clear definition", "examples", "use cases"],
  "evaluation_focus": ["clarity", "depth"]
}
```

### System Design Questions

```json
{
  "question_type": "system_design",
  "expected_topics": ["architecture", "data flow", "scaling strategy"],
  "evaluation_focus": ["scalability", "trade_offs", "components"]
}
```

### Behavioral Questions

```json
{
  "question_type": "behavioral",
  "expected_topics": ["situation", "task", "action", "result"],
  "evaluation_focus": ["star_format", "impact"]
}
```

## Benefits

1. **Better Evaluation**: The AI interviewer can check if candidates cover expected topics
2. **Consistent Grading**: Evaluation focuses on specific aspects (complexity, edge cases, etc.)
3. **Flexible Prompts**: Follow-up questions can reference expected topics
4. **Type Safety**: Explicit fields are clearer than inferring from tags

## Backward Compatibility

- Old questions without these fields will have empty arrays `[]`
- The seed script handles both old and new formats
- Existing functionality is not affected

## Next Steps

1. ✅ Database migration complete
2. ✅ Seed script updated
3. ⏳ Run migration script: `python scripts/migrate_question_format.py`
4. ⏳ Re-seed database: `python seed.py --questions`
5. ⏳ Test with a few questions to verify

## Example Migration Output

```bash
$ python scripts/migrate_question_format.py

🔍 Scanning data/questions for JSON files...
📁 Found 49 JSON files

✅ Migrated data/questions/swe_intern/general/easy.json
✅ Migrated data/questions/swe_intern/general/medium.json
✅ Migrated data/questions/swe_intern/general/hard.json
...

============================================================
📊 Migration Summary:
   Modified: 49
   Skipped:  0
   Errors:   0
============================================================

✨ Migration complete! You can now re-seed the database:
   cd backend
   python seed.py --questions
```
