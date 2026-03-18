"""Helpers to build Gemini models for Pydantic AI agents."""

from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    """Configuration for constructing a Gemini model client.

    Defaults target the Google Generative Language API so a GOOGLE_API_KEY
    works out of the box without Vertex AI credentials.
    """

    model_name: str = DEFAULT_GEMINI_MODEL
    vertexai: bool = False
    api_key_env_var: str = "GOOGLE_API_KEY"


def resolve_google_api_key(
    api_key: str | None = None,
    *,
    env_var: str = "GOOGLE_API_KEY",
) -> str:
    """Resolve the API key from explicit input or environment."""

    candidate = api_key or os.getenv(env_var)
    if candidate is None or not candidate.strip():
        raise ValueError(
            "Google API key is required. Provide api_key or set GOOGLE_API_KEY."
        )
    return candidate.strip()


def build_google_model(
    *,
    settings: GeminiSettings | None = None,
    api_key: str | None = None,
) -> GoogleModel:
    """Create a GoogleModel configured for Gemini and selected Google provider."""

    config = settings or GeminiSettings()
    resolved_api_key = resolve_google_api_key(api_key, env_var=config.api_key_env_var)
    provider = GoogleProvider(vertexai=config.vertexai, api_key=resolved_api_key)
    return GoogleModel(config.model_name, provider=provider)
