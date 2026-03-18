from __future__ import annotations

from typing import Any

import pytest
from pydantic_ai.models.test import TestModel
import ai.agents.gemini as gemini_module

from ai.agents.gemini import GeminiSettings, build_google_model
from ai.agents.planner import (
    PlannerDependencies,
    PlannerOutput,
    PlannerRequest,
    create_planner_agent,
    run_planner,
)
from ai.agents.retriever import (
    RetrieverDependencies,
    RetrieverOutput,
    RetrieverRequest,
    create_retriever_agent,
    run_retriever,
)
from ai.agents.validator import (
    ValidatorOutput,
    ValidatorRequest,
    create_validator_agent,
    run_validator,
)
from ai.prompts import (
    build_planner_user_prompt,
    build_retriever_user_prompt,
    build_validator_user_prompt,
)


def test_gemini_settings_defaults_to_google_gla_mode() -> None:
    settings = GeminiSettings()
    assert settings.vertexai is False


def test_build_google_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        build_google_model(settings=GeminiSettings())


def test_build_google_model_uses_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-test-key")
    model = build_google_model(
        settings=GeminiSettings(model_name="gemini-2.5-flash-lite", vertexai=True)
    )
    assert model.model_name == "gemini-2.5-flash-lite"


def test_build_google_model_uses_non_vertex_provider_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    class DummyProvider:
        def __init__(self, *, vertexai: bool, api_key: str) -> None:
            calls["vertexai"] = vertexai
            calls["api_key"] = api_key

    class DummyModel:
        def __init__(self, model_name: str, provider: object) -> None:
            calls["model_name"] = model_name
            calls["provider"] = provider

    monkeypatch.setattr(gemini_module, "GoogleProvider", DummyProvider)
    monkeypatch.setattr(gemini_module, "GoogleModel", DummyModel)

    model = build_google_model(api_key="dummy-test-key")

    assert isinstance(model, DummyModel)
    assert calls["vertexai"] is False
    assert calls["api_key"] == "dummy-test-key"
    assert calls["model_name"] == "gemini-2.5-flash-lite"
    assert isinstance(calls["provider"], DummyProvider)


def test_prompt_builders_include_expected_sections() -> None:
    planner_prompt = build_planner_user_prompt(
        user_request="Low-cost weekly plan",
        extracted_constraints={"budget_eur": 40, "days": 5},
        retrieval_context={"top_store": "Lidl"},
    )
    assert "USER_REQUEST:" in planner_prompt
    assert "EXTRACTED_CONSTRAINTS_JSON:" in planner_prompt
    assert "RETRIEVAL_CONTEXT_JSON:" in planner_prompt

    retriever_prompt = build_retriever_user_prompt(
        user_request="Need high-protein meals",
        retrieval_hints={"max_ingredients": 6},
    )
    assert "RETRIEVAL_HINTS_JSON:" in retriever_prompt

    validator_prompt = build_validator_user_prompt(
        user_request="No peanuts, max 50 EUR",
        extracted_constraints={"allergies": ["peanut"], "budget_eur": 50},
        plan_draft={"summary": "draft"},
        retrieval_context={"price_currency": "EUR"},
    )
    assert "PLAN_DRAFT_JSON:" in validator_prompt


def test_planner_agent_factory_and_run_with_test_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-test-key")
    agent = create_planner_agent()
    assert agent.output_type is PlannerOutput

    request = PlannerRequest(
        user_request="Create a 2-day vegetarian plan under 25 EUR.",
        budget_eur=25,
        days=2,
        servings_per_meal=2,
        allergies=["peanut"],
    )
    deps = PlannerDependencies(
        retrieved_context={"top_ingredients": ["Tofu", "Brown Rice"]},
        extra_instructions=["Prefer one-pot meals."],
    )

    with agent.override(
        model=TestModel(
            custom_output_args={
                "summary": "Budget-friendly vegetarian plan.",
                "meals": [
                    {
                        "name": "Tofu Rice Bowl",
                        "meal_type": "dinner",
                        "ingredient_names": ["Tofu", "Brown Rice", "Broccoli"],
                        "estimated_cost_eur": 4.8,
                        "rationale": "High protein and low cost.",
                    }
                ],
                "total_estimated_cost_eur": 18.4,
                "assumptions": ["Basic pantry staples available."],
                "missing_information": [],
            }
        )
    ):
        result = run_planner(request, agent=agent, deps=deps)

    assert result.total_estimated_cost_eur == pytest.approx(18.4)
    assert result.meals[0].name == "Tofu Rice Bowl"


def test_retriever_agent_registers_tools_and_runs_with_test_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-test-key")
    agent = create_retriever_agent()
    assert agent.output_type is RetrieverOutput
    assert {
        "fetch_ingredients",
        "fetch_prices",
        "fetch_macronutrient",
    }.issubset(set(agent._function_toolset.tools.keys()))

    request = RetrieverRequest(
        user_request="Find low-cost high-protein ingredients.",
        ingredient_name_hints=["tofu", "beans"],
        category_hints=["protein", "legumes"],
        max_ingredients=5,
    )

    def _list_ingredients(
        name: str | None,
        category: str | None,
        limit: int,
    ) -> dict[str, Any]:
        return {
            "meta": {"name": name, "category": category, "limit": limit},
            "items": [{"id": 1, "name": "Tofu"}],
        }

    def _list_prices(ingredient_id: int, limit: int) -> dict[str, Any]:
        return {
            "meta": {"ingredient_id": ingredient_id, "limit": limit},
            "items": [{"amount": "2.49", "currency": "EUR"}],
        }

    def _get_macro(ingredient_id: int) -> dict[str, Any]:
        return {"ingredient_id": ingredient_id, "protein_g": "16.00"}

    deps = RetrieverDependencies(
        list_ingredients=_list_ingredients,
        list_prices=_list_prices,
        get_macronutrient=_get_macro,
    )

    with agent.override(
        model=TestModel(
            custom_output_args={
                "ingredient_candidates": ["Tofu", "Cannellini Beans"],
                "facts": [
                    {
                        "source": "prices",
                        "detail": "Tofu available from 2.49 EUR per 500g.",
                    }
                ],
                "data_gaps": ["No historical data for lentils in this store."],
                "api_calls_made": [
                    "GET /api/ingredients?name=tofu",
                    "GET /api/prices?ingredient_id=1",
                ],
            }
        )
    ):
        result = run_retriever(request, agent=agent, deps=deps)

    assert "Tofu" in result.ingredient_candidates
    assert result.facts[0].source == "prices"


def test_validator_agent_factory_and_run_with_test_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-test-key")
    agent = create_validator_agent()
    assert agent.output_type is ValidatorOutput

    request = ValidatorRequest(
        user_request="No peanuts and budget <= 30 EUR.",
        extracted_constraints={"allergies": ["peanut"], "budget_eur": 30},
        plan_draft={"summary": "draft", "total_estimated_cost_eur": 34.5},
        retrieval_context={"currency": "EUR"},
    )

    with agent.override(
        model=TestModel(
            custom_output_args={
                "is_valid": False,
                "compliance_score": 0.42,
                "issues": [
                    {
                        "code": "budget_exceeded",
                        "severity": "error",
                        "message": "Total estimated cost exceeds budget by 4.5 EUR.",
                        "meal_name": None,
                    }
                ],
                "suggested_fixes": [
                    "Replace premium ingredients with lower-cost alternatives."
                ],
            }
        )
    ):
        result = run_validator(request, agent=agent)

    assert result.is_valid is False
    assert result.issues[0].code == "budget_exceeded"
