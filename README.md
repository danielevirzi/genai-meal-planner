# GenAI Meal Planner

Deterministic meal-planning data backend with a growing personal ingredient catalog.

The current implementation focuses on Phase 1 foundations:
- SQLAlchemy data model for ingredients, prices, macronutrients, allergens, and alternatives.
- FastAPI CRUD endpoints with validation and pagination metadata.
- YAML-based personal catalog imports so you can keep adding real store observations over time.

## Why this project is useful

You can manually record real prices from specific stores and keep that data in your local database.
Then the automation layer can use those historical price points to prefer lower-cost options for the same ingredient.

## UV-First Setup

Prerequisites:
- Python 3.11+
- uv installed

Install dependencies (including dev/test tools):

```bash
uv sync --all-groups
```

## Run the API (development)

```bash
uv run fastapi dev api/main.py
```

API docs will be available at:
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Run tests

```bash
uv run pytest -q
```

## Personal Ingredient YAML Imports

Use a high-level YAML file to upsert your personal ingredient catalog.

### Import from a local file (CLI)

```bash
uv run python main.py import-yaml examples/personal-ingredients.example.yaml
```

### Import through the API

```bash
curl -X POST http://127.0.0.1:8000/api/imports/ingredients-yaml \
  -H "Content-Type: application/x-yaml" \
  --data-binary @examples/personal-ingredients.example.yaml
```

### Supported YAML shape

```yaml
observed_at: 2026-03-15T10:00:00Z
ingredients:
  - name: Cannellini Beans
    category: legumes
    default_unit: g
    allergens: []
    macronutrients:
      calories_kcal: 333.00
      protein_g: 21.80
      carbs_g: 60.50
      fat_g: 1.40
    prices:
      - store_name: Discount Market
        amount: 1.29
        currency: EUR
        unit_quantity: 0.500
        unit: kg
      - store_name: Neighborhood Shop
        amount: 1.69
        currency: EUR
        unit_quantity: 0.500
        unit: kg
    alternatives:
      - ingredient_name: Brown Rice
        substitution_ratio: 1.000
        note: Pantry backup option.
```

### Import behavior

- Ingredients are matched by name and updated in place.
- Macronutrients are upserted as one profile per ingredient.
- Prices are stored as store-specific observations.
- Price rows are deduplicated by ingredient, store, currency, unit, unit quantity, and observation timestamp.
- Alternatives are matched by source ingredient and target ingredient.
- Re-importing the same catalog is idempotent for the same timestamps.

## Useful endpoints

- Ingredients: /api/ingredients
- Prices: /api/prices
- Macronutrients: /api/macronutrients
- Allergens: /api/allergens
- Alternatives: /api/alternatives
- YAML import: /api/imports/ingredients-yaml

## Notes

- By default, app startup seeds mock data when API_SEED_DATA is truthy.
- For a clean local run without auto-seeding, set API_SEED_DATA=false before starting the API.
