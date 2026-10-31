"""API v1 routers module."""

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

__all__ = [
    "auth",
    "billing",
    "customers",
    "dashboard",
    "discounts",
    "invoices",
    "payments",
    "plans",
    "products",
    "quotations",
    "subscriptions",
    "taxes",
]
