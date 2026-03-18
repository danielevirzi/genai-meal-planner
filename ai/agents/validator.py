"""Validator agent built with Gemini and Pydantic AI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ai.agents.gemini import GeminiSettings, build_google_model
from ai.prompts import VALIDATOR_SYSTEM_PROMPT, build_validator_user_prompt


class ValidationIssue(BaseModel):
    """Single validation finding for a generated plan."""

    code: Literal[
        "budget_exceeded",
        "allergen_conflict",
        "missing_data",
        "constraint_mismatch",
        "other",
    ] = Field(description="Machine-friendly issue code.")
    severity: Literal["error", "warning"] = Field(
        description="Issue severity level.",
    )
    message: str = Field(min_length=1, description="Clear issue explanation.")
    meal_name: str | None = Field(
        default=None,
        description="Optional meal name associated with the issue.",
    )


class ValidatorOutput(BaseModel):
    """Structured validation report for the current meal-plan draft."""

    is_valid: bool = Field(description="True when no blocking errors are found.")
    compliance_score: float = Field(
        ge=0,
        le=1,
        description="Normalized compliance score between 0 and 1.",
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="Detected validation issues ordered by relevance.",
    )
    suggested_fixes: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations to fix issues.",
    )


class ValidatorConstraints(BaseModel):
    """Constraint set used by validator checks."""

    budget_eur: float | None = Field(
        default=None,
        ge=0,
        description="Maximum allowed total budget in EUR.",
    )
    days: int | None = Field(
        default=None,
        ge=1,
        le=14,
        description="Expected number of planned days.",
    )
    servings_per_meal: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Target servings per meal.",
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="Allergens that must not appear in ingredients.",
    )
    dislikes: list[str] = Field(
        default_factory=list,
        description="Ingredients that should be avoided.",
    )
    cuisine_preferences: list[str] = Field(
        default_factory=list,
        description="Preferred cuisines for recommendation alignment.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional constraint metadata not covered by typed fields.",
    )


class PlanDraftMeal(BaseModel):
    """Minimal meal representation used during validation."""

    name: str = Field(min_length=1, description="Meal name.")
    meal_type: str | None = Field(default=None, description="Meal type label.")
    ingredient_names: list[str] = Field(
        default_factory=list,
        description="Ingredient names referenced by the meal.",
    )
    estimated_cost_eur: float | None = Field(
        default=None,
        ge=0,
        description="Estimated meal cost in EUR.",
    )


class PlanDraft(BaseModel):
    """Meal-plan draft payload evaluated by validator."""

    summary: str | None = Field(default=None, description="Plan summary text.")
    meals: list[PlanDraftMeal] = Field(
        default_factory=list,
        description="Meals included in the draft plan.",
    )
    total_estimated_cost_eur: float | None = Field(
        default=None,
        ge=0,
        description="Estimated total plan cost in EUR.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions captured during generation.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Known missing information affecting plan quality.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional plan metadata not covered by typed fields.",
    )


class RetrievalContext(BaseModel):
    """Retrieved data context used while validating the plan."""

    facts: list[str] = Field(
        default_factory=list,
        description="Key retrieval facts relevant to validation decisions.",
    )
    api_calls_made: list[str] = Field(
        default_factory=list,
        description="Trace of retrieval calls that produced the context.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional retrieval metadata for validator reasoning.",
    )


class ValidatorRequest(BaseModel):
    """Input payload for the validator agent."""

    user_request: str = Field(
        min_length=1,
        description="Original user request used as validation baseline.",
    )
    extracted_constraints: ValidatorConstraints = Field(
        default_factory=ValidatorConstraints,
        description="Structured constraints to validate against.",
    )
    plan_draft: PlanDraft = Field(
        default_factory=PlanDraft,
        description="Structured meal-plan draft that will be evaluated.",
    )
    retrieval_context: RetrievalContext = Field(
        default_factory=RetrievalContext,
        description="Structured context collected by the retriever.",
    )


def create_validator_agent(
    *,
    model: Any | None = None,
    settings: GeminiSettings | None = None,
    api_key: str | None = None,
) -> Agent[None, ValidatorOutput]:
    """Create the validator agent with strict issue-report output schema."""

    resolved_model = model or build_google_model(settings=settings, api_key=api_key)
    return Agent(
        resolved_model,
        output_type=ValidatorOutput,
        system_prompt=VALIDATOR_SYSTEM_PROMPT,
    )


def build_validator_prompt(request: ValidatorRequest) -> str:
    """Compose validator prompt from constraints, plan draft, and context."""

    return build_validator_user_prompt(
        user_request=request.user_request,
        extracted_constraints=request.extracted_constraints.model_dump(
            exclude_none=True
        ),
        plan_draft=request.plan_draft.model_dump(exclude_none=True),
        retrieval_context=request.retrieval_context.model_dump(exclude_none=True),
    )


def run_validator(
    request: ValidatorRequest,
    *,
    agent: Agent[None, ValidatorOutput],
) -> ValidatorOutput:
    """Run validator synchronously and return validated feedback."""

    prompt = build_validator_prompt(request)
    return agent.run_sync(prompt).output
