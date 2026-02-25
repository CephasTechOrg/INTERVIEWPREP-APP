from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.user import update_user_profile
from app.schemas.profile import UserProfileOut, UserProfileUpdate
from app.services.storage_service import upload_avatar

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


@router.post("/me/avatar", response_model=UserProfileOut)
async def upload_avatar_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload or replace the current user's profile photo."""
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB).")

    public_url = upload_avatar(file_bytes, content_type, user.id)
    if not public_url:
        raise HTTPException(status_code=500, detail="Avatar upload failed. Check Supabase configuration.")

    current_profile = dict(getattr(user, "profile", {}) or {})
    current_profile["avatar_url"] = public_url

    updated = update_user_profile(db, user, profile=current_profile)
    return UserProfileOut(
        email=updated.email,
        full_name=getattr(updated, "full_name", None),
        role_pref=getattr(updated, "role_pref", None),
        profile=getattr(updated, "profile", None) or {},
    )


@router.post("/deactivate")
def deactivate_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    now = datetime.now(UTC).isoformat()
    update_user_profile(db, user, profile={"deactivated": True, "deactivated_at": now})
    return {"ok": True, "message": "Account deactivated."}
