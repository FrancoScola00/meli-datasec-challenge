# Python 3.12
"""Pydantic schemas for structured, validated classifier output."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Classification(BaseModel):
    """The structured label the LLM must return (shape-validated by pydantic).

    ``extra="forbid"`` rejects hallucinated extra keys. Membership of
    ``sensitivity``/``category`` in the *configured* taxonomy is checked by the
    orchestration layer (classify.py) because the taxonomy is runtime-configurable.
    """

    model_config = ConfigDict(extra="forbid")

    sensitivity: str
    category: str
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class ClassificationResult(BaseModel):
    """Final result returned to callers and the CLI.

    Deliberately carries NO raw input and NO PII - only the label, a redaction
    summary (counts by type), the model id, and an optional error note.
    """

    sensitivity: str
    category: str
    risk_score: int
    confidence: float
    rationale: str
    needs_review: bool
    redactions: dict[str, int] = Field(default_factory=dict)
    model: str
    error: str | None = None
