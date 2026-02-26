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


def _get_rag_context_safe(db: Session, session_id: int) -> str | None:
    """Safely get RAG context, returning None if unavailable."""
    try:
        from app.services.rag_service import get_rag_context_for_session
        context_text, _context_meta = get_rag_context_for_session(db, session_id)
        if context_text:
            logger.info("RAG context retrieved for session_id=%s (%d chars)", session_id, len(context_text))
        return context_text
    except Exception as e:
        logger.debug("RAG context unavailable for session_id=%s: %s", session_id, e)
        return None


def _trigger_embedding_generation(db: Session, session_id: int) -> None:
    """Trigger embedding generation for a completed session."""
    try:
        from app.services.session_embedder import embed_completed_session
        result = embed_completed_session(db, session_id)
        if result:
            logger.info(
                "Session embeddings created for session_id=%s: session=%s, responses=%d",
                session_id, 
                result.get("session_embedded", False),
                result.get("response_examples_created", 0)
            )
    except Exception as e:
        logger.debug("Embedding generation skipped for session_id=%s: %s", session_id, e)


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

    def _calibrate_overall_score(self, overall_score: int, rubric: dict) -> int:
        """
        Apply a light calibration so scores are not overly harsh when rubric signals strong performance.
        Keeps adjustments conservative and bounded.
        """
        try:
            scores = [int(v) for v in rubric.values() if isinstance(v, (int, float))]
        except Exception:
            scores = []
        if not scores:
            return overall_score
        avg = sum(scores) / float(len(scores))
        rubric_score = int(round(avg * 10))
        if overall_score < (rubric_score - 5):
            return max(0, min(100, rubric_score - 2))
        return max(0, min(100, overall_score))

    async def finalize(self, db: Session, session_id: int) -> dict:
        msgs = message_crud.list_messages(db, session_id, limit=200)

        transcript_lines = []
        for m in msgs:
            speaker = "INTERVIEWER" if m.role == "interviewer" else "CANDIDATE" if m.role == "student" else "SYSTEM"
            transcript_lines.append(f"{speaker}: {m.content}")
        transcript = "\n".join(transcript_lines)

        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        track = session.track if session else None

        # Extract difficulty info — used to calibrate the evaluator's scoring thresholds.
        difficulty: str = (getattr(session, "difficulty", None) or "medium").strip().lower()
        difficulty_current: str = (getattr(session, "difficulty_current", None) or difficulty).strip().lower()
        adaptive: bool = bool(getattr(session, "adaptive_difficulty_enabled", False))

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

        # Get RAG context from similar sessions (Phase 5)
        rag_context = _get_rag_context_safe(db, session_id)

        sys = evaluator_system_prompt(
            rag_context=rag_context,
            difficulty=difficulty,
            difficulty_current=difficulty_current,
            adaptive=adaptive,
        )
        user = evaluator_user_prompt(
            transcript,
            rubric_context=rubric_context or None,
            difficulty=difficulty,
            adaptive=adaptive,
        )
        logger.info(
            "Evaluating session_id=%s difficulty=%s adaptive=%s",
            session_id, difficulty, adaptive,
        )

        try:
            data = await self.llm.chat_json(sys, user)
            parsed = EvaluationOutput.model_validate(data)
        except (LLMClientError, ValidationError):
            logger.exception("Evaluation fallback used for session_id=%s", session_id)
            parsed = EvaluationOutput.model_validate(self._fallback_evaluation_data())

        overall_score = int(parsed.overall_score or 0)
        rubric = parsed.rubric.model_dump()
        overall_score = self._calibrate_overall_score(overall_score, rubric)
        summary = {
            "strengths": parsed.strengths,
            "weaknesses": parsed.weaknesses,
            "next_steps": parsed.next_steps,
            # Rich evaluation fields (displayed in ResultsSection)
            "hire_signal": parsed.hire_signal,
            "narrative": parsed.narrative,
            "patterns_observed": parsed.patterns_observed,
            "standout_moments": parsed.standout_moments,
        }

        evaluation_crud.upsert_evaluation(db, session_id, overall_score, rubric, summary)
        logger.info("Evaluation stored session_id=%s score=%s hire_signal=%s", session_id, overall_score, parsed.hire_signal)

        # Generate embeddings for this session (Phase 5: builds RAG knowledge base)
        _trigger_embedding_generation(db, session_id)

        return {"overall_score": overall_score, "rubric": rubric, "summary": summary}
