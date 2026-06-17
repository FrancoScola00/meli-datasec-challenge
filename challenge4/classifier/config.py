# Python 3.12
"""Configuration: the sensitivity taxonomy (from YAML) and runtime settings (from
environment variables). Nothing secret is hardcoded; the API key is read from the
environment only."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_TAXONOMY = Path(__file__).resolve().parent.parent / "taxonomy.yaml"


@dataclass(frozen=True)
class Taxonomy:
    levels: list[str]
    categories: list[str]
    level_descriptions: dict[str, str] = field(default_factory=dict)

    def is_valid_level(self, value: str) -> bool:
        return value in self.levels

    def is_valid_category(self, value: str) -> bool:
        return value in self.categories

    @property
    def most_sensitive(self) -> str:
        """Last level by convention (taxonomy is ordered least -> most sensitive)."""
        return self.levels[-1]


def load_taxonomy(path: str | Path | None = None) -> Taxonomy:
    source = Path(path) if path else _DEFAULT_TAXONOMY
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    levels = [entry["name"] for entry in data["sensitivity_levels"]]
    descriptions = {entry["name"]: entry.get("description", "") for entry in data["sensitivity_levels"]}
    return Taxonomy(levels=levels, categories=list(data["categories"]), level_descriptions=descriptions)


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str
    model: str
    temperature: float
    confidence_threshold: float
    request_timeout: float
    max_retries: int

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def load_settings() -> Settings:
    """Build settings from the environment, with safe defaults for everything but
    the secret. Model defaults to a cheap JSON-reliable model; override via env."""
    return Settings(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.environ.get("CLASSIFIER_MODEL", "openai/gpt-4o-mini"),
        temperature=float(os.environ.get("CLASSIFIER_TEMPERATURE", "0")),
        confidence_threshold=float(os.environ.get("CLASSIFIER_CONFIDENCE_THRESHOLD", "0.55")),
        request_timeout=float(os.environ.get("CLASSIFIER_TIMEOUT", "30")),
        max_retries=int(os.environ.get("CLASSIFIER_MAX_RETRIES", "4")),
    )
