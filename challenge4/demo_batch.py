# Python 3.12
r"""Live BATCH demo (Challenge 4).

Classifies every line of a samples file against the REAL OpenRouter endpoint, then
prints a table and a summary. Makes real network calls (consumes credits / rate
limit). Per-sample failures (e.g. free-tier 429) are caught so a single bad call does
not abort the whole batch.

Run:
    .\.venv\Scripts\python.exe challenge4\demo_batch.py
    .\.venv\Scripts\python.exe challenge4\demo_batch.py --file challenge4\samples.txt
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # put challenge4/ on path

from classifier.classify import Classifier  # noqa: E402
from classifier.config import load_settings, load_taxonomy  # noqa: E402
from classifier.llm_client import OpenRouterClient  # noqa: E402

_DEFAULT_FILE = Path(__file__).resolve().parent / "samples.txt"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description="Live batch classification demo.")
    parser.add_argument("--file", default=str(_DEFAULT_FILE), help="One sample per line.")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass

    settings = load_settings()
    if not settings.has_api_key:
        print("OPENROUTER_API_KEY not set. See challenge4/.env.example.", file=sys.stderr)
        return 2

    samples = [
        line.strip()
        for line in Path(args.file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not samples:
        print(f"No samples found in {args.file}", file=sys.stderr)
        return 2

    taxonomy = load_taxonomy()
    client = OpenRouterClient(settings)
    classifier = Classifier(client, settings, taxonomy)

    print(f"Classifying {len(samples)} samples live against model={settings.model}\n")
    header = f"{'#':>2}  {'SENSITIVITY':<12} {'CATEGORY':<11} {'RISK':>4} {'REVIEW':>6} {'PII':>3}  SAMPLE"
    print(header)
    print("-" * len(header))

    by_level: Counter[str] = Counter()
    total_pii = needs_review = failures = 0
    for i, text in enumerate(samples, 1):
        try:
            r = classifier.classify(text)
        except Exception as exc:  # rate limit / transient - keep the batch going
            failures += 1
            print(f"{i:>2}  {'(failed)':<12} {'-':<11} {'-':>4} {'-':>6} {'-':>3}  "
                  f"{_truncate(text, 38)}  [{type(exc).__name__}]")
            continue
        by_level[r.sensitivity] += 1
        needs_review += r.needs_review
        pii = sum(r.redactions.values())
        total_pii += pii
        print(f"{i:>2}  {r.sensitivity:<12} {r.category:<11} {r.risk_score:>4} "
              f"{str(r.needs_review):>6} {pii:>3}  {_truncate(text, 45)}")

    spread = ", ".join(f"{lvl}={by_level.get(lvl, 0)}" for lvl in taxonomy.levels)
    print("\nSummary")
    print(f"  samples        : {len(samples)}")
    print(f"  by sensitivity : {spread}")
    print(f"  PII redacted   : {total_pii} items (kept from the LLM)")
    print(f"  needs_review   : {needs_review}")
    print(f"  failed calls   : {failures}")
    print(f"  tokens used    : {client.total_tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
