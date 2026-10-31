"""Main FastAPI application entrypoint for RecurFlow."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.router import api_router
from app.core.config import settings
from app.core.database import check_db_connection
from app.core.errors import register_exception_handlers

# Structured logging setup
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recurflow.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown hooks."""
    logger.info("Starting %s in %s environment...", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Subscription Operations & Revenue Management API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uniform error handling
register_exception_handlers(app)

# Include API v1 router
app.include_router(api_router)


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    details: str | None = None


@app.get("/health", tags=["Health"], response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Process liveness check.
    Returns 200 OK if the FastAPI process is alive and responding.
    """
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        environment=settings.APP_ENV,
    )


@app.get(
    "/ready",
    tags=["Health"],
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Database connection verified."},
        503: {"description": "Database connection unreachable."},
    },
)
def readiness_check(response: Response) -> ReadinessResponse:
    """
    Readiness probe verifying live PostgreSQL connectivity.
    Returns 200 when database connectivity is established, or 503 when unreachable.
    """
    is_connected, error_msg = check_db_connection()
    if is_connected:
        return ReadinessResponse(status="ready", database="connected")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="unhealthy",
        database="unreachable",
        details=error_msg,
    )
