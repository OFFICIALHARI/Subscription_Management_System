"""Authentication and user management service."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate


class AuthService:
    """Handles user authentication, password verification, and user provisioning."""

    def authenticate(self, db: Session, credentials: LoginRequest) -> User:
        """Authenticate user against database credentials."""
        user = db.query(User).filter(User.email == credentials.email.lower()).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )
        return user

    def create_token(self, user: User) -> TokenResponse:
        """Create signed JWT access token for user."""
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
        access_token = create_access_token(token_payload)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            role=user.role,
        )

    def register_user(self, db: Session, user_in: UserCreate) -> User:
        """Create a new user with password validation."""
        valid, msg = validate_password_strength(user_in.password)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

        existing = db.query(User).filter(User.email == user_in.email.lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already registered.",
            )

        user = User(
            email=user_in.email.lower(),
            hashed_password=hash_password(user_in.password),
            role=user_in.role.upper(),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


auth_service = AuthService()
