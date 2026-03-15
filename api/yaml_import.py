"""YAML import helpers for building a personal ingredient catalog over time."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Allergen, Alternative, Ingredient, Macronutrient, Price
from api.schemas import IngredientYamlImportSummary


class IngredientCatalogImportError(ValueError):
    """Raised when a YAML catalog cannot be validated or imported."""


class CatalogPriceEntry(BaseModel):
    store_name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    unit_quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    unit: str = Field(default="kg", min_length=1, max_length=20)
    recorded_at: datetime | None = None


class CatalogMacronutrientEntry(BaseModel):
    calories_kcal: Decimal = Field(ge=0)
    protein_g: Decimal = Field(ge=0)
    carbs_g: Decimal = Field(ge=0)
    fat_g: Decimal = Field(ge=0)


class CatalogAlternativeEntry(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=120)
    substitution_ratio: Decimal = Field(default=Decimal("1.0"), gt=0)
    note: str | None = Field(default=None, max_length=255)


class CatalogIngredientEntry(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    default_unit: str = Field(default="g", min_length=1, max_length=20)
    allergens: list[str] | None = None
    macronutrients: CatalogMacronutrientEntry | None = None
    prices: list[CatalogPriceEntry] | None = None
    alternatives: list[CatalogAlternativeEntry] | None = None


class IngredientCatalogDocument(BaseModel):
    observed_at: datetime | None = None
    ingredients: list[CatalogIngredientEntry] = Field(min_length=1)


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _default_observed_at() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _load_catalog(yaml_content: str) -> IngredientCatalogDocument:
    try:
        raw_payload = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        raise IngredientCatalogImportError(f"Invalid YAML document: {exc}") from exc

    if raw_payload is None:
        raise IngredientCatalogImportError("YAML document is empty")

    try:
        return IngredientCatalogDocument.model_validate(raw_payload)
    except ValidationError as exc:
        formatted_errors = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise IngredientCatalogImportError(
            f"Invalid ingredient catalog structure: {formatted_errors}"
        ) from exc


def _get_or_create_allergen(
    session: Session, name: str, summary: IngredientYamlImportSummary
) -> Allergen:
    allergen = session.scalar(select(Allergen).where(Allergen.name == name))
    if allergen is None:
        allergen = Allergen(name=name)
        session.add(allergen)
        session.flush()
        summary.allergens_created += 1
    return allergen


def _upsert_ingredient(
    session: Session,
    entry: CatalogIngredientEntry,
    summary: IngredientYamlImportSummary,
) -> Ingredient:
    ingredient = session.scalar(select(Ingredient).where(Ingredient.name == entry.name))
    if ingredient is None:
        ingredient = Ingredient(
            name=entry.name,
            category=entry.category,
            default_unit=entry.default_unit,
        )
        session.add(ingredient)
        session.flush()
        summary.ingredients_created += 1
    else:
        ingredient.category = entry.category
        ingredient.default_unit = entry.default_unit
        summary.ingredients_updated += 1

    if entry.allergens is not None:
        ingredient.allergens = [
            _get_or_create_allergen(session, allergen_name, summary)
            for allergen_name in entry.allergens
        ]

    return ingredient


def _upsert_macronutrients(
    session: Session,
    ingredient: Ingredient,
    entry: CatalogMacronutrientEntry,
    summary: IngredientYamlImportSummary,
) -> None:
    profile = session.scalar(
        select(Macronutrient).where(Macronutrient.ingredient_id == ingredient.id)
    )
    if profile is None:
        profile = Macronutrient(ingredient=ingredient)
        session.add(profile)
        summary.macronutrients_created += 1
    else:
        summary.macronutrients_updated += 1

    profile.calories_kcal = entry.calories_kcal
    profile.protein_g = entry.protein_g
    profile.carbs_g = entry.carbs_g
    profile.fat_g = entry.fat_g


def _resolve_price_timestamp(
    catalog: IngredientCatalogDocument,
    price_entry: CatalogPriceEntry,
) -> datetime:
    if price_entry.recorded_at is not None:
        return _ensure_utc(price_entry.recorded_at)
    if catalog.observed_at is not None:
        return _ensure_utc(catalog.observed_at)
    return _default_observed_at()


def _upsert_price(
    session: Session,
    ingredient: Ingredient,
    catalog: IngredientCatalogDocument,
    entry: CatalogPriceEntry,
    summary: IngredientYamlImportSummary,
) -> None:
    recorded_at = _resolve_price_timestamp(catalog, entry)
    price = session.scalar(
        select(Price).where(
            Price.ingredient_id == ingredient.id,
            Price.store_name == entry.store_name,
            Price.currency == entry.currency,
            Price.unit_quantity == entry.unit_quantity,
            Price.unit == entry.unit,
            Price.recorded_at == recorded_at,
        )
    )
    if price is None:
        price = Price(ingredient=ingredient, store_name=entry.store_name)
        session.add(price)
        summary.prices_created += 1
    else:
        summary.prices_updated += 1

    price.amount = entry.amount
    price.currency = entry.currency
    price.unit_quantity = entry.unit_quantity
    price.unit = entry.unit
    price.recorded_at = recorded_at


def _resolve_ingredient_by_name(
    session: Session,
    imported_ingredients: dict[str, Ingredient],
    name: str,
) -> Ingredient | None:
    ingredient = imported_ingredients.get(name)
    if ingredient is not None:
        return ingredient
    return session.scalar(select(Ingredient).where(Ingredient.name == name))


def _upsert_alternative(
    session: Session,
    source_ingredient: Ingredient,
    target_ingredient: Ingredient,
    entry: CatalogAlternativeEntry,
    summary: IngredientYamlImportSummary,
) -> None:
    relationship = session.scalar(
        select(Alternative).where(
            Alternative.ingredient_id == source_ingredient.id,
            Alternative.alternative_ingredient_id == target_ingredient.id,
        )
    )
    if relationship is None:
        relationship = Alternative(
            ingredient=source_ingredient,
            alternative_ingredient=target_ingredient,
        )
        session.add(relationship)
        summary.alternatives_created += 1
    else:
        summary.alternatives_updated += 1

    relationship.substitution_ratio = entry.substitution_ratio
    relationship.note = entry.note


def import_ingredient_catalog_yaml(
    session: Session,
    yaml_content: str,
) -> IngredientYamlImportSummary:
    catalog = _load_catalog(yaml_content)
    summary = IngredientYamlImportSummary()
    imported_ingredients: dict[str, Ingredient] = {}

    try:
        for ingredient_entry in catalog.ingredients:
            ingredient = _upsert_ingredient(session, ingredient_entry, summary)
            imported_ingredients[ingredient.name] = ingredient
            summary.processed_ingredient_names.append(ingredient.name)

            if ingredient_entry.macronutrients is not None:
                _upsert_macronutrients(
                    session,
                    ingredient,
                    ingredient_entry.macronutrients,
                    summary,
                )

            if ingredient_entry.prices:
                for price_entry in ingredient_entry.prices:
                    _upsert_price(session, ingredient, catalog, price_entry, summary)

        for ingredient_entry in catalog.ingredients:
            if not ingredient_entry.alternatives:
                continue

            source_ingredient = imported_ingredients[ingredient_entry.name]
            for alternative_entry in ingredient_entry.alternatives:
                target_ingredient = _resolve_ingredient_by_name(
                    session,
                    imported_ingredients,
                    alternative_entry.ingredient_name,
                )
                if target_ingredient is None:
                    raise IngredientCatalogImportError(
                        "Unknown alternative ingredient reference: "
                        f"{alternative_entry.ingredient_name}"
                    )
                if source_ingredient.id == target_ingredient.id:
                    raise IngredientCatalogImportError(
                        "Ingredient cannot list itself as an alternative"
                    )

                _upsert_alternative(
                    session,
                    source_ingredient,
                    target_ingredient,
                    alternative_entry,
                    summary,
                )

        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise


def import_ingredient_catalog_file(
    session: Session,
    file_path: str | Path,
) -> IngredientYamlImportSummary:
    path = Path(file_path)
    if not path.exists():
        raise IngredientCatalogImportError(f"YAML file not found: {path}")

    return import_ingredient_catalog_yaml(session, path.read_text(encoding="utf-8"))
