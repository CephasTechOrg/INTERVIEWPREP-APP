import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.crud import session as session_crud
from app.schemas.session import CreateSessionRequest, SessionOut, SessionSummaryOut
from app.schemas.message import SendMessageRequest, MessageOut, MessageHistoryOut
from app.services.interview_engine import InterviewEngine
from app.core.constants import ALLOWED_COMPANY_STYLES, ALLOWED_DIFFICULTIES, ALLOWED_TRACKS
from app.services.scoring_engine import ScoringEngine
from app.services.llm_client import LLMClientError
from app.crud.message import list_messages
from app.crud.evaluation import get_evaluation
from app.crud import message as message_crud

router = APIRouter(prefix="/sessions")

engine = InterviewEngine()
scorer = ScoringEngine()

logger = logging.getLogger(__name__)


def _validate_session_inputs(track: str, company_style: str, difficulty: str) -> None:
    if track not in ALLOWED_TRACKS:
        raise HTTPException(status_code=422, detail=f"Invalid track '{track}'.")
    if company_style not in ALLOWED_COMPANY_STYLES:
        raise HTTPException(status_code=422, detail=f"Invalid company_style '{company_style}'.")
    if difficulty not in ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=422, detail=f"Invalid difficulty '{difficulty}'.")


@router.get("", response_model=list[SessionSummaryOut])
def list_user_sessions(limit: int = 50, db: Session = Depends(get_db), user=Depends(get_current_user)):
    sessions = session_crud.list_sessions(db, user_id=user.id, limit=limit)
    out: list[SessionSummaryOut] = []
    for s in sessions:
        ev = get_evaluation(db, s.id)
        out.append(
            SessionSummaryOut(
                id=s.id,
                role=s.role,
                track=s.track,
                company_style=s.company_style,
                difficulty=s.difficulty,
                stage=s.stage,
                current_question_id=s.current_question_id,
                questions_asked_count=int(getattr(s, "questions_asked_count", 0) or 0),
                max_questions=int(getattr(s, "max_questions", 7) or 7),
                behavioral_questions_target=int(getattr(s, "behavioral_questions_target", 2) or 2),
                overall_score=ev.overall_score if ev else None,
                created_at=getattr(s, "created_at", None),
            )
        )
    return out


@router.get("/{session_id}/messages", response_model=list[MessageHistoryOut])
def list_session_messages(
    session_id: int,
    limit: int = 2000,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    msgs = message_crud.list_messages(db, session_id, limit=limit)
    return [
        MessageHistoryOut(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=getattr(m, "created_at", None),
        )
        for m in msgs
    ]


@router.post("", response_model=SessionOut)
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    track = (payload.track or "").strip().lower()
    company_style = (payload.company_style or "").strip().lower()
    difficulty = (payload.difficulty or "").strip().lower()
    _validate_session_inputs(track, company_style, difficulty)
    s = session_crud.create_session(
        db=db,
        user_id=user.id,
        role=payload.role,
        track=track,
        company_style=company_style,
        difficulty=difficulty,
        behavioral_questions_target=payload.behavioral_questions_target,
    )
    return SessionOut(
        id=s.id,
        role=s.role,
        track=s.track,
        company_style=s.company_style,
        difficulty=s.difficulty,
        stage=s.stage,
        current_question_id=s.current_question_id,
    )


@router.post("/{session_id}/start", response_model=MessageOut)
async def start_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info("Session start requested id=%s user_id=%s", session_id, user.id)
    try:
        await engine.ensure_question_and_intro(db, s, user_name=getattr(user, "full_name", None))
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    # Return latest interviewer message
    msgs = list_messages(db, session_id, limit=200)
    if not msgs:
        raise HTTPException(status_code=500, detail="No messages found for session.")
    last = msgs[-1]
    return MessageOut(
        id=last.id,
        session_id=session_id,
        role=last.role,
        content=last.content,
        current_question_id=getattr(s, "current_question_id", None),
    )


@router.post("/{session_id}/message", response_model=MessageOut)
async def send_message(session_id: int, payload: SendMessageRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info("Session message user_id=%s session_id=%s", user.id, session_id)
    try:
        await engine.handle_student_message(db, s, payload.content, user_name=getattr(user, "full_name", None))
    except LLMClientError as e:
        # return a clear frontend-friendly message (no crash)
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    # Return the interviewer reply we just created
    msgs = list_messages(db, session_id, limit=200)
    if not msgs:
        raise HTTPException(status_code=500, detail="No messages found for session.")
    last = msgs[-1]
    return MessageOut(
        id=last.id,
        session_id=session_id,
        role=last.role,
        content=last.content,
        current_question_id=getattr(s, "current_question_id", None),
    )


@router.post("/{session_id}/finalize")
async def finalize(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info("Session finalize requested user_id=%s session_id=%s", user.id, session_id)
    try:
        result = await scorer.finalize(db, session_id)
    except LLMClientError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    session_crud.update_stage(db, s, "done")
    return result


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        session_crud.delete_session(db, s)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete session.")

    return {"ok": True}
