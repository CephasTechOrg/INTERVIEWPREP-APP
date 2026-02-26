"""
Main Orchestrator Module for Interview Engine.

Handles the core interview flow and high-level decision logic.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.crud import message as message_crud
from app.crud import question as question_crud
from app.crud import session as session_crud
from app.crud import session_question as session_question_crud
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services import interview_warmup
from app.services.interview_engine_transitions import InterviewEngineTransitions
from app.services.llm_client import LLMClientError
from app.services.llm_schemas import InterviewControllerOutput
from app.services.prompt_templates import (
    interviewer_controller_system_prompt,
    interviewer_controller_user_prompt,
    interviewer_system_prompt,
)

_engine_logger = logging.getLogger(__name__)


def _get_rag_context_for_interview(db: Session, session_id: int) -> str | None:
    """
    Safely get RAG context for live interview.
    Returns None if RAG is unavailable or not enough data.
    """
    try:
        from app.services.rag_service import get_rag_context_for_session
        context_text, _context_meta = get_rag_context_for_session(db, session_id)
        if context_text:
            _engine_logger.debug("RAG context available for session_id=%s", session_id)
        return context_text
    except Exception:
        return None


class InterviewEngineMain(InterviewEngineTransitions):
    """Main interview flow orchestrator."""

    # ──────────────────────────────────────────
    # Session-wide pattern tracking
    # ──────────────────────────────────────────

    def _update_session_patterns(
        self,
        db: Session,
        session: InterviewSession,
        signals: dict,
        q: Any,
        response_quality: str,
    ) -> None:
        """Accumulate cross-question behavioural patterns in skill_state["patterns"]."""
        state = dict(session.skill_state or {})
        pat = dict(state.get("patterns", {}))

        n = int(pat.get("n", 0)) + 1
        pat["n"] = n

        # Track how often the candidate mentions complexity
        if signals.get("mentions_complexity"):
            pat["complexity_count"] = int(pat.get("complexity_count", 0)) + 1

        # Track whether candidate explains approach before coding
        if signals.get("mentions_approach"):
            pat["approach_count"] = int(pat.get("approach_count", 0)) + 1

        # Detect pattern of jumping straight to code
        if signals.get("has_code") and not signals.get("mentions_approach"):
            pat["code_without_plan"] = int(pat.get("code_without_plan", 0)) + 1

        # Track tradeoff mentions
        if signals.get("mentions_tradeoffs"):
            pat["tradeoffs_count"] = int(pat.get("tradeoffs_count", 0)) + 1

        # Track edge-case mentions
        if signals.get("mentions_edge_cases"):
            pat["edge_cases_count"] = int(pat.get("edge_cases_count", 0)) + 1

        # Track question-type strengths / gaps
        qt = self._question_type(q) if q else "coding"
        if response_quality == "strong":
            strong = list(pat.get("strong_types", []))
            if qt not in strong:
                strong.append(qt)
            pat["strong_types"] = strong
        elif response_quality == "weak":
            weak = list(pat.get("weak_types", []))
            if qt not in weak:
                weak.append(qt)
            pat["weak_types"] = weak

        state["patterns"] = pat
        session.skill_state = state
        db.add(session)
        db.commit()

    def _session_patterns_summary(self, session: InterviewSession) -> str | None:
        """
        Convert accumulated patterns into a concise English summary for the controller.
        Returns None if there isn't enough data yet (< 2 questions answered).
        """
        state = dict(session.skill_state or {})
        pat = dict(state.get("patterns", {}))
        n = int(pat.get("n", 0))
        if n < 2:
            return None

        observations: list[str] = []

        # Complexity pattern
        cx = int(pat.get("complexity_count", 0))
        if cx == 0:
            observations.append(
                "Candidate has NOT mentioned time/space complexity across any question so far — recurring gap."
            )
        elif cx < (n + 1) // 2:
            observations.append("Candidate mentions complexity inconsistently — prompt for it when missing.")

        # Approach pattern
        ap = int(pat.get("approach_count", 0))
        if ap < (n + 1) // 2:
            observations.append("Candidate tends to skip explaining their approach and jumps to implementation.")

        # Code-without-plan pattern
        cwp = int(pat.get("code_without_plan", 0))
        if cwp >= 2:
            observations.append(
                f"Candidate has jumped straight to code without a verbal plan {cwp} times — push them to plan first."
            )

        # Tradeoffs
        tr = int(pat.get("tradeoffs_count", 0))
        if tr == 0 and n >= 3:
            observations.append("Candidate has not discussed trade-offs on any question — worth pushing on.")

        # Edge cases
        ec = int(pat.get("edge_cases_count", 0))
        if ec == 0 and n >= 3:
            observations.append("Candidate has not mentioned edge cases yet this session.")

        # Strong / weak types
        strong = list(pat.get("strong_types", []))
        weak = list(pat.get("weak_types", []))
        if strong:
            observations.append(f"Strong on: {', '.join(strong)} questions.")
        if weak:
            observations.append(f"Weaker on: {', '.join(weak)} questions.")

        return " | ".join(observations) if observations else None

    # ──────────────────────────────────────────
    # Per-question hint level tracking
    # ──────────────────────────────────────────

    def _get_hint_level(self, session: InterviewSession, q_id: int) -> int:
        state = dict(session.skill_state or {})
        hints = dict(state.get("hints", {}))
        return int(hints.get(str(q_id), 0))

    def _increment_hint_level(self, db: Session, session: InterviewSession, q_id: int) -> int:
        state = dict(session.skill_state or {})
        hints = dict(state.get("hints", {}))
        current = int(hints.get(str(q_id), 0))
        new_level = min(current + 1, 3)
        hints[str(q_id)] = new_level
        state["hints"] = hints
        session.skill_state = state
        db.add(session)
        db.commit()
        return new_level

    def _dimension_to_missing_key(self, dimension: str | None) -> str | None:
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

    async def ensure_question_and_intro(
        self,
        db: Session,
        session: InterviewSession,
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        """
        Start the interview with a greeting + main question for the first problem.
        If the LLM is unavailable, fall back to a dataset-driven message (no 502).
        """
        warm_step, warm_done = interview_warmup.get_state(session)
        stage = session.stage or "intro"

        if stage == "warmup_behavioral" and not warm_done:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            focus = {"dimensions": self._focus_dimensions(session), "tags": []}
            question_text, qid = self._warmup_behavioral_question(db, session)
            tone_line = self._warmup_transition_line(self._warmup_profile_from_state(session))
            msg = self._warmup_behavioral_reply(session, focus, question_text, tone_line=tone_line)
            message_crud.add_message(db, session.id, "interviewer", msg)
            self._mark_warmup_behavioral_asked(db, session, qid)
            return msg

        if stage == "warmup_smalltalk" and not warm_done:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            warm = self._warmup_state(session)
            profile = self._warmup_profile_from_state(session)
            question = warm.get("smalltalk_question") or self._smalltalk_question(None, "")
            msg = self._warmup_smalltalk_reply(self._warmup_smalltalk_line(profile), question)
            message_crud.add_message(db, session.id, "interviewer", msg)
            return msg

        # Warmup greeting (only when at intro/warmup stage)
        if not warm_done and (stage in (None, "", "intro", "warmup", "warmup_smalltalk")) and stage != "warmup_done":
            if warm_step <= 0:
                msg = None
                try:
                    msg = await self._warmup_prompt(session, user_name=user_name)
                except Exception:
                    msg = None
                if not msg:
                    msg = interview_warmup.prompt_for_step(
                        0, user_name=user_name, interviewer_name=self._interviewer_name(session)
                    )
                if msg:
                    message_crud.add_message(db, session.id, "interviewer", msg)
                    with contextlib.suppress(Exception):
                        self._set_intro_used(db, session)
                    self._set_warmup_state(db, session, 1, False)
                    session_crud.update_stage(db, session, "warmup")
                    return msg

            last = self._last_interviewer_message(db, session.id)
            if last:
                return last

        reply: str | None = None
        if session.questions_asked_count == 0 or session.current_question_id is None:
            q = self._pick_next_main_question(db, session)
            if not q:
                msg = "No questions found for this track/style/difficulty. Please ask admin to load questions."
                message_crud.add_message(db, session.id, "system", msg)
                return msg

            self._reset_for_new_question(db, session, q.id)
            self._set_question_type_state(db, session, q)
            session_question_crud.mark_question_asked(db, session.id, q.id)
            with contextlib.suppress(Exception):
                user_question_seen_crud.mark_question_seen(db, session.user_id, q.id)
            self._increment_questions_asked(db, session)

            # Only use the intro line if warmup was genuinely skipped (no warmup messages in history).
            # After a normal warmup flow, intro_used is always True — this guard prevents mid-interview
            # re-introductions if the flag was somehow not persisted.
            _, warm_done_check = interview_warmup.get_state(session)
            if not preface and not self._intro_used(session) and not warm_done_check:
                intro_line = self._interviewer_intro_line(session)
                if intro_line:
                    preface = intro_line
                    with contextlib.suppress(Exception):
                        self._set_intro_used(db, session)
            # Always mark intro as used once the first question is being presented.
            with contextlib.suppress(Exception):
                self._set_intro_used(db, session)
            sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session), self._interviewer_id(session))
            title, prompt = self._render_question(session, q)
            qt = self._question_type(q)
            if self._is_behavioral(q):
                user = f"""
