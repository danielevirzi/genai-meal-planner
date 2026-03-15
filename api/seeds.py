"""Deterministic mock dataset used for local development and early tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Allergen, Alternative, Ingredient, Macronutrient, Price


INGREDIENTS = (
    {
        "name": "Chicken Breast",
        "category": "protein",
        "default_unit": "g",
        "allergens": (),
        "macronutrients": {
            "calories_kcal": Decimal("165.0"),
            "protein_g": Decimal("31.0"),
            "carbs_g": Decimal("0.0"),
            "fat_g": Decimal("3.6"),
        },
    },
    {
        "name": "Tofu",
        "category": "protein",
        "default_unit": "g",
        "allergens": ("soy",),
        "macronutrients": {
            "calories_kcal": Decimal("144.0"),
            "protein_g": Decimal("17.3"),
            "carbs_g": Decimal("2.8"),
            "fat_g": Decimal("8.7"),
        },
    },
    {
        "name": "Brown Rice",
        "category": "grain",
        "default_unit": "g",
        "allergens": (),
        "macronutrients": {
            "calories_kcal": Decimal("362.0"),
            "protein_g": Decimal("7.5"),
            "carbs_g": Decimal("76.0"),
            "fat_g": Decimal("2.7"),
        },
    },
    {
        "name": "Quinoa",
        "category": "grain",
        "default_unit": "g",
        "allergens": (),
        "macronutrients": {
            "calories_kcal": Decimal("368.0"),
            "protein_g": Decimal("14.1"),
            "carbs_g": Decimal("64.2"),
            "fat_g": Decimal("6.1"),
        },
    },
    {
        "name": "Broccoli",
        "category": "vegetable",
        "default_unit": "g",
        "allergens": (),
        "macronutrients": {
            "calories_kcal": Decimal("34.0"),
            "protein_g": Decimal("2.8"),
            "carbs_g": Decimal("6.6"),
            "fat_g": Decimal("0.4"),
        },
    },
    {
        "name": "Peanut Butter",
        "category": "spread",
        "default_unit": "g",
        "allergens": ("peanuts",),
        "macronutrients": {
            "calories_kcal": Decimal("588.0"),
            "protein_g": Decimal("25.0"),
            "carbs_g": Decimal("20.0"),
            "fat_g": Decimal("50.0"),
        },
    },
)

PRICES = (
    {
        "ingredient": "Chicken Breast",
        "store_name": "Lidl",
        "amount": Decimal("8.49"),
        "currency": "EUR",
        "unit_quantity": Decimal("1.000"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Chicken Breast",
        "store_name": "Whole Foods",
        "amount": Decimal("13.90"),
        "currency": "EUR",
        "unit_quantity": Decimal("1.000"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Tofu",
        "store_name": "Trader Joe's",
        "amount": Decimal("2.29"),
        "currency": "EUR",
        "unit_quantity": Decimal("0.200"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Tofu",
        "store_name": "Whole Foods",
        "amount": Decimal("2.95"),
        "currency": "EUR",
        "unit_quantity": Decimal("0.200"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Brown Rice",
        "store_name": "Lidl",
        "amount": Decimal("1.79"),
        "currency": "EUR",
        "unit_quantity": Decimal("1.000"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Quinoa",
        "store_name": "Whole Foods",
        "amount": Decimal("4.80"),
        "currency": "EUR",
        "unit_quantity": Decimal("0.500"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Broccoli",
        "store_name": "Lidl",
        "amount": Decimal("1.49"),
        "currency": "EUR",
        "unit_quantity": Decimal("0.500"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
    {
        "ingredient": "Peanut Butter",
        "store_name": "Trader Joe's",
        "amount": Decimal("3.10"),
        "currency": "EUR",
        "unit_quantity": Decimal("0.340"),
        "unit": "kg",
        "recorded_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    },
)

ALTERNATIVES = (
    {
        "ingredient": "Chicken Breast",
        "alternative": "Tofu",
        "substitution_ratio": Decimal("1.200"),
        "note": "Use extra tofu to match protein more closely.",
    },
    {
        "ingredient": "Brown Rice",
        "alternative": "Quinoa",
        "substitution_ratio": Decimal("1.000"),
        "note": "Swap one-for-one when a higher-protein grain is preferred.",
    },
)


def _get_or_create_allergen(session: Session, name: str) -> Allergen:
    allergen = session.scalar(select(Allergen).where(Allergen.name == name))
    if allergen is None:
        allergen = Allergen(name=name)
        session.add(allergen)
        session.flush()
    return allergen


def _upsert_macronutrients(
    session: Session, ingredient: Ingredient, data: dict[str, Decimal]
) -> None:
    profile = session.scalar(
        select(Macronutrient).where(Macronutrient.ingredient_id == ingredient.id)
    )
    if profile is None:
        profile = Macronutrient(ingredient=ingredient)
        session.add(profile)

    profile.calories_kcal = data["calories_kcal"]
    profile.protein_g = data["protein_g"]
    profile.carbs_g = data["carbs_g"]
    profile.fat_g = data["fat_g"]


def _upsert_ingredient(session: Session, data: dict[str, object]) -> Ingredient:
    ingredient = session.scalar(
        select(Ingredient).where(Ingredient.name == data["name"])
    )
    if ingredient is None:
        ingredient = Ingredient(
            name=str(data["name"]),
            category=str(data["category"]),
            default_unit=str(data["default_unit"]),
        )
        session.add(ingredient)
        session.flush()
    else:
        ingredient.category = str(data["category"])
        ingredient.default_unit = str(data["default_unit"])

    ingredient.allergens = [
        _get_or_create_allergen(session, allergen_name)
        for allergen_name in data["allergens"]
    ]
    _upsert_macronutrients(session, ingredient, data["macronutrients"])
    return ingredient


def _upsert_price(
    session: Session, ingredient: Ingredient, data: dict[str, object]
) -> None:
    price = session.scalar(
        select(Price).where(
            Price.ingredient_id == ingredient.id,
            Price.store_name == data["store_name"],
        )
    )
    if price is None:
        price = Price(ingredient=ingredient, store_name=str(data["store_name"]))
        session.add(price)

    price.amount = data["amount"]
    price.currency = str(data["currency"])
    price.unit_quantity = data["unit_quantity"]
    price.unit = str(data["unit"])
    price.recorded_at = data["recorded_at"]


def _upsert_alternative(
    session: Session,
    ingredient: Ingredient,
    alternative: Ingredient,
    data: dict[str, object],
) -> None:
    record = session.scalar(
        select(Alternative).where(
            Alternative.ingredient_id == ingredient.id,
            Alternative.alternative_ingredient_id == alternative.id,
        )
    )
    if record is None:
        record = Alternative(ingredient=ingredient, alternative_ingredient=alternative)
        session.add(record)

    record.substitution_ratio = data["substitution_ratio"]
    record.note = str(data["note"])


def seed_mock_data(session: Session) -> None:
    """Populate the database with a deterministic starter dataset."""
    ingredients_by_name: dict[str, Ingredient] = {}

    for ingredient_data in INGREDIENTS:
        ingredient = _upsert_ingredient(session, ingredient_data)
        ingredients_by_name[ingredient.name] = ingredient

    for price_data in PRICES:
        ingredient = ingredients_by_name[str(price_data["ingredient"])]
        _upsert_price(session, ingredient, price_data)

    for alternative_data in ALTERNATIVES:
        ingredient = ingredients_by_name[str(alternative_data["ingredient"])]
        alternative = ingredients_by_name[str(alternative_data["alternative"])]
        _upsert_alternative(session, ingredient, alternative, alternative_data)

    session.commit()
