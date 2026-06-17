# Python 3.12
"""LLM client: the OpenAI SDK pointed at OpenRouter, JSON-only and deterministic,
with bounded retry/backoff. Rate limits (429), transient connection errors and 5xx
are retried with exponential backoff; insufficient credit (402) fails fast because
retrying cannot help. Token usage is accumulated for cost tracking.

``LLMClient`` is a Protocol so the orchestration depends on an interface, letting
tests and the offline eval inject a mock with no network and no SDK requirement.
"""
from __future__ import annotations

import time
from typing import Protocol

from .config import Settings


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> str:
        """Return the model's raw JSON string response."""
        ...


class OpenRouterClient:
    """Concrete client. Imports the OpenAI SDK lazily so offline/mock paths never
    require the dependency or a connection."""

    def __init__(self, settings: Settings) -> None:
        if not settings.has_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set; cannot create a live client.")
        from openai import OpenAI  # lazy import - keeps mock/offline paths SDK-free

        self._settings = settings
        self._client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=settings.request_timeout,
            max_retries=0,  # we own the backoff so 429/402 can be handled explicitly
        )
        self.total_tokens = 0

    def complete_json(self, system: str, user: str) -> str:
        import openai  # lazy

        delay = 1.0
        last_error: Exception | None = None
        for _ in range(self._settings.max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.model,
                    temperature=self._settings.temperature,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                if response.usage is not None:
                    self.total_tokens += response.usage.total_tokens or 0
                return response.choices[0].message.content or ""
            except openai.RateLimitError as exc:  # 429
                last_error = exc
                time.sleep(delay)
                delay *= 2
            except openai.APIStatusError as exc:
                if exc.status_code == 402:  # insufficient credits - retrying won't help
                    raise RuntimeError("OpenRouter returned 402 (insufficient credits).") from exc
                if exc.status_code and exc.status_code >= 500:  # transient server-side
                    last_error = exc
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                last_error = exc
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(
            f"LLM call failed after {self._settings.max_retries} attempts"
        ) from last_error