The warmup conversation just finished. Transition directly into the first question.
Do NOT re-introduce yourself or say "nice to meet you" — you've already met during warmup.
Present the behavioral question conversationally — like a real interviewer asking, not reading from a list.
If a preface is provided, lead with it naturally before the question.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()
            elif qt == "conceptual":
                user = f"""
The warmup conversation just finished. Transition directly into the first question.
Do NOT re-introduce yourself — you've already met during warmup.
Ask about the concept in a natural, conversational way. Don't follow the same formula every time.
If a preface is provided, lead with it naturally before the question.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()
            elif qt == "system_design":
                user = f"""
The warmup conversation just finished. Transition directly into the first question.
Do NOT re-introduce yourself — you've already met during warmup.
Present the system design scenario naturally. Ask where they'd like to start — requirements, constraints, or high-level design.
If a preface is provided, lead with it naturally before the question.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()
            else:
                user = f"""
The warmup conversation just finished. Transition directly into the first coding question.
Do NOT re-introduce yourself — you've already met during warmup.
Present the problem naturally — like handing it off mid-conversation, not reading a script.
Do NOT ask "could you restate the problem" — find a more natural entry point. Vary how you open each problem.
If a preface is provided, lead with it naturally before the question.
Preface (say this first if provided): {preface or ""}
Do NOT use markdown or labels like "Title:" or "Prompt:".

Question context: {self._combine_question_text(title, prompt)}
""".strip()

            try:
                reply = await self.llm.chat(sys, user)
                reply = self._sanitize_ai_text(reply)
            except LLMClientError:
                q_title, q_prompt = self._render_question(session, q)
                q2 = Question(
                    id=q.id,
                    track=q.track,
                    company_style=q.company_style,
                    difficulty=q.difficulty,
                    title=q_title,
                    prompt=q_prompt,
                    tags_csv=q.tags_csv,
                    followups=[self._render_text(session, str(x)) for x in (getattr(q, "followups", []) or [])],
                )
                reply = self._offline_intro(q2, user_name=user_name, preface=preface)
            reply = self._ensure_question_in_reply(reply, title, prompt)
            if preface:
                cleaned = preface.strip()
                if cleaned and cleaned.lower() not in (reply or "").lower():
                    reply = f"{cleaned}\n\n{reply}"

        if reply is None:
            last = self._last_interviewer_message(db, session.id)
            if last:
                return last
            msg = "No interviewer message available. Please send a response or restart the session."
            message_crud.add_message(db, session.id, "system", msg)
            return msg

        message_crud.add_message(db, session.id, "interviewer", reply)
        session_crud.update_stage(db, session, "candidate_solution")
        return reply

    async def handle_student_message(
        self, db: Session, session: InterviewSession, student_text: str, user_name: str | None = None
    ) -> str:
        """
        Store student message and decide next interviewer reply.
        Order of operations:
        1) Persist student text.
        2) Apply quick human-like heuristics (move on / don't know / non-informative / vague).
        3) Delegate to controller LLM for structured action selection.
        4) Use dataset followups / safe defaults if the LLM is unavailable.
        """
        if student_text and student_text.strip():
            message_crud.add_message(db, session.id, "student", student_text.strip())

        warm_step, warm_done = interview_warmup.get_state(session)
        stage = session.stage or "intro"

        # Handle behavioral warmup stage with smart intent detection
        if stage == "warmup_behavioral" and not warm_done:
            # Check if user wants clarification/repetition
            intent_classification = await self._classify_user_intent(student_text, question_context="Behavioral warmup question")
            if intent_classification and intent_classification.confidence >= 0.6:
                if intent_classification.intent == "clarification":
                    # Repeat the behavioral question
                    msgs = message_crud.list_messages(db, session.id, limit=10)
                    behavioral_question = None
                    for m in reversed(msgs):
                        if m.role == "interviewer" and ("tell me about" in m.content.lower() or "describe a time" in m.content.lower()):
                            behavioral_question = m.content
                            break
                    if behavioral_question:
                        clarify_reply = f"Of course! Here's the question again:\n\n{behavioral_question}"
                        message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                        return clarify_reply

            # Normal flow: user answered behavioral, move on
            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                with contextlib.suppress(Exception):
                    self._store_focus(db, session, focus)
            preface = self._warmup_behavioral_ack(student_text)
            self._set_warmup_state(db, session, max(warm_step, 3), True)
            session_crud.update_stage(db, session, "warmup_done")
            return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=preface)

        if not warm_done and (stage in (None, "", "intro", "warmup", "warmup_smalltalk")) and stage != "warmup_done":
            # Warmup flow: greet, then a short small-talk question, then a behavioral warmup question.

            # SMART INTENT: Check if user is asking for clarification/repetition during warmup
            if warm_step > 0:  # After initial greeting
                intent_classification = await self._classify_user_intent(student_text, question_context="Warmup conversation")
                if intent_classification and intent_classification.confidence >= 0.6:
                    if intent_classification.intent == "clarification":
                        # User asking to repeat during warmup - use natural response
                        msgs = message_crud.list_messages(db, session.id, limit=5)
                        last_interviewer_msg = None
                        for m in reversed(msgs):
                            if m.role == "interviewer":
                                last_interviewer_msg = m.content
                                break
                        if last_interviewer_msg:
                            clarify_reply = f"Of course! I asked: {last_interviewer_msg}"
                            message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                            return clarify_reply

            focus = self._extract_focus(student_text)
            has_focus = bool(focus.get("dimensions") or focus.get("tags"))
            if has_focus:
                with contextlib.suppress(Exception):
                    self._store_focus(db, session, focus)

            if warm_step <= 0:
                msg = await self._warmup_prompt(session, user_name=user_name)
                message_crud.add_message(db, session.id, "interviewer", msg)
                with contextlib.suppress(Exception):
                    self._set_intro_used(db, session)
                self._set_warmup_state(db, session, 1, False)
                session_crud.update_stage(db, session, "warmup")
                return msg

            if warm_step == 1:
                # Step 1: User responded to greeting — generate a genuine, contextual reply.
                t_lower = student_text.lower()
                is_reciprocal = any(phrase in t_lower for phrase in [
                    "how are you", "how about you", "what about you", "how is your",
                    "how's your", "and you", "yourself"
                ])

                # Classify tone/topic so we can pick a natural follow-up question.
                profile = await self._classify_warmup_smalltalk(student_text)
                question = self._smalltalk_question(profile, student_text)
                tone = profile.tone if profile else None
                topic = (profile.topic if profile else None) or self._infer_smalltalk_topic(student_text)

                # Let the LLM craft a genuine, contextual reply — no more hardcoded strings.
                msg = await self._warmup_generate_contextual_reply(
                    session=session,
                    student_text=student_text,
                    user_name=user_name,
                    follow_up_question=question,
                    is_reciprocal=is_reciprocal,
                    tone=tone,
                )
                meta: dict[str, Any] = {
                    "smalltalk_question": question,
                    "smalltalk_topic": topic,
                }
                if profile:
                    meta.update({
                        "tone": profile.tone,
                        "energy": profile.energy,
                        "tone_confidence": profile.confidence,
                    })
                message_crud.add_message(db, session.id, "interviewer", msg)
                self._set_warmup_state(db, session, 2, False, **meta)
                session_crud.update_stage(db, session, "warmup_smalltalk")
                return msg

            # Step 2+: User responded to smalltalk — check for reciprocal or transition to behavioral.
            if warm_step == 2:
                t_lower = student_text.lower()
                is_reciprocal = any(phrase in t_lower for phrase in [
                    "how are you", "how about you", "what about you", "how is your",
                    "how's your", "and you", "yourself", "what about your", "asked you"
                ])

                if is_reciprocal:
                    # User still chatting — respond genuinely, then transition.
                    behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
                    tone_from_state = self._warmup_profile_from_state(session)
                    tone_val = tone_from_state.tone if tone_from_state else None

                    if behavioral_target <= 0:
                        natural_response = await self._warmup_generate_contextual_reply(
                            session=session,
                            student_text=student_text,
                            user_name=user_name,
                            follow_up_question=None,
                            is_reciprocal=True,
                            tone=tone_val,
                        )
                        self._set_warmup_state(db, session, 3, True)
                        session_crud.update_stage(db, session, "warmup_done")
                        return await self.ensure_question_and_intro(
                            db, session, user_name=user_name, preface=natural_response
                        )
                    else:
                        question_text, qid = self._warmup_behavioral_question(db, session)
                        msg = await self._warmup_generate_contextual_reply(
                            session=session,
                            student_text=student_text,
                            user_name=user_name,
                            follow_up_question=question_text,
                            is_reciprocal=True,
                            tone=tone_val,
                        )
                        message_crud.add_message(db, session.id, "interviewer", msg)
                        self._set_warmup_state(db, session, 3, False)
                        session_crud.update_stage(db, session, "warmup_behavioral")
                        self._mark_warmup_behavioral_asked(db, session, qid)
                        return msg

            # Normal flow: transition to behavioral question
            behavioral_target = int(getattr(session, "behavioral_questions_target", 0) or 0)
            tone_line = self._warmup_transition_line(self._warmup_profile_from_state(session))
            if behavioral_target <= 0:
                # Skip behavioral warmup if none are requested.
                self._set_warmup_state(db, session, max(warm_step, 3), True)
                session_crud.update_stage(db, session, "warmup_done")
                return await self.ensure_question_and_intro(db, session, user_name=user_name, preface=tone_line)

            msg = await self._warmup_reply(
                session=session,
                student_text=student_text,
                user_name=user_name,
                focus=focus,
                db=db,
                tone_line=tone_line,
            )
            message_crud.add_message(db, session.id, "interviewer", msg)
            self._set_warmup_state(db, session, max(warm_step, 3), False)
            session_crud.update_stage(db, session, "warmup_behavioral")
            return msg

        q = question_crud.get_question(db, session.current_question_id) if session.current_question_id else None
        if q:
            if self._is_behavioral(q):
                allowed_tracks = {session.track, "behavioral"}
                if q.track not in allowed_tracks:
                    q = None
            else:
                if q.track != session.track:
                    q = None
            if q:
                desired_diff = (session.difficulty or "easy").strip().lower()
                if (q.difficulty or "").strip().lower() != desired_diff:
                    q = None
            if q:
                allowed_company = (session.company_style or "").strip().lower() or "general"
                if (q.company_style or "").strip().lower() != allowed_company:
                    q = None

        if q:
            qt, qp = self._render_question(session, q)
            question_context = f"\nQuestion: {qt}\n{qp}\n"
        else:
            question_context = ""

        msgs = message_crud.list_messages(db, session.id, limit=30)
        history: list[dict] = []
        for m in msgs:
            if m.role == "student":
                history.append({"role": "user", "content": m.content})
            elif m.role == "interviewer":
                history.append({"role": "assistant", "content": m.content})

        sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session), self._interviewer_id(session))

        stage = session.stage or "intro"
        max_followups = int(session.max_followups_per_question or 2)
        max_questions = int(session.max_questions or 7)
        min_questions = 5

        if not q:
            # Clear stale question so we can pick a new one.
            session.current_question_id = None
            db.add(session)
            db.commit()
            db.refresh(session)
            return await self.ensure_question_and_intro(db, session, user_name=user_name)

        if stage in ("followups", "candidate_solution") and self._max_followups_reached(session):
            stage = "next_question"

        # SMART INTENT DETECTION: Use AI to understand what user wants (like a human would)
        intent_classification = await self._classify_user_intent(student_text, question_context)

        if intent_classification and intent_classification.confidence >= 0.6:
            intent = intent_classification.intent

            # Handle clarification requests
            if intent == "clarification":
                qt, qp = self._render_question(session, q)
                clarify_reply = f"Of course! Let me restate the question:\n\n**{qt}**\n\n{qp}\n\nTake your time thinking through it."
                message_crud.add_message(db, session.id, "interviewer", clarify_reply)
                # Don't increment followups for clarification requests
                return clarify_reply

            # Handle explicit move-on requests
            if intent == "move_on":
                reason = "move_on"
                preface = self._transition_preface(session, reason=reason)
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

            # Handle "don't know" responses
            if intent == "dont_know":
                reason = "dont_know"
                preface = self._transition_preface(session, reason=reason)
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        # Fallback checks for very short/empty responses (keep as safety net)
        if self._is_non_informative(student_text):
            tokens = self._clean_tokens(student_text)
            if len(tokens) <= 2:
                preface = self._transition_preface(session, reason="move_on")
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            reply = "I'll need a fuller response before we move on. Please outline your approach, key steps, and any assumptions."
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if self._is_vague(student_text):
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            reply = "Can you add more detail on your approach, complexity, and edge cases before we move on?"
            message_crud.add_message(db, session.id, "interviewer", reply)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return reply

        if stage == "next_question":
            preface = self._transition_preface(session)
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        signals = self._candidate_signals(student_text)
        is_behavioral = self._is_behavioral(q)
        is_conceptual = self._is_conceptual_question(q)
        behavioral_missing = self._behavioral_missing_parts(student_text) if is_behavioral else []
        missing_keys_all = self._missing_focus_keys(q, signals, behavioral_missing)
        focus_keys = self._question_focus_keys(q)
        missing_keys_all = self._prioritize_missing_focus(missing_keys_all, session, prefer=focus_keys)

        response_quality = self._response_quality(
            student_text,
            signals,
            is_behavioral,
            behavioral_missing,
            is_conceptual=is_conceptual,
        )

        last_overall = self._skill_last_overall(session)
        if (
            response_quality == "weak"
            and last_overall is not None
            and last_overall >= 8.0
            and not is_behavioral
            and "tradeoffs" not in missing_keys_all
            and not signals.get("mentions_tradeoffs")
        ):
            missing_keys_all = ["tradeoffs"] + missing_keys_all
        critical_missing, optional_missing = self._missing_focus_tiers(
            missing_keys_all,
            is_behavioral,
            behavioral_missing,
        )
        missing_keys = missing_keys_all
        if response_quality == "strong":
            missing_keys = critical_missing
        elif response_quality == "ok":
            missing_keys = critical_missing

        missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)
        signal_summary = self._signal_summary(signals, missing_keys, behavioral_missing)
        skill_summary = self._skill_summary(session)

        if self._is_off_topic(q, student_text, signals):
            reanchor_count = self._get_reanchor_count(session, q.id)
            if reanchor_count < 1 and not self._max_followups_reached(session):
                nudge = "I may be missing how that answers the question. Can you restate the problem and outline your approach?"
                message_crud.add_message(db, session.id, "interviewer", nudge)
                self._increment_followups_used(db, session)
                self._set_reanchor_count(db, session, q.id, reanchor_count + 1)
                session_crud.update_stage(db, session, "followups")
                return nudge
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please answer the next question directly."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        thin_response = self._is_thin_response(
            student_text,
            signals,
            is_behavioral,
            behavioral_missing,
            is_conceptual=is_conceptual,
        )

        if thin_response:
            if self._max_followups_reached(session):
                preface = "Let's move on for now. Please share more detail in your next response."
                session_crud.update_stage(db, session, "next_question")
                return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)
            nudge = self._soft_nudge_prompt(is_behavioral, missing_keys, behavioral_missing)
            message_crud.add_message(db, session.id, "interviewer", nudge)
            self._increment_followups_used(db, session)
            session_crud.update_stage(db, session, "followups")
            return nudge

        prefer_move_on = response_quality in ("strong", "ok") and not critical_missing

        if int(session.followups_used or 0) == 0 and not self._max_followups_reached(session):
            force_followup = False
            if is_behavioral:
                force_followup = len(behavioral_missing) >= 2
            elif not is_conceptual:
                force_followup = "approach" in critical_missing or "correctness" in critical_missing
            if not is_conceptual and signals.get("has_code") and not signals.get("mentions_approach"):
                force_followup = True
            if force_followup:
                targeted = None
                if is_behavioral and behavioral_missing:
                    targeted = self._missing_focus_question("star", behavioral_missing)
                elif not is_conceptual and signals.get("has_code") and not signals.get("mentions_approach"):
                    targeted = "Walk me through your approach and key steps."
                else:
                    targeted = self._phase_followup(
                        q,
                        signals,
                        session,
                        int(session.followups_used or 0),
                    )
                    if not targeted and missing_keys:
                        targeted = self._missing_focus_question(missing_keys[0], behavioral_missing)

                if targeted:
                    message_crud.add_message(db, session.id, "interviewer", targeted)
                    self._increment_followups_used(db, session)
                    session_crud.update_stage(db, session, "followups")
                    return targeted

        # Get RAG context for smarter follow-ups (Phase 5)
        rag_context = _get_rag_context_for_interview(db, session.id)

        # Build cross-question intelligence context
        session_patterns = self._session_patterns_summary(session)
        hint_level = self._get_hint_level(session, q.id)
        # Escalate hint level when candidate is stuck (weak quality + has had a followup already)
        if response_quality == "weak" and int(session.followups_used or 0) >= 1:
            hint_level = self._increment_hint_level(db, session, q.id)

        ctrl_sys = interviewer_controller_system_prompt(session.company_style, session.role, rag_context=rag_context)
        ctrl_user = interviewer_controller_user_prompt(
            stage=stage,
            question_title=self._render_text(session, q.title),
            question_prompt=self._render_text(session, q.prompt),
            candidate_latest=student_text,
            followups_used=int(session.followups_used or 0),
            max_followups=max_followups,
            questions_asked_count=int(session.questions_asked_count or 0),
            max_questions=max_questions,
            signal_summary=signal_summary or None,
            missing_focus=missing_focus or None,
            skill_summary=skill_summary or None,
            response_quality=response_quality,
            is_behavioral=is_behavioral,
            question_type=self._question_type(q),
            session_patterns=session_patterns,
            hint_level=hint_level,
        )

        intent = ""
        confidence = 0.6
        next_focus = None
        coverage = {}
        missing_focus_llm: list[str] = []
        try:
            data = await self.llm.chat_json(ctrl_sys, ctrl_user, history=history)
            ctrl = InterviewControllerOutput.model_validate(data)
            action = ctrl.action
            message = self._sanitize_ai_text((ctrl.message or "").strip())
            done_with_question = bool(ctrl.done_with_question)
            allow_second_followup = bool(ctrl.allow_second_followup)
            quick_rubric_raw = ctrl.quick_rubric.model_dump()
            intent = (ctrl.intent or "").strip().upper() if ctrl.intent else ""
            confidence = float(ctrl.confidence or 0.6)
            next_focus = ctrl.next_focus
            coverage = ctrl.coverage or {}
            missing_focus_llm = ctrl.missing_focus or []
        except Exception:
            action = ""
            message = ""
            done_with_question = False
            allow_second_followup = False
            quick_rubric_raw = None
            coverage = {}
            missing_focus_llm = []

        # Store rolling rubric (used later for adaptive difficulty and weakness targeting).
        if student_text and student_text.strip():
            with contextlib.suppress(Exception):
                self._update_skill_state(db, session, quick_rubric_raw, is_behavioral=self._is_behavioral(q))
            # Accumulate cross-question patterns for future controller context.
            with contextlib.suppress(Exception):
                self._update_session_patterns(db, session, signals, q, response_quality)

        if intent == "WRAP_UP":
            action = "WRAP_UP"
        elif intent == "ADVANCE" and action == "FOLLOWUP":
            action = "MOVE_TO_NEXT_QUESTION"
        elif intent in ("CLARIFY", "DEEPEN", "CHALLENGE") and action in ("MOVE_TO_NEXT_QUESTION", "WRAP_UP"):
            action = "FOLLOWUP"

        if confidence < 0.5:
            allow_second_followup = False
        if confidence < 0.3 and action == "FOLLOWUP" and int(session.followups_used or 0) >= 1:
            action = "MOVE_TO_NEXT_QUESTION"

        if confidence >= 0.55:
            if missing_focus_llm:
                missing_keys = self._prioritize_missing_focus(missing_focus_llm, session, prefer=focus_keys)
                missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)
            elif coverage:
                inferred = self._missing_from_coverage(coverage, is_behavioral)
                if inferred:
                    missing_keys = self._prioritize_missing_focus(inferred, session, prefer=focus_keys)
                    missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)

        if response_quality in ("strong", "ok") and missing_keys:
            crit_after, opt_after = self._missing_focus_tiers(missing_keys, is_behavioral, behavioral_missing)
            if response_quality == "strong":
                missing_keys = crit_after
            else:
                limited: list[str] = []
                for key in crit_after + opt_after[:1]:
                    if key not in limited:
                        limited.append(key)
                missing_keys = limited
            missing_focus = self._missing_focus_summary(missing_keys, behavioral_missing)

        critical_missing, _ = self._missing_focus_tiers(missing_keys, is_behavioral, behavioral_missing)
        clarify_attempts, _ = self._update_clarify_tracking(db, session, q.id, critical_missing)
        if not critical_missing and response_quality in ("strong", "ok") and int(session.followups_used or 0) == 0:
            if action == "FOLLOWUP":
                action = "MOVE_TO_NEXT_QUESTION"

        # Phase 4: Check rubric-based gaps for smarter follow-ups
        rubric_gaps = self._critical_rubric_gaps(session, threshold=5)
        for gap in rubric_gaps:
            if gap not in critical_missing:
                critical_missing.append(gap)

        force_clarify = (
            bool(critical_missing)
            and not self._max_followups_reached(session)
            and clarify_attempts < 2
        )
        if force_clarify:
            if action in ("MOVE_TO_NEXT_QUESTION", "WRAP_UP"):
                action = "FOLLOWUP"
            if int(session.followups_used or 0) >= 1:
                allow_second_followup = True
            if not message:
                message = self._missing_focus_question(critical_missing[0], behavioral_missing) or ""
        elif critical_missing and clarify_attempts >= 2 and action == "FOLLOWUP":
            action = "MOVE_TO_NEXT_QUESTION"

        # Phase 4: Allow second follow-up when confidence is low or missing critical rubric focus
        if (
            int(session.followups_used or 0) == 1
            and not self._max_followups_reached(session)
            and action == "FOLLOWUP"
            and not allow_second_followup
        ):
            if confidence < 0.6:
                allow_second_followup = True
            elif intent == "DEEPEN" and (rubric_gaps or critical_missing):
                allow_second_followup = True

        if prefer_move_on and action == "FOLLOWUP" and not force_clarify:
            action = "MOVE_TO_NEXT_QUESTION"
            message = ""

        if not message:
            focus_key = self._normalize_focus_key(next_focus)
            if focus_key:
                message = self._missing_focus_question(focus_key, behavioral_missing) or ""

        if not message and isinstance(getattr(q, "followups", None), list) and q.followups:
            idx = int(session.followups_used or 0)
            if 0 <= idx < len(q.followups):
                message = self._render_text(session, str(q.followups[idx]).strip())

        if not message:
            message = (
                self._phase_followup(
                    q,
                    signals,
                    session,
                    int(session.followups_used or 0),
                )
                or ""
            )

        if not message:
            missing_line = f"Missing focus: {missing_focus}" if missing_focus else ""
            user_prompt = f"""
Continue the interview.
{question_context}
Ask ONE follow-up question based on the candidate's latest response.
Prefer: constraints, approach clarity, complexity, edge cases, optimization.
{missing_line}
""".strip()
            try:
                message = await self.llm.chat(sys, user_prompt, history=history)
                message = self._sanitize_ai_text(message)
            except LLMClientError:
                if missing_keys:
                    message = self._missing_focus_question(missing_keys[0], behavioral_missing) or ""
                if not message:
                    if self._is_behavioral(q):
                        message = "What was the outcome, and what did you learn from that experience?"
                    else:
                        message = "What is the time complexity of your approach, and what edge cases would you test?"
            action = "FOLLOWUP"

        if action == "WRAP_UP" and int(session.questions_asked_count or 0) >= min_questions:
            message_crud.add_message(db, session.id, "interviewer", message)
            session_crud.update_stage(db, session, "wrapup")
            return message
        if action == "WRAP_UP" and int(session.questions_asked_count or 0) < min_questions:
            action = "MOVE_TO_NEXT_QUESTION"

        if done_with_question and action not in ("WRAP_UP",) and not force_clarify:
            action = "MOVE_TO_NEXT_QUESTION"

        # Followups are short by design: mostly 1; allow 2 only if explicitly requested.
        if action == "FOLLOWUP" and int(session.followups_used or 0) >= 1 and not allow_second_followup:
            action = "MOVE_TO_NEXT_QUESTION"

        if action == "MOVE_TO_NEXT_QUESTION" or self._max_followups_reached(session):
            session_crud.update_stage(db, session, "next_question")
            preface = self._transition_preface(session)
            return await self._advance_to_next_question(db, session, history, user_name=user_name, preface=preface)

        self._increment_followups_used(db, session)
        message_crud.add_message(db, session.id, "interviewer", message)
        session_crud.update_stage(db, session, "followups")
        return message
