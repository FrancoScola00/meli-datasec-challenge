# Python 3.12
"""Leak-prevention data-classification engine (Challenge 4).

Submodules are imported explicitly by callers so that lightweight uses (e.g. the
PII redaction layer) do not pull in the OpenAI SDK. See DESIGN.md for rationale.
"""
__all__ = ["__version__"]
__version__ = "0.1.0"
