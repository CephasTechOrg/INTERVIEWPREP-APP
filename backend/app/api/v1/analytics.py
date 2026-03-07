from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud import session as session_crud
from app.crud.evaluation import get_evaluation
from app.crud.interview_level_outcome import get_level_outcome_by_session
from app.schemas.evaluation import EvaluationOut
from app.schemas.interview_level_outcome import InterviewLevelOutcomeOut

router = APIRouter(prefix="/analytics")


@router.get("/sessions/{session_id}/results", response_model=EvaluationOut)
def get_results(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    ev = get_evaluation(db, session_id)
    if not ev:
        raise HTTPException(status_code=404, detail="No evaluation yet.")
    return EvaluationOut(session_id=session_id, overall_score=ev.overall_score, rubric=ev.rubric, summary=ev.summary)


@router.get("/sessions/{session_id}/level-calibration", response_model=InterviewLevelOutcomeOut)
def get_level_calibration(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get the level calibration assessment for an interview session."""
    s = session_crud.get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    level_outcome = get_level_outcome_by_session(db, str(session_id))
    if not level_outcome:
        raise HTTPException(status_code=404, detail="Level calibration not yet generated.")
    
    return level_outcome
