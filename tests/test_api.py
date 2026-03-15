from __future__ import annotations

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from api.database import Base
from api.models import Allergen, Alternative, Ingredient, Macronutrient, Price
from api.seeds import seed_mock_data


def _make_session(tmp_path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_seed.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, class_=Session
    )
    return SessionLocal()


def test_seed_mock_data_populates_expected_catalog(tmp_path) -> None:
    with _make_session(tmp_path) as session:
        seed_mock_data(session)

        ingredient_count = session.scalar(select(func.count()).select_from(Ingredient))
        price_count = session.scalar(select(func.count()).select_from(Price))
        macro_count = session.scalar(select(func.count()).select_from(Macronutrient))
        allergen_count = session.scalar(select(func.count()).select_from(Allergen))
        alternative_count = session.scalar(
            select(func.count()).select_from(Alternative)
        )

        assert ingredient_count == 6
        assert price_count == 8
        assert macro_count == 6
        assert allergen_count == 2
        assert alternative_count == 2

        chicken = session.scalar(
            select(Ingredient).where(Ingredient.name == "Chicken Breast")
        )
        tofu = session.scalar(select(Ingredient).where(Ingredient.name == "Tofu"))
        brown_rice = session.scalar(
            select(Ingredient).where(Ingredient.name == "Brown Rice")
        )

        assert chicken is not None
        assert tofu is not None
        assert brown_rice is not None
        assert sorted(price.store_name for price in chicken.prices) == [
            "Lidl",
            "Whole Foods",
        ]
        assert [allergen.name for allergen in tofu.allergens] == ["soy"]
        assert [
            alternative.alternative_ingredient.name
            for alternative in brown_rice.alternatives
        ] == ["Quinoa"]


def test_seed_mock_data_is_idempotent(tmp_path) -> None:
    with _make_session(tmp_path) as session:
        seed_mock_data(session)
        seed_mock_data(session)

        assert session.scalar(select(func.count()).select_from(Ingredient)) == 6
        assert session.scalar(select(func.count()).select_from(Price)) == 8
        assert session.scalar(select(func.count()).select_from(Macronutrient)) == 6
        assert session.scalar(select(func.count()).select_from(Allergen)) == 2
        assert session.scalar(select(func.count()).select_from(Alternative)) == 2
