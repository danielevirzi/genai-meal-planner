from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from api.database import Base, get_db
from api.main import create_app
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


def _make_client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_api.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, class_=Session
    )

    with SessionLocal() as session:
        seed_mock_data(session)

    app = create_app(seed_data=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    engine.dispose()


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


def test_ingredient_crud_endpoints(tmp_path) -> None:
    client_gen = _make_client(tmp_path)
    client = next(client_gen)
    try:
        response = client.post(
            "/api/ingredients",
            json={"name": "Tempeh", "category": "protein", "default_unit": "g"},
        )
        assert response.status_code == 201
        created = response.json()
        ingredient_id = created["id"]
        assert created["name"] == "Tempeh"

        response = client.put(
            f"/api/ingredients/{ingredient_id}",
            json={"category": "fermented-protein"},
        )
        assert response.status_code == 200
        assert response.json()["category"] == "fermented-protein"

        response = client.get(f"/api/ingredients/{ingredient_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Tempeh"

        response = client.delete(f"/api/ingredients/{ingredient_id}")
        assert response.status_code == 204

        response = client.get(f"/api/ingredients/{ingredient_id}")
        assert response.status_code == 404
    finally:
        client_gen.close()


def test_price_crud_endpoints(tmp_path) -> None:
    client_gen = _make_client(tmp_path)
    client = next(client_gen)
    try:
        response = client.get("/api/ingredients")
        assert response.status_code == 200
        ingredients = response.json()["items"]
        broccoli_id = next(
            item["id"] for item in ingredients if item["name"] == "Broccoli"
        )

        create_payload = {
            "ingredient_id": broccoli_id,
            "store_name": "Fresh Market",
            "amount": "1.99",
            "currency": "EUR",
            "unit_quantity": "0.500",
            "unit": "kg",
        }
        response = client.post("/api/prices", json=create_payload)
        assert response.status_code == 201
        created = response.json()
        price_id = created["id"]
        assert created["store_name"] == "Fresh Market"
        assert created["recorded_at"] is not None

        response = client.put(
            f"/api/prices/{price_id}",
            json={"amount": "2.09", "store_name": "Fresh Market Plus"},
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["amount"] == "2.09"
        assert updated["store_name"] == "Fresh Market Plus"

        response = client.get(
            "/api/prices",
            params={"ingredient_id": broccoli_id, "store_name": "Fresh Market Plus"},
        )
        assert response.status_code == 200
        payload = response.json()
        filtered = payload["items"]
        assert len(filtered) == 1
        assert filtered[0]["id"] == price_id
        assert payload["meta"]["total"] == 1

        response = client.delete(f"/api/prices/{price_id}")
        assert response.status_code == 204

        response = client.get(f"/api/prices/{price_id}")
        assert response.status_code == 404
    finally:
        client_gen.close()


def test_ingredient_list_supports_search_and_pagination_metadata(tmp_path) -> None:
    client_gen = _make_client(tmp_path)
    client = next(client_gen)
    try:
        response = client.get(
            "/api/ingredients",
            params={"name": "Rice", "category": "grain", "skip": 0, "limit": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {"items", "meta"}
        assert len(payload["items"]) == 1
        assert payload["items"][0]["name"] == "Brown Rice"
        assert payload["meta"]["total"] == 1
        assert payload["meta"]["skip"] == 0
        assert payload["meta"]["limit"] == 1
        assert payload["meta"]["has_more"] is False
    finally:
        client_gen.close()


def test_allergen_crud_endpoints(tmp_path) -> None:
    client_gen = _make_client(tmp_path)
    client = next(client_gen)
    try:
        response = client.post("/api/allergens", json={"name": "sesame"})
        assert response.status_code == 201
        created = response.json()
        allergen_id = created["id"]
        assert created["name"] == "sesame"

        response = client.put(
            f"/api/allergens/{allergen_id}",
            json={"name": "sesame-seed"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "sesame-seed"

        response = client.get("/api/allergens", params={"name": "sesame"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["total"] == 1
        assert payload["items"][0]["id"] == allergen_id

        response = client.delete(f"/api/allergens/{allergen_id}")
        assert response.status_code == 204

        response = client.get(f"/api/allergens/{allergen_id}")
        assert response.status_code == 404
    finally:
        client_gen.close()


def test_alternative_crud_endpoints(tmp_path) -> None:
    client_gen = _make_client(tmp_path)
    client = next(client_gen)
    try:
        response = client.get("/api/ingredients")
        assert response.status_code == 200
        items = response.json()["items"]
        ingredients = {item["name"]: item["id"] for item in items}

        create_payload = {
            "ingredient_id": ingredients["Broccoli"],
            "alternative_ingredient_id": ingredients["Quinoa"],
            "substitution_ratio": "1.100",
            "note": "Use a bit more quinoa for volume.",
        }
        response = client.post("/api/alternatives", json=create_payload)
        assert response.status_code == 201
        created = response.json()
        alternative_id = created["id"]
        assert created["ingredient_id"] == ingredients["Broccoli"]
        assert created["alternative_ingredient_id"] == ingredients["Quinoa"]

        response = client.put(
            f"/api/alternatives/{alternative_id}",
            json={"substitution_ratio": "1.050", "note": "Updated ratio."},
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["substitution_ratio"] == "1.050"
        assert updated["note"] == "Updated ratio."

        response = client.get(
            "/api/alternatives",
            params={"ingredient_id": ingredients["Broccoli"]},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["total"] == 1
        assert payload["items"][0]["id"] == alternative_id

        response = client.delete(f"/api/alternatives/{alternative_id}")
        assert response.status_code == 204

        response = client.get(f"/api/alternatives/{alternative_id}")
        assert response.status_code == 404
    finally:
        client_gen.close()
