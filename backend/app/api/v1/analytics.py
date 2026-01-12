from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud import session as session_crud
from app.crud.evaluation import get_evaluation
from app.schemas.evaluation import EvaluationOut

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
