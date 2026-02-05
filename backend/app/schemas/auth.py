from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class SignupResponse(BaseModel):
    ok: bool = True
    message: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    email: EmailStr


class PerformResetRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str
