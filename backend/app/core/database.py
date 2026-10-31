"""SQLAlchemy 2 database engine, session factory, declarative base, and health check."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("recurflow.database")

# SQLAlchemy 2 synchronous engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> tuple[bool, str | None]:
    """
    Verify PostgreSQL connectivity by executing a lightweight SELECT 1 query.
    Returns (True, None) on success, or (False, error_message) on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as exc:
        err_msg = str(exc.orig) if hasattr(exc, "orig") and exc.orig else str(exc)
        logger.warning("Database readiness probe failed: %s", err_msg)
        return False, err_msg
    except Exception as exc:
        logger.warning("Unexpected connection error during readiness check: %s", exc)
        return False, str(exc)
