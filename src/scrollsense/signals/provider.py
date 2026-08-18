"""LLM Provider abstraction, configuration, and concrete Gemini adapter."""

import json
import os
from typing import Any, Protocol, runtime_checkable
import urllib.error
import urllib.request
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
        """Load LLM credentials and configuration from environment variables.

        Fails explicitly on malformed configuration.
        """
        provider = os.getenv("SCROLLSENSE_LLM_PROVIDER", "gemini")
        model = os.getenv("SCROLLSENSE_LLM_MODEL", "gemini-2.0-flash")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

        timeout_env = os.getenv("SCROLLSENSE_LLM_TIMEOUT")
        if timeout_env is not None:
            try:
                timeout = float(timeout_env)
            except ValueError as e:
                raise ValueError(
                    f"Invalid SCROLLSENSE_LLM_TIMEOUT: '{timeout_env}' is not a valid float"
                ) from e
        else:
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


class GeminiLLMProvider:
    """Concrete LLMProvider adapter calling the Google Gemini REST API with structured output."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def generate_structured_json(self, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        """Call Gemini generateContent endpoint enforcing Pydantic response_schema."""
        if not self.config.api_key:
            raise LLMProviderError("Missing API key for Gemini provider (set GEMINI_API_KEY environment variable)")

        endpoint = f"{self.BASE_URL}/{self.config.model_name}:generateContent?key={self.config.api_key}"

        request_body = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": schema.model_json_schema(),
            },
        }

        data_bytes = json.dumps(request_body).encode("utf-8")
        req = urllib.request.Request(
            url=endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                resp_bytes = response.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            raise LLMProviderError(f"Gemini API HTTP error {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise LLMProviderError(f"Gemini API network error: {e.reason}") from e
        except TimeoutError as e:
            raise LLMProviderError(f"Gemini API request timed out after {self.config.timeout_seconds}s") from e
        except json.JSONDecodeError as e:
            raise LLMProviderError(f"Failed to decode Gemini API response as JSON: {e}") from e

        # Extract structured content from Gemini candidates payload
        try:
            candidates = resp_json.get("candidates", [])
            if not candidates:
                raise LLMProviderError(f"Gemini API returned no candidates in response: {resp_json}")

            text_content = candidates[0]["content"]["parts"][0]["text"]
            structured_dict = json.loads(text_content)
            if not isinstance(structured_dict, dict):
                raise LLMProviderError(f"Gemini response did not parse to a JSON object: {text_content}")
            return structured_dict
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMProviderError(f"Failed to extract structured text payload from Gemini response: {e}") from e
