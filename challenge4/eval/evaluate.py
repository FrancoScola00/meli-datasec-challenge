# Python 3.12
"""Offline evaluation harness.

Runs the classifier over a labelled golden set using RECORDED LLM responses (no
network), then reports per-class precision/recall and overall accuracy. Being
fully offline and deterministic, it is safe to run in CI. Evaluating against
recorded responses isolates the engine's behaviour from model nondeterminism;
live drift is a separate concern (see DESIGN.md).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))  # put challenge4/ on path so `classifier` imports

from classifier.classify import Classifier  # noqa: E402
from classifier.config import Settings, load_taxonomy  # noqa: E402


class _RecordedClient:
    """Returns one pre-recorded JSON response, ignoring the prompt (offline)."""

    def __init__(self, response_json: str) -> None:
        self._response = response_json

    def complete_json(self, system: str, user: str) -> str:
        return self._response


def _eval_settings() -> Settings:
    return Settings(
        api_key=None,
        base_url="",
        model="recorded",
        temperature=0.0,
        confidence_threshold=0.55,
        request_timeout=30,
        max_retries=1,
    )


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(golden_path: Path | None = None, fixtures_path: Path | None = None) -> dict:
    golden = _load_jsonl(golden_path or _HERE / "golden_set.jsonl")
    fixtures = {
        row["id"]: row["response"]
        for row in _load_jsonl(fixtures_path or _HERE / "fixtures" / "responses.jsonl")
    }
    taxonomy = load_taxonomy()
    settings = _eval_settings()

    per_class: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    correct = 0
    for item in golden:
        canned = json.dumps(fixtures[item["id"]])
        classifier = Classifier(_RecordedClient(canned), settings, taxonomy)
        predicted = classifier.classify(item["text"]).sensitivity
        expected = item["sensitivity"]
        if predicted == expected:
            correct += 1
            per_class[expected]["tp"] += 1
        else:
            per_class[predicted]["fp"] += 1
            per_class[expected]["fn"] += 1

    classes: dict[str, dict] = {}
    for label, counts in per_class.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        classes[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "support": tp + fn,
        }
    return {"n": len(golden), "accuracy": round(correct / len(golden), 3), "per_class": classes}


def main() -> int:
    print(json.dumps(evaluate(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
