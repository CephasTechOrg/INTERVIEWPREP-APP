"""
Warmup Module for Interview Engine.

Handles warmup flows, smalltalk, and intent classification.
"""

from __future__ import annotations

import contextlib
import datetime
import logging
import re
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.crud import question as question_crud
from app.crud import session_question as session_question_crud
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services.llm_schemas import UserIntentClassification, WarmupSmalltalkProfile, WarmupToneProfile
from app.services import interview_warmup
from app.services.interview_engine_prompts import InterviewEnginePrompts
from app.services.prompt_templates import (
    user_intent_classifier_system_prompt,
    user_intent_classifier_user_prompt,
    warmup_contextual_reply_user_prompt,
    warmup_prompt_user_prompt,
    warmup_reply_user_prompt,
    warmup_smalltalk_system_prompt,
    warmup_smalltalk_user_prompt,
    warmup_system_prompt,
    warmup_tone_classifier_system_prompt,
    warmup_tone_classifier_user_prompt,
)

_engine_logger = logging.getLogger("app.services.interview_engine")


class InterviewEngineWarmup(InterviewEnginePrompts):
    """Warmup flow and smalltalk methods."""

    def _warmup_focus_line(self, focus: dict[str, Any]) -> str:
        # Removed: generic focus announcements ("I'll focus on problem solving.")
        # sound robotic and add no value in the warmup → interview transition.
        return ""

    def _warmup_behavioral_question_id(self, session: InterviewSession) -> int | None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        raw = warm.get("behavioral_question_id")
        try:
            return int(raw) if raw is not None else None
        except Exception:
            return None

    def _set_warmup_behavioral_question_id(self, db: Session, session: InterviewSession, question_id: int) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        warm = dict(warm)
        warm["behavioral_question_id"] = int(question_id)
        state["warmup"] = warm
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _mark_warmup_behavioral_asked(self, db: Session, session: InterviewSession, question_id: int | None) -> None:
        if not question_id:
            return
        with contextlib.suppress(Exception):
            session_question_crud.mark_question_asked(db, session.id, int(question_id))
        with contextlib.suppress(Exception):
            user_question_seen_crud.mark_question_seen(db, session.user_id, int(question_id))

    def _warmup_behavioral_ack(self, student_text: str | None) -> str:
        return interview_warmup.warmup_ack(student_text)

    def _get_time_of_day(self) -> str:
        """Return 'morning', 'afternoon', or 'evening' based on current time."""
        try:
            hour = datetime.datetime.now().hour
            if 5 <= hour < 12:
                return "morning"
            elif 12 <= hour < 18:
                return "afternoon"
            else:
                return "evening"
        except Exception:
            return "day"

    def _get_greeting_template(self, user_name: str | None, interviewer_name: str | None, time_of_day: str) -> str:
        """Generate varied time-aware greetings."""
        import random
        
        name = (user_name or "").strip() or "there"
        interviewer = interviewer_name or "your interviewer"
        
        # Time-specific greeting variants
        if time_of_day == "morning":
            greetings = [
                f"Good morning, {name}! I'm {interviewer}.",
                f"Morning, {name}! I'm {interviewer}.",
                f"Hi {name}! Hope your morning is going well. I'm {interviewer}.",
            ]
        elif time_of_day == "afternoon":
            greetings = [
                f"Good afternoon, {name}! I'm {interviewer}.",
                f"Hi {name}! I'm {interviewer}.",
                f"Hey {name}! I'm {interviewer}.",
            ]
        else:  # evening or default
            greetings = [
                f"Good evening, {name}! I'm {interviewer}.",
                f"Hi {name}! I'm {interviewer}.",
                f"Hey {name}! Thanks for joining. I'm {interviewer}.",
            ]
        
        greeting = random.choice(greetings)
        
        # Varied check-in questions
        check_ins = [
            "How are you doing?",
            "How's it going?",
            "How are you feeling today?",
            f"How's your {time_of_day} been so far?" if time_of_day != "day" else "How's your day been so far?",
        ]
        check_in = random.choice(check_ins)
        
        return f"{greeting} {check_in}"

    async def _warmup_prompt(self, session: InterviewSession, user_name: str | None = None) -> str:
        time_of_day = self._get_time_of_day()
        sys = warmup_system_prompt(session.company_style, session.role, self._interviewer_name(session), self._interviewer_id(session))
        user = warmup_prompt_user_prompt(user_name, self._interviewer_name(session), self._interviewer_id(session))
        
        # Fallback: use time-aware template
        if not getattr(self.llm, "api_key", None):
            return self._get_greeting_template(user_name, self._interviewer_name(session), time_of_day)
        
        try:
            reply = await self.llm.chat(sys, user)
            return self._sanitize_ai_text(reply)
        except Exception:
            return self._get_greeting_template(user_name, self._interviewer_name(session), time_of_day)

    async def _warmup_reply(
        self,
        session: InterviewSession,
        student_text: str,
        user_name: str | None,
        focus: dict[str, Any],
        db: Session,
        tone_line: str | None = None,
    ) -> str:
        question_text, qid = self._warmup_behavioral_question(db, session)
        focus_line = self._warmup_focus_line(focus) or None
        sys = warmup_system_prompt(session.company_style, session.role, self._interviewer_name(session), self._interviewer_id(session))
        user = warmup_reply_user_prompt(student_text, user_name, question_text, focus_line=focus_line, tone_line=tone_line)

        if not getattr(self.llm, "api_key", None):
            msg = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)
            self._mark_warmup_behavioral_asked(db, session, qid)
            return msg

        try:
            reply = await self.llm.chat(sys, user)
            reply = self._sanitize_ai_text(reply)
        except Exception:
            reply = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)

        if not reply:
            reply = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)

        self._mark_warmup_behavioral_asked(db, session, qid)
        return reply

    def _pick_warmup_behavioral_question(self, db: Session, session: InterviewSession) -> Question | None:
        asked_ids = set(session_question_crud.list_asked_question_ids(db, session.id))
        warmup_id = self._warmup_behavioral_question_id(session)
        if warmup_id:
            asked_ids.add(warmup_id)
        seen = self._seen_question_subquery(session)
        company = (session.company_style or "").strip().lower() or "general"
        track = (session.track or "").strip()
        tracks = [track, "behavioral"] if track else ["behavioral"]
        diff = (session.difficulty or "easy").strip().lower()

        def _query(company_style: str, difficulty: str | None) -> Question | None:
            base = db.query(Question).filter(
                Question.company_style == company_style,
                Question.track.in_(tracks),
                or_(Question.tags_csv.ilike("%behavioral%"), Question.question_type == "behavioral"),
            )
            if difficulty:
                base = base.filter(Question.difficulty == difficulty)
            if asked_ids:
                base = base.filter(~Question.id.in_(asked_ids))
            unseen = base.filter(~Question.id.in_(seen)).order_by(func.random()).first()
            if unseen:
                return unseen
            return base.order_by(func.random()).first()

        for company_style, difficulty in (
            (company, diff),
            (company, None),
            ("general", diff) if company != "general" else (None, None),
            ("general", None) if company != "general" else (None, None),
        ):
            if not company_style:
                continue
            q = _query(company_style, difficulty)
            if q:
                return q
        return None

    def _fallback_warmup_behavioral_question(self, session: InterviewSession) -> str:
        company = self._company_name(session.company_style)
        role = (session.role or "").strip().lower()
        if session.company_style == "general":
            if "intern" in role:
                return "Why are you interested in this internship?"
            return "Why are you interested in this role?"
        if "intern" in role:
            return f"Why do you want to intern at {company}?"
        return f"Why do you want to work at {company}?"

    def _warmup_behavioral_question(self, db: Session, session: InterviewSession) -> tuple[str, int | None]:
        stored_id = self._warmup_behavioral_question_id(session)
        if stored_id:
            q = question_crud.get_question(db, stored_id)
            if q:
                title, prompt = self._render_question(session, q)
                return self._combine_question_text(title, prompt), q.id

        q = self._pick_warmup_behavioral_question(db, session)
        if q:
            with contextlib.suppress(Exception):
                self._set_warmup_behavioral_question_id(db, session, q.id)
            title, prompt = self._render_question(session, q)
            return self._combine_question_text(title, prompt), q.id

        return self._fallback_warmup_behavioral_question(session), None

    def _warmup_state(self, session: InterviewSession) -> dict:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        warm = state.get("warmup")
        return warm if isinstance(warm, dict) else {}

    def _set_warmup_state(
        self,
        db: Session,
        session: InterviewSession,
        step: int,
        done: bool,
        **meta: Any,
    ) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        warm = state.get("warmup") if isinstance(state.get("warmup"), dict) else {}
        warm = dict(warm)
        for key, val in meta.items():
            if val is not None:
                warm[key] = val
        warm["step"] = int(step)
        warm["done"] = bool(done)
        state["warmup"] = warm
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _warmup_profile_from_state(self, session: InterviewSession) -> WarmupToneProfile | None:
        warm = self._warmup_state(session)
        tone = warm.get("tone")
        energy = warm.get("energy")
        confidence_raw = warm.get("tone_confidence")
        if not tone and not energy:
            return None
        try:
            if confidence_raw is None:
                confidence = 0.6
            else:
                confidence = float(confidence_raw)
            return WarmupToneProfile(
                tone=tone or "neutral",
                energy=energy or "medium",
                confidence=confidence,
            )
        except Exception:
            return None

    def _infer_smalltalk_topic(self, text: str) -> str:
        t = self._normalize_text(text)
        if not t:
            return ""
        if any(k in t for k in ("class", "classes", "school", "semester", "lecture", "exam", "homework")):
            return "school"
        if any(k in t for k in ("project", "feature", "build", "prototype", "assignment")):
            return "project"
        if any(k in t for k in ("work", "job", "office", "meeting", "deadline", "shift")):
            return "work"
        if "interview" in t or "prep" in t:
            return "interview_prep"
        if any(k in t for k in ("commute", "traffic", "train", "bus", "drive")):
            return "commute"
        if any(k in t for k in ("weekend", "tonight")):
            return "weekend"
        if "weather" in t:
            return "weather"
        if "day" in t or "today" in t:
            return "day"
        return ""

    def _greeting_ack(self, text: str | None) -> str | None:
        """Enhanced reciprocal greeting acknowledgment with varied responses."""
        import random
        
        t = self._normalize_text(text)
        if not t:
            return None
        
        # Check for reciprocal questions
        reciprocal_phrases = [
            "how are you",
            "how are you doing",
            "how are you doing today",
            "how is it going",
            "hows it going",
            "how's it going",
            "how about you",
            "what about you",
            "and you",
        ]
        
        if any(phrase in t for phrase in reciprocal_phrases):
            # Varied responses to reciprocal questions
            responses = [
                "I'm doing well, thanks for asking!",
                "I'm great, thanks for asking!",
                "Doing well, thank you!",
                "I'm good, thanks!",
                "Pretty good, thanks for asking!",
            ]
            return random.choice(responses)
        
        return None

    def _clean_smalltalk_question(self, question: str | None) -> str:
        q = (question or "").strip()
        if not q:
            return ""
        q = " ".join(q.split())
        q = re.sub(r"^(question|q)[:\-\s]+", "", q, flags=re.IGNORECASE).strip()
        if "?" in q:
            q = q.split("?")[0].strip() + "?"
        else:
            q = q.rstrip(".!") + "?"
        if len(q) > 140:
            q = q[:140].rsplit(" ", 1)[0].rstrip(".!?") + "?"
        return q

    def _is_redundant_smalltalk(self, question: str) -> bool:
        normalized = self._normalize_text(question).rstrip("?").strip()
        return normalized in {
            "how are you",
            "how are you doing",
            "how are you doing today",
            "how is it going",
            "hows it going",
        }

    def _smalltalk_question_from_topic(self, topic: str) -> str | None:
        t = (topic or "").strip().lower()
        if t in ("work", "job"):
            return "What have you been working on today?"
        if t in ("school", "class", "classes"):
            return "How are classes going lately?"
        if t == "project":
            return "What kind of project have you been working on recently?"
        if t in ("interview_prep", "interview"):
            return "How has interview prep been going lately?"
        if t == "commute":
            return "How was your commute today?"
        if t == "weekend":
            return "Any nice plans for later today?"
        if t == "weather":
            return "How's the weather where you are?"
        if t == "day":
            return "How has your day been so far?"
        return None

    def _smalltalk_question(self, profile: WarmupSmalltalkProfile | None, text: str) -> str:
        """Generate varied smalltalk questions based on context and tone."""
        import random
        
        if profile:
            q = self._clean_smalltalk_question(profile.smalltalk_question)
            if q and not self._is_redundant_smalltalk(q):
                return q
            topic = profile.topic or self._infer_smalltalk_topic(text)
        else:
            topic = self._infer_smalltalk_topic(text)

        by_topic = self._smalltalk_question_from_topic(topic)
        if by_topic:
            return by_topic

        # Varied fallback questions based on tone
        if profile and profile.tone in ("excited", "positive"):
            positive_questions = [
                "What's been the highlight of your day so far?",
                "What's been keeping you busy lately?",
                "Anything exciting you're working on?",
            ]
            return random.choice(positive_questions)
        
        if profile and profile.tone in ("stressed", "tired"):
            empathetic_questions = [
                "Has your day been pretty busy so far?",
                "Been a long day?",
                "Lot going on today?",
            ]
            return random.choice(empathetic_questions)
        
        # General fallback questions
        general_questions = [
            "How has your day been so far?",
            "What have you been up to today?",
            "How's everything going?",
        ]
        return random.choice(general_questions)

    def _warmup_smalltalk_line(self, profile: WarmupToneProfile | None) -> str:
        if not profile:
            return "Thanks for sharing."
        tone = profile.tone
        energy = profile.energy

        if tone == "excited":
            return "Love the energy."
        if tone == "positive":
            return "Great to hear."
        if tone == "stressed":
            return "Totally fair."
        if tone == "tired" or tone == "negative":
            return "Thanks for sharing."
        if energy == "high":
            return "Nice, sounds like a good rhythm."
        return "Thanks for sharing."

    def _warmup_transition_line(self, profile: WarmupToneProfile | None) -> str:
        if not profile:
            return "Thanks for sharing."
        tone = profile.tone
        energy = profile.energy

        if tone == "excited":
            return "Love the energy, let's keep that momentum."
        if tone == "positive":
            if energy == "high":
                return "Great to hear, let's keep that momentum."
            if energy == "low":
                return "Great to hear, we'll keep a steady pace."
            return "Great to hear."
        if tone == "stressed":
            return "Totally fair, we'll take it step by step."
        if tone == "tired":
            return "Thanks for sharing, we'll keep the pace comfortable."
        if tone == "negative":
            return "Thanks for sharing, we'll keep it low pressure."
        if energy == "high":
            return "Thanks for sharing, let's use that momentum."
        if energy == "low":
            return "Thanks for sharing, we'll keep the pace comfortable."
        return "Thanks for sharing."

    def _warmup_smalltalk_reply(self, ack_line: str | None, question: str) -> str:
        ack = (ack_line or "Thanks for sharing.").strip()
        if ack and ack[-1] not in ".!?":
            ack = f"{ack}."
        q = self._clean_smalltalk_question(question) or "How has your day been so far?"
        return f"{ack} {q}".strip()

    async def _classify_warmup_smalltalk(self, text: str) -> WarmupSmalltalkProfile | None:
        msg = (text or "").strip()
        if not msg:
            return None
        if not getattr(self.llm, "api_key", None):
            return None
        sys = warmup_smalltalk_system_prompt()
        user = warmup_smalltalk_user_prompt(msg)
        try:
            data = await self.llm.chat_json(sys, user)
            if isinstance(data, dict) and "smalltalk_question" not in data and "question" in data:
                data["smalltalk_question"] = data.get("question")
            return WarmupSmalltalkProfile.model_validate(data)
        except Exception:
            return None

    async def _classify_warmup_tone(self, text: str) -> WarmupToneProfile | None:
        msg = (text or "").strip()
        if not msg:
            return None
        if not getattr(self.llm, "api_key", None):
            return None
        sys = warmup_tone_classifier_system_prompt()
        user = warmup_tone_classifier_user_prompt(msg)
        try:
            data = await self.llm.chat_json(sys, user)
            return WarmupToneProfile.model_validate(data)
        except Exception:
            return None

    async def _classify_user_intent(self, text: str, question_context: str | None = None) -> UserIntentClassification | None:
        """
        AI-powered intent classification. Understands context like a human.
        Falls back to keyword heuristics if LLM unavailable.
        """
        if not text or not text.strip():
            return None

        # Try AI classification first
        sys = user_intent_classifier_system_prompt()
        user = user_intent_classifier_user_prompt(text, question_context)
        try:
            data = await self.llm.chat_json(sys, user)
            classification = UserIntentClassification.model_validate(data)
            _engine_logger.debug(
                "Intent classified: %s (%.2f confidence) - %s",
                classification.intent,
                classification.confidence,
                classification.reasoning
            )
            return classification
        except Exception as e:
            _engine_logger.debug("Intent classification unavailable, using heuristics: %s", e)
            # Fallback to keyword heuristics
            return self._classify_intent_heuristic(text)

    def _classify_intent_heuristic(self, text: str) -> UserIntentClassification:
        """Fallback keyword-based intent classification."""
        if self._is_clarification_request(text):
            return UserIntentClassification(intent="clarification", confidence=0.7, reasoning="Keyword match")
        if self._is_move_on(text):
            return UserIntentClassification(intent="move_on", confidence=0.8, reasoning="Keyword match")
        if self._is_dont_know(text):
            return UserIntentClassification(intent="dont_know", confidence=0.7, reasoning="Keyword match")
        # Default to answering
        return UserIntentClassification(intent="answering", confidence=0.5, reasoning="Default fallback")

    async def _warmup_generate_contextual_reply(
        self,
        session: InterviewSession,
        student_text: str,
        user_name: str | None,
        follow_up_question: str | None = None,
        is_reciprocal: bool = False,
        tone: str | None = None,
    ) -> str:
        """Generate a genuine, contextual warmup reply using the LLM.

        When ``is_reciprocal`` is True the candidate asked "how are YOU doing?" —
        the LLM is instructed to answer that directly before moving on.
        ``follow_up_question`` is the next thing we want the conversation to
        naturally land on (a smalltalk question or a behavioral question).
        """
        sys = warmup_system_prompt(session.company_style, session.role, self._interviewer_name(session), self._interviewer_id(session))
        user = warmup_contextual_reply_user_prompt(
            candidate_text=student_text,
            user_name=user_name,
            follow_up_question=follow_up_question,
            is_reciprocal=is_reciprocal,
            tone=tone,
        )

        def _fallback() -> str:
            base = "I'm doing well, thanks for asking!" if is_reciprocal else "Thanks for sharing."
            if follow_up_question:
                q = self._clean_smalltalk_question(follow_up_question) or follow_up_question
                return f"{base} {q}"
            return base

        if not getattr(self.llm, "api_key", None):
            return _fallback()

        try:
            reply = await self.llm.chat(sys, user)
            return self._sanitize_ai_text(reply) or _fallback()
        except Exception:
            return _fallback()

    def _warmup_behavioral_reply(
        self,
        session: InterviewSession,
        focus: dict[str, Any],
        question_text: str,
        tone_line: str | None = None,
    ) -> str:
        focus_line = self._warmup_focus_line(focus)
        question = question_text or self._fallback_warmup_behavioral_question(session)
        # Ensure regression-friendly phrasing even when LLM is offline:
        # - contains "i am doing well"
        # - contains "your interviewer"
        # - contains "behavioral question"
        interviewer_name = self._interviewer_name(session)
        if interviewer_name:
            base_ack = tone_line or f"I am doing well -- I'm {interviewer_name}, your interviewer."
        else:
            base_ack = tone_line or "I am doing well -- I'm your interviewer."
        if base_ack and base_ack[-1] not in ".!?":
            base_ack = f"{base_ack}."
        parts = [base_ack]
        if focus_line:
            parts.append(focus_line)
        parts.append(f"Let's start with a quick behavioral question: {question}")
        return " ".join(parts).strip()
