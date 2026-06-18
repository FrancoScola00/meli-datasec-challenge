# Python 3.12
"""Tests for Challenge 4 settings loaded from the environment.

The environment is untrusted configuration, so ``load_settings`` validates the
numeric settings and fails loudly on out-of-range values rather than silently
disabling a safety control (e.g. a confidence threshold outside [0, 1]).
"""
import pytest

from classifier.config import load_settings

# Env vars that load_settings() reads, so each test starts from a clean slate.
_ENV_VARS = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "CLASSIFIER_MODEL",
    "CLASSIFIER_TEMPERATURE",
    "CLASSIFIER_CONFIDENCE_THRESHOLD",
    "CLASSIFIER_TIMEOUT",
    "CLASSIFIER_MAX_RETRIES",
)


@pytest.fixture
def clean_env(monkeypatch):
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_are_loaded_and_valid(clean_env):
    settings = load_settings()
    assert settings.temperature == 0.0
    assert settings.confidence_threshold == 0.55
    assert settings.request_timeout == 30.0
    assert settings.max_retries == 4
    assert settings.has_api_key is False  # no key in a clean env


def test_valid_overrides_are_respected(clean_env):
    clean_env.setenv("CLASSIFIER_CONFIDENCE_THRESHOLD", "0.9")
    clean_env.setenv("CLASSIFIER_MAX_RETRIES", "2")
    settings = load_settings()
    assert settings.confidence_threshold == 0.9
    assert settings.max_retries == 2


@pytest.mark.parametrize(
    "name, value",
    [
        ("CLASSIFIER_CONFIDENCE_THRESHOLD", "2"),
        ("CLASSIFIER_CONFIDENCE_THRESHOLD", "-0.1"),
        ("CLASSIFIER_TEMPERATURE", "-1"),
        ("CLASSIFIER_TIMEOUT", "0"),
        ("CLASSIFIER_MAX_RETRIES", "0"),
    ],
)
def test_out_of_range_values_raise(clean_env, name, value):
    clean_env.setenv(name, value)
    with pytest.raises(ValueError):
        load_settings()
