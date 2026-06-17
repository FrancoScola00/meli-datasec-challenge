# Python 3.12
"""Classification orchestration.

Pipeline per sample: redact PII -> build delimited prompt -> call LLM -> validate
against schema + taxonomy -> one bounded repair attempt -> abstain (needs_review)
or fail closed. The original text is never logged or sent; only redacted text is.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from .config import Settings, Taxonomy
from .llm_client import LLMClient
from .models import Classification, ClassificationResult
from .prompts import build_repair_prompt, build_system_prompt, build_user_prompt
from .redaction import redact

logger = logging.getLogger("classifier")


class Classifier:
    """Stateless orchestrator. The LLM client is injected (constructor injection)
    so it can be mocked in tests and swapped for the offline eval."""

    def __init__(self, client: LLMClient, settings: Settings, taxonomy: Taxonomy) -> None:
        self._client = client
        self._settings = settings
        self._taxonomy = taxonomy
        self._system = build_system_prompt(taxonomy)

    def classify(self, text: str) -> ClassificationResult:
        redacted, redactions = redact(text)
        # Log only the redacted summary, never the raw sample.
        logger.info("classifying sample (redactions=%s, chars=%d)", redactions, len(redacted))
        user = build_user_prompt(redacted)

        content = self._client.complete_json(self._system, user)
        classification, error = self._validate(content)

        if classification is None:
            # One bounded repair attempt: feed the schema error back as data.
            repair_user = f"{user}\n\n{build_repair_prompt(error or 'invalid JSON')}"
            content = self._client.complete_json(self._system, repair_user)
            classification, error = self._validate(content)

        if classification is None:
            # Fail closed: an unverifiable label defaults to the most sensitive
            # level and is flagged for human review (never silently under-protected).
            return ClassificationResult(
                sensitivity=self._taxonomy.most_sensitive,
                category="OTHER",
                risk_score=100,
                confidence=0.0,
                rationale="Could not obtain a valid classification; flagged for review.",
                needs_review=True,
                redactions=redactions,
                model=self._settings.model,
                error=error,
            )

        return ClassificationResult(
            sensitivity=classification.sensitivity,
            category=classification.category,
            risk_score=classification.risk_score,
            confidence=classification.confidence,
            rationale=classification.rationale,
            needs_review=classification.confidence < self._settings.confidence_threshold,
            redactions=redactions,
            model=self._settings.model,
        )

    def _validate(self, content: str) -> tuple[Classification | None, str | None]:
        """Parse JSON, validate the schema, then check taxonomy membership."""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            return None, f"invalid JSON: {exc}"
        try:
            classification = Classification.model_validate(data)
        except ValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            return None, f"schema error: {first.get('loc', '')} {first.get('msg', exc)}"
        if not self._taxonomy.is_valid_level(classification.sensitivity):
            return None, f"sensitivity '{classification.sensitivity}' not in taxonomy"
        if not self._taxonomy.is_valid_category(classification.category):
            return None, f"category '{classification.category}' not in taxonomy"
        return classification, None
