"""Prompt templates for the Phase 2 Gemini + Pydantic AI agents."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


PLANNER_SYSTEM_PROMPT = dedent(
    """
	You are the Planner Agent in a deterministic meal-planning system.
	Your task is to generate a practical meal-plan draft that respects constraints.

	Rules:
	- Output MUST follow the provided JSON schema exactly.
	- Prefer realistic meals that can be cooked with common ingredients.
	- If constraints conflict or data is incomplete, surface clear assumptions.
	- Keep explanations concise and actionable.
	"""
).strip()


RETRIEVER_SYSTEM_PROMPT = dedent(
    """
	You are the Retriever Agent in a deterministic meal-planning system.
	Your task is to identify and fetch relevant ingredient, price, and macro data.

	Rules:
	- Use tools when data is needed instead of inventing values.
	- Prefer the smallest number of calls that still produce enough context.
	- Return only structured facts and explicit data gaps.
	- Do not produce a final meal plan.
	"""
).strip()


VALIDATOR_SYSTEM_PROMPT = dedent(
    """
	You are the Validator Agent in a deterministic meal-planning system.
	Your task is to evaluate a generated meal-plan draft against constraints.

	Rules:
	- Report only verifiable issues.
	- Classify each issue as error or warning.
	- Suggest concrete fixes that are easy to apply.
	- Return compliance score between 0 and 1.
	"""
).strip()


def _to_pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)


def build_planner_user_prompt(
    *,
    user_request: str,
    extracted_constraints: dict[str, Any],
    retrieval_context: dict[str, Any] | None = None,
) -> str:
    """Build the planner prompt payload with explicit sections."""

    retrieval_payload = retrieval_context or {}
    return dedent(
        f"""
		USER_REQUEST:
		{user_request.strip()}

		EXTRACTED_CONSTRAINTS_JSON:
		{_to_pretty_json(extracted_constraints)}

		RETRIEVAL_CONTEXT_JSON:
		{_to_pretty_json(retrieval_payload)}
		"""
    ).strip()


def build_retriever_user_prompt(
    *,
    user_request: str,
    retrieval_hints: dict[str, Any],
) -> str:
    """Build the retriever prompt payload with signals for tool usage."""

    return dedent(
        f"""
		USER_REQUEST:
		{user_request.strip()}

		RETRIEVAL_HINTS_JSON:
		{_to_pretty_json(retrieval_hints)}
		"""
    ).strip()


def build_validator_user_prompt(
    *,
    user_request: str,
    extracted_constraints: dict[str, Any],
    plan_draft: dict[str, Any],
    retrieval_context: dict[str, Any] | None = None,
) -> str:
    """Build the validator prompt payload with full check context."""

    retrieval_payload = retrieval_context or {}
    return dedent(
        f"""
		USER_REQUEST:
		{user_request.strip()}

		EXTRACTED_CONSTRAINTS_JSON:
		{_to_pretty_json(extracted_constraints)}

		PLAN_DRAFT_JSON:
		{_to_pretty_json(plan_draft)}

		RETRIEVAL_CONTEXT_JSON:
		{_to_pretty_json(retrieval_payload)}
		"""
    ).strip()
