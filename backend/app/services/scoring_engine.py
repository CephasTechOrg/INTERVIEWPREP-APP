import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud import evaluation as evaluation_crud
from app.crud import message as message_crud
from app.crud import session_question as session_question_crud
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.services.llm_client import DeepSeekClient, LLMClientError
from app.services.llm_schemas import EvaluationOutput
from app.services.prompt_templates import evaluator_system_prompt, evaluator_user_prompt
from app.services.rubric_loader import build_rubric_context

logger = logging.getLogger(__name__)


class ScoringEngine:
    def __init__(self) -> None:
        self.llm = DeepSeekClient()

    def _fallback_evaluation_data(self) -> dict:
        # Minimal offline fallback so the UI never gets a 502 for evaluation.
        # Keep it conservative and clearly generic.
        return {
            "overall_score": 50,
            "rubric": {
                "communication": 5,
                "problem_solving": 5,
                "correctness_reasoning": 5,
                "complexity": 5,
                "edge_cases": 5,
            },
            "strengths": ["Clear attempt to explain the approach."],
            "weaknesses": ["AI evaluation unavailable; results are a placeholder."],
            "next_steps": [
                "Retry Finalize after fixing the AI key/service.",
                "Practice explaining trade-offs and edge cases.",
            ],
        }

    async def finalize(self, db: Session, session_id: int) -> dict:
        msgs = message_crud.list_messages(db, session_id, limit=200)

        transcript_lines = []
        for m in msgs:
            speaker = "INTERVIEWER" if m.role == "interviewer" else "CANDIDATE" if m.role == "student" else "SYSTEM"
            transcript_lines.append(f"{speaker}: {m.content}")
        transcript = "\n".join(transcript_lines)

        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        track = session.track if session else None

        include_behavioral = False
        try:
            asked_ids = session_question_crud.list_asked_question_ids(db, session_id)
            if asked_ids:
                rows = db.query(Question.tags_csv).filter(Question.id.in_(asked_ids)).all()
                for (tags_csv,) in rows:
                    if "behavioral" in (tags_csv or "").lower():
                        include_behavioral = True
                        break
        except Exception:
            include_behavioral = False

        rubric_context = ""
        try:
            rubric_context = build_rubric_context(track, include_behavioral=include_behavioral)
        except Exception:
            rubric_context = ""

        sys = evaluator_system_prompt()
        user = evaluator_user_prompt(transcript, rubric_context=rubric_context or None)

        try:
            data = await self.llm.chat_json(sys, user)
            parsed = EvaluationOutput.model_validate(data)
        except (LLMClientError, ValidationError):
            logger.exception("Evaluation fallback used for session_id=%s", session_id)
            parsed = EvaluationOutput.model_validate(self._fallback_evaluation_data())

        overall_score = int(parsed.overall_score or 0)
        rubric = parsed.rubric.model_dump()
        summary = {
            "strengths": parsed.strengths,
            "weaknesses": parsed.weaknesses,
            "next_steps": parsed.next_steps,
        }

        evaluation_crud.upsert_evaluation(db, session_id, overall_score, rubric, summary)
        logger.info("Evaluation stored session_id=%s score=%s", session_id, overall_score)
        return {"overall_score": overall_score, "rubric": rubric, "summary": summary}
