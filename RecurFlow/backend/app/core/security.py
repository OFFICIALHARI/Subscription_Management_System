"""Security, password hashing, and JWT token management."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Password hasher supporting Argon2 and bcrypt
password_hash = PasswordHash.recommended()

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d|.*[@$!%*?&#^~_+-=]).{9,}$")


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Validates that password is longer than 8 characters, and contains uppercase,
    lowercase, and a special character/digit as mandated by specifications.
    """
    if len(password) <= 8:
        return False, "Password must be strictly longer than 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c in "@$!%*?&#^~_+-=[]{}|:;<>,./" or c.isdigit() for c in password):
        return False, "Password must contain at least one special character or digit."
    return True, None


def hash_password(password: str) -> str:
    """Hash plain text password securely."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate signed JWT access token with UTC expiration."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate signed JWT access token."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return payload
