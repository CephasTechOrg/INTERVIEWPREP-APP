from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.user import update_user_profile
from app.schemas.profile import UserProfileOut, UserProfileUpdate

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserProfileOut)
def get_me(user=Depends(get_current_user)):
    return UserProfileOut(
        email=user.email,
        full_name=getattr(user, "full_name", None),
        role_pref=getattr(user, "role_pref", None),
        profile=getattr(user, "profile", None) or {},
    )


@router.patch("/me", response_model=UserProfileOut)
def update_me(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    updated = update_user_profile(
        db,
        user,
        full_name=payload.full_name,
        role_pref=payload.role_pref,
        profile=payload.profile,
    )
    return UserProfileOut(
        email=updated.email,
        full_name=getattr(updated, "full_name", None),
        role_pref=getattr(updated, "role_pref", None),
        profile=getattr(updated, "profile", None) or {},
    )
