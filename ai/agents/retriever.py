"""Retriever agent built with Gemini and Pydantic AI tool calling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent, RunContext

from ai.agents.gemini import GeminiSettings, build_google_model
from ai.prompts import RETRIEVER_SYSTEM_PROMPT, build_retriever_user_prompt


class RetrievedFact(BaseModel):
    """Single factual statement extracted from retrieval results."""

    source: Literal["ingredients", "prices", "macronutrients", "other"] = Field(
        description="Data source category for the fact.",
    )
    detail: str = Field(
        min_length=1, description="Human-readable fact backed by fetched data."
    )


class RetrieverOutput(BaseModel):
    """Structured retrieval context consumed by downstream agents."""

    ingredient_candidates: list[str] = Field(
        default_factory=list,
        description="Ingredient names worth considering for planning.",
    )
    facts: list[RetrievedFact] = Field(
        default_factory=list,
        description="Structured facts collected from data sources.",
    )
    data_gaps: list[str] = Field(
        default_factory=list,
        description="Missing pieces of information discovered during retrieval.",
    )
    api_calls_made: list[str] = Field(
        default_factory=list,
        description="Trace of endpoint/tool calls used to gather context.",
    )


class RetrievalHints(BaseModel):
    """Hints that guide retriever tool-calling decisions."""

    ingredient_name_hints: list[str] = Field(
        default_factory=list,
        description="Ingredient names to prioritize in lookups.",
    )
    category_hints: list[str] = Field(
        default_factory=list,
        description="Ingredient categories to prioritize.",
    )
    max_ingredients: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum number of ingredient candidates to retrieve.",
    )


class RetrieverRequest(BaseModel):
    """Input payload for the retriever agent."""

    user_request: str = Field(
        min_length=1,
        description="Natural-language user request that drives retrieval.",
    )
    hints: RetrievalHints = Field(
        default_factory=RetrievalHints,
        description="Structured retrieval guidance for tool selection.",
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_shape(cls, data: Any) -> Any:
        """Accept legacy flat hint fields and map them into hints."""

        if not isinstance(data, dict) or "hints" in data:
            return data

        legacy_keys = {
            "ingredient_name_hints",
            "category_hints",
            "max_ingredients",
        }
        hints = {key: data[key] for key in legacy_keys if key in data}
        if not hints:
            return data

        payload = {key: value for key, value in data.items() if key not in legacy_keys}
        payload["hints"] = hints
        return payload


ListIngredientsFn = Callable[[str | None, str | None, int], dict[str, Any]]
ListPricesFn = Callable[[int, int], dict[str, Any]]
ListMacrosFn = Callable[[int], dict[str, Any]]


@dataclass(slots=True)
class RetrieverDependencies:
    """Injected callable dependencies used by retriever tools."""

    list_ingredients: ListIngredientsFn
    list_prices: ListPricesFn
    get_macronutrient: ListMacrosFn


def create_retriever_agent(
    *,
    model: Any | None = None,
    settings: GeminiSettings | None = None,
    api_key: str | None = None,
) -> Agent[RetrieverDependencies, RetrieverOutput]:
    """Create the retriever agent with tool functions wired to dependencies."""

    resolved_model = model or build_google_model(settings=settings, api_key=api_key)
    agent = Agent(
        resolved_model,
        deps_type=RetrieverDependencies,
        output_type=RetrieverOutput,
        system_prompt=RETRIEVER_SYSTEM_PROMPT,
    )

    @agent.tool
    def fetch_ingredients(
        ctx: RunContext[RetrieverDependencies],
        name: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Fetch candidate ingredients from the deterministic catalog."""

        return ctx.deps.list_ingredients(name, category, limit)

    @agent.tool
    def fetch_prices(
        ctx: RunContext[RetrieverDependencies],
        ingredient_id: int,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Fetch historical prices for a selected ingredient."""

        return ctx.deps.list_prices(ingredient_id, limit)

    @agent.tool
    def fetch_macronutrient(
        ctx: RunContext[RetrieverDependencies],
        ingredient_id: int,
    ) -> dict[str, Any]:
        """Fetch macronutrient profile for a selected ingredient."""

        return ctx.deps.get_macronutrient(ingredient_id)

    return agent


def build_retriever_prompt(request: RetrieverRequest) -> str:
    """Compose retriever prompt from user request and hint metadata."""

    retrieval_hints = request.hints.model_dump(exclude_none=True)
    return build_retriever_user_prompt(
        user_request=request.user_request,
        retrieval_hints=retrieval_hints,
    )


def run_retriever(
    request: RetrieverRequest,
    *,
    agent: Agent[RetrieverDependencies, RetrieverOutput],
    deps: RetrieverDependencies,
) -> RetrieverOutput:
    """Run retriever synchronously and return validated retrieval context."""

    prompt = build_retriever_prompt(request)
    return agent.run_sync(prompt, deps=deps).output
