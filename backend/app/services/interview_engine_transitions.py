"""
Transitions Module for Interview Engine.

Handles question advancement, counters, and state transitions.
"""

import contextlib

from sqlalchemy.orm import Session

from app.crud import message as message_crud
from app.crud import session as session_crud
from app.crud import session_question as session_question_crud
from app.crud import user_question_seen as user_question_seen_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services.interview_engine_warmup import InterviewEngineWarmup
from app.services.llm_client import LLMClientError
from app.services.prompt_templates import interviewer_system_prompt


class InterviewEngineTransitions(InterviewEngineWarmup):
    """State transitions and advancement methods."""

    def _increment_questions_asked(self, db: Session, session: InterviewSession) -> None:
        session.questions_asked_count = int(session.questions_asked_count or 0) + 1
        db.add(session)
        db.commit()
        db.refresh(session)

    def _increment_followups_used(self, db: Session, session: InterviewSession) -> None:
        session.followups_used = int(session.followups_used or 0) + 1
        db.add(session)
        db.commit()
        db.refresh(session)

    def _max_questions_reached(self, session: InterviewSession) -> bool:
        max_q = int(session.max_questions or 0)
        if max_q <= 0:
            return False
        return int(session.questions_asked_count or 0) >= max_q

    def _max_followups_reached(self, session: InterviewSession) -> bool:
        max_f = int(session.max_followups_per_question or 0)
        if max_f <= 0:
            return False
        return int(session.followups_used or 0) >= max_f

    def _reset_for_new_question(self, db: Session, session: InterviewSession, question_id: int) -> None:
        session.current_question_id = int(question_id)
        session.followups_used = 0
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        state.pop("reanchor", None)
        state.pop("clarify", None)
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _set_question_type_state(self, db: Session, session: InterviewSession, q: Question) -> None:
        try:
            state = session.skill_state if isinstance(session.skill_state, dict) else {}
        except Exception:
            state = {}
        state = dict(state)
        state["question_type"] = self._question_type(q)
        session.skill_state = state
        db.add(session)
        db.commit()
        db.refresh(session)

    def _last_interviewer_message(self, db: Session, session_id: int) -> str | None:
        msgs = message_crud.list_messages(db, session_id, limit=200)
        for m in reversed(msgs):
            if m.role == "interviewer":
                return m.content
        return None

    async def _ask_new_main_question(
        self,
        db: Session,
        session: InterviewSession,
        q: Question,
        history: list[dict],
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        sys = interviewer_system_prompt(session.company_style, session.role, self._interviewer_name(session))
        title, prompt = self._render_question(session, q)
        question_context = self._combine_question_text(title, prompt)
        if self._is_behavioral(q):
            user = f"""
This is a behavioral question. Ask it clearly and ask the candidate to answer using STAR (Situation, Task, Action, Result).
Avoid extra greetings or transition phrases like "next question".
Do not repeat the question.
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {question_context}
""".strip()
        else:
            user = f"""
Briefly introduce the problem and ask the candidate to clarify constraints.
Ask for a brief plan and key steps, then share "
"complexity, edge cases, and how you'd validate correctness.
Avoid extra greetings or transition phrases like "next question".
Do not repeat the question.
If a preface is provided, say it first.
Do NOT use markdown or labels like "Title:" or "Prompt:".
Preface (optional): {preface or ""}

Question context: {question_context}
""".strip()

        try:
            reply = await self.llm.chat(sys, user, history=history)
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
            reply = self._offline_next_question(q2, user_name=user_name, preface=preface)
        cleaned_reply = self._clean_next_question_reply(reply, user_name=user_name)
        if cleaned_reply:
            reply = cleaned_reply
        reply = self._ensure_question_in_reply(reply, title, prompt)
        if preface:
            cleaned = preface.strip()
            if cleaned and cleaned.lower() not in (reply or "").lower():
                reply = f"{cleaned}\n\n{reply}"
        message_crud.add_message(db, session.id, "interviewer", reply)
        session_crud.update_stage(db, session, "candidate_solution")
        return reply

    async def _advance_to_next_question(
        self,
        db: Session,
        session: InterviewSession,
        history: list[dict],
        user_name: str | None = None,
        preface: str | None = None,
    ) -> str:
        if self._max_questions_reached(session):
            wrap = "Thanks - that's the end of the interview. When you're ready, click Finalize to get your score."
            message_crud.add_message(db, session.id, "interviewer", wrap)
            session_crud.update_stage(db, session, "wrapup")
            return wrap

        # Adaptive difficulty: adjust for the next technical question if appropriate.
        with contextlib.suppress(Exception):
            self._maybe_bump_difficulty_current(db, session)

        next_q = self._pick_next_main_question(db, session)
        if not next_q:
            wrap = "No more questions available. Click Finalize to get your score."
            message_crud.add_message(db, session.id, "interviewer", wrap)
            session_crud.update_stage(db, session, "wrapup")
            return wrap

        self._reset_for_new_question(db, session, next_q.id)
        self._set_question_type_state(db, session, next_q)
        session_question_crud.mark_question_asked(db, session.id, next_q.id)
        with contextlib.suppress(Exception):
            user_question_seen_crud.mark_question_seen(db, session.user_id, next_q.id)
        self._increment_questions_asked(db, session)
        if preface is None:
            preface = self._transition_preface(session)
        return await self._ask_new_main_question(db, session, next_q, history, user_name=user_name, preface=preface)
