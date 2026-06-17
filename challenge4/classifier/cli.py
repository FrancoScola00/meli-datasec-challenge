# Python 3.12
"""CLI for the data-classification engine.

Reads one sample (--text), a batch file (--file, one sample per line), or stdin,
and prints one JSON ClassificationResult per line. Run it via the top-level entry:
    python challenge4/classify_cli.py --text "email me at a@b.com"
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .batch import classify_batch
from .classify import Classifier
from .config import load_settings, load_taxonomy
from .llm_client import OpenRouterClient


def _read_inputs(args: argparse.Namespace) -> list[str]:
    if args.text is not None:
        return [args.text]
    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    return [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify text sensitivity with PII redaction.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="A single text sample to classify.")
    source.add_argument("--file", help="Path to a file with one sample per line.")
    parser.add_argument("--taxonomy", help="Path to a taxonomy YAML (defaults to challenge4/taxonomy.yaml).")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass

    settings = load_settings()
    if not settings.has_api_key:
        print("ERROR: OPENROUTER_API_KEY is not set. See challenge4/.env.example.", file=sys.stderr)
        return 2

    taxonomy = load_taxonomy(args.taxonomy)
    texts = _read_inputs(args)
    if not texts:
        print("ERROR: no input (use --text, --file, or stdin).", file=sys.stderr)
        return 2

    client = OpenRouterClient(settings)
    classifier = Classifier(client, settings, taxonomy)
    for result in classify_batch(classifier, texts, max_workers=args.max_workers):
        print(result.model_dump_json())
    if args.verbose:
        print(f"# tokens used: {client.total_tokens}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
