from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.crud.evaluation import get_evaluation
from app.schemas.evaluation import EvaluationOut

router = APIRouter(prefix="/analytics")


@router.get("/sessions/{session_id}/results", response_model=EvaluationOut)
def get_results(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ev = get_evaluation(db, session_id)
    if not ev:
        raise HTTPException(status_code=404, detail="No evaluation yet.")
    return EvaluationOut(session_id=session_id, overall_score=ev.overall_score, rubric=ev.rubric, summary=ev.summary)
