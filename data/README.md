# Question Dataset Structure

Keep questions organized by role -> company -> difficulty so it stays clear and extensible:

```
data/questions/
  behavioral/
    general/
      easy.json
  swe_intern/
    general/
      easy.json
      medium.json
      hard.json
    amazon/
      easy.json
      medium.json
      hard.json
    apple/
      easy.json
      medium.json
      hard.json
    google/
      easy.json
      medium.json
      hard.json
    microsoft/
      easy.json
      medium.json
      hard.json
    meta/
      easy.json
      medium.json
      hard.json
  swe_engineer/
    general/
      easy.json
      medium.json
      hard.json
```

Each file should contain:
```
{
  "track": "behavioral" | "swe_intern" | "swe_engineer",
  "company_style": "general" | "amazon" | "apple" | "google" | "microsoft" | "meta",
  "difficulty": "easy" | "medium" | "hard",
  "questions": [
    {
      "title": "...",
      "prompt": "...",
      "tags": ["..."],
      "followups": ["...", "..."]
    }
  ]
}
```

Use explicit, consistent names--no vague labels. This keeps future additions unambiguous and easy to validate.

Loader notes:
- The backend loader walks `data/questions` recursively and expects the directory path to match the JSON metadata (track/company/difficulty). Files that don't match their path hints are skipped.
- Keep one JSON per difficulty per company for clarity; multiple files per difficulty are allowed but must match their path and metadata.
- Behavioral questions should include the "behavioral" tag so the interview engine can route them correctly.
- Behavioral questions can live under the main track/company folders (for company-specific behavioral prompts) as long as the tag is present.
