"""Product and Variant catalogue API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.catalogue import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
)
from app.services.catalogue_service import catalogue_service

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: Annotated[bool | None, Query()] = None,
) -> list[Product]:
    """List products with variants."""
    return catalogue_service.list_products(db, is_active=is_active)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_product(
    product_in: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    """Create a new product with optional initial variants."""
    return catalogue_service.create_product(db, product_in)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> Product:
    """Get product details by ID."""
    return catalogue_service.get_product(db, product_id)


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_product_variant(
    product_id: int,
    variant_in: ProductVariantCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ProductVariant:
    """Create a product variant with price adjustment (+/- offset against base price)."""
    return catalogue_service.create_variant(db, product_id, variant_in)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    """Update product information."""
    return catalogue_service.update_product(db, product_id, product_in)
