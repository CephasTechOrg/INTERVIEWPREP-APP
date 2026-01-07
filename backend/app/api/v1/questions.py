from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.crud.question import list_questions, get_question, count_questions
from app.schemas.question import QuestionOut, QuestionCoverageOut
from app.core.constants import ALLOWED_COMPANY_STYLES, ALLOWED_DIFFICULTIES, ALLOWED_TRACKS

router = APIRouter(prefix="/questions")


@router.get("", response_model=list[QuestionOut])
def get_questions(
    track: str | None = None,
    company_style: str | None = None,
    difficulty: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    t = (track or "").strip().lower() if track else None
    c = (company_style or "").strip().lower() if company_style else None
    d = (difficulty or "").strip().lower() if difficulty else None
    if t and t not in ALLOWED_TRACKS:
        raise HTTPException(status_code=422, detail=f"Invalid track '{track}'.")
    if c and c not in ALLOWED_COMPANY_STYLES:
        raise HTTPException(status_code=422, detail=f"Invalid company_style '{company_style}'.")
    if d and d not in ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=422, detail=f"Invalid difficulty '{difficulty}'.")
    qs = list_questions(db, t, c, d)
    return [
        QuestionOut(
            id=q.id,
            track=q.track,
            company_style=q.company_style,
            difficulty=q.difficulty,
            title=q.title,
            prompt=q.prompt,
            tags=q.tags(),
            question_type=getattr(q, "question_type", None),
        )
        for q in qs
    ]


@router.get("/coverage", response_model=QuestionCoverageOut)
def get_question_coverage(
    track: str,
    company_style: str,
    difficulty: str,
    include_behavioral: bool = False,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    t = (track or "").strip().lower()
    c = (company_style or "").strip().lower()
    d = (difficulty or "").strip().lower()
    if t not in ALLOWED_TRACKS:
        raise HTTPException(status_code=422, detail=f"Invalid track '{track}'.")
    if c not in ALLOWED_COMPANY_STYLES:
        raise HTTPException(status_code=422, detail=f"Invalid company_style '{company_style}'.")
    if d not in ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=422, detail=f"Invalid difficulty '{difficulty}'.")

    count = count_questions(
        db,
        track=t,
        company_style=c,
        difficulty=d,
        exclude_behavioral=not include_behavioral,
    )
    fallback = 0
    if c != "general":
        fallback = count_questions(
            db,
            track=t,
            company_style="general",
            difficulty=d,
            exclude_behavioral=not include_behavioral,
        )
    return QuestionCoverageOut(
        track=t,
        company_style=c,
        difficulty=d,
        count=int(count or 0),
        fallback_general=int(fallback or 0),
    )


@router.get("/{question_id}", response_model=QuestionOut)
def get_question_by_id(
    question_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = get_question(db, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")
    return QuestionOut(
        id=q.id,
        track=q.track,
        company_style=q.company_style,
        difficulty=q.difficulty,
        title=q.title,
        prompt=q.prompt,
        tags=q.tags(),
        question_type=getattr(q, "question_type", None),
    )
