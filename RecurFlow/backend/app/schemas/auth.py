"""Authentication and User Pydantic v2 schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """User login request payload."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    role: str = "STAFF"


class UserCreate(UserBase):
    """User registration payload."""

    password: str = Field(..., min_length=9)


class UserUpdate(BaseModel):
    """User update payload."""

    is_active: bool | None = None
    role: str | None = None


class UserResponse(UserBase):
    """User representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
