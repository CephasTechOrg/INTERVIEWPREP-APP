from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.rate_limit import rate_limit
from app.core.security import create_access_token
from app.core.email import send_email
from app.crud.user import (
    create_user,
    authenticate,
    get_by_email,
    set_verification_token,
    verify_user,
    set_reset_token,
    reset_password,
)
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    VerifyRequest,
    ResendVerificationRequest,
    ResetRequest,
    PerformResetRequest,
)
from app.utils.audit import log_audit

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    if get_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = create_user(db, payload.email, payload.password, payload.full_name)
    try:
        send_email(
            user.email,
            "Verify your email",
            f"Welcome to InterviewPrep! Verify your account using this token:\n\n{user.verification_token}\n\n",
        )
    except Exception:
        pass
    log_audit(db, "signup", user_id=user.id, metadata={"email": user.email}, request=request)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_verified:
        log_audit(db, "login_unverified", user_id=user.id, metadata={"email": user.email}, request=request)
        raise HTTPException(status_code=403, detail="Email not verified. Check your email for a verification token.")

    log_audit(db, "login", user_id=user.id, metadata={"email": user.email}, request=request)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token)


@router.post("/verify")
def verify(payload: VerifyRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = verify_user(db, payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token.")
    log_audit(db, "verify_email", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = get_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    token = set_verification_token(db, user)
    try:
        send_email(
            user.email,
            "Verify your email",
            f"Verify your account using this token:\n\n{token}\n\n",
        )
    except Exception:
        pass
    log_audit(db, "resend_verification", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}


@router.post("/request-password-reset")
def request_password_reset(payload: ResetRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = get_by_email(db, payload.email)
    if not user:
        # do not reveal existence
        return {"ok": True}
    token = set_reset_token(db, user)
    try:
        send_email(
            user.email,
            "Reset your password",
            f"Use this token to reset your password:\n\n{token}\n\nToken expires in 30 minutes.",
        )
    except Exception:
        pass
    log_audit(db, "request_password_reset", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}


@router.post("/reset-password")
def perform_password_reset(payload: PerformResetRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = reset_password(db, payload.token, payload.new_password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    log_audit(db, "reset_password", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}
