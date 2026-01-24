from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileOut(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role_pref: str | None = None
    profile: dict = Field(default_factory=dict)


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str | None = None
    role_pref: str | None = None
    profile: dict | None = None
