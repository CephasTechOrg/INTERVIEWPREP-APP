from datetime import datetime

from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    admin_id: int
    username: str
    full_name: str | None = None


class AdminCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str | None = None


class AdminResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        from_attributes = True


class UserBanRequest(BaseModel):
    reason: str | None = None


class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_verified: bool
    is_banned: bool
    ban_reason: str | None = None
    banned_at: datetime | None = None
    created_at: datetime
    role_pref: str = "SWE Intern"
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    verified_users: int
    banned_users: int
    active_interviews: int
    total_questions: int
    timestamp: datetime
