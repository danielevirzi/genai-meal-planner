"""Pydantic schemas for API request and response payloads."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaginationMeta(BaseModel):
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
    has_more: bool


class IngredientBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    default_unit: str = Field(default="g", min_length=1, max_length=20)


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    default_unit: str | None = Field(default=None, min_length=1, max_length=20)


class IngredientRead(IngredientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class IngredientListResponse(BaseModel):
    items: list[IngredientRead]
    meta: PaginationMeta


class PriceBase(BaseModel):
    store_name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    unit_quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    unit: str = Field(default="kg", min_length=1, max_length=20)
    recorded_at: datetime | None = None


class PriceCreate(PriceBase):
    ingredient_id: int


class PriceUpdate(BaseModel):
    store_name: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    unit_quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    recorded_at: datetime | None = None


class PriceRead(PriceBase):
    id: int
    ingredient_id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceListResponse(BaseModel):
    items: list[PriceRead]
    meta: PaginationMeta


class AllergenBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AllergenCreate(AllergenBase):
    pass


class AllergenUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)


class AllergenRead(AllergenBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AllergenListResponse(BaseModel):
    items: list[AllergenRead]
    meta: PaginationMeta


class AlternativeBase(BaseModel):
    ingredient_id: int
    alternative_ingredient_id: int
    substitution_ratio: Decimal = Field(default=Decimal("1.0"), gt=0)
    note: str | None = Field(default=None, max_length=255)


class AlternativeCreate(AlternativeBase):
    pass


class AlternativeUpdate(BaseModel):
    substitution_ratio: Decimal | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=255)


class AlternativeRead(AlternativeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AlternativeListResponse(BaseModel):
    items: list[AlternativeRead]
    meta: PaginationMeta
