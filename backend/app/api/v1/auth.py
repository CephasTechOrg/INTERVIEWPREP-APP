import contextlib
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.rate_limit import rate_limit
from app.core.config import settings
from app.core.email import send_email
from app.core.security import create_access_token, hash_password
from app.crud import pending_signup as pending_signup_crud
from app.crud.user import (
    authenticate,
    create_user_from_hash,
    get_by_email,
    reset_password,
    set_reset_token,
    set_verification_token,
    verify_user,
)
from app.schemas.auth import (
    LoginRequest,
    PerformResetRequest,
    ResendVerificationRequest,
    ResetRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyRequest,
)
from app.utils.audit import log_audit

router = APIRouter(prefix="/auth")


def _rate_key(request: Request, tag: str, email: str | None = None) -> str:
    ip = request.client.host if request and request.client else "unknown"
    e = (email or "").strip().lower()
    if e:
        return f"{tag}:{ip}:{e}"
    return f"{tag}:{ip}"


@router.post("/signup", response_model=SignupResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "signup", email), max_calls=6, window_sec=60)
    if get_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    password_hash = hash_password(payload.password)
    pending, code = pending_signup_crud.upsert_pending_signup(
        db,
        email=email,
        password_hash=password_hash,
        full_name=payload.full_name,
    )
    with contextlib.suppress(Exception):
        send_email(
            email,
            "Verify your email",
            (
                "Welcome to InterviewPrep! Use this 6-digit code to finish your signup:\n\n"
                f"{code}\n\n"
                "This code expires in 30 minutes."
            ),
        )
    log_audit(db, "signup_pending", user_id=None, metadata={"email": email}, request=request)
    return SignupResponse(ok=True, message="Verification code sent. Enter the 6-digit code to finish signup.")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "login", email), max_calls=10, window_sec=60)
    user = authenticate(db, email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_verified:
        log_audit(db, "login_unverified", user_id=user.id, metadata={"email": user.email}, request=request)
        raise HTTPException(status_code=403, detail="Email not verified. Enter the 6-digit code to finish signup.")

    log_audit(db, "login", user_id=user.id, metadata={"email": user.email}, request=request)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token)


@router.post("/verify", response_model=TokenResponse)
def verify(payload: VerifyRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "verify", email), max_calls=8, window_sec=60)
    code = (payload.code or "").strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="Verification code must be 6 digits.")

    pending = pending_signup_crud.verify_pending(db, email, code)
    if pending:
        existing = get_by_email(db, email)
        if existing:
            pending_signup_crud.delete_pending(db, pending)
            raise HTTPException(status_code=400, detail="Account already exists. Please sign in.")
        user = create_user_from_hash(
            db,
            email=email,
            password_hash=pending.password_hash,
            full_name=pending.full_name,
            is_verified=True,
        )
        pending_signup_crud.delete_pending(db, pending)
        log_audit(db, "verify_email", user_id=user.id, metadata={"email": user.email}, request=request)
        token = create_access_token(user.email)
        return TokenResponse(access_token=token)

    user = verify_user(db, email, code)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
    log_audit(db, "verify_email", user_id=user.id, metadata={"email": user.email}, request=request)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token)


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "resend", email), max_calls=4, window_sec=60)
    pending = pending_signup_crud.get_by_email(db, email)
    if pending:
        _, code = pending_signup_crud.upsert_pending_signup(
            db,
            email=email,
            password_hash=pending.password_hash,
            full_name=pending.full_name,
        )
        with contextlib.suppress(Exception):
            send_email(
                email,
                "Verify your email",
                ("Use this 6-digit code to finish your signup:\n\n" f"{code}\n\n" "This code expires in 30 minutes."),
            )
        log_audit(db, "resend_verification", user_id=None, metadata={"email": email}, request=request)
        return {"ok": True}

    user = get_by_email(db, email)
    if user and not user.is_verified:
        token = set_verification_token(db, user)
        with contextlib.suppress(Exception):
            send_email(
                user.email,
                "Verify your email",
                ("Use this 6-digit code to verify your account:\n\n" f"{token}\n\n" "This code expires in 30 minutes."),
            )
        log_audit(db, "resend_verification", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}


@router.post("/request-password-reset")
def request_password_reset(payload: ResetRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    rate_limit(request, key=_rate_key(request, "reset_request", email), max_calls=6, window_sec=60)
    user = get_by_email(db, email)
    if not user:
        # do not reveal existence
        return {"ok": True}
    token = set_reset_token(db, user)
    reset_link = None
    if settings.FRONTEND_URL:
        base = settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{base}/login.html?view=reset&token={quote(token)}&email={quote(user.email)}"
    with contextlib.suppress(Exception):
        lines = [
            "Use this token to reset your password:",
            "",
            token,
            "",
            "Token expires in 30 minutes.",
        ]
        if reset_link:
            lines.extend(["", "Or open this link:", reset_link])
        send_email(user.email, "Reset your password", "\n".join(lines))
    log_audit(db, "request_password_reset", user_id=user.id, metadata={"email": user.email}, request=request)
    resp: dict[str, str | bool] = {"ok": True}
    if settings.ENV == "dev":
        resp["token"] = token
        if reset_link:
            resp["reset_link"] = reset_link
    return resp


@router.post("/reset-password")
def perform_password_reset(payload: PerformResetRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, key=_rate_key(request, "reset", None), max_calls=6, window_sec=60)
    user = reset_password(db, payload.token, payload.new_password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    log_audit(db, "reset_password", user_id=user.id, metadata={"email": user.email}, request=request)
    return {"ok": True}
