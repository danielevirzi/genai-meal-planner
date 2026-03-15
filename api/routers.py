"""API router definitions for first CRUD endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Allergen, Alternative, Ingredient, Macronutrient, Price
from api.schemas import (
    AllergenCreate,
    AllergenListResponse,
    AllergenRead,
    AllergenUpdate,
    AlternativeCreate,
    AlternativeListResponse,
    AlternativeRead,
    AlternativeUpdate,
    IngredientCreate,
    IngredientListResponse,
    IngredientRead,
    IngredientUpdate,
    MacronutrientCreate,
    MacronutrientListResponse,
    MacronutrientRead,
    MacronutrientUpdate,
    PaginationMeta,
    PriceCreate,
    PriceListResponse,
    PriceRead,
    PriceUpdate,
)


DbDep = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/api", tags=["api"])


def _build_meta(total: int, skip: int, limit: int) -> PaginationMeta:
    return PaginationMeta(
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@router.get("/ingredients", response_model=IngredientListResponse)
def list_ingredients(
    db: DbDep,
    name: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> IngredientListResponse:
    statement = select(Ingredient)
    count_statement = select(func.count()).select_from(Ingredient)

    if name is not None:
        term = f"%{name}%"
        statement = statement.where(Ingredient.name.ilike(term))
        count_statement = count_statement.where(Ingredient.name.ilike(term))

    if category is not None:
        statement = statement.where(Ingredient.category == category)
        count_statement = count_statement.where(Ingredient.category == category)

    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(statement.order_by(Ingredient.id).offset(skip).limit(limit))
    )
    return IngredientListResponse(
        items=items, meta=_build_meta(total=total, skip=skip, limit=limit)
    )


@router.get("/ingredients/{ingredient_id}", response_model=IngredientRead)
def get_ingredient(
    ingredient_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Ingredient:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found"
        )
    return ingredient


@router.post(
    "/ingredients", response_model=IngredientRead, status_code=status.HTTP_201_CREATED
)
def create_ingredient(payload: IngredientCreate, db: DbDep) -> Ingredient:
    existing = db.scalar(select(Ingredient).where(Ingredient.name == payload.name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingredient name already exists",
        )

    ingredient = Ingredient(
        name=payload.name,
        category=payload.category,
        default_unit=payload.default_unit,
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/ingredients/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: Annotated[int, Path(ge=1)],
    payload: IngredientUpdate,
    db: DbDep,
) -> Ingredient:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        duplicate = db.scalar(
            select(Ingredient).where(
                Ingredient.name == update_data["name"],
                Ingredient.id != ingredient_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ingredient name already exists",
            )

    for field_name, value in update_data.items():
        setattr(ingredient, field_name, value)

    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Response:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found"
        )

    db.delete(ingredient)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/prices", response_model=PriceListResponse)
def list_prices(
    db: DbDep,
    ingredient_id: Annotated[int | None, Query(ge=1)] = None,
    store_name: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PriceListResponse:
    statement = select(Price)
    count_statement = select(func.count()).select_from(Price)

    if ingredient_id is not None:
        statement = statement.where(Price.ingredient_id == ingredient_id)
        count_statement = count_statement.where(Price.ingredient_id == ingredient_id)

    if store_name is not None:
        statement = statement.where(Price.store_name == store_name)
        count_statement = count_statement.where(Price.store_name == store_name)

    total = int(db.scalar(count_statement) or 0)
    items = list(db.scalars(statement.order_by(Price.id).offset(skip).limit(limit)))
    return PriceListResponse(
        items=items, meta=_build_meta(total=total, skip=skip, limit=limit)
    )


@router.get("/prices/{price_id}", response_model=PriceRead)
def get_price(
    price_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Price:
    price = db.get(Price, price_id)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Price not found"
        )
    return price


@router.post("/prices", response_model=PriceRead, status_code=status.HTTP_201_CREATED)
def create_price(payload: PriceCreate, db: DbDep) -> Price:
    ingredient = db.get(Ingredient, payload.ingredient_id)
    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found"
        )

    price = Price(
        ingredient_id=payload.ingredient_id,
        store_name=payload.store_name,
        amount=payload.amount,
        currency=payload.currency,
        unit_quantity=payload.unit_quantity,
        unit=payload.unit,
    )
    if payload.recorded_at is not None:
        price.recorded_at = payload.recorded_at

    db.add(price)
    db.commit()
    db.refresh(price)
    return price


@router.put("/prices/{price_id}", response_model=PriceRead)
def update_price(
    price_id: Annotated[int, Path(ge=1)],
    payload: PriceUpdate,
    db: DbDep,
) -> Price:
    price = db.get(Price, price_id)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Price not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if field_name == "recorded_at" and value is None:
            continue
        setattr(price, field_name, value)

    db.commit()
    db.refresh(price)
    return price


@router.delete("/prices/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price(
    price_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Response:
    price = db.get(Price, price_id)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Price not found"
        )

    db.delete(price)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/macronutrients", response_model=MacronutrientListResponse)
def list_macronutrients(
    db: DbDep,
    ingredient_id: Annotated[int | None, Query(ge=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=300)] = 100,
) -> MacronutrientListResponse:
    statement = select(Macronutrient)
    count_statement = select(func.count()).select_from(Macronutrient)

    if ingredient_id is not None:
        statement = statement.where(Macronutrient.ingredient_id == ingredient_id)
        count_statement = count_statement.where(
            Macronutrient.ingredient_id == ingredient_id
        )

    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(statement.order_by(Macronutrient.id).offset(skip).limit(limit))
    )
    return MacronutrientListResponse(
        items=items, meta=_build_meta(total=total, skip=skip, limit=limit)
    )


@router.get("/macronutrients/{macronutrient_id}", response_model=MacronutrientRead)
def get_macronutrient(
    macronutrient_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Macronutrient:
    macronutrient = db.get(Macronutrient, macronutrient_id)
    if macronutrient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macronutrient not found",
        )
    return macronutrient


@router.post(
    "/macronutrients",
    response_model=MacronutrientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_macronutrient(payload: MacronutrientCreate, db: DbDep) -> Macronutrient:
    ingredient = db.get(Ingredient, payload.ingredient_id)
    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found",
        )

    existing = db.scalar(
        select(Macronutrient).where(
            Macronutrient.ingredient_id == payload.ingredient_id
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Macronutrient profile for ingredient already exists",
        )

    macronutrient = Macronutrient(
        ingredient_id=payload.ingredient_id,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
    )
    db.add(macronutrient)
    db.commit()
    db.refresh(macronutrient)
    return macronutrient


@router.put(
    "/macronutrients/{macronutrient_id}",
    response_model=MacronutrientRead,
)
def update_macronutrient(
    macronutrient_id: Annotated[int, Path(ge=1)],
    payload: MacronutrientUpdate,
    db: DbDep,
) -> Macronutrient:
    macronutrient = db.get(Macronutrient, macronutrient_id)
    if macronutrient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macronutrient not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(macronutrient, field_name, value)

    db.commit()
    db.refresh(macronutrient)
    return macronutrient


@router.delete(
    "/macronutrients/{macronutrient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_macronutrient(
    macronutrient_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Response:
    macronutrient = db.get(Macronutrient, macronutrient_id)
    if macronutrient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macronutrient not found",
        )

    db.delete(macronutrient)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/allergens", response_model=AllergenListResponse)
def list_allergens(
    db: DbDep,
    name: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AllergenListResponse:
    statement = select(Allergen)
    count_statement = select(func.count()).select_from(Allergen)

    if name is not None:
        statement = statement.where(Allergen.name.ilike(f"%{name}%"))
        count_statement = count_statement.where(Allergen.name.ilike(f"%{name}%"))

    total = int(db.scalar(count_statement) or 0)
    items = list(db.scalars(statement.order_by(Allergen.id).offset(skip).limit(limit)))
    return AllergenListResponse(
        items=items, meta=_build_meta(total=total, skip=skip, limit=limit)
    )


@router.get("/allergens/{allergen_id}", response_model=AllergenRead)
def get_allergen(
    allergen_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Allergen:
    allergen = db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allergen not found"
        )
    return allergen


@router.post(
    "/allergens", response_model=AllergenRead, status_code=status.HTTP_201_CREATED
)
def create_allergen(payload: AllergenCreate, db: DbDep) -> Allergen:
    existing = db.scalar(select(Allergen).where(Allergen.name == payload.name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Allergen name already exists"
        )

    allergen = Allergen(name=payload.name)
    db.add(allergen)
    db.commit()
    db.refresh(allergen)
    return allergen


@router.put("/allergens/{allergen_id}", response_model=AllergenRead)
def update_allergen(
    allergen_id: Annotated[int, Path(ge=1)],
    payload: AllergenUpdate,
    db: DbDep,
) -> Allergen:
    allergen = db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allergen not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        duplicate = db.scalar(
            select(Allergen).where(
                Allergen.name == update_data["name"],
                Allergen.id != allergen_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Allergen name already exists",
            )

    for field_name, value in update_data.items():
        setattr(allergen, field_name, value)

    db.commit()
    db.refresh(allergen)
    return allergen


@router.delete("/allergens/{allergen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allergen(
    allergen_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Response:
    allergen = db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allergen not found"
        )

    db.delete(allergen)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/alternatives", response_model=AlternativeListResponse)
def list_alternatives(
    db: DbDep,
    ingredient_id: Annotated[int | None, Query(ge=1)] = None,
    alternative_ingredient_id: Annotated[int | None, Query(ge=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=300)] = 100,
) -> AlternativeListResponse:
    statement = select(Alternative)
    count_statement = select(func.count()).select_from(Alternative)

    if ingredient_id is not None:
        statement = statement.where(Alternative.ingredient_id == ingredient_id)
        count_statement = count_statement.where(
            Alternative.ingredient_id == ingredient_id
        )

    if alternative_ingredient_id is not None:
        statement = statement.where(
            Alternative.alternative_ingredient_id == alternative_ingredient_id
        )
        count_statement = count_statement.where(
            Alternative.alternative_ingredient_id == alternative_ingredient_id
        )

    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(statement.order_by(Alternative.id).offset(skip).limit(limit))
    )
    return AlternativeListResponse(
        items=items, meta=_build_meta(total=total, skip=skip, limit=limit)
    )


@router.get("/alternatives/{alternative_id}", response_model=AlternativeRead)
def get_alternative(
    alternative_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Alternative:
    alternative = db.get(Alternative, alternative_id)
    if alternative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alternative not found"
        )
    return alternative


@router.post(
    "/alternatives", response_model=AlternativeRead, status_code=status.HTTP_201_CREATED
)
def create_alternative(payload: AlternativeCreate, db: DbDep) -> Alternative:
    if payload.ingredient_id == payload.alternative_ingredient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient and alternative must differ",
        )

    source = db.get(Ingredient, payload.ingredient_id)
    target = db.get(Ingredient, payload.alternative_ingredient_id)
    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found"
        )

    existing = db.scalar(
        select(Alternative).where(
            Alternative.ingredient_id == payload.ingredient_id,
            Alternative.alternative_ingredient_id == payload.alternative_ingredient_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alternative pair already exists",
        )

    alternative = Alternative(
        ingredient_id=payload.ingredient_id,
        alternative_ingredient_id=payload.alternative_ingredient_id,
        substitution_ratio=payload.substitution_ratio,
        note=payload.note,
    )
    db.add(alternative)
    db.commit()
    db.refresh(alternative)
    return alternative


@router.put("/alternatives/{alternative_id}", response_model=AlternativeRead)
def update_alternative(
    alternative_id: Annotated[int, Path(ge=1)],
    payload: AlternativeUpdate,
    db: DbDep,
) -> Alternative:
    alternative = db.get(Alternative, alternative_id)
    if alternative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alternative not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(alternative, field_name, value)

    db.commit()
    db.refresh(alternative)
    return alternative


@router.delete("/alternatives/{alternative_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alternative(
    alternative_id: Annotated[int, Path(ge=1)],
    db: DbDep,
) -> Response:
    alternative = db.get(Alternative, alternative_id)
    if alternative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alternative not found"
        )

    db.delete(alternative)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
