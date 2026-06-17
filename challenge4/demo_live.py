# Python 3.12
r"""Live demo against a REAL OpenRouter endpoint (Challenge 4).

This script makes a real network call and consumes credits. It is intentionally
separate from the test suite, which never touches the network.

Runbook:
  1. Copy the env template and add your key:
       Copy-Item challenge4/.env.example challenge4/.env   # then edit challenge4/.env
     or set the variable in your shell:
       $env:OPENROUTER_API_KEY = "sk-or-v1-..."
  2. Run:
       .\.venv\Scripts\python.exe challenge4\demo_live.py --text "Email me at a@b.com"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # put challenge4/ on path

from classifier.classify import Classifier  # noqa: E402
from classifier.config import load_settings, load_taxonomy  # noqa: E402
from classifier.llm_client import OpenRouterClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Live OpenRouter classification demo.")
    parser.add_argument(
        "--text",
        default="Please email me at jane.doe@example.com or call 11-5555-1234",
        help="Text sample to classify.",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass

    settings = load_settings()
    if not settings.has_api_key:
        print(
            "OPENROUTER_API_KEY not set. Copy challenge4/.env.example to challenge4/.env "
            "and add your key, or set the env var.",
            file=sys.stderr,
        )
        return 2

    taxonomy = load_taxonomy()
    client = OpenRouterClient(settings)
    classifier = Classifier(client, settings, taxonomy)

    print(f"model: {settings.model}")
    print(f"input (pre-redaction, shown locally only): {args.text!r}")
    result = classifier.classify(args.text)
    print(result.model_dump_json(indent=2))
    print(f"# tokens used: {client.total_tokens}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
