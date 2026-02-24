"""
Interview Engine Utilities Module

Extracted utility methods for text processing, data validation, clamping,
and other helper functions used throughout the interview engine.

These methods are stateless and have no dependencies on complex interview logic.
"""

import re
from typing import Any

from app.models.interview_session import InterviewSession
from app.models.question import Question


class InterviewEngineUtils:
    """Utility methods for text processing, validation, and data normalization."""

    _RUBRIC_KEYS: tuple[str, ...] = (
        "communication",
        "problem_solving",
        "correctness_reasoning",
        "complexity",
        "edge_cases",
    )
    _SYSTEM_DESIGN_TAGS: set[str] = {
        "system-design",
        "distributed-systems",
        "system-thinking",
        "scalability",
        "reliability",
        "architecture",
        "observability",
        "databases",
        "api",
    }
    _CONCEPTUAL_TAGS: set[str] = {"fundamentals", "concepts", "oop"}

    def _clamp_int(self, value: Any, default: int, lo: int, hi: int) -> int:
        """Clamp integer value to range [lo, hi]."""
        try:
            n = int(value)
        except Exception:
            n = int(default)
        return max(lo, min(hi, n))

    def _coerce_quick_rubric(self, raw: Any) -> dict:
        """Convert raw data to rubric dict with clamped values."""
        raw_dict = raw if isinstance(raw, dict) else {}
        return {k: self._clamp_int(raw_dict.get(k), default=5, lo=0, hi=10) for k in self._RUBRIC_KEYS}

    def _user_name_safe(self, name: str | None) -> str:
        """Safely extract and clean user name."""
        if not name:
            return ""
        return name.strip()

    def _company_name(self, company_style: str) -> str:
        """Convert company style to display name."""
        if not company_style or company_style == "general":
            return "this company"
        return company_style[:1].upper() + company_style[1:]

    def _effective_difficulty(self, session: InterviewSession) -> str:
        """Get effective difficulty level from session."""
        selected = (getattr(session, "difficulty", None) or "easy").strip().lower()
        current = (getattr(session, "difficulty_current", None) or "").strip().lower()
        if selected in ("easy", "medium", "hard"):
            return selected
        if current in ("easy", "medium", "hard"):
            return current
        return "easy"

    def _render_text(self, session: InterviewSession, text: str) -> str:
        """Replace company placeholders in text."""
        company = self._company_name(session.company_style)
        return (text or "").replace("{company}", company).replace("X company", company).replace("X Company", company)

    def _render_question(self, session: InterviewSession, q: Question) -> tuple[str, str]:
        """Render question title and prompt with company substitution."""
        return self._render_text(session, q.title), self._render_text(session, q.prompt)

    def _normalize_text(self, text: str | None) -> str:
        """Normalize text: lowercase and collapse whitespace."""
        return " ".join((text or "").lower().split())

    def _clean_tokens(self, text: str | None) -> list[str]:
        """Extract clean tokens from text."""
        raw = (text or "").lower().replace("```", " ")
        tokens = [re.sub(r"[^a-z0-9']+", "", w) for w in raw.split()]
        return [t for t in tokens if t]

    def _keyword_tokens(self, text: str | None) -> set[str]:
        """Extract significant keyword tokens (excluding stop words)."""
        stop = {
            "the", "a", "an", "and", "or", "to", "of", "for", "in", "on",
            "with", "without", "is", "are", "was", "were", "be", "been",
            "it", "this", "that", "as", "by", "from", "at", "you", "your",
            "i", "we", "they", "he", "she", "them", "our", "their",
            "can", "could", "should", "would", "about", "into", "over",
            "under", "than", "then", "if", "else", "when", "while",
        }
        tokens = self._clean_tokens(text)
        return {t for t in tokens if len(t) > 2 and t not in stop}

    def _overlap_ratio(self, base: set[str], text: str | None) -> float:
        """Calculate keyword overlap ratio between base set and text."""
        if not base:
            return 0.0
        other = self._keyword_tokens(text)
        if not other:
            return 0.0
        return len(base & other) / float(len(base))

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        """Check if text contains any of the keywords."""
        return any(k in text for k in keywords)

    def _has_code_block(self, text: str | None) -> bool:
        """Detect if text contains code blocks."""
        raw = text or ""
        if "```" in raw:
            return True
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "function ", "public ", "private ")):
                return True
            if stripped.startswith(("for ", "while ", "if ", "else ", "elif ")):
                return True
            if stripped.endswith(";") and ("=" in stripped or "return" in stripped):
                return True
        return False

    def _mentions_complexity(self, text: str | None) -> bool:
        """Check if text mentions complexity."""
        t = self._normalize_text(text)
        return "o(" in t or self._contains_any(
            t,
            ["big o", "time complexity", "space complexity", "complexity", "runtime", "amortized"],
        )

    def _mentions_edge_cases(self, text: str | None) -> bool:
        """Check if text mentions edge cases."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["edge case", "corner case", "boundary", "empty", "null", "none", "zero", "negative", "overflow"],
        )

    def _mentions_constraints(self, text: str | None) -> bool:
        """Check if text mentions constraints."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["constraint", "constraints", "limit", "bounds", "input size", "range", "assumption"],
        )

    def _mentions_approach(self, text: str | None) -> bool:
        """Check if text mentions approach/algorithm."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            [
                "approach",
                "algorithm",
                "strategy",
                "plan",
                "idea",
                "i would",
                "we can",
                "i will",
                "i can",
                "use a",
                "use an",
            ],
        )

    def _mentions_tradeoffs(self, text: str | None) -> bool:
        """Check if text mentions trade-offs."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["trade-off", "tradeoff", "versus", " vs ", "pros", "cons", "alternative", "option"],
        )

    def _mentions_correctness(self, text: str | None) -> bool:
        """Check if text mentions correctness/proof."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            ["correct", "proof", "invariant", "why it works", "guarantee"],
        )

    def _mentions_tests(self, text: str | None) -> bool:
        """Check if text mentions tests."""
        t = self._normalize_text(text)
        return self._contains_any(
            t,
            [
                "test",
                "tests",
                "unit test",
                "unit tests",
                "example",
                "examples",
                "cases",
                "test case",
                "test cases",
                "validate",
                "verification",
                "assert",
            ],
        )

    def _behavioral_missing_parts(self, text: str | None) -> list[str]:
        """Detect missing STAR parts in behavioral response."""
        t = self._normalize_text(text)
        if "star" in t:
            return []
        parts = {
            "situation": ["situation", "context", "background"],
            "task": ["task", "goal", "responsibility"],
            "action": ["action", "implemented", "built", "led", "drove", "executed", "delivered"],
            "result": ["result", "impact", "outcome", "metric", "learned", "improved", "increased", "decreased"],
        }
        missing = []
        for name, keywords in parts.items():
            if not self._contains_any(t, keywords):
                missing.append(name)
        return missing

    def _is_clarification_request(self, text: str) -> bool:
        """Check if user is asking for question clarification/repetition."""
        t = (text or "").strip().lower()
        if not t:
            return False
        clarify_keywords = [
            "repeat", "again", "clarify", "explain", "rephrase", "restate",
            "what was", "what is", "can you repeat", "say that again",
            "didn't catch", "didnt catch", "missed that", "understand the question",
            "what's the question", "whats the question", "confus", "unclear",
            "elaborate", "more detail", "tell me more about", "what do you mean"
        ]
        return any(k in t for k in clarify_keywords)

    def _is_move_on(self, text: str) -> bool:
        """Check if user is requesting to move to next question."""
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = ["move on", "next question", "skip", "pass", "go next", "next please", "next pls"]
        if self._is_clarification_request(text):
            return False
        return any(k in t for k in keywords)

    def _is_dont_know(self, text: str) -> bool:
        """Check if user says they don't know."""
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = ["don't know", "dont know", "do not know", "no idea", "i dunno"]
        tokens_count = len(self._clean_tokens(text))
        if tokens_count > 10:
            return False
        if "not sure" in t or "unsure" in t:
            return tokens_count <= 5
        return any(k in t for k in keywords)

    def _is_non_informative(self, text: str) -> bool:
        """Check if response is too short to be meaningful."""
        tokens = self._clean_tokens(text)
        if not tokens:
            return True
        if len(tokens) == 1:
            return True
        short = {
            "ok", "okay", "k", "kk", "sure", "yes", "yeah", "yep", "yup",
            "alright", "cool", "fine", "thanks", "thank", "no", "nah"
        }
        if len(tokens) <= 2 and all(t in short for t in tokens):
            return True
        return False

    def _is_vague(self, text: str) -> bool:
        """Check if response is too vague/short to be useful."""
        tokens = self._clean_tokens(text)
        if not tokens:
            return True
        if len(tokens) < 5:
            if self._is_clarification_request(text):
                return False
            technical_patterns = ["array", "hash", "map", "list", "tree", "graph", "stack", "queue",
                                 "o(", "time", "space", "complexity", "algorithm", "function",
                                 "class", "object", "pointer", "node", "edge", "vertex"]
            t_lower = text.lower()
            if any(pattern in t_lower for pattern in technical_patterns):
                return False
            return True
        return False

    def _is_thin_response(
        self,
        text: str | None,
        signals: dict[str, bool],
        is_behavioral: bool,
        behavioral_missing: list[str],
        is_conceptual: bool = False,
    ) -> bool:
        """Check if response lacks substance."""
        if self._is_clarification_request(text or ""):
            return False
        
        tokens = self._clean_tokens(text)
        if not tokens:
            return True

        if is_conceptual:
            return len(tokens) < 8
        
        if len(tokens) >= 3:
            t_lower = (text or "").lower()
            technical_patterns = ["array", "hash", "map", "dict", "list", "tree", "graph",
                                 "o(n)", "o(1)", "o(log", "time", "space", "algorithm"]
            if any(pattern in t_lower for pattern in technical_patterns):
                return False
        
        if is_behavioral:
            return len(behavioral_missing) >= 3
        if signals.get("has_code") and not signals.get("mentions_approach"):
            return True
        content_signals = [
            "mentions_approach",
            "mentions_constraints",
            "mentions_correctness",
            "mentions_complexity",
            "mentions_edge_cases",
            "mentions_tradeoffs",
        ]
        return not any(signals.get(k) for k in content_signals)

    def _response_quality(
        self,
        text: str | None,
        signals: dict[str, bool],
        is_behavioral: bool,
        behavioral_missing: list[str],
        is_conceptual: bool = False,
    ) -> str:
        """Assess response quality."""
        if self._is_clarification_request(text or ""):
            return "ok"
        
        tokens = self._clean_tokens(text)
        if is_conceptual:
            if len(tokens) < 8:
                return "weak"
            if len(tokens) >= 25:
                return "strong"
            return "ok"
        if len(tokens) < 8:
            return "weak"
        if is_behavioral:
            if len(behavioral_missing) >= 3:
                return "weak"
            if not behavioral_missing and len(tokens) >= 25:
                return "strong"
            return "ok"
        if signals.get("has_code") and not signals.get("mentions_approach"):
            return "weak"
        if not signals.get("mentions_approach"):
            return "weak"
        coverage = 0
        for key in (
            "mentions_constraints",
            "mentions_correctness",
            "mentions_complexity",
            "mentions_edge_cases",
            "mentions_tradeoffs",
        ):
            if signals.get(key):
                coverage += 1
        if coverage >= 3:
            return "strong"
        if coverage >= 1 or len(tokens) >= 20:
            return "ok"
        return "weak"

    def _sanitize_ai_text(self, text: str | None) -> str:
        """Sanitize AI-generated text by removing markdown and special chars."""
        if not text:
            return ""
        replacements = {
            "\u2019": "'",
            "\u2018": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2014": "--",
            "\u2013": "-",
            "\u2026": "...",
            "\u2022": "-",
            "\u00b7": "-",
            "\u00a0": " ",
        }
        cleaned = "".join(replacements.get(ch, ch) for ch in text)
        cleaned = cleaned.replace("```", "")
        cleaned = "".join(ch if ord(ch) < 128 else "" for ch in cleaned)

        title = ""
        prompt = ""
        lines: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.replace("**", "").replace("__", "").replace("`", "")
            line = re.sub(r"^[-*]\s+", "", line)
            line = re.sub(r"^\d+\.\s+", "", line)

            lower = line.lower()
            if lower.startswith("title:"):
                title = line.split(":", 1)[1].strip()
                continue
            if lower.startswith("prompt:"):
                prompt = line.split(":", 1)[1].strip()
                continue

            lines.append(line)

        if title or prompt:
            question = " ".join([part for part in [title, prompt] if part])
            if lines:
                lines.append(question)
                return "\n\n".join(lines).strip()
            return question.strip()

        return "\n\n".join(lines).strip()

    def _is_ready_to_start(self, text: str | None) -> bool:
        """Check if user is ready to start interview."""
        t = self._normalize_text(text)
        if not t:
            return False
        keywords = ["ready", "let's start", "lets start", "start interview", "go ahead", "begin", "start now"]
        return self._contains_any(t, keywords)

    def _normalize_focus_key(self, key: str | None) -> str | None:
        """Normalize focus key variations to standard form."""
        k = (key or "").strip().lower()
        if not k:
            return None
        mapping = {
            "edge case": "edge_cases",
            "edge cases": "edge_cases",
            "edge": "edge_cases",
            "edges": "edge_cases",
            "complexity": "complexity",
            "runtime": "complexity",
            "big o": "complexity",
            "correctness": "correctness",
            "proof": "correctness",
            "invariant": "correctness",
            "trade-off": "tradeoffs",
            "tradeoff": "tradeoffs",
            "tradeoffs": "tradeoffs",
            "approach": "approach",
            "plan": "approach",
            "constraints": "constraints",
            "assumptions": "constraints",
            "star": "star",
            "impact": "impact",
            "outcome": "impact",
        }
        if k in mapping:
            return mapping[k]
        if k in {"approach", "constraints", "correctness", "complexity", "edge_cases", "tradeoffs", "star", "impact"}:
            return k
        return None

    def _dimension_to_missing_key(self, dimension: str | None) -> str | None:
        """Convert rubric dimension to missing focus key."""
        if dimension == "edge_cases":
            return "edge_cases"
        if dimension == "complexity":
            return "complexity"
        if dimension == "correctness_reasoning":
            return "correctness"
        if dimension == "problem_solving":
            return "approach"
        if dimension == "communication":
            return "approach"
        return None

    def _clean_next_question_reply(self, text: str | None, user_name: str | None = None) -> str:
        """Clean AI-generated reply for next question."""
        if not text:
            return ""
        cleaned = text.strip()

        name = (user_name or "").strip()
        if name:
            cleaned = re.sub(
                rf"^(?:hi|hello|hey)(?:\s+there)?\s+{re.escape(name)}[\s,!.:-]*",
                "",
                cleaned,
                flags=re.I,
            )
        cleaned = re.sub(r"^(?:hi|hello|hey)(?:\s+there)?[\s,!.:-]*", "", cleaned, flags=re.I)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
        if not paragraphs:
            return cleaned

        transition_re = re.compile(r"\b(move to the next question|next question)\b", re.I)
        greeting_re = re.compile(r"^(hi|hello|hey)\b", re.I)
        seen: set[str] = set()
        cleaned_paragraphs: list[str] = []
        for para in paragraphs:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            kept: list[str] = []
            for sent in sentences:
                s = sent.strip()
                if not s:
                    continue
                if "?" not in s and greeting_re.search(s):
                    continue
                if "?" not in s and transition_re.search(s):
                    continue
                norm = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
                if norm and norm in seen:
                    continue
                if norm:
                    seen.add(norm)
                kept.append(s)
            if kept:
                cleaned_paragraphs.append(" ".join(kept))

        if not cleaned_paragraphs:
            return cleaned
        cleaned = "\n\n".join(cleaned_paragraphs).strip()
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
