"""
Prompt Generation Module for Interview Engine.

Handles prompt assembly, transitions, and offline question formatting.
"""

from typing import Any
import re

from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services.interview_engine_questions import InterviewEngineQuestions


class InterviewEnginePrompts(InterviewEngineQuestions):
    """Prompt assembly and reply cleaning methods."""

    def _transition_preface(self, session: InterviewSession, reason: str | None = None) -> str:
        focus_dims = self._focus_dimensions(session)
        idx = int(session.questions_asked_count or 0)

        # Only emit a focus hint every 3rd question (idx 0, 3, 6...) to avoid
        # sounding like a broken record. Omit on move_on/dont_know — they're
        # already awkward moments; no need to pile on.
        show_focus = (reason is None) and bool(focus_dims) and (idx % 3 == 0) and (idx > 0)
        focus_line = ""
        if show_focus:
            if "complexity" in focus_dims and "edge_cases" in focus_dims:
                focus_line = "Pay attention to both complexity and edge cases here."
            elif "complexity" in focus_dims:
                focus_line = "Think carefully about complexity on this one."
            elif "edge_cases" in focus_dims:
                focus_line = "Watch out for edge cases."
            elif focus_dims:
                focus_line = f"This one's about {focus_dims[0].replace('_', ' ')}."

        if reason == "move_on":
            leads = [
                "Got it, let's move on.",
                "No problem, let's skip to the next one.",
                "Sure, moving on.",
                "Alright, let's try a different one.",
                "Fair enough, let's switch gears.",
            ]
            return leads[idx % len(leads)]

        if reason == "dont_know":
            leads = [
                "No worries — that one trips people up.",
                "All good, happens to everyone.",
                "That's fine, let's try something else.",
                "No stress, let's keep going.",
                "Totally fine. Let's move on.",
            ]
            return leads[idx % len(leads)]

        # Normal transition after answering
        bridges = [
            "Alright, next one.",
            "Good. Moving on.",
            "Okay, let's try another.",
            "Nice. Next question.",
            "Right, let's keep going.",
            "Got it. Here's the next one.",
            "Okay, let's switch it up.",
            "Good stuff. Next.",
        ]
        bridge = bridges[idx % len(bridges)]
        if focus_line:
            return f"{bridge} {focus_line}"
        return bridge

    def _clean_next_question_reply(self, text: str | None, user_name: str | None = None) -> str:
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
        # Strip standalone "Understood." / "Got it." openers that duplicate the preface
        cleaned = re.sub(r"^(?:understood|got it|sure|alright|okay|of course)[.,!]?\s*", "", cleaned, flags=re.I)
        # Strip re-introductions mid-interview
        cleaned = re.sub(
            r"(?:hi|hello|hey)[,!]?\s+(?:i'm|i am)\s+\w+[,!]?\s+(?:and\s+)?i'?ll?\s+be\s+your\s+interviewer[^.]*\.",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"nice\s+to\s+meet\s+you[!.,]?\s*", "", cleaned, flags=re.I)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
        if not paragraphs:
            return cleaned

        transition_re = re.compile(r"\b(move to the next question|next question)\b", re.I)
        greeting_re = re.compile(r"^(hi|hello|hey)\b", re.I)
        intro_re = re.compile(r"\bi'?ll?\s+be\s+your\s+interviewer\b", re.I)
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
                if intro_re.search(s):
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

    def _ensure_question_in_reply(self, reply: str | None, title: str, prompt: str) -> str:
        if not reply:
            return ""
        cleaned = reply.strip()
        if not cleaned:
            return ""
        lower = cleaned.lower()
        prompt_clean = (prompt or "").strip()
        # Check if a meaningful portion of the prompt is already in the reply.
        # Use a 60-char prefix so paraphrased intros don't trigger a redundant append.
        prompt_prefix = prompt_clean[:60].lower()
        if prompt_clean and (prompt_clean.lower() in lower or (prompt_prefix and prompt_prefix in lower)):
            return cleaned
        # Only append the prompt (not the LeetCode-style title) — the title is
        # a UI display label that sounds unnatural when read aloud by TTS.
        if not prompt_clean:
            return cleaned
        return f"{cleaned}\n\n{prompt_clean}".strip()

    def _combine_question_text(self, title: str | None, prompt: str | None) -> str:
        t = (title or "").strip()
        p = (prompt or "").strip()
        if t and p:
            t_norm = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
            p_norm = re.sub(r"[^a-z0-9]+", " ", p.lower()).strip()
            if t_norm and p_norm:
                if t_norm in p_norm:
                    return p
                if p_norm in t_norm:
                    return t
            if t.endswith(("?", ".", "!", ":")):
                return f"{t} {p}"
            return f"{t}. {p}"
        return t or p

    def _offline_intro(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        name = self._user_name_safe(user_name)
        greeting = f"Hi {name}!" if name else "Hi!"
        question_text = self._combine_question_text(q.title, q.prompt)
        qt = self._question_type(q)
        if self._is_behavioral(q):
            body = f"{question_text} Please answer using STAR (Situation, Task, Action, Result)."
        elif qt == "conceptual":
            body = f"{question_text} Please explain the concept clearly and give a simple example."
        elif qt == "system_design":
            body = f"{question_text} Please clarify requirements, then outline a high-level design and trade-offs."
        else:
            body = (
                f"{question_text} Start by restating the problem and clarifying constraints, "
                "then outline your approach and complexity."
            )
        parts = []
        if preface:
            parts.append(preface.strip())
        parts.append(f"{greeting} {body}".strip())
        return "\n\n".join([p for p in parts if p]).strip()

    def _offline_next_question(self, q: Question, user_name: str | None = None, preface: str | None = None) -> str:
        question_text = self._combine_question_text(q.title, q.prompt)
        qt = self._question_type(q)
        if self._is_behavioral(q):
            body = f"{question_text} Please answer using STAR (Situation, Task, Action, Result)."
        elif qt == "conceptual":
            body = f"{question_text} Please explain the concept clearly and give a simple example."
        elif qt == "system_design":
            body = f"{question_text} Please clarify requirements, then outline a high-level design and trade-offs."
        else:
            body = (
                f"{question_text} Start with constraints and a brief plan, then share complexity and edge cases."
            )
        if preface:
            return f"{preface.strip()}\n\n{body}".strip()
        return body.strip()
