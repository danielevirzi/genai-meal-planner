"""SQLAlchemy ORM models for meal planner deterministic data layer."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


ingredient_allergens = Table(
    "ingredient_allergens",
    Base.metadata,
    Column(
        "ingredient_id",
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "allergen_id", ForeignKey("allergens.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Ingredient(Base):
    """Master catalog entry for an ingredient used in recipes and shopping."""

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(80), default=None)
    default_unit: Mapped[str] = mapped_column(String(20), default="g")

    prices: Mapped[list["Price"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    macronutrient_profile: Mapped["Macronutrient | None"] = relationship(
        back_populates="ingredient",
        uselist=False,
        cascade="all, delete-orphan",
    )
    allergens: Mapped[list["Allergen"]] = relationship(
        secondary=ingredient_allergens,
        back_populates="ingredients",
    )

    alternatives: Mapped[list["Alternative"]] = relationship(
        back_populates="ingredient",
        foreign_keys="Alternative.ingredient_id",
        cascade="all, delete-orphan",
    )
    alternative_for: Mapped[list["Alternative"]] = relationship(
        back_populates="alternative_ingredient",
        foreign_keys="Alternative.alternative_ingredient_id",
    )


class Price(Base):
    """Historical price point for an ingredient at a specific store and unit quantity."""

    __tablename__ = "prices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_prices_amount_non_negative"),
        CheckConstraint("unit_quantity > 0", name="ck_prices_unit_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    store_name: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    unit_quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), default=Decimal("1.0")
    )
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    ingredient: Mapped[Ingredient] = relationship(back_populates="prices")


class Macronutrient(Base):
    """Macronutrient profile stored per 100g equivalent of an ingredient."""

    __tablename__ = "macronutrients"
    __table_args__ = (
        UniqueConstraint("ingredient_id", name="uq_macronutrients_ingredient_id"),
        CheckConstraint("calories_kcal >= 0", name="ck_macro_calories_non_negative"),
        CheckConstraint("protein_g >= 0", name="ck_macro_protein_non_negative"),
        CheckConstraint("carbs_g >= 0", name="ck_macro_carbs_non_negative"),
        CheckConstraint("fat_g >= 0", name="ck_macro_fat_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    calories_kcal: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))

    ingredient: Mapped[Ingredient] = relationship(
        back_populates="macronutrient_profile"
    )


class Allergen(Base):
    """Reference table for allergen labels (e.g., gluten, peanuts)."""

    __tablename__ = "allergens"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)

    ingredients: Mapped[list[Ingredient]] = relationship(
        secondary=ingredient_allergens,
        back_populates="allergens",
    )


class Alternative(Base):
    """Directed substitution edge from one ingredient to a possible alternative."""

    __tablename__ = "alternatives"
    __table_args__ = (
        UniqueConstraint(
            "ingredient_id", "alternative_ingredient_id", name="uq_alternative_pair"
        ),
        CheckConstraint("substitution_ratio > 0", name="ck_alternative_ratio_positive"),
        CheckConstraint(
            "ingredient_id != alternative_ingredient_id",
            name="ck_alternative_no_self_ref",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    alternative_ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        index=True,
    )
    substitution_ratio: Mapped[Decimal] = mapped_column(
        Numeric(8, 3), default=Decimal("1.0")
    )
    note: Mapped[str | None] = mapped_column(String(255), default=None)

    ingredient: Mapped[Ingredient] = relationship(
        foreign_keys=[ingredient_id],
        back_populates="alternatives",
    )
    alternative_ingredient: Mapped[Ingredient] = relationship(
        foreign_keys=[alternative_ingredient_id],
        back_populates="alternative_for",
    )
