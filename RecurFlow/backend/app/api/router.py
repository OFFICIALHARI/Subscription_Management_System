"""Main API routing assembly — wires all domain routers under /api/v1 prefix."""

from fastapi import APIRouter

from app.api.v1.routers import (
    auth,
    billing,
    customers,
    dashboard,
    discounts,
    invoices,
    payments,
    plans,
    products,
    quotations,
    subscriptions,
    taxes,
)
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)

# Register all domain routers
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(taxes.router)
api_router.include_router(products.router)
api_router.include_router(plans.router)
api_router.include_router(discounts.router)
api_router.include_router(quotations.router)
api_router.include_router(subscriptions.router)
api_router.include_router(billing.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
api_router.include_router(dashboard.router)


@api_router.get("/status", tags=["System"])
def api_status() -> dict[str, str]:
    """Basic API v1 health check."""
    return {"status": "online", "api_version": "v1"}
