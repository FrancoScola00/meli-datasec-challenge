# Python 3.12
"""Batch classification with bounded concurrency.

Rate-limit handling and backoff live in the LLM client; this layer only caps
parallelism and preserves input order. Threads are appropriate because the OpenAI
SDK call is I/O-bound and releases the GIL while waiting on the network.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .classify import Classifier
from .models import ClassificationResult


def classify_batch(
    classifier: Classifier, texts: list[str], max_workers: int = 4
) -> list[ClassificationResult]:
    if not texts:
        return []
    workers = max(1, min(max_workers, len(texts)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(classifier.classify, texts))  # map preserves order
