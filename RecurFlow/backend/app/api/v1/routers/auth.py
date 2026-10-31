"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate user with email and password, returning signed JWT."""
    user = auth_service.authenticate(db, credentials)
    return auth_service.create_token(user)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Retrieve details of the currently authenticated user."""
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN"]))],
)
def register_user(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Register a new user account (Admin only)."""
    return auth_service.register_user(db, user_in)
