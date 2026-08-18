"""LLM Provider abstraction and configuration for structured ReelSignal extraction."""

import os
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    """Configuration for LLM provider connections and credentials."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(default="gemini", description="Provider identifier (e.g. gemini, openai, mock)")
    model_name: str = Field(default="gemini-2.0-flash", description="Target model version/name")
    api_key: str | None = Field(default=None, description="Provider API key (read from environment)")
    timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0, description="Request timeout in seconds")

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM credentials and configuration from environment variables."""
        provider = os.getenv("SCROLLSENSE_LLM_PROVIDER", "gemini")
        model = os.getenv("SCROLLSENSE_LLM_MODEL", "gemini-2.0-flash")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        timeout_str = os.getenv("SCROLLSENSE_LLM_TIMEOUT", "15.0")
        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 15.0

        return cls(
            provider_name=provider,
            model_name=model,
            api_key=api_key,
            timeout_seconds=timeout,
        )


class LLMProviderError(RuntimeError):
    """Raised when an external LLM provider fails, times out, or returns a network error."""


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers capable of returning strictly validated structured JSON."""

    @property
    def model_name(self) -> str:
        """Name of the underlying LLM model."""
        ...

    def generate_structured_json(self, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        """Send prompt to LLM and receive structured dictionary conforming to target Pydantic schema."""
        ...
